from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
import os

from ..models.database import get_db, create_tables
from ..services.discovery import DiscoveryService

router = APIRouter(prefix="/api/discovery", tags=["discovery"])

def get_discovery_service(db: Session = Depends(get_db)) -> DiscoveryService:
    """Get discovery service instance"""
    # Get search directories from environment or use defaults
    search_dirs = os.getenv("SEARCH_DIRECTORIES", "/music,/audio").split(",")
    search_dirs = [dir.strip() for dir in search_dirs if dir.strip()]
    
    return DiscoveryService(
        db_session=db,
        search_directories=search_dirs
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

@router.get("/stats")
async def get_discovery_stats(discovery_service: DiscoveryService = Depends(get_discovery_service)):
    """Get discovery statistics"""
    try:
        from ..models.database import File
        
        db = discovery_service.db
        
        # Get total files
        total_files = db.query(File).filter(File.is_active == True).count()
        
        # Get analyzed files
        analyzed_files = db.query(File).filter(File.is_active == True, File.is_analyzed == True).count()
        
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
async def get_discovery_config(discovery_service: DiscoveryService = Depends(get_discovery_service)):
    """Get discovery configuration"""
    return {
        "status": "success",
        "config": {
            "search_directories": discovery_service.search_directories,
            "supported_extensions": discovery_service.supported_extensions
        }
    }
