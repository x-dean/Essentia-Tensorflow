import logging
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from pydantic import BaseModel
from contextlib import contextmanager

from ..models.database import get_db
from ..services.analyzer_manager import analyzer_manager
from ..services.independent_essentia_service import essentia_service
from ..services.independent_tensorflow_service import tensorflow_service
from ..services.independent_faiss_service import faiss_service
from ..services.analysis_coordinator import analysis_coordinator
from ..core.analysis_config import analysis_config_loader

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analyzer", tags=["analyzer"])

@router.get("/status")
async def get_analyzer_status():
    """Get analyzer service status"""
    try:
        # Check if essential services are available
        try:
            import tensorflow as tf
            tensorflow_available = True
            tensorflow_version = tf.__version__
        except ImportError:
            tensorflow_available = False
            tensorflow_version = None
        
        try:
            import essentia
            essentia_available = True
            essentia_version = essentia.__version__
        except ImportError:
            essentia_available = False
            essentia_version = None
        
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
                    "enabled": True,
                    "version": essentia_version,
                    "description": "Independent Essentia analyzer"
                },
                "tensorflow": {
                    "available": tensorflow_available,
                    "enabled": analysis_config.algorithms.enable_tensorflow,
                    "version": tensorflow_version,
                    "description": "Independent TensorFlow analyzer"
                },
                "faiss": {
                    "available": faiss_available,
                    "enabled": analysis_config.algorithms.enable_faiss,
                    "version": faiss_version,
                    "description": "Independent FAISS analyzer"
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
            "error": str(e)
        }

@router.get("/statistics")
async def get_analysis_statistics():
    """Get analysis statistics"""
    try:
        db = next(get_db())
        stats = analysis_coordinator.get_analysis_stats(db)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/essentia")
async def analyze_essentia(
    max_files: Optional[int] = Query(None, description="Maximum number of files to analyze"),
    force_reanalyze: bool = Query(False, description="Force re-analysis of existing files")
):
    """Analyze files using independent Essentia analyzer"""
    try:
        db = next(get_db())
        result = essentia_service.analyze_pending_files(db, max_files=max_files, force_reanalyze=force_reanalyze)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tensorflow")
async def analyze_tensorflow(
    max_files: Optional[int] = Query(None, description="Maximum number of files to analyze"),
    force_reanalyze: bool = Query(False, description="Force re-analysis of existing files")
):
    """Analyze files using independent TensorFlow analyzer"""
    try:
        db = next(get_db())
        result = tensorflow_service.analyze_pending_files(db, max_files=max_files, force_reanalyze=force_reanalyze)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/faiss")
async def analyze_faiss(
    max_files: Optional[int] = Query(None, description="Maximum number of files to analyze"),
    force_reanalyze: bool = Query(False, description="Force re-analysis of existing files")
):
    """Analyze files using independent FAISS analyzer"""
    try:
        db = next(get_db())
        result = faiss_service.analyze_pending_files(db, max_files=max_files, force_reanalyze=force_reanalyze)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/complete")
async def analyze_complete(
    max_files: Optional[int] = Query(None, description="Maximum number of files to analyze"),
    force_reanalyze: bool = Query(False, description="Force re-analysis of existing files")
):
    """Analyze files using all independent analyzers"""
    try:
        db = next(get_db())
        result = analysis_coordinator.analyze_pending_files(db, max_files=max_files, force_reanalyze=force_reanalyze)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/fix-status")
async def fix_analyzer_status_records():
    """Ensure all files have analyzer status records"""
    try:
        db = next(get_db())
        from ..services.discovery import DiscoveryService
        discovery_service = DiscoveryService(db)
        result = discovery_service.ensure_status_records_exist()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/categorize")
async def categorize_files():
    """Categorize files by length"""
    try:
        db = next(get_db())
        result = analyzer_manager.categorize_files_by_length(db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Legacy endpoints for backward compatibility
@router.post("/two-step/essentia")
async def analyze_essentia_legacy(
    max_files: Optional[int] = Query(None, description="Maximum number of files to analyze"),
    force_reanalyze: bool = Query(False, description="Force re-analysis of existing files")
):
    """Legacy endpoint - redirects to new independent Essentia analyzer"""
    return await analyze_essentia(max_files=max_files, force_reanalyze=force_reanalyze)

@router.post("/analyze")
async def analyze_files_legacy(
    include_tensorflow: bool = Query(True, description="Include TensorFlow analysis"),
    include_faiss: bool = Query(True, description="Include FAISS analysis"),
    max_files: Optional[int] = Query(None, description="Maximum number of files to analyze")
):
    """Legacy endpoint - redirects to complete analysis"""
    return await analyze_complete(max_files=max_files, force_reanalyze=False)

