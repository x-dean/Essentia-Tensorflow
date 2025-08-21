from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy import and_, or_
from typing import List, Optional, Dict, Any
import json
import math
import os
from datetime import datetime

from src.playlist_app.models.database import get_db, File, AudioMetadata, FileStatus, TrackAnalysisSummary, TensorFlowAnalysisResults
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
        
        # Always join with analysis summary to get analysis data
        query = query.outerjoin(TrackAnalysisSummary)
        query = query.outerjoin(TensorFlowAnalysisResults)
        
        if analyzed_only:
            query = query.filter(TrackAnalysisSummary.analysis_status == "complete")
        
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
                        "analysis_errors": track.analysis_summary.analysis_errors,
                        # Essentia analysis results
                        "tempo": track.analysis_summary.bpm,
                        "key_analysis": track.analysis_summary.key,
                        "scale": track.analysis_summary.scale,
                        "energy": track.analysis_summary.energy,
                        "danceability": track.analysis_summary.danceability,
                        "loudness": track.analysis_summary.loudness,
                        "dynamic_complexity": track.analysis_summary.dynamic_complexity,
                        "rhythm_confidence": track.analysis_summary.rhythm_confidence,
                        "key_strength": track.analysis_summary.key_strength,
                        # TensorFlow analysis results
                        "valence": track.analysis_summary.tensorflow_valence,
                        "acousticness": track.analysis_summary.tensorflow_acousticness,
                        "instrumentalness": track.analysis_summary.tensorflow_instrumentalness,
                        "speechiness": track.analysis_summary.tensorflow_speechiness,
                        "liveness": track.analysis_summary.tensorflow_liveness,
                        # Quality control
                        "analysis_quality_score": track.analysis_summary.analysis_quality_score,
                        "confidence_threshold": track.analysis_summary.confidence_threshold
                    })
                else:
                    track_data.update({
                        "analysis_status": None,
                        "analysis_date": None,
                        "analysis_duration": None,
                        "analysis_errors": None,
                        "tempo": None,
                        "key_analysis": None,
                        "scale": None,
                        "energy": None,
                        "danceability": None,
                        "loudness": None,
                        "dynamic_complexity": None,
                        "rhythm_confidence": None,
                        "key_strength": None,
                        "valence": None,
                        "acousticness": None,
                        "instrumentalness": None,
                        "speechiness": None,
                        "liveness": None,
                        "analysis_quality_score": None,
                        "confidence_threshold": None
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
                
                # Add analysis data if available
                if track.analysis_summary:
                    track_data["analysis"] = {
                        "analysis_status": track.analysis_summary.analysis_status,
                        "analysis_date": track.analysis_summary.analysis_date.isoformat() if track.analysis_summary.analysis_date else None,
                        "analysis_duration": track.analysis_summary.analysis_duration,
                        "analysis_errors": track.analysis_summary.analysis_errors,
                        # Essentia analysis results
                        "tempo": track.analysis_summary.bpm,
                        "key": track.analysis_summary.key,
                        "scale": track.analysis_summary.scale,
                        "energy": track.analysis_summary.energy,
                        "danceability": track.analysis_summary.danceability,
                        "loudness": track.analysis_summary.loudness,
                        "dynamic_complexity": track.analysis_summary.dynamic_complexity,
                        "rhythm_confidence": track.analysis_summary.rhythm_confidence,
                        "key_strength": track.analysis_summary.key_strength,
                        # TensorFlow analysis results
                        "valence": track.analysis_summary.tensorflow_valence,
                        "acousticness": track.analysis_summary.tensorflow_acousticness,
                        "instrumentalness": track.analysis_summary.tensorflow_instrumentalness,
                        "speechiness": track.analysis_summary.tensorflow_speechiness,
                        "liveness": track.analysis_summary.tensorflow_liveness,
                        # Quality control
                        "analysis_quality_score": track.analysis_summary.analysis_quality_score,
                        "confidence_threshold": track.analysis_summary.confidence_threshold
                    }
                
                # Add TensorFlow predictions if available
                if hasattr(track, 'tensorflow_analysis_results') and track.tensorflow_analysis_results:
                    tf_results = track.tensorflow_analysis_results
                    if not track_data.get("analysis"):
                        track_data["analysis"] = {}
                    track_data["analysis"]["tensorflow_predictions"] = {
                        "top_predictions": tf_results.top_predictions,
                        "genre_scores": tf_results.genre_scores,
                        "mood_scores": tf_results.mood_scores,
                        "dominant_genres": tf_results.dominant_genres,
                        "dominant_moods": tf_results.dominant_moods,
                        "emotion_dimensions": tf_results.emotion_dimensions,
                        "model_used": tf_results.model_used,
                        "analysis_timestamp": tf_results.analysis_timestamp.isoformat() if tf_results.analysis_timestamp else None,
                        "analysis_duration": tf_results.analysis_duration
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

@router.get("/stream/{track_id}")
async def stream_track(track_id: int, db: Session = Depends(get_db)):
    """
    Stream an audio track by ID.
    
    This endpoint returns the audio file for streaming playback in the browser.
    """
    try:
        # Get the track from database
        track = db.query(File).filter(File.id == track_id).first()
        if not track:
            raise HTTPException(status_code=404, detail="Track not found")
        
        # Check if file exists
        if not os.path.exists(track.file_path):
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        # Return the file for streaming
        return FileResponse(
            path=track.file_path,
            media_type="audio/mpeg",  # Default to MP3, could be made dynamic
            filename=track.file_name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error streaming track {track_id}: {e}")
        raise HTTPException(status_code=500, detail="Error streaming track")

# Add other endpoints as needed...
