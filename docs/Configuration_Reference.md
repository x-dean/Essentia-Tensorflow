# Configuration Reference Guide

This document provides detailed explanations for every setting in `config/analysis_config.json`.

## Table of Contents
- [Essentia Settings](#essentia-settings)
- [Performance Settings](#performance-settings)
- [Analysis Strategies](#analysis-strategies)
- [Output Settings](#output-settings)
- [Quality Settings](#quality-settings)
- [Performance Profiles](#performance-profiles)

## Essentia Settings

### Audio Processing
```json
"audio_processing": {
  "sample_rate": 44100,
  "channels": 1,
  "frame_size": 2048,
  "hop_size": 1024,
  "window_type": "hann",
  "zero_padding": 0
}
```

| Setting | Value | Description | Impact |
|---------|-------|-------------|---------|
| `sample_rate` | 44100 | Audio sample rate in Hz (CD quality) | Higher = better quality, slower processing |
| `channels` | 1 | Number of audio channels (1=mono, 2=stereo) | Mono is faster, stereo provides more info |
| `frame_size` | 2048 | Number of samples per analysis frame | Larger = better frequency resolution |
| `hop_size` | 1024 | Samples between consecutive frames | Smaller = better time resolution |
| `window_type` | "hann" | Window function for spectral analysis | Options: hann, hamming, blackman |
| `zero_padding` | 0 | Additional zero padding for FFT | 0 = no padding, higher = smoother spectra |

### Spectral Analysis
```json
"spectral_analysis": {
  "min_frequency": 20.0,
  "max_frequency": 8000.0,
  "n_mels": 96,
  "n_mfcc": 40,
  "n_spectral_peaks": 100,
  "silence_threshold": -60.0
}
```

| Setting | Value | Description | Impact |
|---------|-------|-------------|---------|
| `min_frequency` | 20.0 | Minimum frequency for analysis in Hz | Human hearing range starts at ~20Hz |
| `max_frequency` | 8000.0 | Maximum frequency for analysis in Hz | Most musical content is below 8kHz |
| `n_mels` | 96 | Number of mel-frequency bands | More = better MFCC accuracy |
| `n_mfcc` | 40 | Number of MFCC coefficients | Audio fingerprint features |
| `n_spectral_peaks` | 100 | Maximum spectral peaks to extract | More = more detailed harmonic analysis |
| `silence_threshold` | -60.0 | Threshold in dB for silence detection | Lower = more sensitive to quiet parts |

### Track Analysis
```json
"track_analysis": {
  "min_track_length": 1.0,
  "max_track_length": 600.0,
  "chunk_duration": 45.0,
  "overlap_ratio": 0.5
}
```

| Setting | Value | Description | Impact |
|---------|-------|-------------|---------|
| `min_track_length` | 1.0 | Minimum track duration in seconds | Filters out very short files |
| `max_track_length` | 600.0 | Maximum track duration in seconds | Defines "long track" threshold (10 minutes) |
| `chunk_duration` | 45.0 | Duration of each audio segment analyzed | Longer = more detailed analysis |
| `overlap_ratio` | 0.5 | Overlap between consecutive chunks | 0.5 = 50% overlap, smoother transitions |

### Algorithms
```json
"algorithms": {
  "enable_tensorflow": false,
  "enable_complex_rhythm": false,
  "enable_complex_harmonic": false,
  "enable_beat_tracking": false,
  "enable_tempo_tap": false,
  "enable_rhythm_extractor": false,
  "enable_pitch_analysis": false,
  "enable_chord_detection": false
}
```

| Setting | Value | Description | Impact |
|---------|-------|-------------|---------|
| `enable_tensorflow` | false | Enable TensorFlow-based models | Slower but more accurate |
| `enable_complex_rhythm` | false | Enable complex rhythm analysis | Can cause hanging on some files |
| `enable_complex_harmonic` | false | Enable complex harmonic analysis | Can cause hanging on some files |
| `enable_beat_tracking` | false | Enable beat tracking algorithms | Provides beat timing information |
| `enable_tempo_tap` | false | Enable tempo tap detection | Interactive tempo analysis |
| `enable_rhythm_extractor` | false | Enable rhythm extraction | Can cause hanging on some files |
| `enable_pitch_analysis` | false | Enable pitch analysis algorithms | Provides pitch information |
| `enable_chord_detection` | false | Enable chord detection algorithms | Provides chord information |

## Performance Settings

### Parallel Processing
```json
"parallel_processing": {
  "max_workers": 8,
  "chunk_size": 20,
  "timeout_per_file": 300,
  "memory_limit_mb": 512
}
```

| Setting | Value | Description | Impact |
|---------|-------|-------------|---------|
| `max_workers` | 8 | Number of parallel processes | More = faster but more CPU usage |
| `chunk_size` | 20 | Number of files processed per batch | Larger = more efficient processing |
| `timeout_per_file` | 300 | Maximum time per file in seconds | Prevents hanging on problematic files |
| `memory_limit_mb` | 512 | Memory limit per worker in MB | Prevents memory issues |

### Caching
```json
"caching": {
  "enable_cache": true,
  "cache_duration_hours": 24,
  "max_cache_size_mb": 1024
}
```

| Setting | Value | Description | Impact |
|---------|-------|-------------|---------|
| `enable_cache` | true | Enable caching of analysis results | Faster subsequent runs |
| `cache_duration_hours` | 24 | How long to keep cached results | Balance between speed and disk usage |
| `max_cache_size_mb` | 1024 | Maximum cache size in MB | Prevents unlimited disk usage |

### Optimization
```json
"optimization": {
  "use_ffmpeg_streaming": true,
  "smart_segmentation": true,
  "skip_existing_analysis": true,
  "batch_size": 50
}
```

| Setting | Value | Description | Impact |
|---------|-------|-------------|---------|
| `use_ffmpeg_streaming` | true | Use FFmpeg for streaming audio | Prevents loading entire file into memory |
| `smart_segmentation` | true | Use intelligent segment selection | Analyzes key parts based on track length |
| `skip_existing_analysis` | true | Skip files with existing results | Faster incremental processing |
| `batch_size` | 50 | Number of files per batch | Optimizes database operations |

## Analysis Strategies

The system uses different analysis strategies based on track length:

### Short Tracks (0-5 minutes)
```json
"short_tracks": {
  "max_duration": 300,
  "strategy": "key_segments",
  "segments": ["beginning", "middle", "end"],
  "segment_duration": 30
}
```
- **Strategy**: Analyze 3 key segments
- **Segments**: Beginning, middle, end
- **Use Case**: Pop songs, short tracks

### Medium Tracks (5-10 minutes)
```json
"medium_tracks": {
  "max_duration": 600,
  "strategy": "three_point",
  "segments": ["beginning", "quarter", "middle", "three_quarter", "end"],
  "segment_duration": 30
}
```
- **Strategy**: Analyze 5 strategic points
- **Segments**: Beginning, quarter, middle, three-quarter, end
- **Use Case**: Longer songs, electronic tracks

### Long Tracks (10+ minutes)
```json
"long_tracks": {
  "max_duration": 3600,
  "strategy": "strategic_points",
  "segments": ["beginning", "20_percent", "40_percent", "60_percent", "80_percent", "end"],
  "segment_duration": 30
}
```
- **Strategy**: Analyze 6 evenly distributed points
- **Segments**: Beginning, 20%, 40%, 60%, 80%, end
- **Use Case**: Classical music, mixes, podcasts

## Output Settings

```json
"output": {
  "store_individual_columns": true,
  "store_complete_json": true,
  "compress_json": false,
  "include_segment_details": true,
  "include_processing_metadata": true
}
```

| Setting | Value | Description | Impact |
|---------|-------|-------------|---------|
| `store_individual_columns` | true | Store features in separate DB columns | Easy SQL queries |
| `store_complete_json` | true | Store complete analysis as JSON | Full analysis data |
| `compress_json` | false | Compress JSON data | Saves space, slower access |
| `include_segment_details` | true | Include segment analysis details | More detailed results |
| `include_processing_metadata` | true | Include processing time, errors | Debugging information |

## Quality Settings

### Fallback Values
```json
"fallback_values": {
  "tempo": 120.0,
  "key": "C",
  "scale": "major",
  "key_strength": 0.0
}
```
These values are used when analysis fails:
- **tempo**: 120.0 BPM (standard pop tempo)
- **key**: "C" (neutral key)
- **scale**: "major" (most common scale)
- **key_strength**: 0.0 (no confidence)

### Error Handling
```json
"error_handling": {
  "continue_on_error": true,
  "log_errors": true,
  "retry_failed": false,
  "max_retries": 3
}
```

| Setting | Value | Description | Impact |
|---------|-------|-------------|---------|
| `continue_on_error` | true | Continue processing other files if one fails | Robust batch processing |
| `log_errors` | true | Log detailed error information | Better debugging |
| `retry_failed` | false | Retry failed files automatically | Can slow down processing |
| `max_retries` | 3 | Maximum number of retry attempts | Prevents infinite loops |

## Performance Profiles

The system includes three predefined performance profiles:

### High Accuracy
- **Description**: Maximum accuracy, slower processing
- **Sample Rate**: 48000 Hz
- **Frame Size**: 4096 samples
- **MFCC**: 60 coefficients
- **TensorFlow**: Enabled
- **Use Case**: Research, high-quality analysis

### Balanced (Default)
- **Description**: Good balance of accuracy and speed
- **Sample Rate**: 44100 Hz
- **Frame Size**: 2048 samples
- **MFCC**: 40 coefficients
- **TensorFlow**: Disabled
- **Use Case**: General purpose, most scenarios

### High Speed
- **Description**: Faster processing, reduced accuracy
- **Sample Rate**: 22050 Hz
- **Frame Size**: 1024 samples
- **MFCC**: 20 coefficients
- **TensorFlow**: Disabled
- **Use Case**: Quick analysis, large libraries

## Quick Configuration Examples

### For Large Music Libraries (Speed Focus)
```json
{
  "performance": {
    "parallel_processing": {
      "max_workers": 12,
      "chunk_size": 50
    }
  },
  "essentia": {
    "track_analysis": {
      "chunk_duration": 30.0
    }
  }
}
```

### For High-Quality Analysis (Accuracy Focus)
```json
{
  "essentia": {
    "audio_processing": {
      "sample_rate": 48000,
      "frame_size": 4096
    },
    "algorithms": {
      "enable_tensorflow": true
    }
  },
  "performance": {
    "parallel_processing": {
      "max_workers": 4
    }
  }
}
```

### For Classical Music (Long Tracks)
```json
{
  "essentia": {
    "track_analysis": {
      "max_track_length": 1800.0
    }
  },
  "analysis_strategies": {
    "long_tracks": {
      "max_duration": 1800,
      "segments": ["beginning", "10_percent", "25_percent", "50_percent", "75_percent", "90_percent", "end"]
    }
  }
}
```

## Modifying Configuration

### Method 1: Edit JSON File
1. Edit `config/analysis_config.json`
2. Restart the application or use `reload-config` command

### Method 2: Use CLI Commands
```bash
# Override settings for specific runs
python playlist_cli.py analyze --max-workers 6 --max-files 15

# Reload configuration
python playlist_cli.py reload-config

# View current configuration
python playlist_cli.py analysis-config
```

### Method 3: Use API Endpoints
```bash
# View configuration
curl http://localhost:8000/api/analyzer/config

# Reload configuration
curl -X POST http://localhost:8000/api/analyzer/config/reload
```

## Troubleshooting

### Common Issues

1. **Analysis too slow**: Increase `max_workers`, decrease `chunk_duration`
2. **Memory errors**: Decrease `memory_limit_mb`, enable `use_ffmpeg_streaming`
3. **Files hanging**: Decrease `timeout_per_file`, disable complex algorithms
4. **Poor accuracy**: Increase `sample_rate`, `frame_size`, enable TensorFlow
5. **Disk space issues**: Decrease `max_cache_size_mb`, enable `compress_json`

### Performance Tuning

- **CPU-bound**: Increase `max_workers` up to number of CPU cores
- **Memory-bound**: Decrease `memory_limit_mb`, enable streaming
- **I/O-bound**: Increase `chunk_size`, enable caching
- **Accuracy vs Speed**: Use performance profiles or adjust individual settings
