import logging
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from pydantic import BaseModel
from contextlib import contextmanager

from ..models.database import get_db
from ..services.analyzer_manager import analyzer_manager
from ..services.audio_analysis_service import audio_analysis_service
from src.playlist_app.core.analysis_config import analysis_config_loader

logger = logging.getLogger(__name__)

# Function for multiprocessing (must be at module level)
def analyze_single_file_mp(file_path, include_tensorflow=False, force_reanalyze=False):
    """Analyze a single file for multiprocessing"""
    try:
        # Import here to avoid issues with multiprocessing
        from src.playlist_app.services.audio_analysis_service import AudioAnalysisService
        from src.playlist_app.models.database import create_engine, sessionmaker, Session
        import os
        
        # Create a new database engine for this worker process
        DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://playlist_user:playlist_password@localhost:5432/playlist_db")
        
        # Create isolated engine for this worker process
        worker_engine = create_engine(
            DATABASE_URL,
            # Connection pool settings for worker processes
            pool_size=5,  # Smaller pool for individual workers
            max_overflow=10,  # Allow some overflow
            pool_timeout=30,  # Timeout for getting connection
            pool_recycle=1800,  # Recycle connections every 30 minutes
            pool_pre_ping=True,  # Verify connections before use
            # Transaction isolation
            isolation_level="READ_COMMITTED",
            # Connection settings
            connect_args={
                "connect_timeout": 10,
                "application_name": f"playlist_app_worker_{os.getpid()}"
            }
        )
        
        # Create session factory for this worker
        WorkerSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=worker_engine)
        
        # Create a new service instance with worker-specific session management
        class WorkerAudioAnalysisService(AudioAnalysisService):
            @contextmanager
            def _get_db_session(self):
                """Context manager for database sessions with proper error handling"""
                db = WorkerSessionLocal()
                try:
                    yield db
                except Exception:
                    db.rollback()
                    raise
                finally:
                    db.close()
        
        # Create a new service instance for each process
        audio_service = WorkerAudioAnalysisService()
        result = audio_service.analyze_file(file_path, include_tensorflow, force_reanalyze=force_reanalyze)
        
        # Clean up the engine
        worker_engine.dispose()
        
        return {"file_path": file_path, "status": "success", "result": result}
    except Exception as e:
        logger.error(f"Failed to analyze {file_path}: {e}")
        return {"file_path": file_path, "status": "failed", "error": str(e)}

router = APIRouter(prefix="/api/analyzer", tags=["analyzer"])

@router.get("/status")
async def get_analyzer_status():
    """Get analyzer service status"""
    try:
        # Check if essential services are available
        from ..services.audio_analysis_service import audio_analysis_service
        from ..core.analysis_config import analysis_config_loader
        
        # Check if TensorFlow is available
        try:
            import tensorflow as tf
            tensorflow_available = True
            tensorflow_version = tf.__version__
        except ImportError:
            tensorflow_available = False
            tensorflow_version = None
        
        # Check if Essentia is available
        try:
            import essentia
            essentia_available = True
            essentia_version = essentia.__version__
        except ImportError:
            essentia_available = False
            essentia_version = None
        
        # Check if FAISS is available
        try:
            import faiss
            faiss_available = True
            faiss_version = faiss.__version__
        except ImportError:
            faiss_available = False
            faiss_version = None
        
        # Get analysis configuration
        analysis_config = analysis_config_loader.get_config()
        
        return {
            "status": "operational",
            "services": {
                "essentia": {
                    "available": essentia_available,
                    "version": essentia_version
                },
                "tensorflow": {
                    "available": tensorflow_available,
                    "version": tensorflow_version,
                    "enabled": analysis_config.algorithms.enable_tensorflow
                },
                "faiss": {
                    "available": faiss_available,
                    "version": faiss_version,
                    "enabled": analysis_config.algorithms.enable_faiss
                }
            },
            "configuration": {
                "tensorflow_enabled": analysis_config.algorithms.enable_tensorflow,
                "faiss_enabled": analysis_config.algorithms.enable_faiss,
                "max_workers": analysis_config.parallel_processing.max_workers,
                "batch_size": analysis_config.optimization.batch_size
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "service": "analyzer",
            "error": str(e)
        }

class AnalyzeFileRequest(BaseModel):
    file_path: str
    include_tensorflow: bool = True
    force_reanalyze: bool = False

class AnalyzeFilesRequest(BaseModel):
    file_paths: List[str]
    include_tensorflow: bool = True

@router.get("/categorize")
async def categorize_files(db: Session = Depends(get_db)):
    """Categorize files by length"""
    try:
        categories = analyzer_manager.categorize_files_by_length(db, include_analyzed=False)
        return {
            "status": "success",
            "categories": categories,
            "total_files": sum(len(files) for files in categories.values())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Categorization failed: {str(e)}")

@router.post("/analyze-batches")
async def analyze_batches(
    db: Session = Depends(get_db),
    include_tensorflow: Optional[bool] = None,
    max_workers: Optional[int] = None,
    max_files: Optional[int] = None
):
    """Process all batches automatically using threading for parallel processing"""
    try:
        # Get configuration
        config = analysis_config_loader.get_config()
        
        # Use configuration values for TensorFlow and FAISS if not explicitly provided
        if include_tensorflow is None:
            include_tensorflow = config.algorithms.enable_tensorflow
        
        # Use config value if max_workers not provided
        if max_workers is None:
            max_workers = config.parallel_processing.max_workers
        
        # Get all files that need analysis
        from sqlalchemy import text
        result = db.execute(text("SELECT file_path FROM files WHERE is_analyzed = false"))
        all_files = [row[0] for row in result]
        
        # Limit files if max_files is specified
        if max_files and max_files > 0:
            all_files = all_files[:max_files]
            logger.info(f"Limited to {max_files} files for analysis")
        
        if not all_files:
            return {"message": "No files need analysis", "total_files": 0}
        
        logger.info(f"Analyzing {len(all_files)} files with {max_workers} workers (TensorFlow: {include_tensorflow}, FAISS: {config.algorithms.enable_faiss})")
        
        # Use multiprocessing for parallel analysis (CPU-bound tasks)
        import multiprocessing as mp
        from concurrent.futures import ProcessPoolExecutor, as_completed
        import time
        import os
        
        # Use the module-level function for multiprocessing
        from functools import partial
        analyze_func = partial(analyze_single_file_mp, include_tensorflow=include_tensorflow, force_reanalyze=False)
        
        # Process files in parallel using multiprocessing
        start_time = time.time()
        results = []
        
        # Use ProcessPoolExecutor for CPU-bound tasks
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all analysis tasks
            future_to_file = {executor.submit(analyze_func, file_path): file_path 
                            for file_path in all_files}
            
            # Collect results as they complete
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.info(f"Completed analysis for {file_path}")
                except Exception as e:
                    logger.error(f"Exception for {file_path}: {e}")
                    results.append({"file_path": file_path, "status": "failed", "error": str(e)})
        
        # Calculate statistics
        successful = [r for r in results if r.get("status") != "failed"]
        failed = [r for r in results if r.get("status") == "failed"]
        
        total_time = time.time() - start_time
        
        return {
            "status": "success",
            "results": {
                "total_files": len(all_files),
                "successful": len(successful),
                "failed": len(failed),
                "processing_time": total_time,
                "files_per_second": len(all_files) / total_time if total_time > 0 else 0,
                "max_workers": max_workers,
                "tensorflow_enabled": include_tensorflow,
                "faiss_enabled": config.algorithms.enable_faiss,
                "message": f"Batch analysis completed: {len(successful)} successful, {len(failed)} failed in {total_time:.2f}s"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze batches: {str(e)}")



@router.post("/analyze-category/{category}")
async def analyze_category(
    category: str,
    db: Session = Depends(get_db),
    include_tensorflow: bool = True
):
    """Analyze all files in a specific category using existing batches"""
    try:
        result = analyzer_manager.analyze_batches_by_category(
            db, 
            category, 
            include_tensorflow=include_tensorflow
        )
        
        return {
            "status": "success",
            "result": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Category analysis failed: {str(e)}")

@router.get("/length-stats")
async def get_length_statistics(db: Session = Depends(get_db)):
    """Get length statistics"""
    try:
        stats = analyzer_manager.get_length_statistics(db)
        return {
            "status": "success",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get length statistics: {str(e)}")

@router.get("/categories")
async def get_length_categories():
    """Get available length categories"""
    try:
        categories = analyzer_manager.length_categories
        return {
            "status": "success",
            "categories": categories
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get categories: {str(e)}")

@router.post("/analyze-file")
async def analyze_file(
    request: AnalyzeFileRequest
):
    """Analyze a single audio file using Essentia"""
    try:
        result = audio_analysis_service.analyze_file(
            request.file_path, 
            request.include_tensorflow,
            request.force_reanalyze
        )
        return {
            "status": "success",
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.post("/analyze-files")
async def analyze_files(
    request: AnalyzeFilesRequest,
    background_tasks: BackgroundTasks
):
    """Analyze multiple audio files using Essentia"""
    try:
        result = audio_analysis_service.analyze_files_batch(
            request.file_paths, 
            request.include_tensorflow
        )
        return {
            "status": "success",
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")

@router.get("/analysis/{file_path:path}")
async def get_analysis(file_path: str):
    """Get analysis results for a file"""
    try:
        result = audio_analysis_service.get_analysis(file_path)
        if not result:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        return {
            "status": "success",
            "result": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analysis: {str(e)}")

@router.get("/analysis-summary/{file_path:path}")
async def get_analysis_summary(file_path: str):
    """Get analysis summary for a file"""
    try:
        result = audio_analysis_service.get_analysis_summary(file_path)
        if not result:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        return {
            "status": "success",
            "result": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analysis summary: {str(e)}")

@router.get("/unanalyzed-files")
async def get_unanalyzed_files(
    limit: Optional[int] = Query(None, description="Maximum number of files to return")
):
    """Get list of files that haven't been analyzed yet"""
    try:
        files = audio_analysis_service.get_unanalyzed_files(limit)
        return {
            "status": "success",
            "files": files,
            "count": len(files)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get unanalyzed files: {str(e)}")

@router.get("/statistics")
async def get_analysis_statistics():
    """Get analysis statistics"""
    try:
        stats = audio_analysis_service.get_analysis_statistics()
        return {
            "status": "success",
            "statistics": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")

@router.post("/force-reanalyze")
async def force_reanalyze(
    db: Session = Depends(get_db),
    include_tensorflow: bool = False,
    max_workers: Optional[int] = None,
    max_files: Optional[int] = None
):
    """Force re-analyze all files with multiprocessing for parallel processing"""
    try:
        # Get configuration
        config = analysis_config_loader.get_config()
        
        # Use config value if max_workers not provided
        if max_workers is None:
            max_workers = config.parallel_processing.max_workers
        
        # Mark all files for re-analysis
        from sqlalchemy import text
        db.execute(text("UPDATE files SET is_analyzed = false"))
        db.commit()
        
        # Get all files
        result = db.execute(text("SELECT file_path FROM files"))
        all_files = [row[0] for row in result]
        
        # Limit files if max_files is specified
        if max_files and max_files > 0:
            all_files = all_files[:max_files]
            logger.info(f"Limited to {max_files} files for force re-analyze")
        
        logger.info(f"Force re-analyzing {len(all_files)} files with {max_workers} workers")
        
        # Use multiprocessing for parallel analysis (CPU-bound tasks)
        import multiprocessing as mp
        from concurrent.futures import ProcessPoolExecutor, as_completed
        import time
        import os
        
        # Use the module-level function for multiprocessing
        from functools import partial
        analyze_func = partial(analyze_single_file_mp, include_tensorflow=include_tensorflow, force_reanalyze=True)
        
        # Process files in parallel using multiprocessing
        start_time = time.time()
        results = []
        
        # Use ProcessPoolExecutor for CPU-bound tasks
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all analysis tasks
            future_to_file = {executor.submit(analyze_func, file_path): file_path 
                            for file_path in all_files}
            
            # Collect results as they complete
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.info(f"Completed analysis for {file_path}")
                except Exception as e:
                    logger.error(f"Exception for {file_path}: {e}")
                    results.append({"file_path": file_path, "status": "failed", "error": str(e)})
        
        # Calculate statistics
        successful = [r for r in results if r.get("status") != "failed"]
        failed = [r for r in results if r.get("status") == "failed"]
        
        total_time = time.time() - start_time
        
        return {
            "status": "success",
            "results": {
                "total_files": len(all_files),
                "successful": len(successful),
                "failed": len(failed),
                "processing_time": total_time,
                "files_per_second": len(all_files) / total_time if total_time > 0 else 0,
                "max_workers": max_workers,
                "message": f"Force re-analysis completed: {len(successful)} successful, {len(failed)} failed in {total_time:.2f}s"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Force re-analysis failed: {str(e)}")

@router.delete("/analysis/{file_path:path}")
async def delete_analysis(file_path: str):
    """Delete analysis results for a file"""
    try:
        success = audio_analysis_service.delete_analysis(file_path)
        if not success:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        return {
            "status": "success",
            "message": "Analysis deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete analysis: {str(e)}")

@router.get("/config")
async def get_analyzer_config():
    """Get current analyzer configuration"""
    try:
        config = analysis_config_loader.get_config()
        return {
            "status": "success",
            "config": {
                "performance": {
                    "parallel_processing": {
                        "max_workers": config.parallel_processing.max_workers,
                        "chunk_size": config.parallel_processing.chunk_size,
                        "timeout_per_file": config.parallel_processing.timeout_per_file,
                        "memory_limit_mb": config.parallel_processing.memory_limit_mb
                    },
                    "caching": {
                        "enable_cache": config.caching.enable_cache,
                        "cache_duration_hours": config.caching.cache_duration_hours,
                        "max_cache_size_mb": config.caching.max_cache_size_mb
                    },
                    "optimization": {
                        "use_ffmpeg_streaming": config.optimization.use_ffmpeg_streaming,
                        "smart_segmentation": config.optimization.smart_segmentation,
                        "skip_existing_analysis": config.optimization.skip_existing_analysis,
                        "batch_size": config.optimization.batch_size
                    }
                },
                "essentia": {
                    "audio_processing": {
                        "sample_rate": config.audio_processing.sample_rate,
                        "channels": config.audio_processing.channels,
                        "frame_size": config.audio_processing.frame_size,
                        "hop_size": config.audio_processing.hop_size,
                        "window_type": config.audio_processing.window_type,
                        "zero_padding": config.audio_processing.zero_padding
                    },
                    "spectral_analysis": {
                        "min_frequency": config.spectral_analysis.min_frequency,
                        "max_frequency": config.spectral_analysis.max_frequency,
                        "n_mels": config.spectral_analysis.n_mels,
                        "n_mfcc": config.spectral_analysis.n_mfcc,
                        "n_spectral_peaks": config.spectral_analysis.n_spectral_peaks,
                        "silence_threshold": config.spectral_analysis.silence_threshold
                    },
                    "track_analysis": {
                        "min_track_length": config.track_analysis.min_track_length,
                        "max_track_length": config.track_analysis.max_track_length,
                        "chunk_duration": config.track_analysis.chunk_duration,
                        "overlap_ratio": config.track_analysis.overlap_ratio
                    },
                    "algorithms": {
                        "enable_tensorflow": config.algorithms.enable_tensorflow,
                        "enable_complex_rhythm": config.algorithms.enable_complex_rhythm,
                        "enable_complex_harmonic": config.algorithms.enable_complex_harmonic,
                        "enable_beat_tracking": config.algorithms.enable_beat_tracking,
                        "enable_tempo_tap": config.algorithms.enable_tempo_tap,
                        "enable_rhythm_extractor": config.algorithms.enable_rhythm_extractor,
                        "enable_pitch_analysis": config.algorithms.enable_pitch_analysis,
                        "enable_chord_detection": config.algorithms.enable_chord_detection
                    }
                },
                "output": {
                    "store_individual_columns": config.output.store_individual_columns,
                    "store_complete_json": config.output.store_complete_json,
                    "compress_json": config.output.compress_json,
                    "include_segment_details": config.output.include_segment_details,
                    "include_processing_metadata": config.output.include_processing_metadata
                },
                "quality": {
                    "min_confidence_threshold": config.quality.min_confidence_threshold,
                    "fallback_values": config.quality.fallback_values,
                    "continue_on_error": config.quality.continue_on_error,
                    "log_errors": config.quality.log_errors,
                    "retry_failed": config.quality.retry_failed,
                    "max_retries": config.quality.max_retries
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analyzer config: {str(e)}")

@router.post("/config/reload")
async def reload_analysis_config():
    """Reload analysis configuration from file"""
    try:
        analysis_config_loader.reload_config()
        return {
            "status": "success",
            "message": "Configuration reloaded successfully",
            "config": analysis_config_loader.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reload configuration: {str(e)}")

@router.get("/config/performance")
async def get_performance_config():
    """Get performance-related configuration"""
    try:
        config = analysis_config_loader.get_config()
        return {
            "status": "success",
            "performance": {
                "parallel_processing": config.parallel_processing.__dict__,
                "caching": config.caching.__dict__,
                "optimization": config.optimization.__dict__
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance config: {str(e)}")

@router.get("/config/essentia")
async def get_essentia_config():
    """Get Essentia-related configuration"""
    try:
        config = analysis_config_loader.get_config()
        return {
            "status": "success",
            "essentia": {
                "audio_processing": config.audio_processing.__dict__,
                "spectral_analysis": config.spectral_analysis.__dict__,
                "track_analysis": config.track_analysis.__dict__,
                "algorithms": config.algorithms.__dict__
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Essentia config: {str(e)}")

# === FAISS Vector Indexing Endpoints ===

@router.post("/faiss/build-index")
async def build_faiss_index(
    include_tensorflow: bool = True,
    force_rebuild: bool = False
):
    """Build FAISS index from analyzed tracks"""
    try:
        result = audio_analysis_service.build_faiss_index(include_tensorflow, force_rebuild)
        return {
            "status": "success",
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build FAISS index: {str(e)}")

@router.post("/faiss/search")
async def search_similar_tracks(
    file_path: str,
    top_n: int = 5
):
    """Search for similar tracks using FAISS index"""
    try:
        similar_tracks = audio_analysis_service.find_similar_tracks(file_path, top_n)
        return {
            "status": "success",
            "query_file": file_path,
            "similar_tracks": similar_tracks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search similar tracks: {str(e)}")

@router.get("/faiss/statistics")
async def get_faiss_statistics():
    """Get FAISS index statistics"""
    try:
        stats = audio_analysis_service.get_faiss_statistics()
        return {
            "status": "success",
            "statistics": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get FAISS statistics: {str(e)}")

@router.post("/faiss/rebuild-index")
async def rebuild_faiss_index(
    include_tensorflow: bool = True
):
    """Force rebuild FAISS index"""
    try:
        result = audio_analysis_service.build_faiss_index(include_tensorflow, force_rebuild=True)
        return {
            "status": "success",
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rebuild FAISS index: {str(e)}")
