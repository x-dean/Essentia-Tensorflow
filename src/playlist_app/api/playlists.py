from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from ..models.database_v2 import (
    get_db, Playlist, PlaylistTrack, 
    File, AudioMetadata
)
from ..core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/playlists", tags=["playlists"])

# Pydantic models
class PlaylistCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_public: bool = True
    cover_image_url: Optional[str] = None

class PlaylistUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None
    cover_image_url: Optional[str] = None

class PlaylistTrackAdd(BaseModel):
    file_id: int
    position: Optional[int] = None
    notes: Optional[str] = None

class PlaylistTrackUpdate(BaseModel):
    position: Optional[int] = None
    notes: Optional[str] = None
    rating: Optional[int] = None

class PlaylistResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_public: bool
    cover_image_url: Optional[str]
    total_duration: int
    track_count: int
    rating_avg: float
    generation_type: Optional[str]
    created_at: datetime
    updated_at: datetime

class PlaylistTrackResponse(BaseModel):
    id: int
    file_id: int
    position: int
    added_at: datetime
    notes: Optional[str]
    rating: Optional[int]
    selection_reason: Optional[str]
    selection_score: Optional[float]
    track_title: Optional[str]
    track_artist: Optional[str]
    track_album: Optional[str]
    track_duration: Optional[float]

class PlaylistDetailResponse(PlaylistResponse):
    tracks: List[PlaylistTrackResponse]

def update_playlist_stats(db: Session, playlist_id: int):
    """Update playlist statistics (track count, duration, etc.)"""
    try:
        # Get playlist tracks with metadata
        tracks = db.query(
            PlaylistTrack, AudioMetadata
        ).join(
            AudioMetadata, PlaylistTrack.file_id == AudioMetadata.file_id, isouter=True
        ).filter(
            PlaylistTrack.playlist_id == playlist_id
        ).all()
        
        total_duration = sum(track.AudioMetadata.duration or 0 for track in tracks)
        track_count = len(tracks)
        
        # Calculate average rating
        ratings = [track.PlaylistTrack.rating for track in tracks if track.PlaylistTrack.rating is not None]
        rating_avg = sum(ratings) / len(ratings) if ratings else 0
        
        # Update playlist
        playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
        if playlist:
            playlist.total_duration = int(total_duration)
            playlist.track_count = track_count
            playlist.rating_avg = rating_avg
            playlist.updated_at = datetime.utcnow()
            db.commit()
            
    except Exception as e:
        logger.error(f"Error updating playlist stats: {e}")

@router.get("/", response_model=List[PlaylistResponse])
async def get_playlists(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    public_only: bool = Query(False)
):
    """Get all playlists"""
    try:
        query = db.query(Playlist)
        
        if public_only:
            query = query.filter(Playlist.is_public == True)
        
        playlists = query.order_by(Playlist.updated_at.desc()).offset(offset).limit(limit).all()
        
        result = []
        for playlist in playlists:
            result.append(PlaylistResponse(
                id=playlist.id,
                name=playlist.name,
                description=playlist.description,
                is_public=playlist.is_public,
                cover_image_url=playlist.cover_image_url,
                total_duration=playlist.total_duration,
                track_count=playlist.track_count,
                rating_avg=playlist.rating_avg,
                generation_type=playlist.generation_type,
                created_at=playlist.created_at,
                updated_at=playlist.updated_at
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting playlists: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/", response_model=PlaylistResponse)
async def create_playlist(
    playlist_data: PlaylistCreate,
    db: Session = Depends(get_db)
):
    """Create a new playlist"""
    try:
        playlist = Playlist(
            name=playlist_data.name,
            description=playlist_data.description,
            is_public=playlist_data.is_public,
            cover_image_url=playlist_data.cover_image_url,
            total_duration=0,
            track_count=0,
            rating_avg=0,
            generation_type="manual"
        )
        
        db.add(playlist)
        db.commit()
        db.refresh(playlist)
        
        logger.info(f"Playlist created: {playlist.name}")
        
        return PlaylistResponse(
            id=playlist.id,
            name=playlist.name,
            description=playlist.description,
            is_public=playlist.is_public,
            cover_image_url=playlist.cover_image_url,
            total_duration=playlist.total_duration,
            track_count=playlist.track_count,
            play_count=playlist.play_count,
            rating_avg=playlist.rating_avg,
            created_at=playlist.created_at,
            updated_at=playlist.updated_at,
            last_played=playlist.last_played
        )
        
    except Exception as e:
        logger.error(f"Error creating playlist: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/{playlist_id}", response_model=PlaylistDetailResponse)
async def get_playlist(
    playlist_id: int,
    db: Session = Depends(get_db)
):
    """Get playlist details with tracks"""
    try:
        playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
        if not playlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Playlist not found"
            )
        
        # Get playlist tracks with metadata
        tracks = db.query(
            PlaylistTrack, AudioMetadata
        ).join(
            AudioMetadata, PlaylistTrack.file_id == AudioMetadata.file_id, isouter=True
        ).filter(
            PlaylistTrack.playlist_id == playlist_id
        ).order_by(PlaylistTrack.position).all()
        
        track_responses = []
        for track in tracks:
            track_responses.append(PlaylistTrackResponse(
                id=track.PlaylistTrack.id,
                file_id=track.PlaylistTrack.file_id,
                position=track.PlaylistTrack.position,
                added_at=track.PlaylistTrack.added_at,
                notes=track.PlaylistTrack.notes,
                rating=track.PlaylistTrack.rating,
                play_count=track.PlaylistTrack.play_count,
                last_played=track.PlaylistTrack.last_played,
                track_title=track.AudioMetadata.title if track.AudioMetadata else None,
                track_artist=track.AudioMetadata.artist if track.AudioMetadata else None,
                track_album=track.AudioMetadata.album if track.AudioMetadata else None,
                track_duration=track.AudioMetadata.duration if track.AudioMetadata else None
            ))
        
        return PlaylistDetailResponse(
            id=playlist.id,
            name=playlist.name,
            description=playlist.description,
            is_public=playlist.is_public,
            cover_image_url=playlist.cover_image_url,
            total_duration=playlist.total_duration,
            track_count=playlist.track_count,
            rating_avg=playlist.rating_avg,
            generation_type=playlist.generation_type,
            created_at=playlist.created_at,
            updated_at=playlist.updated_at,
            tracks=track_responses
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting playlist: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.put("/{playlist_id}", response_model=PlaylistResponse)
async def update_playlist(
    playlist_id: int,
    playlist_data: PlaylistUpdate,
    db: Session = Depends(get_db)
):
    """Update playlist details"""
    try:
        playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
        if not playlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Playlist not found"
            )
        
        if playlist_data.name is not None:
            playlist.name = playlist_data.name
        if playlist_data.description is not None:
            playlist.description = playlist_data.description
        if playlist_data.is_public is not None:
            playlist.is_public = playlist_data.is_public
        if playlist_data.cover_image_url is not None:
            playlist.cover_image_url = playlist_data.cover_image_url
        
        playlist.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(playlist)
        
        logger.info(f"Playlist updated: {playlist.name}")
        
        return PlaylistResponse(
            id=playlist.id,
            name=playlist.name,
            description=playlist.description,
            is_public=playlist.is_public,
            cover_image_url=playlist.cover_image_url,
            total_duration=playlist.total_duration,
            track_count=playlist.track_count,
            play_count=playlist.play_count,
            rating_avg=playlist.rating_avg,
            created_at=playlist.created_at,
            updated_at=playlist.updated_at,
            last_played=playlist.last_played
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating playlist: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.delete("/{playlist_id}")
async def delete_playlist(
    playlist_id: int,
    db: Session = Depends(get_db)
):
    """Delete a playlist"""
    try:
        playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
        if not playlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Playlist not found"
            )
        
        # Delete playlist tracks first
        db.query(PlaylistTrack).filter(PlaylistTrack.playlist_id == playlist_id).delete()
        
        # Delete playlist
        db.delete(playlist)
        db.commit()
        
        logger.info(f"Playlist deleted: {playlist.name}")
        
        return {"message": "Playlist deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting playlist: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/{playlist_id}/tracks", response_model=PlaylistTrackResponse)
async def add_track_to_playlist(
    playlist_id: int,
    track_data: PlaylistTrackAdd,
    db: Session = Depends(get_db)
):
    """Add a track to a playlist"""
    try:
        playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
        if not playlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Playlist not found"
            )
        
        # Check if file exists
        file = db.query(File).filter(File.id == track_data.file_id).first()
        if not file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Determine position
        if track_data.position is None:
            # Add to end
            max_position = db.query(func.max(PlaylistTrack.position)).filter(
                PlaylistTrack.playlist_id == playlist_id
            ).scalar()
            position = (max_position or 0) + 1
        else:
            position = track_data.position
            # Shift existing tracks
            db.query(PlaylistTrack).filter(
                and_(
                    PlaylistTrack.playlist_id == playlist_id,
                    PlaylistTrack.position >= position
                )
            ).update({PlaylistTrack.position: PlaylistTrack.position + 1})
        
        # Create playlist track
        playlist_track = PlaylistTrack(
            playlist_id=playlist_id,
            file_id=track_data.file_id,
            position=position,
            notes=track_data.notes
        )
        
        db.add(playlist_track)
        db.commit()
        db.refresh(playlist_track)
        
        # Update playlist stats
        update_playlist_stats(db, playlist_id)
        
        logger.info(f"Track added to playlist: {playlist.name}")
        
        # Get track metadata
        metadata = db.query(AudioMetadata).filter(AudioMetadata.file_id == track_data.file_id).first()
        
        return PlaylistTrackResponse(
            id=playlist_track.id,
            file_id=playlist_track.file_id,
            position=playlist_track.position,
            added_at=playlist_track.added_at,
            notes=playlist_track.notes,
            rating=playlist_track.rating,
            play_count=playlist_track.play_count,
            last_played=playlist_track.last_played,
            track_title=metadata.title if metadata else None,
            track_artist=metadata.artist if metadata else None,
            track_album=metadata.album if metadata else None,
            track_duration=metadata.duration if metadata else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding track to playlist: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.put("/{playlist_id}/tracks/{track_id}", response_model=PlaylistTrackResponse)
async def update_playlist_track(
    playlist_id: int,
    track_id: int,
    track_data: PlaylistTrackUpdate,
    db: Session = Depends(get_db)
):
    """Update a playlist track"""
    try:
        playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
        if not playlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Playlist not found"
            )
        
        playlist_track = db.query(PlaylistTrack).filter(
            and_(
                PlaylistTrack.id == track_id,
                PlaylistTrack.playlist_id == playlist_id
            )
        ).first()
        
        if not playlist_track:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Playlist track not found"
            )
        
        if track_data.position is not None:
            playlist_track.position = track_data.position
        if track_data.notes is not None:
            playlist_track.notes = track_data.notes
        if track_data.rating is not None:
            playlist_track.rating = track_data.rating
        
        db.commit()
        db.refresh(playlist_track)
        
        # Update playlist stats
        update_playlist_stats(db, playlist_id)
        
        # Get track metadata
        metadata = db.query(AudioMetadata).filter(AudioMetadata.file_id == playlist_track.file_id).first()
        
        return PlaylistTrackResponse(
            id=playlist_track.id,
            file_id=playlist_track.file_id,
            position=playlist_track.position,
            added_at=playlist_track.added_at,
            notes=playlist_track.notes,
            rating=playlist_track.rating,
            play_count=playlist_track.play_count,
            last_played=playlist_track.last_played,
            track_title=metadata.title if metadata else None,
            track_artist=metadata.artist if metadata else None,
            track_album=metadata.album if metadata else None,
            track_duration=metadata.duration if metadata else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating playlist track: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.delete("/{playlist_id}/tracks/{track_id}")
async def remove_track_from_playlist(
    playlist_id: int,
    track_id: int,
    db: Session = Depends(get_db)
):
    """Remove a track from a playlist"""
    try:
        playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
        if not playlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Playlist not found"
            )
        
        playlist_track = db.query(PlaylistTrack).filter(
            and_(
                PlaylistTrack.id == track_id,
                PlaylistTrack.playlist_id == playlist_id
            )
        ).first()
        
        if not playlist_track:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Playlist track not found"
            )
        
        # Remove track
        db.delete(playlist_track)
        db.commit()
        
        # Update playlist stats
        update_playlist_stats(db, playlist_id)
        
        logger.info(f"Track removed from playlist: {playlist.name}")
        
        return {"message": "Track removed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing track from playlist: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


