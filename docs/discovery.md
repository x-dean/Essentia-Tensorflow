# Discovery System

The Discovery System is the first step in the playlist generation app. It automatically scans predefined directories for audio files, tracks them in a database, and manages file additions/removals efficiently.

## Features

- **Automatic File Discovery**: Scans directories for audio files with configurable extensions
- **Hash-Based Deduplication**: Uses filename + filesize hash to avoid re-analyzing duplicate files
- **Caching System**: Speeds up discovery by caching file information
- **File Tracking**: Tracks added/removed files and updates database accordingly
- **REST API**: Full API for discovery operations

## Supported File Formats

- MP3 (.mp3)
- WAV (.wav)
- FLAC (.flac)
- OGG (.ogg)
- M4A (.m4a)
- AAC (.aac)
- WMA (.wma)
- OPUS (.opus)

## Configuration

### Environment Variables

```bash
# Database connection
DATABASE_URL=sqlite:///./playlist_app.db

# Search directories (comma-separated)
SEARCH_DIRECTORIES=/music,/audio,/home/user/music

# Discovery settings
DISCOVERY_CACHE_TTL=3600
DISCOVERY_BATCH_SIZE=100

# Logging
LOG_LEVEL=INFO
```

### Default Configuration

- **Search Directories**: `/music`, `/audio`
- **Database**: SQLite (local file)
- **Cache TTL**: 1 hour
- **Batch Size**: 100 files

## API Endpoints

### Initialize Database
```http
POST /api/discovery/init
```
Creates database tables if they don't exist.

### Scan for Files
```http
POST /api/discovery/scan
```
Scans configured directories for new/removed files.

**Response:**
```json
{
  "status": "success",
  "message": "File discovery completed",
  "results": {
    "added_count": 5,
    "removed_count": 2,
    "unchanged_count": 100,
    "added_files": ["/music/song1.mp3", "/music/song2.wav"],
    "removed_files": ["/music/old_song.mp3"]
  }
}
```

### Get Discovered Files
```http
GET /api/discovery/files?limit=100&offset=0
```
Returns list of discovered files with pagination.

**Response:**
```json
{
  "status": "success",
  "files": [
    {
      "id": 1,
      "file_path": "/music/song1.mp3",
      "file_name": "song1.mp3",
      "file_size": 5242880,
      "file_extension": ".mp3",
      "discovered_at": "2024-01-01T12:00:00",
      "is_analyzed": false
    }
  ],
  "count": 1
}
```

### Get File by Hash
```http
GET /api/discovery/files/{file_hash}
```
Returns file information by its hash.

### Get Discovery Statistics
```http
GET /api/discovery/stats
```
Returns discovery statistics.

**Response:**
```json
{
  "status": "success",
  "stats": {
    "total_files": 150,
    "analyzed_files": 75,
    "unanalyzed_files": 75,
    "extension_distribution": {
      ".mp3": 100,
      ".wav": 30,
      ".flac": 20
    }
  }
}
```

### Get Configuration
```http
GET /api/discovery/config
```
Returns current discovery configuration.

## Database Schema

### Files Table
```sql
CREATE TABLE files (
    id INTEGER PRIMARY KEY,
    file_path VARCHAR UNIQUE NOT NULL,
    file_name VARCHAR NOT NULL,
    file_size INTEGER NOT NULL,
    file_hash VARCHAR UNIQUE NOT NULL,
    file_extension VARCHAR NOT NULL,
    discovered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_modified DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_analyzed BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE
);
```

### Discovery Cache Table
```sql
CREATE TABLE discovery_cache (
    id INTEGER PRIMARY KEY,
    file_path VARCHAR UNIQUE NOT NULL,
    file_size INTEGER NOT NULL,
    file_hash VARCHAR NOT NULL,
    last_checked DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Usage Examples

### Python Usage
```python
from models import SessionLocal, create_tables
from discovery import DiscoveryService

# Initialize database
create_tables()

# Create discovery service
db = SessionLocal()
discovery_service = DiscoveryService(db)

# Scan for files
results = discovery_service.discover_files()
print(f"Added: {len(results['added'])} files")
print(f"Removed: {len(results['removed'])} files")

# Get discovered files
files = discovery_service.get_discovered_files(limit=10)
for file in files:
    print(f"Found: {file['file_name']}")
```

### Command Line Testing
```bash
# Test the discovery system
python test_discovery.py

# Run the API server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## File Hash Algorithm

The system uses MD5 hash of `filename_filesize` to identify files:
```python
hash_input = f"{file_name}_{file_size}".encode('utf-8')
file_hash = hashlib.md5(hash_input).hexdigest()
```

This approach:
- Avoids re-analyzing files when moved to different paths
- Prevents duplicate entries for same files
- Is fast and efficient for large file collections

## Performance Considerations

- **Caching**: File information is cached to avoid recalculating hashes
- **Batch Processing**: Files are processed in configurable batches
- **Incremental Updates**: Only new/removed files are processed
- **Database Indexing**: File paths and hashes are indexed for fast lookups

## Integration with Playlist System

The discovery system is designed to integrate with the playlist system:
- Files marked as `is_analyzed=False` are candidates for audio analysis
- When files are removed, playlist cleanup is triggered
- File hashes are used to link files with audio analysis results

## Error Handling

- Invalid file paths are logged and skipped
- Database errors trigger rollback and logging
- File permission errors are handled gracefully
- Network timeouts are retried with exponential backoff
