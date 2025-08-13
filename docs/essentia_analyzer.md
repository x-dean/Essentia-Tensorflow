# Essentia Audio Analyzer

A comprehensive audio analysis system using Essentia and TensorFlow for extracting musical features from audio tracks.

## Overview

The Essentia analyzer provides:

- **Basic audio features**: RMS, energy, loudness, spectral characteristics
- **Rhythm analysis**: Tempo, beat tracking, onset detection
- **Harmonic analysis**: Pitch, key detection, chord recognition
- **TensorFlow integration**: Pre-trained models for advanced analysis
- **Database persistence**: Store and retrieve analysis results
- **Batch processing**: Analyze multiple files efficiently

## Quick Notes & Caveats

### Model Compatibility
- **MusiCNN input shape**: Must adapt `compute_mel_log()` and input reshaping to match exact input shape (n_mels, time, channels)
- **Sample rate matching**: If your model was trained on 22.05 kHz, either retrain or resample to match — otherwise accuracy drops
- **TensorFlow model availability**: Models are optional and gracefully handled if not available

### Essentia Availability
- **Fallback support**: If Essentia is not installed, the pipeline falls back to librosa for descriptors
- **Feature differences**: Essentia gives slightly different/possibly better features but is optional for core pipeline

### Memory Management
- **Resource limits**: `resource.setrlimit(RLIMIT_AS)` enforces per-process address-space caps on Linux
- **Worker OOM prevention**: Can cause worker OOM kills if set too low. Start with `per_worker_mem_mb = 900` and tune
- **Memory monitoring**: Monitor memory usage during batch processing

### Performance Tradeoffs
- **Sample rate impact**: Raising sample rate to 44.1 kHz improves quality but increases CPU and memory
- **Concurrency tuning**: You must lower concurrency to hold total RAM under 4 GB
- **Chunk processing**: Long tracks are processed in chunks to manage memory

### Edge Cases
- **Short tracks**: Very short tracks (< chunk length) are processed full-track
- **Long tracks**: Use `select_novelty_chunks` or increase `n_chunks` if you want more coverage
- **Silent audio**: Handled gracefully with silence detection

## Configuration

### AudioAnalysisConfig

```python
@dataclass
class AudioAnalysisConfig:
    sample_rate: int = 44100          # Target sample rate
    channels: int = 1                 # Mono audio
    frame_size: int = 2048            # FFT frame size
    hop_size: int = 1024              # Frame hop size
    window_type: str = 'hann'         # Window function
    zero_padding: int = 0             # Zero padding for FFT
    min_frequency: float = 20.0       # Minimum frequency for analysis
    max_frequency: float = 8000.0     # Maximum frequency for analysis
    n_mels: int = 96                  # Number of mel bands
    n_mfcc: int = 40                  # Number of MFCC coefficients
    n_spectral_peaks: int = 100       # Number of spectral peaks
    silence_threshold: float = -60.0  # Silence detection threshold
    min_track_length: float = 1.0     # Minimum track length (seconds)
    max_track_length: float = 600.0   # Maximum track length (seconds)
    chunk_duration: float = 30.0      # Chunk duration for long tracks
    overlap_ratio: float = 0.5        # Overlap between chunks
```

### Environment Variables

```bash
# Audio processing
AUDIO_SAMPLE_RATE=44100
AUDIO_CHANNELS=1
AUDIO_FRAME_SIZE=2048
AUDIO_HOP_SIZE=1024

# Memory management
PER_WORKER_MEM_MB=900
MAX_CONCURRENT_ANALYSIS=4

# TensorFlow settings
ENABLE_TENSORFLOW=true
TENSORFLOW_MODELS=musicnn,tempo_cnn,vggish
```

## Usage Examples

### Basic Analysis

```python
from src.playlist_app.services.essentia_analyzer import essentia_analyzer

# Analyze a single file
results = essentia_analyzer.analyze_audio_file("path/to/audio.mp3")

# Get analysis summary
summary = essentia_analyzer.get_analysis_summary(results)
print(f"Tempo: {summary['key_features']['tempo']} BPM")
print(f"Key: {summary['key_features']['key']} {summary['key_features']['scale']}")
```

### Database Integration

```python
from src.playlist_app.services.audio_analysis_service import audio_analysis_service
from src.playlist_app.models.database import SessionLocal

db = SessionLocal()

# Analyze and store in database
results = audio_analysis_service.analyze_file(db, "path/to/audio.mp3")

# Retrieve analysis
stored_results = audio_analysis_service.get_analysis(db, "path/to/audio.mp3")

# Get summary
summary = audio_analysis_service.get_analysis_summary(db, "path/to/audio.mp3")
```

### Batch Processing

```python
# Analyze multiple files
file_paths = ["track1.mp3", "track2.mp3", "track3.mp3"]
batch_results = audio_analysis_service.analyze_files_batch(db, file_paths)

print(f"Successfully analyzed: {batch_results['successful']}")
print(f"Failed: {batch_results['failed']}")
```

### API Usage

```bash
# Analyze a single file
curl -X POST "http://localhost:8000/api/analyzer/analyze-file" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "music/track.mp3", "include_tensorflow": true}'

# Get analysis results
curl "http://localhost:8000/api/analyzer/analysis/music/track.mp3"

# Get analysis summary
curl "http://localhost:8000/api/analyzer/analysis-summary/music/track.mp3"

# Get unanalyzed files
curl "http://localhost:8000/api/analyzer/unanalyzed-files?limit=10"

# Get statistics
curl "http://localhost:8000/api/analyzer/statistics"
```

## Feature Extraction

### Basic Features

- **RMS**: Root Mean Square energy
- **Energy**: Total energy of the signal
- **Loudness**: Perceived loudness
- **Spectral Centroid**: Brightness of the sound
- **Spectral Rolloff**: Frequency below which 85% of energy is contained
- **Spectral Contrast**: Difference between peaks and valleys
- **Spectral Complexity**: Measure of spectral complexity
- **MFCC**: Mel-frequency cepstral coefficients

### Rhythm Features

- **Tempo**: Estimated tempo in BPM
- **Beat Tracking**: Precise beat timestamps
- **Rhythm Confidence**: Confidence in rhythm analysis
- **Onset Detection**: Detection of note onsets
- **Rhythm Ticks**: Rhythm pattern analysis

### Harmonic Features

- **Key Detection**: Musical key (e.g., "C", "F#")
- **Scale**: Major or minor scale
- **Key Strength**: Confidence in key detection
- **Chord Detection**: Chord progression analysis
- **Pitch Analysis**: Fundamental frequency tracking
- **Chromagram**: Chromatic feature representation

### TensorFlow Features

- **MusiCNN**: Music analysis with convolutional neural networks
- **TempoCNN**: Tempo estimation using CNNs
- **VGGish**: Audio feature extraction
- **FSDSINet**: Sound event detection

## Database Schema

### AudioAnalysis Table

```sql
CREATE TABLE audio_analysis (
    id SERIAL PRIMARY KEY,
    file_id INTEGER REFERENCES files(id),
    
    -- Analysis metadata
    analysis_timestamp TIMESTAMP,
    analysis_duration FLOAT,
    sample_rate INTEGER,
    duration FLOAT,
    
    -- Basic features
    rms FLOAT,
    energy FLOAT,
    loudness FLOAT,
    spectral_centroid_mean FLOAT,
    spectral_centroid_std FLOAT,
    spectral_rolloff_mean FLOAT,
    spectral_rolloff_std FLOAT,
    spectral_contrast_mean FLOAT,
    spectral_contrast_std FLOAT,
    spectral_complexity_mean FLOAT,
    spectral_complexity_std FLOAT,
    
    -- MFCC features (JSON)
    mfcc_mean TEXT,
    mfcc_bands_mean TEXT,
    
    -- Rhythm features
    tempo FLOAT,
    tempo_confidence FLOAT,
    rhythm_bpm FLOAT,
    rhythm_confidence FLOAT,
    beat_confidence FLOAT,
    beats TEXT,  -- JSON array
    rhythm_ticks TEXT,  -- JSON array
    rhythm_estimates TEXT,  -- JSON array
    onset_detections TEXT,  -- JSON array
    
    -- Harmonic features
    key VARCHAR,
    scale VARCHAR,
    key_strength FLOAT,
    chords TEXT,  -- JSON array
    chord_strengths TEXT,  -- JSON array
    pitch_yin TEXT,  -- JSON array
    pitch_yin_confidence TEXT,  -- JSON array
    pitch_melodia TEXT,  -- JSON array
    pitch_melodia_confidence TEXT,  -- JSON array
    chromagram TEXT,  -- JSON array
    
    -- TensorFlow features (JSON)
    tensorflow_features TEXT,
    
    -- Complete analysis (JSON)
    complete_analysis TEXT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## Performance Optimization

### Memory Management

1. **Chunk Processing**: Long tracks are processed in chunks
2. **Resource Limits**: Set appropriate memory limits per worker
3. **Garbage Collection**: Explicit cleanup after analysis
4. **Streaming**: Process audio in frames to reduce memory usage

### CPU Optimization

1. **Parallel Processing**: Use multiple workers for batch analysis
2. **Algorithm Selection**: Choose appropriate algorithms for your use case
3. **Sample Rate**: Balance quality vs performance
4. **Caching**: Cache intermediate results when possible

### Database Optimization

1. **Indexing**: Index frequently queried fields
2. **JSON Storage**: Store large arrays as JSON for flexibility
3. **Batch Operations**: Use batch inserts for multiple analyses
4. **Connection Pooling**: Reuse database connections

## Error Handling

### Common Issues

1. **File Not Found**: Audio file doesn't exist
2. **Unsupported Format**: Audio format not supported
3. **Corrupted Audio**: Audio file is corrupted
4. **Memory Issues**: Insufficient memory for analysis
5. **TensorFlow Errors**: Model loading or inference failures

### Error Recovery

```python
try:
    results = essentia_analyzer.analyze_audio_file("track.mp3")
except FileNotFoundError:
    logger.error("Audio file not found")
except ValueError as e:
    logger.error(f"Invalid audio file: {e}")
except MemoryError:
    logger.error("Insufficient memory for analysis")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
```

## Testing

### Unit Tests

```python
import pytest
from src.playlist_app.services.essentia_analyzer import essentia_analyzer

def test_basic_feature_extraction():
    # Generate test audio
    import numpy as np
    sr = 44100
    t = np.linspace(0, 1, sr)
    test_audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)
    
    # Test basic features
    features = essentia_analyzer.extract_basic_features(test_audio)
    assert 'rms' in features
    assert 'energy' in features
    assert 'loudness' in features

def test_rhythm_analysis():
    # Test rhythm features
    features = essentia_analyzer.extract_rhythm_features(test_audio)
    assert 'tempo' in features
    assert 'rhythm_bpm' in features
```

### Integration Tests

```python
def test_database_integration():
    # Test database storage and retrieval
    results = audio_analysis_service.analyze_file(db, "test.mp3")
    stored = audio_analysis_service.get_analysis(db, "test.mp3")
    assert stored is not None
    assert stored['duration'] == results['duration']
```

## Troubleshooting

### Common Problems

1. **Essentia Import Error**: Ensure essentia-tensorflow is installed
2. **TensorFlow Model Errors**: Check model availability and compatibility
3. **Memory Issues**: Reduce batch size or increase memory limits
4. **Database Connection**: Verify database connectivity and permissions
5. **Audio Format Issues**: Ensure audio files are in supported formats

### Debug Mode

```python
import logging
logging.getLogger('src.playlist_app.services.essentia_analyzer').setLevel(logging.DEBUG)
```

### Performance Monitoring

```python
# Monitor analysis duration
start_time = time.time()
results = essentia_analyzer.analyze_audio_file("track.mp3")
duration = time.time() - start_time
print(f"Analysis took {duration:.2f} seconds")

# Monitor memory usage
import psutil
process = psutil.Process()
memory_info = process.memory_info()
print(f"Memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")
```

## Best Practices

1. **Preprocessing**: Always resample to consistent sample rate
2. **Error Handling**: Implement robust error handling for all operations
3. **Caching**: Cache analysis results to avoid recomputation
4. **Batch Processing**: Use batch operations for multiple files
5. **Resource Management**: Monitor and manage memory usage
6. **Validation**: Validate audio files before analysis
7. **Logging**: Implement comprehensive logging for debugging
8. **Testing**: Test with various audio formats and lengths

