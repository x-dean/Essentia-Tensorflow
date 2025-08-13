# Playlist App Functions Documentation

## Overview

This document describes the core functions and capabilities of the Playlist App, focusing on file discovery and metadata extraction with genre enrichment.

##  File Discovery System

### Core Discovery Functions

#### `discover_files()`
**Location**: `src/playlist_app/services/discovery.py`

**Purpose**: Scans configured directories for audio files and manages them in the database.

**Features**:
- Scans multiple directories from `config/discovery.json`
- Supports formats: MP3, FLAC, OGG, M4A, WAV, WMA, AAC, OPUS
- Tracks file changes (added, removed, unchanged)
- Automatic metadata extraction during discovery
- Hash-based duplicate detection

**Returns**: Dictionary with counts of added, removed, and unchanged files

#### `re_discover_files()`
**Location**: `src/playlist_app/services/discovery.py`

**Purpose**: Complete re-scan of all files, clearing existing data and re-processing everything.

**Features**:
- Clears all existing files and metadata from database
- Re-scans all configured directories
- Re-extracts metadata for all files
- Triggers genre enrichment for files with missing genres

**Use Case**: Initial setup, after configuration changes, or to re-process all files

#### `add_file_to_db(file_path: str, db: Session)`
**Location**: `src/playlist_app/services/discovery.py`

**Purpose**: Adds a single file to the database with metadata extraction.

**Features**:
- Validates file exists and is supported format
- Calculates file hash for duplicate detection
- Extracts metadata using `AudioMetadataAnalyzer`
- Saves file record and metadata to database

### Discovery Configuration

**File**: `config/discovery.json`

```json
{
  "search_directories": [
    "/music",
    "/audio"
  ],
  "supported_formats": [
    ".mp3", ".flac", ".ogg", ".m4a", ".wav", ".wma", ".aac", ".opus"
  ],
  "recursive": true,
  "follow_symlinks": false
}
```

##  Metadata Extraction System

### Core Metadata Functions

#### `analyze_file(file_path: str, db: Session)`
**Location**: `src/playlist_app/services/metadata.py`

**Purpose**: Extracts comprehensive metadata from audio files.

**Extracted Fields**:
- **Basic**: title, artist, album, track_number, year, genre
- **Advanced**: album_artist, disc_number, composer, duration, bpm, key
- **Technical**: bitrate, sample_rate, channels, file_size, format
- **Audio Quality**: replaygain values, encoder information
- **External IDs**: MusicBrainz track/artist/album IDs

**Supported Formats**:
- **MP3**: ID3v1, ID3v2 tags
- **FLAC**: Vorbis comments
- **OGG**: Vorbis comments
- **M4A**: iTunes-style metadata
- **WAV**: RIFF chunks
- **WMA**: ASF metadata
- **AAC**: ADTS headers

#### `_normalize_metadata(raw_metadata: Dict)`
**Location**: `src/playlist_app/services/metadata.py`

**Purpose**: Normalizes and cleans extracted metadata.

**Features**:
- Maps raw tag names to standardized field names
- Converts data types (strings to numbers, dates to years)
- Handles special formats (track numbers as "X/Y", dates as timestamps)
- Triggers genre enrichment for missing/generic genres

#### `_convert_data_types(metadata: Dict)`
**Location**: `src/playlist_app/services/metadata.py`

**Purpose**: Converts metadata values to appropriate Python types.

**Conversions**:
- **Year**: ID3TimeStamp → int, date strings → int
- **Track/Disc Numbers**: "X/Y" strings → int
- **BPM**: string → float
- **Duration**: various formats → float
- **ReplayGain**: string → float
- **Bitrate/Sample Rate**: string → int

##  Genre Enrichment System

### Multi-API Genre Detection

#### `enrich_metadata(metadata: Dict)`
**Location**: `src/playlist_app/services/genre_enrichment.py`

**Purpose**: Enriches missing genres using multiple external APIs.

**Fallback Chain**:
1. **MusicBrainz** (free, no API key required)
2. **Last.fm** (requires API key)
3. **Discogs** (requires API key)

**Logic**:
- Only triggers if genre is missing, "other", "unknown", or empty
- Tries each service in order until genre is found
- Respects rate limits for each service
- Graceful error handling for failed API calls

### External API Services

#### MusicBrainz Service
**Location**: `src/playlist_app/services/musicbrainz.py`

**Features**:
- Free API, no authentication required
- Searches by artist + title + album
- Extracts genre from track tags or artist tags
- Rate limited to 1 request/second

#### Last.fm Service
**Location**: `src/playlist_app/services/lastfm.py`

**Features**:
- Requires API key (free tier available)
- Searches track info and artist top tags
- Rate limited to 0.5 requests/second
- Excellent genre coverage for popular music

#### Discogs Service
**Location**: `src/playlist_app/services/discogs.py`

**Features**:
- Requires API key (free tier available)
- Searches releases and artist profiles
- Rate limited to 1 request/second
- Excellent for electronic music and underground genres

### Genre Enrichment Configuration

**File**: `config/app_settings.json`

```json
{
  "external_apis": {
    "musicbrainz": {
      "enabled": true,
      "rate_limit": 1.0,
      "timeout": 10
    },
    "lastfm": {
      "enabled": true,
      "api_key": "your_lastfm_api_key",
      "rate_limit": 0.5,
      "timeout": 10
    },
    "discogs": {
      "enabled": true,
      "api_key": "your_discogs_api_key",
      "rate_limit": 1.0,
      "timeout": 10
    }
  }
}
```

## ️ CLI Commands

### Discovery Commands

#### `scan`
```bash
python playlist_cli.py scan [--verbose]
```
- Scans for new files
- Shows detailed progress with `--verbose`

#### `list`
```bash
python playlist_cli.py list [--limit N] [--offset N] [--format table|json]
```
- Lists discovered files
- Supports pagination and multiple output formats

#### `stats`
```bash
python playlist_cli.py stats [--format table|json]
```
- Shows discovery statistics
- File counts, format distribution, size totals

#### `re-discover`
```bash
python playlist_cli.py re-discover [--verbose]
```
- Complete re-scan of all files
- Clears existing data and re-processes everything

### Metadata Commands

#### `metadata-stats`
```bash
python playlist_cli.py metadata-stats [--format table|json]
```
- Shows metadata analysis statistics
- Genre distribution, year breakdown, analysis percentage

#### `show-metadata <file_id>`
```bash
python playlist_cli.py show-metadata 123 [--format table|json]
```
- Shows detailed metadata for specific file
- Includes all extracted fields and technical information

#### `search`
```bash
python playlist_cli.py search [--query "text"] [--artist "name"] [--album "name"] [--genre "genre"] [--year 2020] [--limit N]
```
- Searches metadata across all fields
- Supports multiple filter combinations

#### `enrich-genres`
```bash
python playlist_cli.py enrich-genres [--limit N] [--format table|json]
```
- Lists files with missing/generic genres
- Shows which files need genre enrichment

##  API Endpoints

### Discovery Endpoints

#### `POST /api/discovery/scan`
- Triggers file discovery
- Returns discovery results

#### `GET /api/discovery/files`
- Lists all discovered files
- Supports pagination and filtering

#### `GET /api/discovery/stats`
- Returns discovery statistics

#### `POST /api/discovery/re-discover`
- Triggers complete re-discovery
- Clears existing data and re-processes

### Metadata Endpoints

#### `GET /api/metadata/{file_id}`
- Returns metadata for specific file

#### `GET /api/metadata/search`
- Searches metadata with query parameters

#### `GET /api/metadata/stats/overview`
- Returns metadata statistics

##  Database Schema

### File Table
```sql
CREATE TABLE files (
    id SERIAL PRIMARY KEY,
    file_path VARCHAR(500) UNIQUE NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_hash VARCHAR(64) UNIQUE,
    file_size BIGINT,
    file_format VARCHAR(10),
    is_analyzed BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### AudioMetadata Table
```sql
CREATE TABLE audio_metadata (
    id SERIAL PRIMARY KEY,
    file_id INTEGER REFERENCES files(id),
    title VARCHAR(255),
    artist VARCHAR(255),
    album VARCHAR(255),
    track_number INTEGER,
    year INTEGER,
    genre VARCHAR(100),
    album_artist VARCHAR(255),
    disc_number INTEGER,
    composer VARCHAR(255),
    duration FLOAT,
    bpm FLOAT,
    key VARCHAR(10),
    comment TEXT,
    mood VARCHAR(100),
    rating INTEGER,
    isrc VARCHAR(20),
    encoder VARCHAR(100),
    bitrate INTEGER,
    sample_rate INTEGER,
    channels INTEGER,
    format VARCHAR(50),
    file_size BIGINT,
    file_format VARCHAR(10),
    replaygain_track_gain FLOAT,
    replaygain_album_gain FLOAT,
    replaygain_track_peak FLOAT,
    replaygain_album_peak FLOAT,
    musicbrainz_track_id VARCHAR(50),
    musicbrainz_artist_id VARCHAR(50),
    musicbrainz_album_id VARCHAR(50),
    musicbrainz_album_artist_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

##  Usage Examples

### Initial Setup
```bash
# 1. Configure directories
# Edit config/discovery.json

# 2. Configure API keys (optional)
# Edit config/app_settings.json

# 3. Start the system
docker-compose up -d

# 4. Initial discovery
python playlist_cli.py re-discover --verbose
```

### Regular Operations
```bash
# Scan for new files
python playlist_cli.py scan

# Check statistics
python playlist_cli.py stats
python playlist_cli.py metadata-stats

# Search for specific music
python playlist_cli.py search --artist "Coldplay" --year 2020

# Check files needing genre enrichment
python playlist_cli.py enrich-genres
```

### API Usage
```bash
# Get all files
curl "http://localhost:8000/api/discovery/files"

# Search metadata
curl "http://localhost:8000/api/metadata/search?artist=Coldplay&year=2020"

# Get file metadata
curl "http://localhost:8000/api/metadata/123"
```

##  Error Handling

### Discovery Errors
- **File not found**: Logged and skipped
- **Unsupported format**: Logged and skipped
- **Permission denied**: Logged and skipped
- **Database errors**: Rollback and retry

### Metadata Errors
- **Corrupted files**: Graceful handling with partial extraction
- **Missing tags**: Continue with available data
- **Type conversion errors**: Logged and default values used
- **API failures**: Fallback to next service in chain

### Genre Enrichment Errors
- **API timeouts**: Skip to next service
- **Rate limit exceeded**: Automatic retry with backoff
- **Invalid API keys**: Service disabled, others continue
- **Network errors**: Graceful degradation

##  Performance Considerations

### Discovery Performance
- **Hash calculation**: SHA-256 for duplicate detection
- **Batch processing**: Multiple files processed concurrently
- **Database optimization**: Indexed queries for file lookups

### Metadata Performance
- **Local extraction**: Mutagen for embedded metadata
- **External APIs**: Rate limited and cached where possible
- **Database writes**: Batch commits for efficiency

### Genre Enrichment Performance
- **Fallback chain**: Stops at first successful result
- **Rate limiting**: Respects API limits to avoid blocking
- **Parallel processing**: Multiple services can be tried concurrently

##  Configuration Files

### Discovery Configuration
- **File**: `config/discovery.json`
- **Purpose**: Define search directories and file formats

### App Settings
- **File**: `config/app_settings.json`
- **Purpose**: API configuration, performance settings, external services

### Docker Configuration
- **File**: `docker-compose.yml`
- **Purpose**: Container orchestration and networking

##  Logging

### Log Levels
- **INFO**: Normal operations, successful discoveries
- **WARNING**: Non-critical issues, API failures
- **ERROR**: Critical failures, database errors
- **DEBUG**: Detailed debugging information

### Log Files
- **Location**: `/app/logs/`
- **Rotation**: Automatic log rotation
- **Format**: Structured JSON logging

---

*This documentation covers the core functionality as of version 1.0. For additional features and updates, refer to the main README.md file.*
