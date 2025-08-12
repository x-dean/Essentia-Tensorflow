"""
FAISS API Router

Provides REST endpoints for FAISS vector similarity search and index management.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import os

from ..models.database import get_db
from ..services.faiss_service import faiss_service
from ..services.essentia_analyzer import essentia_analyzer

router = APIRouter(prefix="/api/faiss", tags=["FAISS"])

@router.get("/status")
async def get_faiss_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get FAISS service status"""
    try:
        # Check if FAISS is available
        try:
            import faiss
            faiss_available = True
            faiss_version = faiss.__version__
        except ImportError:
            faiss_available = False
            faiss_version = None
        
        # Check if index exists
        index_exists = faiss_service.index_exists()
        
        # Get basic stats if index exists
        stats = {}
        if index_exists:
            try:
                stats = faiss_service.get_index_statistics(db)
            except Exception:
                stats = {"error": "Could not get statistics"}
        
        return {
            "status": "operational" if faiss_available else "error",
            "service": "faiss",
            "faiss_available": faiss_available,
            "faiss_version": faiss_version,
            "index_exists": index_exists,
            "statistics": stats
        }
    except Exception as e:
        return {
            "status": "error",
            "service": "faiss",
            "error": str(e)
        }

@router.post("/build-index")
async def build_index(
    include_tensorflow: bool = Query(True, description="Include MusiCNN features"),
    force_rebuild: bool = Query(False, description="Force rebuild existing index"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Build FAISS index from analyzed tracks in database.
    
    Args:
        include_tensorflow: Whether to include MusiCNN features
        force_rebuild: Whether to force rebuild existing index
        db: Database session
        
    Returns:
        Build results
    """
    try:
        result = faiss_service.build_index_from_database(
            db=db,
            include_tensorflow=include_tensorflow,
            force_rebuild=force_rebuild
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build index: {str(e)}")

@router.get("/statistics")
async def get_index_statistics(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get FAISS index statistics.
    
    Args:
        db: Database session
        
    Returns:
        Index statistics
    """
    try:
        stats = faiss_service.get_index_statistics(db)
        
        if "error" in stats:
            raise HTTPException(status_code=400, detail=stats["error"])
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")

@router.post("/add-track")
async def add_track_to_index(
    file_path: str = Query(..., description="Path to audio file"),
    include_tensorflow: bool = Query(True, description="Include MusiCNN features"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Add a single track to the FAISS index.
    
    Args:
        file_path: Path to audio file
        include_tensorflow: Whether to include MusiCNN features
        db: Database session
        
    Returns:
        Add results
    """
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
        result = faiss_service.add_track_to_index(
            db=db,
            file_path=file_path,
            include_tensorflow=include_tensorflow
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add track: {str(e)}")

@router.get("/similar-tracks")
async def find_similar_tracks(
    query_path: str = Query(..., description="Path to query audio file"),
    top_n: int = Query(5, ge=1, le=50, description="Number of similar tracks to return"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Find similar tracks using FAISS index.
    
    Args:
        query_path: Path to query audio file
        top_n: Number of similar tracks to return
        db: Database session
        
    Returns:
        List of similar tracks with similarity scores
    """
    try:
        # Check if query file exists
        if not os.path.exists(query_path):
            raise HTTPException(status_code=404, detail=f"Query file not found: {query_path}")
        
        similar_tracks = faiss_service.find_similar_tracks(
            db=db,
            query_path=query_path,
            top_n=top_n
        )
        
        # Format results
        results = []
        for track_path, similarity in similar_tracks:
            track_name = os.path.basename(track_path)
            results.append({
                "track_path": track_path,
                "track_name": track_name,
                "similarity": similarity
            })
        
        return {
            "query_file": query_path,
            "query_name": os.path.basename(query_path),
            "total_results": len(results),
            "similar_tracks": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to find similar tracks: {str(e)}")

@router.post("/similar-by-vector")
async def find_similar_by_vector(
    query_vector: List[float] = Query(..., description="Query feature vector"),
    top_n: int = Query(5, ge=1, le=50, description="Number of similar tracks to return"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Find similar tracks using a pre-computed feature vector.
    
    Args:
        query_vector: Query feature vector
        top_n: Number of similar tracks to return
        db: Database session
        
    Returns:
        List of similar tracks with similarity scores
    """
    try:
        import numpy as np
        
        # Convert to numpy array
        query_array = np.array(query_vector, dtype=np.float32)
        
        similar_tracks = faiss_service.find_similar_by_vector(
            db=db,
            query_vector=query_array,
            top_n=top_n
        )
        
        # Format results
        results = []
        for track_path, similarity in similar_tracks:
            track_name = os.path.basename(track_path)
            results.append({
                "track_path": track_path,
                "track_name": track_name,
                "similarity": similarity
            })
        
        return {
            "vector_dimension": len(query_vector),
            "total_results": len(results),
            "similar_tracks": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to find similar tracks: {str(e)}")

@router.post("/extract-vector")
async def extract_feature_vector(
    file_path: str = Query(..., description="Path to audio file"),
    include_tensorflow: bool = Query(True, description="Include MusiCNN features"),
    normalize: bool = Query(True, description="Normalize the vector")
) -> Dict[str, Any]:
    """
    Extract feature vector from audio file.
    
    Args:
        file_path: Path to audio file
        include_tensorflow: Whether to include MusiCNN features
        normalize: Whether to normalize the vector
        
    Returns:
        Feature vector and metadata
    """
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
        # Extract feature vector
        vector = essentia_analyzer.extract_feature_vector(
            file_path,
            include_tensorflow=include_tensorflow,
            normalize=normalize
        )
        
        return {
            "file_path": file_path,
            "file_name": os.path.basename(file_path),
            "vector_dimension": len(vector),
            "include_tensorflow": include_tensorflow,
            "normalized": normalize,
            "vector": vector.tolist()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract vector: {str(e)}")

@router.post("/generate-playlist")
async def generate_playlist(
    seed_track: str = Query(..., description="Path to seed track"),
    playlist_length: int = Query(10, ge=1, le=50, description="Length of playlist"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Generate a playlist from a seed track using FAISS similarity search.
    
    Args:
        seed_track: Path to seed track
        playlist_length: Length of playlist
        db: Database session
        
    Returns:
        Generated playlist
    """
    try:
        # Check if seed track exists
        if not os.path.exists(seed_track):
            raise HTTPException(status_code=404, detail=f"Seed track not found: {seed_track}")
        
        # Find similar tracks
        similar_tracks = faiss_service.find_similar_tracks(
            db=db,
            query_path=seed_track,
            top_n=playlist_length
        )
        
        # Format playlist
        playlist = []
        for track_path, similarity in similar_tracks:
            track_name = os.path.basename(track_path)
            playlist.append({
                "track_path": track_path,
                "track_name": track_name,
                "similarity": similarity
            })
        
        # Calculate playlist statistics
        if playlist:
            similarities = [track["similarity"] for track in playlist]
            avg_similarity = sum(similarities) / len(similarities)
            min_similarity = min(similarities)
            max_similarity = max(similarities)
        else:
            avg_similarity = min_similarity = max_similarity = 0.0
        
        return {
            "seed_track": seed_track,
            "seed_name": os.path.basename(seed_track),
            "playlist_length": len(playlist),
            "requested_length": playlist_length,
            "playlist": playlist,
            "statistics": {
                "average_similarity": avg_similarity,
                "min_similarity": min_similarity,
                "max_similarity": max_similarity,
                "similarity_range": max_similarity - min_similarity
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate playlist: {str(e)}")

@router.post("/save-index")
async def save_index_to_disk(
    base_path: str = Query(".", description="Base path for saving index files")
) -> Dict[str, Any]:
    """
    Save FAISS index to disk.
    
    Args:
        base_path: Base path for saving index files
        
    Returns:
        Save results
    """
    try:
        success = faiss_service.save_index_to_disk(base_path)
        
        if success:
            return {
                "success": True,
                "message": "Index saved successfully",
                "base_path": base_path,
                "files": [
                    f"{faiss_service.index_name}.faiss",
                    f"{faiss_service.index_name}.json"
                ]
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to save index")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save index: {str(e)}")

@router.post("/load-index")
async def load_index_from_database(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Load FAISS index from database.
    
    Args:
        db: Database session
        
    Returns:
        Load results
    """
    try:
        result = faiss_service.load_index_from_database(db)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load index: {str(e)}")
