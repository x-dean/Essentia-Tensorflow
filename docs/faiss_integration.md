# FAISS Integration for Efficient Music Similarity Search

This document describes the FAISS (Facebook AI Similarity Search) integration in the EssentiaAnalyzer for efficient large-scale music similarity search and playlist generation.

## Overview

FAISS is a library for efficient similarity search and clustering of dense vectors. In our music analysis system, it's used to:

- Index music feature vectors for fast similarity search
- Scale to large music libraries (thousands to millions of tracks)
- Provide efficient playlist generation based on musical similarity
- Enable real-time music recommendations

## Features

### Automatic Index Type Selection

The system automatically chooses the optimal FAISS index type based on library size:

- **Small libraries (< 1,000 tracks)**: `IndexFlatIP` for exact search
- **Medium libraries (1,000-10,000 tracks)**: `IndexIVFFlat` with clustering
- **Large libraries (> 10,000 tracks)**: `IndexIVFPQ` for memory efficiency

### Vector Features

Each track is represented by a feature vector containing:

- **Rhythm features**: BPM, tempo confidence
- **Harmonic features**: Key strength, one-hot encoded key (12 notes), scale (major/minor)
- **MusiCNN features**: Genre probabilities, mood probabilities
- **Normalized vectors**: All vectors are L2-normalized for cosine similarity

### Persistence

- **Index saving**: FAISS indexes can be saved to disk for reuse
- **Metadata storage**: Track paths and vector dimensions are preserved
- **Fast loading**: Pre-built indexes can be loaded quickly

## Installation

### Option 1: CPU-only (Recommended for most users)

```bash
pip install faiss-cpu>=1.7.4
```

### Option 2: GPU acceleration (Requires CUDA)

```bash
pip install faiss-gpu>=1.7.4
```

### Option 3: Using Conda

```bash
# CPU version
conda install -c conda-forge faiss-cpu

# GPU version
conda install -c conda-forge faiss-gpu
```

## Usage Examples

### Basic Library Building

```python
from playlist_app.services.essentia_analyzer import EssentiaAnalyzer

# Initialize analyzer
analyzer = EssentiaAnalyzer()

# Add tracks to library
analyzer.add_to_library("track1.mp3")
analyzer.add_to_library("track2.wav")

# Add multiple tracks efficiently
audio_files = ["track3.mp3", "track4.flac", "track5.m4a"]
analyzer.add_multiple_to_library(audio_files)
```

### Similarity Search

```python
# Find similar tracks
similar_tracks = analyzer.find_similar("query_track.mp3", top_n=5)

for track_path, similarity in similar_tracks:
    print(f"{track_path}: {similarity:.3f}")
```

### Batch Search

```python
# Search for multiple queries
query_files = ["query1.mp3", "query2.wav"]
batch_results = analyzer.find_similar_batch(query_files, top_n=3)

for query_file, similar_tracks in batch_results.items():
    print(f"Similar to {query_file}:")
    for track_path, similarity in similar_tracks:
        print(f"  {track_path}: {similarity:.3f}")
```

### Index Persistence

```python
# Save index to disk
analyzer.save_index("my_music_library")

# Load index from disk
analyzer.load_index("my_music_library")

# Get library statistics
stats = analyzer.get_library_stats()
print(f"Library has {stats['total_tracks']} tracks")
```

### Vector-based Search

```python
# Extract feature vector
query_vector = analyzer.extract_feature_vector("query_track.mp3")

# Search using pre-computed vector
similar_tracks = analyzer.search_by_vector(query_vector, top_n=5)
```

## Performance Characteristics

### Search Speed

- **Small libraries (< 1K tracks)**: ~1ms per query
- **Medium libraries (1K-10K tracks)**: ~5-10ms per query
- **Large libraries (> 10K tracks)**: ~20-50ms per query

### Memory Usage

- **IndexFlatIP**: ~4 bytes per vector dimension per track
- **IndexIVFFlat**: ~4 bytes per vector dimension per track + clustering overhead
- **IndexIVFPQ**: ~1 byte per vector dimension per track (compressed)

### Accuracy vs Speed Trade-offs

- **IndexFlatIP**: 100% accuracy, slower for large libraries
- **IndexIVFFlat**: ~95-99% accuracy, good speed/accuracy balance
- **IndexIVFPQ**: ~90-95% accuracy, fastest for very large libraries

## Advanced Configuration

### Custom Index Types

```python
# For specific use cases, you can modify the index selection logic
# in the _build_faiss_index method
```

### GPU Acceleration

If you have a CUDA-capable GPU:

1. Install `faiss-gpu` instead of `faiss-cpu`
2. The system will automatically use GPU acceleration when available
3. Expect 5-10x speedup for large libraries

### Memory Optimization

For very large libraries (> 100K tracks):

- Use `IndexIVFPQ` with smaller sub-vectors (m=4 instead of m=8)
- Reduce bits per sub-vector (bits=4 instead of bits=8)
- Trade some accuracy for memory efficiency

## Troubleshooting

### FAISS Not Available

If you see "FAISS not available" warnings:

1. Install FAISS: `pip install faiss-cpu`
2. Check your Python environment
3. The system will fall back to basic similarity search

### Memory Issues

For large libraries:

1. Use CPU-only FAISS if GPU memory is limited
2. Reduce batch sizes when adding tracks
3. Consider using compressed index types

### Performance Issues

1. Ensure vectors are properly normalized
2. Check that FAISS is using the optimal index type
3. Monitor system resources during indexing

## Integration with Existing Code

The FAISS integration is designed to be:

- **Backward compatible**: Works with existing EssentiaAnalyzer code
- **Graceful degradation**: Falls back to basic search if FAISS unavailable
- **Configurable**: Can be enabled/disabled based on needs
- **Extensible**: Easy to add new index types or search methods

## Future Enhancements

Potential improvements:

- **Hierarchical indexing**: Multi-level indexes for different music attributes
- **Real-time updates**: Incremental index updates for new tracks
- **Multi-modal search**: Combine audio features with metadata
- **Distributed indexing**: Support for distributed FAISS clusters
