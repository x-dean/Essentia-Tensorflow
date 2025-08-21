from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy import and_, or_
from typing import List, Optional, Dict, Any
import json
import math
from datetime import datetime

from src.playlist_app.models.database import get_db, File, AudioMetadata, FileStatus, TrackAnalysisSummary
from src.playlist_app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/tracks", tags=["tracks"])

def safe_json_serialize(obj):
    """Safely serialize objects to JSON, handling NaN and Infinity"""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
    return obj

def clean_float_values(data):
    """Recursively clean float values in a dictionary"""
    if isinstance(data, dict):
        cleaned = {}
        for key, value in data.items():
            cleaned[key] = clean_float_values(value)
        return cleaned
    elif isinstance(data, list):
        return [clean_float_values(item) for item in data]
    elif isinstance(data, float):
        return safe_json_serialize(data)
    else:
        return data

def extract_spectral_features(analysis):
    """Safely extract spectral features from complete_analysis JSON"""
    if not analysis.complete_analysis:
        return {}
    
    try:
        complete_data = json.loads(analysis.complete_analysis)
        if "spectral" in complete_data:
            spectral = complete_data["spectral_features"]
            return {
                "spectral_centroid": spectral.get("spectral_centroid"),
                "spectral_rolloff": spectral.get("spectral_rolloff")
            }
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    
    return {}

@router.get("/")
async def get_all_tracks(
    db: Session = Depends(get_db),
    limit: int = Query(100, description="Maximum number of tracks to return"),
    offset: int = Query(0, description="Number of tracks to skip"),
    analyzed_only: bool = Query(False, description="Return only analyzed tracks"),
    has_metadata: bool = Query(False, description="Return only tracks with metadata"),
    format: str = Query("summary", description="Response format: summary, detailed, or minimal")
):
    """
    Get all tracks with their attributes.
    
    - **summary**: Basic track info with key attributes
    - **detailed**: Full track information including all analysis data
    - **minimal**: Just track IDs and file paths
    """
    try:
        query = db.query(File)
        
        if analyzed_only:
            query = query.join(TrackAnalysisSummary).filter(TrackAnalysisSummary.analysis_status == "complete")
        
        if has_metadata:
            query = query.join(AudioMetadata)
        
        total_count = query.count()
        # If limit is 0, don't apply limit (get all tracks)
        if limit == 0:
            tracks = query.order_by(File.discovered_at.desc()).offset(offset).all()
        else:
            tracks = query.order_by(File.discovered_at.desc()).offset(offset).limit(limit).all()
        
        if format == "minimal":
            result = []
            for track in tracks:
                track_data = {
                    "id": track.id,
                    "file_path": track.file_path,
                    "file_name": track.file_name,
                    "status": track.status.value if track.status else None,
                }
                
                # Add analysis status from track summary if available
                if track.analysis_summary:
                    track_data["analysis_status"] = track.analysis_summary.analysis_status
                else:
                    track_data["analysis_status"] = None
                
                result.append(track_data)
        elif format == "summary":
            result = []
            for track in tracks:
                track_data = {
                    "id": track.id,
                    "file_path": track.file_path,
                    "file_name": track.file_name,
                    "file_size": track.file_size,
                    "file_extension": track.file_extension,
                    "discovered_at": track.discovered_at.isoformat() if track.discovered_at else None,
                    "status": track.status.value if track.status else None,
                    "has_metadata": track.has_metadata,
                    "is_active": track.is_active
                }
                
                # Add analysis status from track summary if available
                if track.analysis_summary:
                    track_data.update({
                        "analysis_status": track.analysis_summary.analysis_status,
                        "analysis_date": track.analysis_summary.analysis_date.isoformat() if track.analysis_summary.analysis_date else None,
                        "analysis_duration": track.analysis_summary.analysis_duration,
                        "analysis_errors": track.analysis_summary.analysis_errors
                    })
                else:
                    track_data.update({
                        "analysis_status": None,
                        "analysis_date": None,
                        "analysis_duration": None,
                        "analysis_errors": None
                    })
                
                # Add metadata if available
                if track.metadata:
                    metadata = track.metadata
                    track_data.update({
                        "title": metadata.title,
                        "artist": metadata.artist,
                        "album": metadata.album,
                        "album_artist": metadata.album_artist,
                        "year": metadata.year,
                        "genre": metadata.genre,
                        "duration": metadata.duration,
                        "bpm": metadata.bpm,
                        "key": metadata.key,
                        "bitrate": metadata.bitrate,
                        "sample_rate": metadata.sample_rate,
                        "channels": metadata.channels,
                        "file_format": metadata.file_format,
                        "mood": metadata.mood
                    })
                
                # Analysis data is available through the individual analyzer status tables
                # and results tables, which can be accessed via separate endpoints
                
                result.append(clean_float_values(track_data))
        else:  # detailed
            result = []
            for track in tracks:
                track_data = {
                    "id": track.id,
                    "file_path": track.file_path,
                    "file_name": track.file_name,
                    "file_size": track.file_size,
                    "file_hash": track.file_hash,
                    "file_extension": track.file_extension,
                    "discovered_at": track.discovered_at.isoformat() if track.discovered_at else None,
                    "last_modified": track.last_modified.isoformat() if track.last_modified else None,
                    "analysis_status": track.analysis_summary.analysis_status if track.analysis_summary else None,
                    "is_active": track.is_active
                }
                
                # Add full metadata if available
                if track.metadata:
                    metadata = track.metadata
                    track_data["metadata"] = {
                        "title": metadata.title,
                        "artist": metadata.artist,
                        "album": metadata.album,
                        "album_artist": metadata.album_artist,
                        "year": metadata.year,
                        "genre": metadata.genre,
                        "duration": metadata.duration,
                        "bpm": metadata.bpm,
                        "key": metadata.key,
                        "mood": metadata.mood,
                        "bitrate": metadata.bitrate,
                        "sample_rate": metadata.sample_rate,
                        "channels": metadata.channels,
                        "file_format": metadata.file_format,
                        "created_at": metadata.created_at.isoformat() if metadata.created_at else None,
                        "updated_at": metadata.updated_at.isoformat() if metadata.updated_at else None
                    }
                
                # Analysis data is available through the individual analyzer status tables
                # and results tables, which can be accessed via separate endpoints
                
                result.append(clean_float_values(track_data))
        
        return {
            "total_count": total_count,
            "returned_count": len(result),
            "offset": offset,
            "limit": limit,
            "tracks": result
        }
        
    except Exception as e:
        logger.error(f"Error getting tracks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Add other endpoints as needed...
