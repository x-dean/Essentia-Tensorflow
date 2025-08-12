# Playlist App CLI Usage

The CLI commands are now available directly from the Docker container without needing `python` in front.

## Available Commands

### Main Playlist Commands
```bash
# Scan for new audio files
docker exec -it playlist-app playlist scan

# List discovered files
docker exec -it playlist-app playlist list
docker exec -it playlist-app playlist list --limit 10
docker exec -it playlist-app playlist list --format json

# Show statistics
docker exec -it playlist-app playlist stats

# Show configuration
docker exec -it playlist-app playlist config

# Validate search directories
docker exec -it playlist-app playlist validate

# Re-discover all files
docker exec -it playlist-app playlist re-discover

# Search metadata
docker exec -it playlist-app playlist search --query "love"
docker exec -it playlist-app playlist search --artist "Coldplay"

# Enrich genres
docker exec -it playlist-app playlist enrich-genres --limit 5

# Categorize files by length
docker exec -it playlist-app playlist categorize

# Analyze files
docker exec -it playlist-app playlist analyze --max-workers 4 --max-files 10

# Force re-analyze
docker exec -it playlist-app playlist force-reanalyze

# Show analysis configuration
docker exec -it playlist-app playlist analysis-config

# Reload configuration
docker exec -it playlist-app playlist reload-config

# Show length statistics
docker exec -it playlist-app playlist length-stats
```

### Analysis Commands
```bash
# Get analysis statistics
docker exec -it playlist-app analyze statistics

# Get file categorization
docker exec -it playlist-app analyze categorize

# Get length statistics
docker exec -it playlist-app analyze length-stats

# Get available categories
docker exec -it playlist-app analyze categories

# Analyze all batches
docker exec -it playlist-app analyze analyze-all

# Analyze specific category
docker exec -it playlist-app analyze analyze-category normal

# Analyze specific files
docker exec -it playlist-app analyze analyze-files music/track1.mp3 music/track2.mp3

# Get analysis for a file
docker exec -it playlist-app analyze get-analysis music/track.mp3

# Get unanalyzed files
docker exec -it playlist-app analyze unanalyzed --limit 10
```

### Database Commands
```bash
# Reset database (requires confirmation)
docker exec -it playlist-app python /usr/local/bin/db reset-db --confirm

# Show database help
docker exec -it playlist-app python /usr/local/bin/db --help
```

## Quick Examples

### Daily Workflow
```bash
# 1. Scan for new files
docker exec -it playlist-app playlist scan

# 2. Check statistics
docker exec -it playlist-app playlist stats

# 3. Analyze new files
docker exec -it playlist-app analyze analyze-all

# 4. Check analysis progress
docker exec -it playlist-app analyze statistics
```

### Troubleshooting
```bash
# Check if files are being discovered
docker exec -it playlist-app playlist list --limit 5

# Validate search directories
docker exec -it playlist-app playlist validate

# Check analysis coverage
docker exec -it playlist-app analyze statistics

# Force re-analyze if needed
docker exec -it playlist-app playlist force-reanalyze --max-files 1
```

## Notes

- All commands run inside the Docker container
- The `playlist` command provides most discovery and management functions
- The `analyze` command provides audio analysis functions
- The `db` command provides database operations (use with `python` due to line ending issues)
- Use `--help` with any command to see available options
- Use `--verbose` or `-v` for detailed output
- Use `--json` for machine-readable output
