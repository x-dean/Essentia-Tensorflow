# Tracks API Reference

This document provides comprehensive documentation for the Tracks API, which offers fast access to track attributes without requiring complex database queries.

## Overview

The Tracks API provides three main endpoints for accessing track information:

- **GET `/api/tracks/`** - Get all tracks with pagination and filtering
- **GET `/api/tracks/{track_id}`** - Get a specific track by ID
- **GET `/api/tracks/search/`** - Search tracks by various criteria
- **GET `/api/tracks/stats/overview`** - Get overview statistics

## Response Formats

All endpoints support three response formats:

### 1. Minimal Format
```json
{
  "id": 846,
  "file_path": "/music/Alex Warren - Carry You Home.mp3",
  "file_name": "Alex Warren - Carry You Home.mp3",
  "analysis_status": "pending"
}
```

### 2. Summary Format (Default)
```json
{
  "id": 846,
  "file_path": "/music/Alex Warren - Carry You Home.mp3",
  "file_name": "Alex Warren - Carry You Home.mp3",
  "file_size": 6744856,
  "file_extension": ".mp3",
  "discovered_at": "2025-08-11T12:03:58.681419",
  "analysis_status": "pending",
  "is_active": true,
  "title": "Carry You Home",
  "artist": "Alex Warren",
  "album": "Bangers Only",
  "track_number": 35,
  "year": 2025,
  "genre": "Pop",
  "duration": 166.8808843537415,
  "bpm": 0.0,
  "key": null,
  "bitrate": 320000,
  "sample_rate": 44100,
  "tempo": 200.0,
  "key_analysis": "Bb",
  "scale": "major",
  "key_strength": 0.9350617527961731,
  "energy": 81583.337890625,
  "loudness": 1874.3298950195312,
  "spectral_centroid_mean": null,
  "analysis_timestamp": "2025-08-11T14:49:35.848451"
}
```

### 3. Detailed Format
```json
{
  "id": 846,
  "file_path": "/music/Alex Warren - Carry You Home.mp3",
  "file_name": "Alex Warren - Carry You Home.mp3",
  "file_size": 6744856,
  "file_hash": "e268259938924d506bc237dc0110ef4b",
  "file_extension": ".mp3",
  "discovered_at": "2025-08-11T12:03:58.681419",
  "last_modified": "2025-08-11T12:03:58.720960",
  "analysis_status": "pending",
  "is_active": true,
  "metadata": {
    "title": "Carry You Home",
    "artist": "Alex Warren",
    "album": "Bangers Only",
    "track_number": 35,
    "year": 2025,
    "genre": "Pop",
    "album_artist": "Various Artists",
    "disc_number": 1,
    "composer": null,
    "duration": 166.8808843537415,
    "bpm": 0.0,
    "key": null,
    "comment": null,
    "mood": null,
    "rating": null,
    "isrc": "USAT22403017",
    "encoder": null,
    "bitrate": 320000,
    "sample_rate": 44100,
    "channels": null,
    "format": null,
    "file_size": 6744856,
    "file_format": ".mp3",
    "replaygain_track_gain": null,
    "replaygain_album_gain": null,
    "replaygain_track_peak": null,
    "replaygain_album_peak": null,
    "musicbrainz_track_id": null,
    "musicbrainz_artist_id": null,
    "musicbrainz_album_id": null,
    "musicbrainz_album_artist_id": null,
    "created_at": "2025-08-11T12:03:58.722021",
    "updated_at": "2025-08-11T12:03:58.722024"
  },
  "analysis": {
    "analysis_timestamp": "2025-08-11T14:49:35.848451",
    "analysis_duration": 0.0,
    "sample_rate": null,
    "duration": null,
    "basic_features": {
      "rms": 0.2368331104516983,
      "energy": 81583.337890625,
      "loudness": 1874.3298950195312,
      "spectral_centroid_mean": null,
      "spectral_centroid_std": null,
      "spectral_rolloff_mean": null,
      "spectral_rolloff_std": null,
      "spectral_contrast_mean": -4.4235007762908936,
      "spectral_contrast_std": 4.599072217941284,
      "spectral_complexity_mean": 19.768158026429525,
      "spectral_complexity_std": 12.833303703874865
    },
    "mfcc_features": {
      "mfcc_mean": [],
      "mfcc_bands_mean": []
    },
    "rhythm_features": {
      "tempo": 200.0,
      "tempo_confidence": 0.0,
      "rhythm_bpm": 200.0,
      "rhythm_confidence": 0.0,
      "beat_confidence": 0.0,
      "beats": [],
      "rhythm_ticks": [],
      "rhythm_estimates": [],
      "onset_detections": []
    },
    "harmonic_features": {
      "key": "Bb",
      "scale": "major",
      "key_strength": 0.9350617527961731,
      "chords": [],
      "chord_strengths": [],
      "pitch_yin": [],
      "pitch_yin_confidence": [],
      "pitch_melodia": [],
      "pitch_melodia_confidence": [],
      "chromagram": []
    },
    "tensorflow_features": {},
    "complete_analysis": { /* Full analysis data */ },
    "created_at": "2025-08-11T14:49:35.849448",
    "updated_at": "2025-08-11T14:49:35.849451"
  }
}
```

## Endpoints

### 1. Get All Tracks

**Endpoint:** `GET /api/tracks/`

**Parameters:**
- `limit` (int, default: 100) - Maximum number of tracks to return
- `offset` (int, default: 0) - Number of tracks to skip
- `analyzed_only` (bool, default: false) - Return only analyzed tracks
- `has_metadata` (bool, default: false) - Return only tracks with metadata
- `format` (string, default: "summary") - Response format: "minimal", "summary", or "detailed"

**Example:**
```bash
# Get first 10 tracks in summary format
curl "http://localhost:8000/api/tracks/?limit=10&format=summary"

# Get only analyzed tracks
curl "http://localhost:8000/api/tracks/?analyzed_only=true"

# Get tracks with metadata only
curl "http://localhost:8000/api/tracks/?has_metadata=true"
```

**Response:**
```json
{
  "total_count": 87,
  "returned_count": 10,
  "offset": 0,
  "limit": 10,
  "tracks": [/* array of track objects */]
}
```

### 2. Get Track by ID

**Endpoint:** `GET /api/tracks/{track_id}`

**Parameters:**
- `track_id` (int, path parameter) - Track ID
- `format` (string, default: "detailed") - Response format

**Example:**
```bash
# Get track with ID 846 in detailed format
curl "http://localhost:8000/api/tracks/846?format=detailed"

# Get track in minimal format
curl "http://localhost:8000/api/tracks/846?format=minimal"
```

**Response:** Single track object in the specified format

### 3. Search Tracks

**Endpoint:** `GET /api/tracks/search/`

**Parameters:**
- `title` (string, optional) - Search in title
- `artist` (string, optional) - Search in artist
- `album` (string, optional) - Search in album
- `genre` (string, optional) - Search in genre
- `key` (string, optional) - Search by musical key
- `min_tempo` (float, optional) - Minimum tempo
- `max_tempo` (float, optional) - Maximum tempo
- `min_duration` (float, optional) - Minimum duration in seconds
- `max_duration` (float, optional) - Maximum duration in seconds
- `analyzed_only` (bool, default: false) - Only return analyzed tracks
- `limit` (int, default: 50) - Maximum number of tracks to return
- `offset` (int, default: 0) - Number of tracks to skip
- `format` (string, default: "summary") - Response format

**Example:**
```bash
# Search for tracks by artist
curl "http://localhost:8000/api/tracks/search/?artist=Alex&format=summary"

# Search for tracks in a specific genre
curl "http://localhost:8000/api/tracks/search/?genre=Pop&format=summary"

# Search for tracks with tempo between 120-140 BPM
curl "http://localhost:8000/api/tracks/search/?min_tempo=120&max_tempo=140"

# Search for tracks with duration between 3-5 minutes
curl "http://localhost:8000/api/tracks/search/?min_duration=180&max_duration=300"

# Search for tracks in C major key
curl "http://localhost:8000/api/tracks/search/?key=C"
```

**Response:**
```json
{
  "total_count": 2,
  "returned_count": 2,
  "offset": 0,
  "limit": 50,
  "search_criteria": {
    "title": null,
    "artist": "Alex",
    "album": null,
    "genre": null,
    "key": null,
    "min_tempo": null,
    "max_tempo": null,
    "min_duration": null,
    "max_duration": null,
    "analyzed_only": false
  },
  "tracks": [/* array of track objects */]
}
```

### 4. Get Overview Statistics

**Endpoint:** `GET /api/tracks/stats/overview`

**Parameters:** None

**Example:**
```bash
curl "http://localhost:8000/api/tracks/stats/overview"
```

**Response:**
```json
{
  "total_tracks": 87,
  "analyzed_tracks": 1,
  "tracks_with_metadata": 86,
  "analysis_coverage": 1.15,
  "metadata_coverage": 98.85,
  "unique_artists": 81,
  "unique_albums": 61,
  "unique_genres": 19,
  "unique_keys": 1,
  "file_formats": {
    ".flac": 15,
    ".mp3": 57,
    ".m4a": 2,
    ".ogg": 13
  }
}
```

## Track Attributes

### File Information
- `id` - Unique track ID
- `file_path` - Full file path
- `file_name` - File name
- `file_size` - File size in bytes
- `file_hash` - File hash (detailed format only)
- `file_extension` - File extension
- `discovered_at` - When the file was discovered
- `last_modified` - Last modification time (detailed format only)
- `analysis_status` - Analysis status: "pending", "essentia_complete", "tensorflow_complete", "complete", "failed"
- `is_active` - Whether the track is active

### Metadata (Summary & Detailed)
- `title` - Track title
- `artist` - Artist name
- `album` - Album name
- `track_number` - Track number
- `year` - Release year
- `genre` - Genre
- `album_artist` - Album artist (detailed format only)
- `disc_number` - Disc number (detailed format only)
- `composer` - Composer (detailed format only)
- `duration` - Duration in seconds
- `bpm` - BPM from metadata
- `key` - Musical key from metadata
- `comment` - Comments (detailed format only)
- `mood` - Mood (detailed format only)
- `rating` - Rating (detailed format only)
- `isrc` - ISRC code (detailed format only)
- `encoder` - Encoder (detailed format only)
- `bitrate` - Bitrate
- `sample_rate` - Sample rate
- `channels` - Number of channels (detailed format only)
- `format` - Audio format (detailed format only)
- `file_size` - File size from metadata (detailed format only)
- `file_format` - File format (detailed format only)
- `replaygain_*` - ReplayGain values (detailed format only)
- `musicbrainz_*` - MusicBrainz IDs (detailed format only)

### Analysis Features (Summary & Detailed)
- `tempo` - Analyzed tempo
- `key_analysis` - Analyzed musical key
- `scale` - Musical scale
- `key_strength` - Key detection confidence
- `energy` - Energy level
- `loudness` - Loudness
- `spectral_centroid_mean` - Spectral centroid mean
- `analysis_timestamp` - When analysis was performed

### Detailed Analysis (Detailed Format Only)
- `basic_features` - RMS, energy, loudness, spectral features
- `mfcc_features` - MFCC coefficients and mel bands
- `rhythm_features` - Tempo, beats, rhythm analysis
- `harmonic_features` - Key, scale, chords, pitch analysis
- `tensorflow_features` - TensorFlow model outputs
- `complete_analysis` - Full analysis data with segment details

## Usage Examples

### Quick Track Lookup
```bash
# Get basic info for a track
curl "http://localhost:8000/api/tracks/846?format=summary"
```

### Batch Processing
```bash
# Get all tracks in minimal format for batch processing
curl "http://localhost:8000/api/tracks/?format=minimal&limit=1000"
```

### Advanced Search
```bash
# Find all Pop tracks with tempo > 120 BPM
curl "http://localhost:8000/api/tracks/search/?genre=Pop&min_tempo=120&analyzed_only=true"
```

### Library Statistics
```bash
# Get overview of your music library
curl "http://localhost:8000/api/tracks/stats/overview"
```

### Filtering by Analysis Status
```bash
# Get only analyzed tracks
curl "http://localhost:8000/api/tracks/?analyzed_only=true"

# Get only tracks with metadata
curl "http://localhost:8000/api/tracks/?has_metadata=true"
```

## Performance Notes

- **Minimal format** is fastest for bulk operations
- **Summary format** provides a good balance of information and speed
- **Detailed format** includes all data but is slower
- All endpoints support pagination for large datasets
- Search endpoints are optimized for common queries
- NaN and Infinity values are automatically converted to `null` for JSON compatibility

## Error Handling

- **404 Not Found** - Track ID doesn't exist
- **500 Internal Server Error** - Database or processing error
- All errors include descriptive messages

## Integration with Other APIs

The Tracks API complements other APIs in the system:

- **Discovery API** - For finding new tracks
- **Analyzer API** - For analyzing tracks
- **Metadata API** - For metadata extraction
- **Configuration API** - For system settings

This provides a complete workflow from discovery to analysis to querying.
