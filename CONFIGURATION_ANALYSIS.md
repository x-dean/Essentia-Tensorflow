# Configuration Analysis Report

## Overview
This document provides a comprehensive analysis of all configurable settings in the Essentia-Tensorflow Playlist App, identifying hardcoded values that should be made configurable and providing recommendations for configuration management.

## Current Configuration Files

### 1. app_settings.json
**Location**: `config/app_settings.json`
**Purpose**: Main application settings

**Current Settings**:
- API configuration (host, port, workers, CORS)
- Performance settings (concurrent requests, timeouts, background tasks)
- Discovery settings (background enabled, interval, auto scan)
- Paths (Python path, data directories)
- External APIs (MusicBrainz, LastFM, Discogs)

### 2. analysis_config.json
**Location**: `config/analysis_config.json`
**Purpose**: Audio analysis configuration

**Current Settings**:
- Essentia audio processing parameters
- Spectral analysis settings
- Track analysis parameters
- Algorithm enable/disable flags
- Performance and caching settings
- Analysis strategies for different track lengths
- Output configuration
- Quality thresholds and fallback values

### 3. database.json
**Location**: `config/database.json`
**Purpose**: Database connection settings

**Current Settings**:
- Connection pool configuration
- Pool timeout and recycle settings

### 4. logging.json
**Location**: `config/logging.json`
**Purpose**: Logging configuration

**Current Settings**:
- Log level
- File size limits
- Backup settings
- Compression settings

## Hardcoded Values Found

### 1. Main Application (main.py)

**Hardcoded Values**:
- `discovery_interval = 300` (5 minutes) - Line 79
- `max_retries = 30` (PostgreSQL connection) - Line 145
- `LOG_MAX_SIZE = "10485760"` (10MB) - Line 39
- `LOG_BACKUP_COUNT = "5"` - Line 40

**Recommendations**:
- Move discovery interval to `app_settings.json` under `discovery.interval`
- Move PostgreSQL retry settings to `database.json`
- Move logging settings to `logging.json`

### 2. Discovery Service (src/playlist_app/services/discovery.py)

**Hardcoded Values**:
- Supported file extensions in `DiscoveryConfig.SUPPORTED_EXTENSIONS`
- Discovery cache TTL: `DISCOVERY_CACHE_TTL = 3600` (1 hour)
- Discovery batch size: `DISCOVERY_BATCH_SIZE = 100`

**Recommendations**:
- Move supported extensions to `app_settings.json` under `discovery.supported_extensions`
- Move cache TTL to `app_settings.json` under `discovery.cache_ttl`
- Move batch size to `app_settings.json` under `discovery.batch_size`

### 3. Essentia Analyzer (src/playlist_app/services/essentia_analyzer.py)

**Hardcoded Values**:
- TensorFlow log suppression settings
- Essentia log suppression settings
- Default fallback values in `safe_float()` function: `-999.0`

**Recommendations**:
- Move log suppression settings to `logging.json` under `suppression`
- Move fallback values to `analysis_config.json` under `quality.fallback_values`

### 4. Audio Analysis Service (src/playlist_app/services/audio_analysis_service.py)

**Hardcoded Values**:
- Database retry settings: `max_retries = 3`, `retry_delay = 1`
- Exponential backoff multiplier: `retry_delay *= 2`

**Recommendations**:
- Move database retry settings to `database.json` under `retry_settings`

### 5. FAISS Service (src/playlist_app/services/faiss_service.py)

**Hardcoded Values**:
- Default index name: `"music_library"`
- Vector hash computation method

**Recommendations**:
- Move index name to `app_settings.json` under `faiss.index_name`
- Add vector configuration to `analysis_config.json` under `vector_analysis`

### 6. Web UI (web-ui/src/services/api.ts)

**Hardcoded Values**:
- API timeout: `60000` (60 seconds) - Line 6
- Analysis timeout: `300000` (5 minutes) - Line 245
- FAISS timeout: `300000` (5 minutes) - Line 275

**Recommendations**:
- Move timeouts to `app_settings.json` under `api.timeouts`

### 7. CLI Tools

**Hardcoded Values**:
- Default API base URL: `"http://localhost:8000"` in batch_analyzer_cli.py
- Request timeouts and retry logic

**Recommendations**:
- Move API base URL to environment variable or config file
- Add CLI-specific configuration section

## Recommended Configuration Structure

### 1. Enhanced app_settings.json

```json
{
  "api": {
    "host": "0.0.0.0",
    "port": 8000,
    "workers": 1,
    "reload": false,
    "timeouts": {
      "default": 60,
      "analysis": 300,
      "faiss": 300,
      "discovery": 120
    },
    "cors": {
      "enabled": true,
      "origins": ["*"],
      "methods": ["GET", "POST", "PUT", "DELETE"],
      "headers": ["*"]
    }
  },
  "performance": {
    "max_concurrent_requests": 100,
    "request_timeout": 30,
    "background_tasks": {
      "enabled": true,
      "max_workers": 4
    }
  },
  "discovery": {
    "background_enabled": false,
    "interval": 3600,
    "auto_scan_on_startup": true,
    "supported_extensions": [".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma", ".opus"],
    "cache_ttl": 3600,
    "batch_size": 100
  },
  "paths": {
    "python_path": "/app/src",
    "data_directory": "/app/data",
    "cache_directory": "/app/cache",
    "logs_directory": "/app/logs"
  },
  "faiss": {
    "index_name": "music_library",
    "vector_dimension": 128,
    "similarity_threshold": 0.8
  },
  "external_apis": {
    "musicbrainz": {
      "enabled": true,
      "rate_limit": 1.0,
      "timeout": 10,
      "user_agent": "PlaylistApp/1.0 (dean@example.com)"
    },
    "lastfm": {
      "enabled": true,
      "api_key": "2b07c1e8a2d308a749760ab8d579baa8",
      "base_url": "https://ws.audioscrobbler.com/2.0/",
      "rate_limit": 0.5,
      "timeout": 10
    },
    "discogs": {
      "enabled": true,
      "api_key": "fHtjqUtbbXdHMqMBqvblPvKpOCInINhDTUCHvgcS",
      "base_url": "https://api.discogs.com/",
      "rate_limit": 1.0,
      "timeout": 10,
      "user_agent": "PlaylistApp/1.0"
    }
  }
}
```

### 2. Enhanced database.json

```json
{
  "pool_size": 25,
  "max_overflow": 35,
  "pool_timeout": 45,
  "pool_recycle": 7200,
  "retry_settings": {
    "max_retries": 3,
    "initial_delay": 1,
    "backoff_multiplier": 2,
    "max_delay": 30
  },
  "connection_timeout": 30,
  "_metadata": {
    "last_updated": "2025-08-12T22:07:49.016956",
    "version": "1.0"
  }
}
```

### 3. Enhanced logging.json

```json
{
  "log_level": "DEBUG",
  "max_file_size": 20480,
  "max_backups": 10,
  "compress": true,
  "suppression": {
    "tensorflow": true,
    "essentia": true,
    "librosa": true,
    "matplotlib": true,
    "pil": true
  },
  "structured_logging": {
    "enabled": false,
    "format": "json"
  },
  "_metadata": {
    "last_updated": "2025-08-12T22:07:49.031562",
    "version": "1.0"
  }
}
```

### 4. Enhanced analysis_config.json

```json
{
  "essentia": {
    "audio_processing": {
      "sample_rate": 44100,
      "channels": 1,
      "frame_size": 2048,
      "hop_size": 1024,
      "window_type": "hann",
      "zero_padding": 0
    },
    "spectral_analysis": {
      "min_frequency": 20.0,
      "max_frequency": 8000.0,
      "n_mels": 96,
      "n_mfcc": 40,
      "n_spectral_peaks": 100,
      "silence_threshold": -60.0
    },
    "track_analysis": {
      "min_track_length": 1.0,
      "max_track_length": 600.0,
      "chunk_duration": 45.0,
      "overlap_ratio": 0.5
    },
    "algorithms": {
      "enable_tensorflow": true,
      "enable_complex_rhythm": false,
      "enable_complex_harmonic": true,
      "enable_beat_tracking": true,
      "enable_tempo_tap": true,
      "enable_rhythm_extractor": true,
      "enable_pitch_analysis": true,
      "enable_chord_detection": true
    }
  },
  "performance": {
    "parallel_processing": {
      "max_workers": 8,
      "chunk_size": 25,
      "timeout_per_file": 600,
      "memory_limit_mb": 512
    },
    "caching": {
      "enable_cache": true,
      "cache_duration_hours": 24,
      "max_cache_size_mb": 1024
    },
    "optimization": {
      "use_ffmpeg_streaming": true,
      "smart_segmentation": true,
      "skip_existing_analysis": true,
      "batch_size": 50
    }
  },
  "analysis_strategies": {
    "short_tracks": {
      "max_duration": 300,
      "strategy": "key_segments",
      "segments": ["beginning", "middle", "end"],
      "segment_duration": 30
    },
    "medium_tracks": {
      "max_duration": 600,
      "strategy": "three_point",
      "segments": ["beginning", "quarter", "middle", "three_quarter", "end"],
      "segment_duration": 30
    },
    "long_tracks": {
      "max_duration": 3600,
      "strategy": "strategic_points",
      "segments": ["beginning", "20_percent", "40_percent", "60_percent", "80_percent", "end"],
      "segment_duration": 30
    }
  },
  "vector_analysis": {
    "feature_vector_size": 128,
    "similarity_metrics": ["cosine", "euclidean"],
    "index_type": "IVFFlat",
    "nlist": 100
  },
  "output": {
    "store_individual_columns": true,
    "store_complete_json": true,
    "compress_json": false,
    "include_segment_details": true,
    "include_processing_metadata": true
  },
  "quality": {
    "min_confidence_threshold": 0.3,
    "fallback_values": {
      "tempo": 120.0,
      "key": "C",
      "scale": "major",
      "key_strength": 0.0,
      "default_float": -999.0
    },
    "error_handling": {
      "continue_on_error": true,
      "log_errors": true,
      "retry_failed": false,
      "max_retries": 3
    }
  }
}
```

## Implementation Priority

### High Priority (Should be implemented first)
1. Move hardcoded timeouts to configuration
2. Move database retry settings to configuration
3. Move discovery settings to configuration
4. Move logging suppression settings to configuration

### Medium Priority
1. Move FAISS settings to configuration
2. Move CLI settings to configuration
3. Add vector analysis configuration
4. Enhance error handling configuration

### Low Priority
1. Add structured logging configuration
2. Add advanced performance tuning options
3. Add external API rate limiting configuration

## Migration Strategy

1. **Phase 1**: Create new configuration sections without removing old hardcoded values
2. **Phase 2**: Update code to use configuration values with fallback to hardcoded defaults
3. **Phase 3**: Remove hardcoded values and require configuration
4. **Phase 4**: Add validation and documentation for all configuration options

## Configuration Validation

Add validation for:
- Numeric ranges (timeouts, limits, thresholds)
- File paths and directory existence
- API key formats
- Required vs optional settings
- Cross-configuration dependencies

## Documentation Updates

Update documentation to include:
- Complete configuration reference
- Default values for all settings
- Configuration examples for different use cases
- Migration guides for existing installations
