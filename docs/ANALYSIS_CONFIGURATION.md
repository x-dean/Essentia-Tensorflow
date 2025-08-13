# Audio Analysis Configuration Guide

## Overview

The audio analysis system uses Essentia for extracting musical features from audio files. This document describes the configuration options and how to optimize the analysis process for different use cases.

## Configuration Structure

The analysis configuration is stored in `config/analysis_config.json` and is organized into several sections:

### 1. Essentia Configuration

#### Audio Processing
- **sample_rate**: Target sample rate for analysis (default: 44100 Hz)
- **channels**: Number of audio channels (default: 1 for mono)
- **frame_size**: Size of analysis frames (default: 2048 samples) - **CRITICAL FOR ACCURACY**
- **hop_size**: Step size between frames (default: 1024 samples) - **CRITICAL FOR ACCURACY**
- **window_type**: Window function type (default: "hann")
- **zero_padding**: Additional zero padding (default: 0)

**️ IMPORTANT**: Reducing `frame_size` and `hop_size` will **decrease accuracy**, not improve performance. These values are optimized for spectral analysis quality.

#### Spectral Analysis
- **min_frequency**: Minimum frequency for analysis (default: 20.0 Hz)
- **max_frequency**: Maximum frequency for analysis (default: 8000.0 Hz)
- **n_mels**: Number of mel bands (default: 96)
- **n_mfcc**: Number of MFCC coefficients (default: 40)
- **n_spectral_peaks**: Number of spectral peaks (default: 100)
- **silence_threshold**: Silence detection threshold in dB (default: -60.0)

#### Track Analysis
- **min_track_length**: Minimum track length in seconds (default: 1.0)
- **max_track_length**: Maximum track length in seconds (default: 600.0)
- **chunk_duration**: Duration of analysis chunks (default: 30.0 seconds)
- **overlap_ratio**: Overlap between chunks (default: 0.5)

#### Algorithms
- **enable_tensorflow**: Enable TensorFlow-based analysis (default: false)
- **enable_complex_rhythm**: Enable complex rhythm algorithms (default: false)
- **enable_complex_harmonic**: Enable complex harmonic algorithms (default: false)
- **enable_beat_tracking**: Enable beat tracking (default: false)
- **enable_tempo_tap**: Enable tempo tap algorithm (default: false)
- **enable_rhythm_extractor**: Enable rhythm extractor (default: false)
- **enable_pitch_analysis**: Enable pitch analysis (default: false)
- **enable_chord_detection**: Enable chord detection (default: false)

### 2. Performance Configuration

#### Parallel Processing
- **max_workers**: Maximum number of parallel workers (default: 4)
- **chunk_size**: Number of files processed per batch (default: 10)
- **timeout_per_file**: Timeout per file in seconds (default: 300)
- **memory_limit_mb**: Memory limit per worker in MB (default: 512)

#### Caching
- **enable_cache**: Enable result caching (default: true)
- **cache_duration_hours**: Cache duration in hours (default: 24)
- **max_cache_size_mb**: Maximum cache size in MB (default: 1024)

#### Optimization
- **use_ffmpeg_streaming**: Use FFmpeg for streaming chunks (default: true)
- **smart_segmentation**: Use smart segmentation based on track length (default: true)
- **skip_existing_analysis**: Skip files already analyzed (default: true)
- **batch_size**: Number of files in each batch (default: 50)

### 3. Analysis Strategies

The system uses different analysis strategies based on track length:

#### Short Tracks (0-5 minutes)
- **strategy**: "key_segments"
- **segments**: ["beginning", "middle", "end"]
- **segment_duration**: 30 seconds

#### Medium Tracks (5-10 minutes)
- **strategy**: "three_point"
- **segments**: ["beginning", "quarter", "middle", "three_quarter", "end"]
- **segment_duration**: 30 seconds

#### Long Tracks (10+ minutes)
- **strategy**: "strategic_points"
- **segments**: ["beginning", "20_percent", "40_percent", "60_percent", "80_percent", "end"]
- **segment_duration**: 30 seconds

### 4. Output Configuration

- **store_individual_columns**: Store features in individual database columns (default: true)
- **store_complete_json**: Store complete analysis as JSON (default: true)
- **compress_json**: Compress JSON output (default: false)
- **include_segment_details**: Include segment analysis details (default: true)
- **include_processing_metadata**: Include processing metadata (default: true)

### 5. Quality Configuration

#### Fallback Values
- **tempo**: Default tempo when analysis fails (default: 120.0 BPM)
- **key**: Default key when analysis fails (default: "C")
- **scale**: Default scale when analysis fails (default: "major")
- **key_strength**: Default key strength when analysis fails (default: 0.0)

#### Error Handling
- **continue_on_error**: Continue processing other files on error (default: true)
- **log_errors**: Log detailed error information (default: true)
- **retry_failed**: Retry failed analyses (default: false)
- **max_retries**: Maximum number of retry attempts (default: 3)

## Performance Optimization

### Why More Workers Don't Always Help

The analysis is CPU-intensive and involves:
1. **FFmpeg operations** for audio streaming
2. **Essentia algorithms** for feature extraction
3. **Database operations** for storing results

### ️ CRITICAL: What NOT to Change for Performance

**DO NOT reduce these values** as they will **decrease accuracy**:

- **frame_size**: Keep at 2048+ for good frequency resolution
- **hop_size**: Keep at 1024 for good temporal resolution
- **sample_rate**: Keep at 44100Hz for full frequency range

###  SAFE Performance Optimizations

#### 1. **Parallel Processing** (Most Effective)
```json
{
  "performance": {
    "parallel_processing": {
      "max_workers": 8,  // Increase based on CPU cores
      "chunk_size": 20   // Increase batch size
    }
  }
}
```

#### 2. **Smart Segmentation** (Very Effective)
```json
{
  "performance": {
    "optimization": {
      "smart_segmentation": true  // Analyze only key parts
    }
  }
}
```

#### 3. **Algorithm Selection** (Effective)
```json
{
  "essentia": {
    "algorithms": {
      "enable_tensorflow": false,        // Disable for speed
      "enable_complex_rhythm": false,    // Use simple algorithms
      "enable_complex_harmonic": false   // Use simple algorithms
    }
  }
}
```

#### 4. **FFmpeg Streaming** (Memory Efficient)
```json
{
  "performance": {
    "optimization": {
      "use_ffmpeg_streaming": true  // Don't load entire files
    }
  }
}
```

###  Accuracy vs Speed Trade-offs

#### **High Accuracy Profile** (Slower):
```json
{
  "audio_processing": {
    "sample_rate": 48000,
    "frame_size": 4096,
    "hop_size": 512
  },
  "spectral_analysis": {
    "n_mels": 128,
    "n_mfcc": 60,
    "n_spectral_peaks": 200
  }
}
```

#### **Balanced Profile** (Recommended):
```json
{
  "audio_processing": {
    "sample_rate": 44100,
    "frame_size": 2048,
    "hop_size": 1024
  },
  "spectral_analysis": {
    "n_mels": 96,
    "n_mfcc": 40,
    "n_spectral_peaks": 100
  }
}
```

#### **High Speed Profile** (Reduced Accuracy):
```json
{
  "audio_processing": {
    "sample_rate": 22050,  // Loses high frequencies
    "frame_size": 1024,    // Reduced frequency resolution
    "hop_size": 512        // Reduced temporal resolution
  },
  "spectral_analysis": {
    "n_mels": 64,          // Reduced frequency detail
    "n_mfcc": 20,          // Reduced spectral detail
    "n_spectral_peaks": 50 // Reduced peak detection
  }
}
```

### Recommended Settings

#### For High-Performance Systems (8+ cores, 16GB+ RAM)
```json
{
  "performance": {
    "parallel_processing": {
      "max_workers": 8,
      "chunk_size": 20,
      "timeout_per_file": 600
    }
  },
  "performance": {
    "optimization": {
      "smart_segmentation": true,
      "use_ffmpeg_streaming": true
    }
  }
}
```

#### For Standard Systems (4 cores, 8GB RAM)
```json
{
  "performance": {
    "parallel_processing": {
      "max_workers": 4,
      "chunk_size": 10,
      "timeout_per_file": 300
    }
  }
}
```

#### For Low-Resource Systems (2 cores, 4GB RAM)
```json
{
  "performance": {
    "parallel_processing": {
      "max_workers": 2,
      "chunk_size": 5,
      "timeout_per_file": 600
    }
  }
}
```

## Troubleshooting

### Common Issues

1. **Analysis taking too long**
   -  Increase `max_workers` (up to CPU core count)
   -  Enable `smart_segmentation`
   -  Disable complex algorithms
   -  Don't reduce `frame_size` or `hop_size`

2. **Memory errors**
   -  Enable `use_ffmpeg_streaming`
   -  Reduce `memory_limit_mb`
   -  Use `smart_segmentation`
   -  Don't reduce `frame_size` or `hop_size`

3. **Database connection errors**
   -  Reduce `max_workers` to avoid connection pool exhaustion
   -  Increase database connection pool size

4. **Files failing analysis**
   -  Check file format support
   -  Increase `timeout_per_file`
   -  Enable `retry_failed`

### Monitoring

Monitor these metrics during analysis:
- **Processing time per file**
- **Memory usage per worker**
- **Database connection usage**
- **Error rates**

## API Usage

### Force Re-Analyze with Custom Workers
```bash
curl -X POST "http://localhost:8000/api/analyzer/force-reanalyze?max_workers=8"
```

### Analyze Specific Files
```bash
curl -X POST "http://localhost:8000/api/analyzer/analyze-file" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "/music/song.mp3", "include_tensorflow": false}'
```

### Get Analysis Statistics
```bash
curl "http://localhost:8000/api/analyzer/statistics"
```

### View Configuration
```bash
curl "http://localhost:8000/api/analyzer/config"
```

### Reload Configuration
```bash
curl -X POST "http://localhost:8000/api/analyzer/config/reload"
```

## File Support

### Supported Formats
- **MP3**: Full support
- **M4A**: Full support
- **FLAC**: Full support
- **OGG**: Full support
- **WAV**: Full support

### Format-Specific Notes
- **M4A**: Uses FFmpeg streaming for optimal performance
- **FLAC**: Native Essentia support
- **OGG**: May require additional codecs

## Best Practices

1. **Start with balanced settings** and adjust based on needs
2. **Monitor system resources** during analysis
3. **Use smart segmentation** for large libraries
4. **Enable caching** for repeated analysis
5. **Log errors** for troubleshooting
6. **Test with a small subset** before full library analysis
7. **Never reduce frame_size or hop_size** for performance
8. **Focus on parallel processing** for speed improvements
