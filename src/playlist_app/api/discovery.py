from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Optional
import os

from ..models.database import get_db, create_tables, File, DiscoveryCache, FileStatus
from ..services.discovery import DiscoveryService
from ..core.logging import get_logger

router = APIRouter(prefix="/api/discovery", tags=["discovery"])

def get_discovery_service(db: Session = Depends(get_db)) -> DiscoveryService:
    """Get discovery service instance"""
    from ..core.config import DiscoveryConfig
    
    return DiscoveryService(
        db_session=db,
        search_directories=DiscoveryConfig.SEARCH_DIRECTORIES,
        supported_extensions=DiscoveryConfig.get_supported_extensions()
    )

@router.post("/scan")
async def scan_files(discovery_service: DiscoveryService = Depends(get_discovery_service)):
    """Scan for new files, update database, and extract metadata automatically"""
    try:
        results = discovery_service.discover_files()
        return {
            "status": "success",
            "message": "File discovery and metadata extraction completed",
            "results": {
                "added_count": len(results["added"]),
                "removed_count": len(results["removed"]),
                "unchanged_count": len(results["unchanged"]),
                "added_files": results["added"],
                "removed_files": results["removed"]
            },
            "note": "Metadata is automatically extracted for newly discovered files"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")

@router.get("/files")
async def get_files(
    limit: int = Query(100, ge=1, le=1000, description="Number of files to return"),
    offset: int = Query(0, ge=0, description="Number of files to skip"),
    discovery_service: DiscoveryService = Depends(get_discovery_service)
):
    """Get list of discovered files"""
    try:
        files = discovery_service.get_discovered_files(limit=limit, offset=offset)
        return {
            "status": "success",
            "files": files,
            "count": len(files)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get files: {str(e)}")

@router.get("/files/{file_hash}")
async def get_file_by_hash(
    file_hash: str,
    discovery_service: DiscoveryService = Depends(get_discovery_service)
):
    """Get file by hash"""
    try:
        file = discovery_service.get_file_by_hash(file_hash)
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        return {
            "status": "success",
            "file": file
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get file: {str(e)}")

@router.get("/status")
async def get_discovery_status(discovery_service: DiscoveryService = Depends(get_discovery_service)):
    """Get discovery service status"""
    try:
        db = discovery_service.db
        
        # Get basic stats
        total_files = db.query(File).filter(File.is_active == True).count()
        analyzed_files = db.query(File).filter(File.is_active == True, File.analysis_status == "complete").count()
        
        # Check if discovery directories exist
        from ..core.config import DiscoveryConfig
        existing_dirs = []
        for directory in DiscoveryConfig.SEARCH_DIRECTORIES:
            if os.path.exists(directory):
                existing_dirs.append(directory)
        
        return {
            "status": "operational" if existing_dirs else "warning",
            "service": "discovery",
            "total_files": total_files,
            "analyzed_files": analyzed_files,
            "search_directories": DiscoveryConfig.get_search_directories(),
            "existing_directories": existing_dirs,
            "supported_extensions": DiscoveryConfig.get_supported_extensions()
        }
    except Exception as e:
        return {
            "status": "error",
            "service": "discovery",
            "error": str(e)
        }

@router.get("/stats")
async def get_discovery_stats(discovery_service: DiscoveryService = Depends(get_discovery_service)):
    """Get discovery statistics"""
    try:
        db = discovery_service.db
        
        # Get total files
        total_files = db.query(File).filter(File.is_active == True).count()
        
        # Get analyzed files
        analyzed_files = db.query(File).filter(File.is_active == True, File.analysis_status == "complete").count()
        
        # Get status distribution
        status_counts = db.query(File.status, func.count(File.id)).group_by(File.status).all()
        status_stats = {status.value if status else "unknown": count for status, count in status_counts}
        
        # Get files by extension
        extension_stats = {}
        files = db.query(File).filter(File.is_active == True).all()
        for file in files:
            ext = file.file_extension
            extension_stats[ext] = extension_stats.get(ext, 0) + 1
        
        return {
            "status": "success",
            "stats": {
                "total_files": total_files,
                "analyzed_files": analyzed_files,
                "unanalyzed_files": total_files - analyzed_files,
                "status_distribution": status_stats,
                "extension_distribution": extension_stats
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@router.post("/init")
async def initialize_database():
    """Initialize database tables"""
    try:
        create_tables()
        return {
            "status": "success",
            "message": "Database tables created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database initialization failed: {str(e)}")

@router.post("/re-discover")
async def re_discover_all_files(discovery_service: DiscoveryService = Depends(get_discovery_service)):
    """Re-discover all files (useful for initial setup or after file changes)"""
    try:
        results = discovery_service.re_discover_files()
        return {
            "status": "success",
            "message": "Re-discovery completed",
            "results": {
                "added_count": len(results["added"]),
                "removed_count": len(results["removed"]),
                "unchanged_count": len(results["unchanged"]),
                "added_files": results["added"],
                "removed_files": results["removed"]
            },
            "note": "All files were re-discovered and metadata was extracted for new files"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Re-discovery failed: {str(e)}")

@router.get("/config")
async def get_discovery_config():
    """Get discovery configuration"""
    try:
        from ..core.config_loader import config_loader
        from ..core.config import DiscoveryConfig
        
        # Get discovery configuration from config_loader
        discovery_config = config_loader.get_discovery_config()
        
        # Return current configuration
        return {
            "status": "success",
            "config": {
                "search_directories": discovery_config.get("search_directories", DiscoveryConfig.get_search_directories()),
                "supported_extensions": discovery_config.get("supported_extensions", DiscoveryConfig.get_supported_extensions()),
                "batch_size": discovery_config.get("scan_settings", {}).get("batch_size", DiscoveryConfig.get_batch_size()),
                "cache_settings": discovery_config.get("cache_settings", {}),
                "scan_settings": discovery_config.get("scan_settings", {}),
                "hash_settings": discovery_config.get("hash_settings", {})
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get discovery config: {str(e)}")
