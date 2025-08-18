import logging
import time
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from contextlib import contextmanager
from datetime import datetime
import json

from ..models.database import File, AudioAnalysis, AudioMetadata, get_db_session, close_db_session, FileStatus
from ..core.logging import get_logger
from .essentia_analyzer import essentia_analyzer, safe_json_serialize
from .tensorflow_analyzer import tensorflow_analyzer
from .faiss_service import faiss_service

logger = logging.getLogger(__name__)

class ModularAnalysisService:
    """
    Modular analysis service that coordinates Essentia, TensorFlow, and FAISS modules.
    
    Each module can be enabled/disabled independently:
    - Essentia: Audio feature extraction
    - TensorFlow: Machine learning classification (MusicNN)
    - FAISS: Vector similarity search
    """
    
    def __init__(self):
        self.essentia_analyzer = essentia_analyzer
        self.tensorflow_analyzer = tensorflow_analyzer
        self.faiss_service = faiss_service
    
    @contextmanager
    def _get_db_session(self):
        """Context manager for database sessions with proper error handling and retry logic"""
        # Get retry settings from configuration
        try:
            from ..core.config_loader import config_loader
            db_config = config_loader.get_database_config()
            retry_settings = db_config.get("retry_settings", {})
            max_retries = retry_settings.get("max_retries", 3)
            retry_delay = retry_settings.get("initial_delay", 1)
            backoff_multiplier = retry_settings.get("backoff_multiplier", 2)
            max_delay = retry_settings.get("max_delay", 30)
        except Exception:
            # Fallback to hardcoded values
            max_retries = 3
            retry_delay = 1
            backoff_multiplier = 2
            max_delay = 30
        
        delay = retry_delay
        for attempt in range(max_retries):
            db = get_db_session()
            try:
                yield db
                break  # Success, exit retry loop
            except Exception as e:
                close_db_session(db)
                
                # Check if it's a connection-related error
                if "server closed the connection" in str(e) or "PGRES_TUPLES_OK" in str(e):
                    if attempt < max_retries - 1:
                        logger.warning(f"Database connection error (attempt {attempt + 1}/{max_retries}): {e}")
                        import time
                        time.sleep(delay)
                        delay = min(delay * backoff_multiplier, max_delay)  # Exponential backoff with cap
                        continue
                    else:
                        logger.error(f"Database connection failed after {max_retries} attempts: {e}")
                        raise
                else:
                    # Non-connection error, don't retry
                    raise
            finally:
                if attempt == max_retries - 1:
                    close_db_session(db)
    
    def get_module_status(self) -> Dict[str, Any]:
        """Get status of all analysis modules"""
        try:
            from ..core.analysis_config import analysis_config_loader
            config = analysis_config_loader.get_config()
            
            return {
                "essentia": {
                    "enabled": True,  # Essentia is always available
                    "available": True,
                    "description": "Audio feature extraction"
                },
                "tensorflow": {
                    "enabled": config.algorithms.enable_tensorflow,
                    "available": self.tensorflow_analyzer.is_available(),
                    "description": "Machine learning classification (MusicNN)"
                },
                "faiss": {
                    "enabled": config.algorithms.enable_faiss,
                    "available": True,  # FAISS availability is checked at runtime
                    "description": "Vector similarity search"
                }
            }
        except Exception as e:
            logger.error(f"Failed to get module status: {e}")
            return {
                "essentia": {"enabled": True, "available": True, "description": "Audio feature extraction"},
                "tensorflow": {"enabled": False, "available": False, "description": "Machine learning classification"},
                "faiss": {"enabled": False, "available": False, "description": "Vector similarity search"}
            }
    
    def analyze_file(self, file_path: str, enable_essentia: bool = True, 
                    enable_tensorflow: bool = False, enable_faiss: bool = False, 
                    force_reanalyze: bool = False) -> Dict[str, Any]:
        """
        Analyze a single audio file using enabled modules.
        
        Args:
            file_path: Path to audio file
            enable_essentia: Whether to run Essentia analysis
            enable_tensorflow: Whether to run TensorFlow analysis
            enable_faiss: Whether to update FAISS index
            force_reanalyze: Whether to force re-analysis even if it exists
            
        Returns:
            Analysis results from all enabled modules
        """
        with self._get_db_session() as db:
            try:
                # Check if file exists in database
                file_record = db.query(File).filter(File.file_path == file_path).first()
                if not file_record:
                    raise ValueError(f"File not found in database: {file_path}")
                
                # Check if analysis already exists
                existing_analysis = db.query(AudioAnalysis).filter(
                    AudioAnalysis.file_id == file_record.id
                ).first()
                
                if existing_analysis and not force_reanalyze:
                    logger.info(f"Analysis already exists for {file_path}, returning existing results")
                    return self._load_existing_analysis(existing_analysis)
                
                # Perform analysis with enabled modules
                results = {
                    "file_path": file_path,
                    "analysis_timestamp": time.time(),
                    "modules_used": []
                }
                
                # Essentia analysis (always available)
                if enable_essentia:
                    try:
                        logger.info(f"Running Essentia analysis for {file_path}")
                        essentia_results = self.essentia_analyzer.analyze_audio_file(file_path)
                        results["essentia"] = essentia_results
                        results["modules_used"].append("essentia")
                        logger.info(f"Essentia analysis completed for {file_path}")
                    except Exception as e:
                        logger.error(f"Essentia analysis failed for {file_path}: {e}")
                        results["essentia"] = {"error": str(e)}
                
                # TensorFlow analysis
                if enable_tensorflow and self.tensorflow_analyzer.is_available():
                    try:
                        logger.info(f"Running TensorFlow analysis for {file_path}")
                        tensorflow_results = self.tensorflow_analyzer.analyze_audio_file(file_path)
                        results["tensorflow"] = tensorflow_results
                        results["modules_used"].append("tensorflow")
                        logger.info(f"TensorFlow analysis completed for {file_path}")
                    except Exception as e:
                        logger.error(f"TensorFlow analysis failed for {file_path}: {e}")
                        results["tensorflow"] = {"error": str(e)}
                elif enable_tensorflow and not self.tensorflow_analyzer.is_available():
                    logger.warning(f"TensorFlow analysis requested but not available for {file_path}")
                    results["tensorflow"] = {"error": "TensorFlow analysis not available"}
                
                # FAISS indexing
                if enable_faiss:
                    try:
                        logger.info(f"Updating FAISS index for {file_path}")
                        # This would typically involve adding the file's features to the FAISS index
                        # For now, we'll just mark it as ready for indexing
                        results["faiss"] = {"status": "ready_for_indexing"}
                        results["modules_used"].append("faiss")
                        logger.info(f"FAISS indexing prepared for {file_path}")
                    except Exception as e:
                        logger.error(f"FAISS indexing failed for {file_path}: {e}")
                        results["faiss"] = {"error": str(e)}
                
                # Store results in database
                self._store_analysis_results(db, file_record, results)
                
                # Update file status
                file_record.has_audio_analysis = True
                file_record.analysis_status = FileStatus.COMPLETED
                db.commit()
                
                logger.info(f"Modular analysis completed for {file_path}")
                return results
                
            except Exception as e:
                db.rollback()
                logger.error(f"Analysis failed for {file_path}: {e}")
                # Return error results instead of raising
                return {
                    "file_path": file_path,
                    "analysis_timestamp": time.time(),
                    "error": str(e),
                    "modules_used": []
                }
    
    def analyze_files_batch(self, file_paths: List[str], enable_essentia: bool = True,
                           enable_tensorflow: bool = False, enable_faiss: bool = False,
                           force_reanalyze: bool = False) -> Dict[str, Any]:
        """
        Analyze multiple files using enabled modules.
        
        Args:
            file_paths: List of file paths to analyze
            enable_essentia: Whether to run Essentia analysis
            enable_tensorflow: Whether to run TensorFlow analysis
            enable_faiss: Whether to update FAISS index
            force_reanalyze: Whether to force re-analysis
            
        Returns:
            Batch analysis results
        """
        results = {
            "total_files": len(file_paths),
            "successful": 0,
            "failed": 0,
            "results": [],
            "modules_used": []
        }
        
        if enable_essentia:
            results["modules_used"].append("essentia")
        if enable_tensorflow:
            results["modules_used"].append("tensorflow")
        if enable_faiss:
            results["modules_used"].append("faiss")
        
        logger.info(f"Starting batch analysis of {len(file_paths)} files with modules: {results['modules_used']}")
        
        for file_path in file_paths:
            try:
                file_result = self.analyze_file(
                    file_path, 
                    enable_essentia=enable_essentia,
                    enable_tensorflow=enable_tensorflow,
                    enable_faiss=enable_faiss,
                    force_reanalyze=force_reanalyze
                )
                results["results"].append({
                    "file_path": file_path,
                    "status": "success",
                    "result": file_result
                })
                results["successful"] += 1
                logger.info(f"Successfully analyzed {file_path}")
                
            except Exception as e:
                logger.error(f"Failed to analyze {file_path}: {e}")
                results["results"].append({
                    "file_path": file_path,
                    "status": "failed",
                    "error": str(e)
                })
                results["failed"] += 1
        
        logger.info(f"Batch analysis completed: {results['successful']} successful, {results['failed']} failed")
        return results
    
    def _load_existing_analysis(self, analysis_record: AudioAnalysis) -> Dict[str, Any]:
        """Load existing analysis results from database"""
        try:
            results = {
                "file_path": analysis_record.file.file_path,
                "analysis_timestamp": analysis_record.created_at.timestamp(),
                "modules_used": []
            }
            
            # Parse stored analysis data
            if analysis_record.analysis_data:
                stored_data = analysis_record.analysis_data
                if isinstance(stored_data, str):
                    import json
                    stored_data = json.loads(stored_data)
                
                # Extract module results
                if "essentia" in stored_data:
                    results["essentia"] = stored_data["essentia"]
                    results["modules_used"].append("essentia")
                
                if "tensorflow" in stored_data:
                    results["tensorflow"] = stored_data["tensorflow"]
                    results["modules_used"].append("tensorflow")
                
                if "faiss" in stored_data:
                    results["faiss"] = stored_data["faiss"]
                    results["modules_used"].append("faiss")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to load existing analysis: {e}")
            return {"error": f"Failed to load existing analysis: {str(e)}"}
    
    def _store_analysis_results(self, db: Session, file_record: File, results: Dict[str, Any]):
        """Store analysis results in database"""
        try:
            # Check if analysis record exists
            analysis_record = db.query(AudioAnalysis).filter(
                AudioAnalysis.file_id == file_record.id
            ).first()
            
            if not analysis_record:
                analysis_record = AudioAnalysis(file_id=file_record.id)
                db.add(analysis_record)
            
            # Extract features from Essentia results
            if "essentia" in results and "error" not in results["essentia"]:
                essentia_data = results["essentia"]
                
                # Basic features
                if "basic_features" in essentia_data:
                    basic = essentia_data["basic_features"]
                    analysis_record.loudness = basic.get("loudness", -999.0)
                    analysis_record.dynamic_complexity = basic.get("dynamic_complexity", -999.0)
                    analysis_record.spectral_complexity = basic.get("spectral_complexity", -999.0)
                
                # Spectral features
                if "spectral_features" in essentia_data:
                    spectral = essentia_data["spectral_features"]
                    analysis_record.spectral_centroid = spectral.get("spectral_centroid", -999.0)
                    analysis_record.spectral_rolloff = spectral.get("spectral_rolloff", -999.0)
                    analysis_record.spectral_bandwidth = spectral.get("spectral_bandwidth", -999.0)
                    analysis_record.spectral_flatness = spectral.get("spectral_flatness", -999.0)
                
                # Rhythm features
                if "rhythm_features" in essentia_data:
                    rhythm = essentia_data["rhythm_features"]
                    analysis_record.estimated_bpm = rhythm.get("bpm", -999.0)
                    analysis_record.rhythm_confidence = rhythm.get("rhythm_confidence", -999.0)
                    analysis_record.beat_confidence = rhythm.get("beat_confidence", -999.0)
                
                # Harmonic features
                if "harmonic_features" in essentia_data:
                    harmonic = essentia_data["harmonic_features"]
                    analysis_record.key = harmonic.get("key", "unknown")
                    analysis_record.scale = harmonic.get("scale", "unknown")
                    analysis_record.key_strength = harmonic.get("key_strength", -999.0)
                    analysis_record.chords = json.dumps(harmonic.get("chords", []))
                    analysis_record.chord_strength = harmonic.get("chord_strength", -999.0)
                
                # MFCC features
                if "mfcc_features" in essentia_data:
                    mfcc = essentia_data["mfcc_features"]
                    analysis_record.mfcc_mean = json.dumps(mfcc.get("mfcc_mean", []))
                    analysis_record.mfcc_std = json.dumps(mfcc.get("mfcc_std", []))
            
            # Store TensorFlow results
            if "tensorflow" in results and "error" not in results["tensorflow"]:
                analysis_record.tensorflow_features = json.dumps(results["tensorflow"])
            
            # Store complete analysis as JSON
            analysis_record.complete_analysis = json.dumps(results)
            analysis_record.updated_at = datetime.utcnow()
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Failed to store analysis results for {file_record.file_path}: {e}")
            db.rollback()
            raise

# Global instance
modular_analysis_service = ModularAnalysisService()
