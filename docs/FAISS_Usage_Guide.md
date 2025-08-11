# FAISS Usage Guide for Music Similarity Search

This guide explains how to use FAISS (Facebook AI Similarity Search) for high-performance music similarity search and playlist generation in the playlist application.

## Table of Contents

1. [Overview](#overview)
2. [Basic Usage](#basic-usage)
3. [API Endpoints](#api-endpoints)
4. [Python Service Usage](#python-service-usage)
5. [Playlist Generation](#playlist-generation)
6. [Performance Optimization](#performance-optimization)
7. [Troubleshooting](#troubleshooting)

## Overview

FAISS is a library for efficient similarity search and clustering of dense vectors. In our application, it's used to:

- **Build vector indexes** from audio analysis results
- **Find similar tracks** based on musical features
- **Generate playlists** from seed tracks
- **Enable fast similarity search** across large music libraries

### Key Features

- **High Performance**: Sub-second similarity search across thousands of tracks
- **Musical Features**: Uses tempo, key, scale, dominant chroma, and MusiCNN genre tags
- **Vector Dimension**: 67-dimensional feature vectors (including 50 MusiCNN tags)
- **Database Integration**: Persistent storage with PostgreSQL
- **REST API**: Full HTTP API for integration

## Basic Usage

### 1. Building the FAISS Index

The first step is to build a FAISS index from your analyzed tracks:

```python
from playlist_app.services.faiss_service import faiss_service
from playlist_app.models.database import SessionLocal

# Get database session
db = SessionLocal()

# Build index from database
result = faiss_service.build_index_from_database(
    db=db,
    include_tensorflow=True,  # Include MusiCNN features
    force_rebuild=False       # Don't rebuild if exists
)

print(f"Index built with {result['total_vectors']} vectors")
print(f"Vector dimension: {result['vector_dimension']}")
print(f"Build time: {result['build_time']:.2f}s")
```

### 2. Finding Similar Tracks

Once the index is built, you can find similar tracks:

```python
# Find tracks similar to a query file
similar_tracks = faiss_service.find_similar_tracks(
    db=db,
    query_path="/music/track.mp3",
    top_n=5
)

for track_path, similarity in similar_tracks:
    print(f"{track_path}: {similarity:.3f}")
```

### 3. Adding New Tracks

Add new tracks to the existing index:

```python
# Add a single track
result = faiss_service.add_track_to_index(
    db=db,
    file_path="/music/new_track.mp3",
    include_tensorflow=True
)

if "error" not in result:
    print("Track added successfully!")
```

## API Endpoints

The application provides REST API endpoints for FAISS functionality:

### Build Index

```bash
# Build FAISS index from database
curl -X POST "http://localhost:8000/api/faiss/build-index?include_tensorflow=true&force_rebuild=false"
```

**Response:**
```json
{
  "success": true,
  "total_vectors": 100,
  "vector_dimension": 67,
  "build_time": 12.34,
  "index_type": "IndexFlatIP"
}
```

### Get Statistics

```bash
# Get index statistics
curl -X GET "http://localhost:8000/api/faiss/statistics"
```

**Response:**
```json
{
  "index_name": "music_library",
  "index_type": "IndexFlatIP",
  "vector_dimension": 67,
  "total_vectors": 100,
  "indexed_vectors": 95,
  "total_files": 150,
  "analyzed_files": 100,
  "indexed_files": 95,
  "index_coverage": 95.0,
  "build_time": 12.34,
  "faiss_available": true,
  "index_loaded": true
}
```

### Find Similar Tracks

```bash
# Find similar tracks
curl -X GET "http://localhost:8000/api/faiss/similar-tracks?query_path=/music/track.mp3&top_n=5"
```

**Response:**
```json
{
  "query_file": "/music/track.mp3",
  "query_name": "track.mp3",
  "total_results": 5,
  "similar_tracks": [
    {
      "track_path": "/music/similar1.mp3",
      "track_name": "similar1.mp3",
      "similarity": 0.987
    },
    {
      "track_path": "/music/similar2.mp3",
      "track_name": "similar2.mp3",
      "similarity": 0.945
    }
  ]
}
```

### Generate Playlist

```bash
# Generate playlist from seed track
curl -X POST "http://localhost:8000/api/faiss/generate-playlist?seed_track=/music/seed.mp3&playlist_length=10"
```

**Response:**
```json
{
  "seed_track": "/music/seed.mp3",
  "seed_name": "seed.mp3",
  "playlist_length": 10,
  "requested_length": 10,
  "playlist": [
    {
      "track_path": "/music/track1.mp3",
      "track_name": "track1.mp3",
      "similarity": 0.987
    }
  ],
  "statistics": {
    "average_similarity": 0.856,
    "min_similarity": 0.723,
    "max_similarity": 0.987,
    "similarity_range": 0.264
  }
}
```

### Extract Feature Vector

```bash
# Extract feature vector from audio file
curl -X POST "http://localhost:8000/api/faiss/extract-vector?file_path=/music/track.mp3&include_tensorflow=true&normalize=true"
```

**Response:**
```json
{
  "file_path": "/music/track.mp3",
  "file_name": "track.mp3",
  "vector_dimension": 67,
  "include_tensorflow": true,
  "normalized": true,
  "vector": [0.1, 0.2, 0.3, ...]
}
```

## Python Service Usage

### Complete Example

```python
#!/usr/bin/env python3
"""
Complete FAISS usage example
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from playlist_app.services.faiss_service import faiss_service
from playlist_app.models.database import SessionLocal

def main():
    # Get database session
    db = SessionLocal()
    
    try:
        # 1. Build index
        print("Building FAISS index...")
        result = faiss_service.build_index_from_database(
            db=db,
            include_tensorflow=True,
            force_rebuild=False
        )
        
        if "error" in result:
            print(f"Error: {result['error']}")
            return
        
        print(f"Index built: {result['total_vectors']} vectors")
        
        # 2. Get statistics
        stats = faiss_service.get_index_statistics(db)
        print(f"Index coverage: {stats['index_coverage']:.1f}%")
        
        # 3. Find similar tracks
        query_file = "/music/example.mp3"
        if os.path.exists(query_file):
            similar_tracks = faiss_service.find_similar_tracks(
                db=db,
                query_path=query_file,
                top_n=5
            )
            
            print(f"\nSimilar to {os.path.basename(query_file)}:")
            for track_path, similarity in similar_tracks:
                track_name = os.path.basename(track_path)
                print(f"  {track_name}: {similarity:.3f}")
        
        # 4. Generate playlist
        if os.path.exists(query_file):
            playlist_tracks = faiss_service.find_similar_tracks(
                db=db,
                query_path=query_file,
                top_n=10
            )
            
            print(f"\nGenerated playlist:")
            for i, (track_path, similarity) in enumerate(playlist_tracks, 1):
                track_name = os.path.basename(track_path)
                print(f"  {i:2d}. {track_name} (similarity: {similarity:.3f})")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
```

## Playlist Generation

### Basic Playlist Generation

```python
def generate_playlist(seed_track, playlist_length=10):
    """Generate a playlist from a seed track"""
    
    db = SessionLocal()
    
    try:
        # Ensure index is loaded
        faiss_service.load_index_from_database(db)
        
        # Find similar tracks
        similar_tracks = faiss_service.find_similar_tracks(
            db=db,
            query_path=seed_track,
            top_n=playlist_length
        )
        
        # Format playlist
        playlist = []
        for track_path, similarity in similar_tracks:
            playlist.append({
                "track_path": track_path,
                "track_name": os.path.basename(track_path),
                "similarity": similarity
            })
        
        return playlist
        
    finally:
        db.close()

# Usage
playlist = generate_playlist("/music/seed_track.mp3", 15)
for track in playlist:
    print(f"{track['track_name']}: {track['similarity']:.3f}")
```

### Advanced Playlist Generation

```python
def generate_diverse_playlist(seed_track, playlist_length=10, diversity_threshold=0.8):
    """Generate a diverse playlist with similarity threshold"""
    
    db = SessionLocal()
    
    try:
        # Get more candidates than needed
        candidates = faiss_service.find_similar_tracks(
            db=db,
            query_path=seed_track,
            top_n=playlist_length * 3  # Get more candidates
        )
        
        # Filter by diversity threshold
        playlist = []
        for track_path, similarity in candidates:
            if similarity >= diversity_threshold:
                playlist.append({
                    "track_path": track_path,
                    "track_name": os.path.basename(track_path),
                    "similarity": similarity
                })
                
                if len(playlist) >= playlist_length:
                    break
        
        return playlist
        
    finally:
        db.close()
```

## Performance Optimization

### Index Types

The application uses different FAISS index types based on your needs:

- **IndexFlatIP**: Exact search, highest accuracy, slower for large datasets
- **IndexIVFFlat**: Approximate search, good balance of speed/accuracy
- **IndexHNSW**: Hierarchical search, fastest for large datasets

### Performance Tips

1. **Batch Operations**: Use batch methods for multiple tracks
2. **Index Persistence**: Save and load indexes to avoid rebuilding
3. **Vector Normalization**: Enable normalization for better similarity scores
4. **GPU Acceleration**: Use FAISS-GPU for large datasets

### Performance Monitoring

```python
import time

def benchmark_search(query_file, num_searches=10):
    """Benchmark search performance"""
    
    db = SessionLocal()
    
    try:
        total_time = 0
        
        for i in range(num_searches):
            start_time = time.time()
            
            similar_tracks = faiss_service.find_similar_tracks(
                db=db,
                query_path=query_file,
                top_n=5
            )
            
            search_time = time.time() - start_time
            total_time += search_time
            
            print(f"Search {i+1}: {search_time:.3f}s")
        
        avg_time = total_time / num_searches
        print(f"Average search time: {avg_time:.3f}s")
        print(f"Searches per second: {1/avg_time:.1f}")
        
    finally:
        db.close()
```

## Troubleshooting

### Common Issues

#### 1. "FAISS not available" Error

**Problem**: FAISS library not installed
**Solution**: Install FAISS
```bash
pip install faiss-cpu  # CPU version
# or
pip install faiss-gpu  # GPU version
```

#### 2. "No analyzed files found" Error

**Problem**: No tracks have been analyzed yet
**Solution**: Analyze tracks first
```python
from playlist_app.services.audio_analysis_service import AudioAnalysisService

service = AudioAnalysisService()
service.analyze_file(db, "/music/track.mp3", include_tensorflow=True)
```

#### 3. "Index not found" Error

**Problem**: FAISS index doesn't exist
**Solution**: Build the index
```python
faiss_service.build_index_from_database(db, include_tensorflow=True)
```

#### 4. Low Similarity Scores

**Problem**: Tracks are too different
**Solutions**:
- Check if tracks are in the same genre
- Verify audio quality
- Try different similarity thresholds

### Debug Information

Enable debug logging to troubleshoot issues:

```python
import logging
logging.getLogger("playlist_app.services.faiss_service").setLevel(logging.DEBUG)
```

### Index Statistics

Check index health:

```python
stats = faiss_service.get_index_statistics(db)
print(f"Index coverage: {stats['index_coverage']:.1f}%")
print(f"Total vectors: {stats['total_vectors']}")
print(f"FAISS available: {stats['faiss_available']}")
print(f"Index loaded: {stats['index_loaded']}")
```

## Advanced Features

### Custom Similarity Metrics

```python
def custom_similarity_search(query_vector, top_n=5):
    """Custom similarity search with additional filtering"""
    
    db = SessionLocal()
    
    try:
        # Get all vectors from database
        vector_records = db.query(VectorIndex).all()
        
        similarities = []
        for record in vector_records:
            vector_data = json.loads(record.vector_data)
            vector = np.array(vector_data, dtype=np.float32)
            
            # Custom similarity calculation
            sim = np.dot(query_vector, vector) / (np.linalg.norm(query_vector) * np.linalg.norm(vector))
            
            # Additional filtering (e.g., by genre, tempo)
            if sim > 0.5:  # Minimum similarity threshold
                similarities.append((record.file.file_path, float(sim)))
        
        # Sort and return top N
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_n]
        
    finally:
        db.close()
```

### Index Maintenance

```python
def maintain_index():
    """Maintain FAISS index"""
    
    db = SessionLocal()
    
    try:
        # 1. Check for new tracks
        new_tracks = db.query(File).filter(
            File.is_analyzed == True,
            ~File.id.in_(db.query(VectorIndex.file_id).subquery())
        ).all()
        
        # 2. Add new tracks to index
        for track in new_tracks:
            faiss_service.add_track_to_index(db, track.file_path)
        
        # 3. Remove deleted tracks
        # (Implementation depends on your deletion tracking)
        
        # 4. Save updated index
        faiss_service.save_index_to_disk(".")
        
        print(f"Index maintained: {len(new_tracks)} new tracks added")
        
    finally:
        db.close()
```

## Conclusion

FAISS provides powerful similarity search capabilities for music applications. With the provided API and Python service, you can:

- Build efficient vector indexes from audio analysis
- Find similar tracks in milliseconds
- Generate playlists automatically
- Scale to large music libraries
- Integrate with web applications via REST API

The combination of Essentia audio analysis and FAISS similarity search creates a robust foundation for music recommendation and playlist generation systems.
