from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy import and_, or_
from typing import List, Optional, Dict, Any
import json
import math
from datetime import datetime

from src.playlist_app.models.database import get_db, File, AudioMetadata, AudioAnalysis, FileStatus
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
            spectral = complete_data["spectral"]
            return {
                "spectral_centroid_mean": spectral.get("centroid", {}).get("mean"),
                "spectral_centroid_std": spectral.get("centroid", {}).get("std"),
                "spectral_rolloff_mean": spectral.get("rolloff", {}).get("mean"),
                "spectral_rolloff_std": spectral.get("rolloff", {}).get("std"),
                "spectral_contrast_mean": spectral.get("contrast", {}).get("mean"),
                "spectral_contrast_std": spectral.get("contrast", {}).get("std"),
                "spectral_complexity_mean": spectral.get("complexity", {}).get("mean"),
                "spectral_complexity_std": spectral.get("complexity", {}).get("std")
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
            query = query.filter(File.has_audio_analysis == True)
        
        if has_metadata:
            query = query.join(AudioMetadata)
        
        total_count = query.count()
        tracks = query.order_by(File.discovered_at.desc()).offset(offset).limit(limit).all()
        
        if format == "minimal":
            result = [
                {
                    "id": track.id,
                    "file_path": track.file_path,
                    "file_name": track.file_name,
                    "status": track.status.value if track.status else None,
                    "is_analyzed": track.is_analyzed
                }
                for track in tracks
            ]
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
                    "is_analyzed": track.is_analyzed,
                    "has_metadata": track.has_metadata,
                    "has_audio_analysis": track.has_audio_analysis,
                    "is_active": track.is_active
                }
                
                # Add metadata if available
                if track.audio_metadata:
                    metadata = track.audio_metadata
                    track_data.update({
                        "title": metadata.title,
                        "artist": metadata.artist,
                        "album": metadata.album,
                        "track_number": metadata.track_number,
                        "year": metadata.year,
                        "genre": metadata.genre,
                        "duration": metadata.duration,
                        "bpm": metadata.bpm,
                        "key": metadata.key,
                        "bitrate": metadata.bitrate,
                        "sample_rate": metadata.sample_rate
                    })
                
                # Add analysis summary if available
                if track.audio_analysis:
                    analysis = track.audio_analysis
                    track_data.update({
                        "tempo": analysis.tempo,
                        "key_analysis": analysis.key,
                        "scale": analysis.scale,
                        "key_strength": analysis.key_strength,
                        "energy": analysis.energy,
                        "loudness": analysis.loudness,
                        "analysis_timestamp": analysis.analysis_timestamp.isoformat() if analysis.analysis_timestamp else None
                    })
                    
                    # Add spectral features from complete_analysis
                    spectral_features = extract_spectral_features(analysis)
                    track_data.update(spectral_features)
                
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
                    "is_analyzed": track.is_analyzed,
                    "is_active": track.is_active
                }
                
                # Add full metadata if available
                if track.audio_metadata:
                    metadata = track.audio_metadata
                    track_data["metadata"] = {
                        "title": metadata.title,
                        "artist": metadata.artist,
                        "album": metadata.album,
                        "track_number": metadata.track_number,
                        "year": metadata.year,
                        "genre": metadata.genre,
                        "album_artist": metadata.album_artist,
                        "disc_number": metadata.disc_number,
                        "composer": metadata.composer,
                        "duration": metadata.duration,
                        "bpm": metadata.bpm,
                        "key": metadata.key,
                        "comment": metadata.comment,
                        "mood": metadata.mood,
                        "rating": metadata.rating,
                        "isrc": metadata.isrc,
                        "encoder": metadata.encoder,
                        "bitrate": metadata.bitrate,
                        "sample_rate": metadata.sample_rate,
                        "channels": metadata.channels,
                        "format": metadata.format,
                        "file_size": metadata.file_size,
                        "file_format": metadata.file_format,
                        "replaygain_track_gain": metadata.replaygain_track_gain,
                        "replaygain_album_gain": metadata.replaygain_album_gain,
                        "replaygain_track_peak": metadata.replaygain_track_peak,
                        "replaygain_album_peak": metadata.replaygain_album_peak,
                        "musicbrainz_track_id": metadata.musicbrainz_track_id,
                        "musicbrainz_artist_id": metadata.musicbrainz_artist_id,
                        "musicbrainz_album_id": metadata.musicbrainz_album_id,
                        "musicbrainz_album_artist_id": metadata.musicbrainz_album_artist_id,
                        "created_at": metadata.created_at.isoformat() if metadata.created_at else None,
                        "updated_at": metadata.updated_at.isoformat() if metadata.updated_at else None
                    }
                
                # Add full analysis if available
                if track.audio_analysis:
                    analysis = track.audio_analysis
                    track_data["analysis"] = {
                        "analysis_timestamp": analysis.analysis_timestamp.isoformat() if analysis.analysis_timestamp else None,
                        "analysis_duration": analysis.analysis_duration,
                        "sample_rate": analysis.sample_rate,
                        "duration": analysis.duration,
                        "basic_features": {
                            "rms": analysis.rms,
                            "energy": analysis.energy,
                            "loudness": analysis.loudness
                        },
                        "mfcc_features": {
                            # MFCC features are stored in complete_analysis JSON
                        },
                        "rhythm_features": {
                            "tempo": analysis.tempo,
                            "tempo_confidence": analysis.tempo_confidence,
                            "tempo_methods_used": analysis.tempo_methods_used
                        },
                        "harmonic_features": {
                            "key": analysis.key,
                            "scale": analysis.scale,
                            "key_strength": analysis.key_strength,
                            "dominant_chroma": analysis.dominant_chroma,
                            "dominant_chroma_strength": analysis.dominant_chroma_strength
                        },
                        "tensorflow_features": json.loads(analysis.tensorflow_features) if analysis.tensorflow_features else None,
                        "complete_analysis": json.loads(analysis.complete_analysis) if analysis.complete_analysis else None
                    }
                    
                    # Add spectral features from complete_analysis
                    spectral_features = extract_spectral_features(analysis)
                    if spectral_features:
                        track_data["analysis"]["spectral_features"] = spectral_features
                
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
