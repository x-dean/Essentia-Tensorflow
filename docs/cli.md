# Playlist App CLI

A command-line interface for the Playlist App Discovery System. This CLI provides easy access to all discovery functionality through simple commands.

## Installation

### Option 1: Direct Execution
```bash
# Make the CLI executable
chmod +x cli.py
chmod +x playlist

# Run directly
./cli.py scan
./playlist scan
```

### Option 2: Install as Package
```bash
# Install in development mode
pip install -e .

# Use the installed command
playlist scan
```

### Option 3: Python Module
```bash
# Run as Python module
python -m cli scan
```

## Quick Start

1. **Initialize and scan for files:**
   ```bash
   ./cli.py scan --verbose
   ```

2. **List discovered files:**
   ```bash
   ./cli.py list
   ```

3. **Check statistics:**
   ```bash
   ./cli.py stats
   ```

## Commands

### `scan` - Scan for Files
Scans configured directories for new audio files and updates the database.

```bash
./cli.py scan [--verbose]
```

**Options:**
- `--verbose, -v`: Show detailed output including file names

**Example:**
```bash
$ ./cli.py scan --verbose
Scanning directories for audio files...
Search directories: /music, /audio
Supported extensions: .mp3, .wav, .flac, .ogg, .m4a, .aac, .wma, .opus

Discovery Results:
  Added: 5 files
  Removed: 2 files
  Unchanged: 100 files

Added files:
  + song1.mp3
  + song2.wav
  + song3.flac
```

### `list` - List Discovered Files
Lists discovered files with various formatting options.

```bash
./cli.py list [--limit N] [--offset N] [--format FORMAT]
```

**Options:**
- `--limit, -l`: Number of files to show (default: 50)
- `--offset, -o`: Number of files to skip (default: 0)
- `--format, -f`: Output format: `table` or `json` (default: table)

**Examples:**
```bash
# List first 10 files
./cli.py list --limit 10

# List files in JSON format
./cli.py list --format json

# List files with pagination
./cli.py list --limit 20 --offset 40
```

**Table Output:**
```
Name                    Ext      Size      Status    
------------------------------------------------
song1.mp3              .mp3     5.2MB     Pending   
song2.wav              .wav     12.1MB    Analyzed  
song3.flac             .flac    8.7MB     Pending   
```

**JSON Output:**
```json
{
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
  "count": 1,
  "limit": 50,
  "offset": 0
}
```

### `stats` - Show Statistics
Displays discovery statistics including file counts and extension distribution.

```bash
./cli.py stats [--format FORMAT]
```

**Options:**
- `--format, -f`: Output format: `table` or `json` (default: table)

**Table Output:**
```
Discovery Statistics:
==============================
Total Files:      150
Analyzed Files:   75
Pending Analysis: 75

File Extensions:
--------------------
.mp3        100 files
.wav         30 files
.flac        20 files
```

### `config` - Show Configuration
Displays current configuration settings.

```bash
./cli.py config
```

**Output:**
```
Discovery Configuration:
==============================
Database URL:     sqlite:///./playlist_app.db
Search Directories: /music, /audio
Supported Extensions: .mp3, .wav, .flac, .ogg, .m4a, .aac, .wma, .opus
Cache TTL:        3600 seconds
Batch Size:       100
Log Level:        INFO
```

### `validate` - Validate Directories
Checks if configured search directories exist.

```bash
./cli.py validate
```

**Output:**
```
Validating search directories...

 /music
 /audio (does not exist)

Some search directories do not exist. Please check your configuration.
```

### `categorize` - Categorize Files by Length
Categorizes audio files based on their duration into length categories.

```bash
./cli.py categorize [--format FORMAT]
```

**Options:**
- `--format, -f`: Output format: `table` or `json` (default: table)

**Categories:**
- `normal`: 0-5 minutes (0-300 seconds)
- `long`: 5-10 minutes (300-600 seconds)  
- `very_long`: 10+ minutes (600+ seconds)
- `unknown`: Files with unknown duration

**Table Output:**
```
File Length Categories:
------------------------------------------------------------
Category         Count      Description                    
------------------------------------------------------------
normal           45         0-5 minutes                    
long             12         5-10 minutes                   
very_long        3          10+ minutes                    
unknown          0          Unknown duration               
------------------------------------------------------------
Total            60                                         
```

### `analyze-batches` - Analyze Files in Batches
Analyzes files in batches organized by length category for efficient processing.

```bash
./cli.py analyze-batches [--category CATEGORY] [--batch-size N] [--verbose]
```

**Options:**
- `--category, -c`: Specific category to analyze: `normal`, `long`, or `very_long`
- `--batch-size, -b`: Number of files per batch (default: 50)
- `--verbose, -v`: Show detailed output

**Examples:**
```bash
# Analyze all categories in batches
./cli.py analyze-batches --batch-size 25

# Analyze only long tracks
./cli.py analyze-batches --category long --verbose

# Analyze with custom batch size
./cli.py analyze-batches --batch-size 100
```

**Verbose Output:**
```
Analyzing files in batches (batch_size: 50)

Analysis Results:
  Total batches processed: 3
  Total files processed: 120
  Successful: 115
  Failed: 5

Category Statistics:
  normal: 85
  long: 25
  very_long: 5
```

### `length-stats` - Show Length Statistics
Displays detailed statistics about file lengths and categories.

```bash
./cli.py length-stats [--format FORMAT]
```

**Options:**
- `--format, -f`: Output format: `table` or `json` (default: table)

**Table Output:**
```
Length Statistics:
------------------------------------------------------------
Metric                      Value                             
------------------------------------------------------------
Total files                 150                               
Analyzed files              120                               

Category Counts:
  normal: 85
  long: 25
  very_long: 5
  unknown: 5

Duration Ranges:
  Min duration: 45 seconds
  Max duration: 1800 seconds
  Avg duration: 245.67 seconds
```

## Configuration

The CLI uses the same configuration as the API. Set environment variables to customize behavior:

```bash
# Database
export DATABASE_URL="sqlite:///./playlist_app.db"

# Search directories (comma-separated)
export SEARCH_DIRECTORIES="/music,/audio,/home/user/music"

# Discovery settings
export DISCOVERY_CACHE_TTL=3600
export DISCOVERY_BATCH_SIZE=100

# Logging
export LOG_LEVEL=INFO
```

## Usage Examples

### Basic Workflow
```bash
# 1. Check configuration
./cli.py config

# 2. Validate directories
./cli.py validate

# 3. Scan for files
./cli.py scan --verbose

# 4. Check results
./cli.py stats

# 5. List discovered files
./cli.py list --limit 20
```

### Batch Processing
```bash
# Scan and get statistics in one go
./cli.py scan && ./cli.py stats

# List files in JSON for scripting
./cli.py list --format json --limit 100 > files.json
```

### Integration with Shell Scripts
```bash
#!/bin/bash
# Example script to monitor music directory

echo "Starting music discovery..."

# Scan for new files
./cli.py scan

# Get statistics
./cli.py stats

# List unanalyzed files
./cli.py list --limit 50 | grep "Pending"
```

## Error Handling

The CLI provides clear error messages and appropriate exit codes:

- **Exit Code 0**: Success
- **Exit Code 1**: Error or failure

**Common Error Scenarios:**
```bash
# Database not accessible
Error initializing database: [Errno 13] Permission denied

# Invalid directory
 /invalid/path (does not exist)

# No files found
No files found.
```

## Integration with API

The CLI works alongside the API server:

```bash
# Start API server
uvicorn main:app --host 0.0.0.0 --port 8000 &

# Use CLI for discovery
./cli.py scan

# Use API for other operations
curl http://localhost:8000/api/discovery/stats
```

## Troubleshooting

### Common Issues

1. **Permission Denied:**
   ```bash
   chmod +x cli.py
   chmod +x playlist
   ```

2. **Database Locked:**
   ```bash
   # Check if another process is using the database
   lsof playlist_app.db
   ```

3. **No Files Found:**
   ```bash
   # Check configuration
   ./cli.py config
   
   # Validate directories
   ./cli.py validate
   ```

4. **Import Errors:**
   ```bash
   # Install dependencies
   pip install -r requirements.txt
   ```

### Debug Mode
Set environment variable for verbose logging:
```bash
export LOG_LEVEL=DEBUG
./cli.py scan
```

## Advanced Usage

### Custom Search Directories
```bash
# Temporary override
SEARCH_DIRECTORIES="/custom/music" ./cli.py scan

# Permanent configuration
echo 'export SEARCH_DIRECTORIES="/custom/music"' >> ~/.bashrc
```

### Batch Operations
```bash
# Process all files in batches
for i in {0..1000..50}; do
    ./cli.py list --limit 50 --offset $i
done
```

### Integration with Cron
```cron
# Scan for new files every hour
0 * * * * cd /path/to/playlist-app && ./cli.py scan >> /var/log/playlist.log 2>&1
```

## Exit Codes

- `0`: Success
- `1`: General error
- `2`: Invalid arguments
- `3`: Database error
- `4`: File system error

## Performance Tips

1. **Use caching:** The discovery system caches file information for faster subsequent scans
2. **Batch operations:** Use `--limit` and `--offset` for large file collections
3. **JSON output:** Use `--format json` for programmatic processing
4. **Regular scans:** Run scans periodically rather than continuously

## Support

For issues and questions:
- Check the main README.md
- Review the API documentation
- Check error messages and exit codes
- Validate configuration with `./cli.py config`
