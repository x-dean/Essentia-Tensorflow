from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional, Dict, Any
import json
import math
from datetime import datetime

from src.playlist_app.models.database import get_db, File, AudioMetadata, AudioAnalysis
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
            query = query.filter(File.is_analyzed == True)
        
        if has_metadata:
            query = query.join(AudioMetadata)
        
        total_count = query.count()
        tracks = query.offset(offset).limit(limit).all()
        
        if format == "minimal":
            result = [
                {
                    "id": track.id,
                    "file_path": track.file_path,
                    "file_name": track.file_name,
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
                    "is_analyzed": track.is_analyzed,
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
                        "spectral_centroid_mean": analysis.spectral_centroid_mean,
                        "analysis_timestamp": analysis.analysis_timestamp.isoformat() if analysis.analysis_timestamp else None
                    })
                
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
                            "loudness": analysis.loudness,
                            "spectral_centroid_mean": analysis.spectral_centroid_mean,
                            "spectral_centroid_std": analysis.spectral_centroid_std,
                            "spectral_rolloff_mean": analysis.spectral_rolloff_mean,
                            "spectral_rolloff_std": analysis.spectral_rolloff_std,
                            "spectral_contrast_mean": analysis.spectral_contrast_mean,
                            "spectral_contrast_std": analysis.spectral_contrast_std,
                            "spectral_complexity_mean": analysis.spectral_complexity_mean,
                            "spectral_complexity_std": analysis.spectral_complexity_std
                        },
                        "mfcc_features": {
                            "mfcc_mean": json.loads(analysis.mfcc_mean) if analysis.mfcc_mean else None,
                            "mfcc_bands_mean": json.loads(analysis.mfcc_bands_mean) if analysis.mfcc_bands_mean else None
                        },
                        "rhythm_features": {
                            "tempo": analysis.tempo,
                            "tempo_confidence": analysis.tempo_confidence,
                            "rhythm_bpm": analysis.rhythm_bpm,
                            "rhythm_confidence": analysis.rhythm_confidence,
                            "beat_confidence": analysis.beat_confidence,
                            "beats": json.loads(analysis.beats) if analysis.beats else None,
                            "rhythm_ticks": json.loads(analysis.rhythm_ticks) if analysis.rhythm_ticks else None,
                            "rhythm_estimates": json.loads(analysis.rhythm_estimates) if analysis.rhythm_estimates else None,
                            "onset_detections": json.loads(analysis.onset_detections) if analysis.onset_detections else None
                        },
                        "harmonic_features": {
                            "key": analysis.key,
                            "scale": analysis.scale,
                            "key_strength": analysis.key_strength,
                            "chords": json.loads(analysis.chords) if analysis.chords else None,
                            "chord_strengths": json.loads(analysis.chord_strengths) if analysis.chord_strengths else None,
                            "pitch_yin": json.loads(analysis.pitch_yin) if analysis.pitch_yin else None,
                            "pitch_yin_confidence": json.loads(analysis.pitch_yin_confidence) if analysis.pitch_yin_confidence else None,
                            "pitch_melodia": json.loads(analysis.pitch_melodia) if analysis.pitch_melodia else None,
                            "pitch_melodia_confidence": json.loads(analysis.pitch_melodia_confidence) if analysis.pitch_melodia_confidence else None,
                            "chromagram": json.loads(analysis.chromagram) if analysis.chromagram else None
                        },
                        "tensorflow_features": json.loads(analysis.tensorflow_features) if analysis.tensorflow_features else None,
                        "complete_analysis": json.loads(analysis.complete_analysis) if analysis.complete_analysis else None,
                        "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
                        "updated_at": analysis.updated_at.isoformat() if analysis.updated_at else None
                    }
                
                result.append(clean_float_values(track_data))
        
        return {
            "total_count": total_count,
            "returned_count": len(result),
            "offset": offset,
            "limit": limit,
            "tracks": result
        }
        
    except Exception as e:
        logger.error(f"Error getting tracks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/{track_id}")
async def get_track_by_id(
    track_id: int,
    db: Session = Depends(get_db),
    format: str = Query("detailed", description="Response format: summary, detailed, or minimal")
):
    """
    Get a specific track by ID with all its attributes.
    """
    try:
        track = db.query(File).filter(File.id == track_id).first()
        
        if not track:
            raise HTTPException(status_code=404, detail=f"Track with ID {track_id} not found")
        
        if format == "minimal":
            return {
                "id": track.id,
                "file_path": track.file_path,
                "file_name": track.file_name,
                "is_analyzed": track.is_analyzed
            }
        elif format == "summary":
            track_data = {
                "id": track.id,
                "file_path": track.file_path,
                "file_name": track.file_name,
                "file_size": track.file_size,
                "file_extension": track.file_extension,
                "discovered_at": track.discovered_at.isoformat() if track.discovered_at else None,
                "is_analyzed": track.is_analyzed,
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
                    "spectral_centroid_mean": analysis.spectral_centroid_mean,
                    "analysis_timestamp": analysis.analysis_timestamp.isoformat() if analysis.analysis_timestamp else None
                })
            
            return clean_float_values(track_data)
        else:  # detailed
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
                        "loudness": analysis.loudness,
                        "spectral_centroid_mean": analysis.spectral_centroid_mean,
                        "spectral_centroid_std": analysis.spectral_centroid_std,
                        "spectral_rolloff_mean": analysis.spectral_rolloff_mean,
                        "spectral_rolloff_std": analysis.spectral_rolloff_std,
                        "spectral_contrast_mean": analysis.spectral_contrast_mean,
                        "spectral_contrast_std": analysis.spectral_contrast_std,
                        "spectral_complexity_mean": analysis.spectral_complexity_mean,
                        "spectral_complexity_std": analysis.spectral_complexity_std
                    },
                    "mfcc_features": {
                        "mfcc_mean": json.loads(analysis.mfcc_mean) if analysis.mfcc_mean else None,
                        "mfcc_bands_mean": json.loads(analysis.mfcc_bands_mean) if analysis.mfcc_bands_mean else None
                    },
                    "rhythm_features": {
                        "tempo": analysis.tempo,
                        "tempo_confidence": analysis.tempo_confidence,
                        "rhythm_bpm": analysis.rhythm_bpm,
                        "rhythm_confidence": analysis.rhythm_confidence,
                        "beat_confidence": analysis.beat_confidence,
                        "beats": json.loads(analysis.beats) if analysis.beats else None,
                        "rhythm_ticks": json.loads(analysis.rhythm_ticks) if analysis.rhythm_ticks else None,
                        "rhythm_estimates": json.loads(analysis.rhythm_estimates) if analysis.rhythm_estimates else None,
                        "onset_detections": json.loads(analysis.onset_detections) if analysis.onset_detections else None
                    },
                    "harmonic_features": {
                        "key": analysis.key,
                        "scale": analysis.scale,
                        "key_strength": analysis.key_strength,
                        "chords": json.loads(analysis.chords) if analysis.chords else None,
                        "chord_strengths": json.loads(analysis.chord_strengths) if analysis.chord_strengths else None,
                        "pitch_yin": json.loads(analysis.pitch_yin) if analysis.pitch_yin else None,
                        "pitch_yin_confidence": json.loads(analysis.pitch_yin_confidence) if analysis.pitch_yin_confidence else None,
                        "pitch_melodia": json.loads(analysis.pitch_melodia) if analysis.pitch_melodia else None,
                        "pitch_melodia_confidence": json.loads(analysis.pitch_melodia_confidence) if analysis.pitch_melodia_confidence else None,
                        "chromagram": json.loads(analysis.chromagram) if analysis.chromagram else None
                    },
                    "tensorflow_features": json.loads(analysis.tensorflow_features) if analysis.tensorflow_features else None,
                    "complete_analysis": json.loads(analysis.complete_analysis) if analysis.complete_analysis else None,
                    "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
                    "updated_at": analysis.updated_at.isoformat() if analysis.updated_at else None
                }
            
            return clean_float_values(track_data)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting track {track_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/search/")
async def search_tracks(
    db: Session = Depends(get_db),
    title: Optional[str] = Query(None, description="Search in title"),
    artist: Optional[str] = Query(None, description="Search in artist"),
    album: Optional[str] = Query(None, description="Search in album"),
    genre: Optional[str] = Query(None, description="Search in genre"),
    key: Optional[str] = Query(None, description="Search by musical key"),
    min_tempo: Optional[float] = Query(None, description="Minimum tempo"),
    max_tempo: Optional[float] = Query(None, description="Maximum tempo"),
    min_duration: Optional[float] = Query(None, description="Minimum duration in seconds"),
    max_duration: Optional[float] = Query(None, description="Maximum duration in seconds"),
    analyzed_only: bool = Query(False, description="Only return analyzed tracks"),
    limit: int = Query(50, description="Maximum number of tracks to return"),
    offset: int = Query(0, description="Number of tracks to skip"),
    format: str = Query("summary", description="Response format: summary, detailed, or minimal")
):
    """
    Search tracks by various criteria.
    """
    try:
        query = db.query(File).join(AudioMetadata)
        
        # Apply filters
        if title:
            query = query.filter(AudioMetadata.title.ilike(f"%{title}%"))
        if artist:
            query = query.filter(AudioMetadata.artist.ilike(f"%{artist}%"))
        if album:
            query = query.filter(AudioMetadata.album.ilike(f"%{album}%"))
        if genre:
            query = query.filter(AudioMetadata.genre.ilike(f"%{genre}%"))
        if key:
            query = query.filter(AudioMetadata.key == key)
        if min_tempo:
            query = query.filter(AudioMetadata.bpm >= min_tempo)
        if max_tempo:
            query = query.filter(AudioMetadata.bpm <= max_tempo)
        if min_duration:
            query = query.filter(AudioMetadata.duration >= min_duration)
        if max_duration:
            query = query.filter(AudioMetadata.duration <= max_duration)
        if analyzed_only:
            query = query.filter(File.is_analyzed == True)
        
        total_count = query.count()
        tracks = query.offset(offset).limit(limit).all()
        
        # Format response similar to get_all_tracks
        if format == "minimal":
            result = [
                {
                    "id": track.id,
                    "file_path": track.file_path,
                    "file_name": track.file_name,
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
                    "is_analyzed": track.is_analyzed,
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
                        "spectral_centroid_mean": analysis.spectral_centroid_mean,
                        "analysis_timestamp": analysis.analysis_timestamp.isoformat() if analysis.analysis_timestamp else None
                    })
                
                result.append(clean_float_values(track_data))
        else:  # detailed - same as get_all_tracks detailed format
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
                            "loudness": analysis.loudness,
                            "spectral_centroid_mean": analysis.spectral_centroid_mean,
                            "spectral_centroid_std": analysis.spectral_centroid_std,
                            "spectral_rolloff_mean": analysis.spectral_rolloff_mean,
                            "spectral_rolloff_std": analysis.spectral_rolloff_std,
                            "spectral_contrast_mean": analysis.spectral_contrast_mean,
                            "spectral_contrast_std": analysis.spectral_contrast_std,
                            "spectral_complexity_mean": analysis.spectral_complexity_mean,
                            "spectral_complexity_std": analysis.spectral_complexity_std
                        },
                        "mfcc_features": {
                            "mfcc_mean": json.loads(analysis.mfcc_mean) if analysis.mfcc_mean else None,
                            "mfcc_bands_mean": json.loads(analysis.mfcc_bands_mean) if analysis.mfcc_bands_mean else None
                        },
                        "rhythm_features": {
                            "tempo": analysis.tempo,
                            "tempo_confidence": analysis.tempo_confidence,
                            "rhythm_bpm": analysis.rhythm_bpm,
                            "rhythm_confidence": analysis.rhythm_confidence,
                            "beat_confidence": analysis.beat_confidence,
                            "beats": json.loads(analysis.beats) if analysis.beats else None,
                            "rhythm_ticks": json.loads(analysis.rhythm_ticks) if analysis.rhythm_ticks else None,
                            "rhythm_estimates": json.loads(analysis.rhythm_estimates) if analysis.rhythm_estimates else None,
                            "onset_detections": json.loads(analysis.onset_detections) if analysis.onset_detections else None
                        },
                        "harmonic_features": {
                            "key": analysis.key,
                            "scale": analysis.scale,
                            "key_strength": analysis.key_strength,
                            "chords": json.loads(analysis.chords) if analysis.chords else None,
                            "chord_strengths": json.loads(analysis.chord_strengths) if analysis.chord_strengths else None,
                            "pitch_yin": json.loads(analysis.pitch_yin) if analysis.pitch_yin else None,
                            "pitch_yin_confidence": json.loads(analysis.pitch_yin_confidence) if analysis.pitch_yin_confidence else None,
                            "pitch_melodia": json.loads(analysis.pitch_melodia) if analysis.pitch_melodia else None,
                            "pitch_melodia_confidence": json.loads(analysis.pitch_melodia_confidence) if analysis.pitch_melodia_confidence else None,
                            "chromagram": json.loads(analysis.chromagram) if analysis.chromagram else None
                        },
                        "tensorflow_features": json.loads(analysis.tensorflow_features) if analysis.tensorflow_features else None,
                        "complete_analysis": json.loads(analysis.complete_analysis) if analysis.complete_analysis else None,
                        "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
                        "updated_at": analysis.updated_at.isoformat() if analysis.updated_at else None
                    }
                
                result.append(clean_float_values(track_data))
        
        return {
            "total_count": total_count,
            "returned_count": len(result),
            "offset": offset,
            "limit": limit,
            "search_criteria": {
                "title": title,
                "artist": artist,
                "album": album,
                "genre": genre,
                "key": key,
                "min_tempo": min_tempo,
                "max_tempo": max_tempo,
                "min_duration": min_duration,
                "max_duration": max_duration,
                "analyzed_only": analyzed_only
            },
            "tracks": result
        }
        
    except Exception as e:
        logger.error(f"Error searching tracks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/stats/overview")
async def get_tracks_overview(db: Session = Depends(get_db)):
    """
    Get overview statistics about tracks.
    """
    try:
        total_tracks = db.query(File).count()
        analyzed_tracks = db.query(File).filter(File.is_analyzed == True).count()
        tracks_with_metadata = db.query(File).join(AudioMetadata).count()
        
        # Get unique values for common fields
        unique_artists = db.query(AudioMetadata.artist).distinct().count()
        unique_albums = db.query(AudioMetadata.album).distinct().count()
        unique_genres = db.query(AudioMetadata.genre).distinct().count()
        unique_keys = db.query(AudioMetadata.key).distinct().count()
        
        # Get file format distribution
        format_counts = db.query(File.file_extension, func.count(File.id)).group_by(File.file_extension).all()
        
        return {
            "total_tracks": total_tracks,
            "analyzed_tracks": analyzed_tracks,
            "tracks_with_metadata": tracks_with_metadata,
            "analysis_coverage": round((analyzed_tracks / total_tracks * 100) if total_tracks > 0 else 0, 2),
            "metadata_coverage": round((tracks_with_metadata / total_tracks * 100) if total_tracks > 0 else 0, 2),
            "unique_artists": unique_artists,
            "unique_albums": unique_albums,
            "unique_genres": unique_genres,
            "unique_keys": unique_keys,
            "file_formats": dict(format_counts)
        }
        
    except Exception as e:
        logger.error(f"Error getting tracks overview: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/reset-database")
async def reset_database(
    db: Session = Depends(get_db),
    confirm: bool = Query(False, description="Must be True to confirm database reset")
):
    """
    Reset and recreate the database.
    
    This endpoint will drop all existing tables and recreate them.
    WARNING: This will permanently delete all data!
    """
    try:
        if not confirm:
            raise HTTPException(
                status_code=400, 
                detail="Database reset requires explicit confirmation. Set confirm=true to proceed."
            )
        
        from src.playlist_app.models.database import Base, engine, create_tables
        
        # Drop all tables
        logger.info("Dropping all database tables...")
        Base.metadata.drop_all(bind=engine)
        
        # Recreate tables
        logger.info("Recreating database tables...")
        create_tables()
        
        return {
            "status": "success",
            "message": "Database reset completed successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database reset failed: {str(e)}")

@router.get("/database-status")
async def get_database_status(db: Session = Depends(get_db)):
    """
    Get current database status and table information.
    """
    try:
        from src.playlist_app.models.database import Base, engine
        
        # Get table information
        inspector = engine.dialect.inspector(engine)
        tables = inspector.get_table_names()
        
        table_info = {}
        total_records = 0
        
        for table_name in tables:
            try:
                record_count = db.execute(f"SELECT COUNT(*) FROM {table_name}").scalar()
                table_info[table_name] = {
                    "record_count": record_count,
                    "exists": True
                }
                total_records += record_count
            except Exception as e:
                table_info[table_name] = {
                    "record_count": 0,
                    "exists": False,
                    "error": str(e)
                }
        
        # Check if tables exist
        expected_tables = [
            "files", "discovery_cache", "audio_metadata", 
            "audio_analysis", "vector_index", "faiss_index_metadata"
        ]
        
        missing_tables = [table for table in expected_tables if table not in tables]
        
        return {
            "database_status": "connected",
            "total_tables": len(tables),
            "expected_tables": expected_tables,
            "missing_tables": missing_tables,
            "total_records": total_records,
            "table_info": table_info,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting database status: {str(e)}")
        return {
            "database_status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
