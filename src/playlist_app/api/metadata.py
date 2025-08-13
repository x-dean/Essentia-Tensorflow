from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
import logging
from pydantic import BaseModel

from ..models.database import get_db, File, AudioMetadata
from ..services.genre_enrichment import genre_enrichment_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/metadata", tags=["metadata"])

class EnrichGenresRequest(BaseModel):
    file_paths: List[str] = []
    force_reenrich: bool = False
    max_files: int = None

@router.post("/enrich-genres")
async def enrich_genres(
    request: EnrichGenresRequest,
    db: Session = Depends(get_db)
):
    """Enrich genre information for specified files or all files"""
    try:
        if request.file_paths:
            # Enrich specific files
            files_to_enrich = request.file_paths
        else:
            # Get all files that need enrichment
            query = db.query(File)
            if not request.force_reenrich:
                # Only files without genre or with generic genres
                query = query.filter(
                    (File.audio_metadata == None) |
                    (AudioMetadata.genre.is_(None)) |
                    (AudioMetadata.genre == "") |
                    (AudioMetadata.genre.in_(["Unknown", "unknown", "Unknown Genre"]))
                )
            
            files = query.all()
            files_to_enrich = [f.file_path for f in files]
            
            if request.max_files:
                files_to_enrich = files_to_enrich[:request.max_files]
        
        enriched_count = 0
        failed_count = 0
        
        for file_path in files_to_enrich:
            try:
                # Get file record
                file_record = db.query(File).filter(File.file_path == file_path).first()
                if not file_record:
                    continue
                
                # Get or create metadata
                metadata = db.query(AudioMetadata).filter(AudioMetadata.file_id == file_record.id).first()
                if not metadata:
                    # Create basic metadata if it doesn't exist
                    metadata = AudioMetadata(
                        file_id=file_record.id,
                        title=file_record.file_name,
                        artist="Unknown",
                        album="Unknown"
                    )
                    db.add(metadata)
                    db.commit()
                    db.refresh(metadata)
                
                # Enrich metadata
                enriched_metadata = genre_enrichment_manager.enrich_metadata({
                    'title': metadata.title,
                    'artist': metadata.artist,
                    'album': metadata.album
                })
                
                # Update metadata with enriched genre
                if enriched_metadata.get('genre'):
                    metadata.genre = enriched_metadata['genre']
                    db.commit()
                    enriched_count += 1
                    logger.info(f"Enriched genre for {file_path}: {enriched_metadata['genre']}")
                
            except Exception as e:
                logger.error(f"Failed to enrich {file_path}: {e}")
                failed_count += 1
        
        return {
            "status": "success",
            "results": {
                "total_files": len(files_to_enrich),
                "enriched": enriched_count,
                "failed": failed_count,
                "message": f"Genre enrichment completed: {enriched_count} enriched, {failed_count} failed"
            }
        }
        
    except Exception as e:
        logger.error(f"Genre enrichment failed: {e}")
        raise HTTPException(status_code=500, detail=f"Genre enrichment failed: {str(e)}")

@router.post("/force-reenrich")
async def force_reenrich_metadata(
    db: Session = Depends(get_db),
    max_files: int = None
):
    """Force re-enrich metadata for all files"""
    try:
        # Get all files with metadata
        files = db.query(File).filter(File.has_metadata == True).all()
        files_to_enrich = [f.file_path for f in files]
        
        if max_files:
            files_to_enrich = files_to_enrich[:max_files]
        
        enriched_count = 0
        failed_count = 0
        
        for file_path in files_to_enrich:
            try:
                # Get file record
                file_record = db.query(File).filter(File.file_path == file_path).first()
                if not file_record:
                    continue
                
                # Get metadata
                metadata = db.query(AudioMetadata).filter(AudioMetadata.file_id == file_record.id).first()
                if not metadata:
                    continue
                
                # Re-enrich metadata
                enriched_metadata = genre_enrichment_manager.enrich_metadata({
                    'title': metadata.title,
                    'artist': metadata.artist,
                    'album': metadata.album
                })
                
                # Update metadata with enriched information
                if enriched_metadata.get('genre'):
                    metadata.genre = enriched_metadata['genre']
                if enriched_metadata.get('year'):
                    metadata.year = enriched_metadata['year']
                
                db.commit()
                enriched_count += 1
                logger.info(f"Re-enriched metadata for {file_path}")
                
            except Exception as e:
                logger.error(f"Failed to re-enrich {file_path}: {e}")
                failed_count += 1
        
        return {
            "status": "success",
            "results": {
                "total_files": len(files_to_enrich),
                "enriched": enriched_count,
                "failed": failed_count,
                "message": f"Metadata re-enrichment completed: {enriched_count} enriched, {failed_count} failed"
            }
        }
        
    except Exception as e:
        logger.error(f"Metadata re-enrichment failed: {e}")
        raise HTTPException(status_code=500, detail=f"Metadata re-enrichment failed: {str(e)}")

@router.get("/search")
async def search_metadata(
    query: str = "",
    artist: str = "",
    album: str = "",
    genre: str = "",
    year: int = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Search metadata"""
    try:
        # Build query
        metadata_query = db.query(AudioMetadata)
        
        if query:
            metadata_query = metadata_query.filter(
                (AudioMetadata.title.ilike(f"%{query}%")) |
                (AudioMetadata.artist.ilike(f"%{query}%")) |
                (AudioMetadata.album.ilike(f"%{query}%"))
            )
        
        if artist:
            metadata_query = metadata_query.filter(AudioMetadata.artist.ilike(f"%{artist}%"))
        
        if album:
            metadata_query = metadata_query.filter(AudioMetadata.album.ilike(f"%{album}%"))
        
        if genre:
            metadata_query = metadata_query.filter(AudioMetadata.genre.ilike(f"%{genre}%"))
        
        if year:
            metadata_query = metadata_query.filter(AudioMetadata.year == year)
        
        # Get total count
        total_count = metadata_query.count()
        
        # Get paginated results
        results = metadata_query.offset(offset).limit(limit).all()
        
        # Convert to list of dictionaries
        metadata_list = []
        for metadata in results:
            metadata_list.append({
                "id": metadata.id,
                "file_id": metadata.file_id,
                "title": metadata.title,
                "artist": metadata.artist,
                "album": metadata.album,
                "track_number": metadata.track_number,
                "year": metadata.year,
                "genre": metadata.genre,
                "duration": metadata.duration,
                "bpm": metadata.bpm,
                "key": metadata.key
            })
        
        return {
            "success": True,
            "results": metadata_list,
            "total_count": total_count,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Error searching metadata: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/{file_id}")
async def get_file_metadata(
    file_id: int,
    db: Session = Depends(get_db)
):
    """Get metadata for a specific file"""
    try:
        # First check if the file exists
        file_record = db.query(File).filter(File.id == file_id).first()
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Get the metadata record
        metadata = db.query(AudioMetadata).filter(AudioMetadata.file_id == file_id).first()
        if not metadata:
            # Return empty metadata structure instead of 404
            return {
                "success": True,
                "metadata": {
                    "id": None,
                    "file_id": file_id,
                    "title": None,
                    "artist": None,
                    "album": None,
                    "track_number": None,
                    "year": None,
                    "genre": None,
                    "album_artist": None,
                    "disc_number": None,
                    "composer": None,
                    "duration": None,
                    "bpm": None,
                    "key": None,
                    "comment": None,
                    "mood": None,
                    "rating": None,
                    "isrc": None,
                    "encoder": None,
                    "bitrate": None,
                    "sample_rate": None,
                    "channels": None,
                    "format": None,
                    "file_size": None,
                    "file_format": None,
                    "replaygain_track_gain": None,
                    "replaygain_album_gain": None,
                    "replaygain_track_peak": None,
                    "replaygain_album_peak": None,
                    "musicbrainz_track_id": None,
                    "musicbrainz_artist_id": None,
                    "musicbrainz_album_id": None,
                    "musicbrainz_album_artist_id": None,
                    "created_at": None,
                    "updated_at": None
                },
                "message": "No metadata found for this file. Metadata is automatically extracted during discovery."
            }
        
        # Convert to dictionary
        metadata_dict = {
            "id": metadata.id,
            "file_id": metadata.file_id,
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
            "created_at": metadata.created_at,
            "updated_at": metadata.updated_at
        }
        
        return {
            "success": True,
            "metadata": metadata_dict
        }
        
    except Exception as e:
        logger.error(f"Error getting metadata for file {file_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get metadata: {str(e)}")

@router.get("/stats/overview")
async def get_metadata_stats(db: Session = Depends(get_db)):
    """Get metadata analysis statistics"""
    try:
        # Get total files
        total_files = db.query(File).count()
        
        # Get analyzed files
        analyzed_files = db.query(File).filter(File.has_metadata == True).count()
        
        # Get files with metadata
        files_with_metadata = db.query(AudioMetadata).count()
        
        # Get genre distribution
        genre_stats = db.query(AudioMetadata.genre, func.count(AudioMetadata.id)).\
            filter(AudioMetadata.genre.isnot(None)).\
            group_by(AudioMetadata.genre).\
            order_by(func.count(AudioMetadata.id).desc()).\
            limit(10).all()
        
        # Get year distribution
        year_stats = db.query(AudioMetadata.year, func.count(AudioMetadata.id)).\
            filter(AudioMetadata.year.isnot(None)).\
            group_by(AudioMetadata.year).\
            order_by(AudioMetadata.year.desc()).\
            limit(10).all()
        
        return {
            "success": True,
            "stats": {
                "total_files": total_files,
                "analyzed_files": analyzed_files,
                "files_with_metadata": files_with_metadata,
                "analysis_percentage": round((analyzed_files / total_files * 100) if total_files > 0 else 0, 2),
                "top_genres": [{"genre": genre, "count": count} for genre, count in genre_stats],
                "top_years": [{"year": year, "count": count} for year, count in year_stats]
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting metadata stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
