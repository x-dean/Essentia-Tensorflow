# CLI Commands Usage Guide

This document explains how to use the CLI commands for the Essentia-Tensorflow Playlist App.

## Quick Start

All CLI commands are accessed through the `playlist` command:

```bash
docker-compose exec playlist-app playlist <command> [subcommand] [options]
```

## Available Commands

### Health and Status

#### Check system health
```bash
docker-compose exec playlist-app playlist health
```

#### Get system status
```bash
docker-compose exec playlist-app playlist status
```

### Discovery Operations

#### Scan for new files
```bash
docker-compose exec playlist-app playlist discovery scan
```

#### Get discovery statistics
```bash
docker-compose exec playlist-app playlist discovery stats
```

#### List discovered files
```bash
docker-compose exec playlist-app playlist discovery list --limit 50 --offset 0
```

#### Trigger discovery manually
```bash
docker-compose exec playlist-app playlist discovery trigger
```

#### Get discovery status
```bash
docker-compose exec playlist-app playlist discovery status
```

#### Toggle background discovery
```bash
docker-compose exec playlist-app playlist discovery toggle-background
```

### Analysis Operations

#### Get analysis statistics
```bash
docker-compose exec playlist-app playlist analysis stats
```

#### Categorize files by length
```bash
docker-compose exec playlist-app playlist analysis categorize
```

#### Start analysis
```bash
docker-compose exec playlist-app playlist analysis start --include-tensorflow --max-workers 4
```

#### Trigger analysis manually
```bash
docker-compose exec playlist-app playlist analysis trigger
```

#### Get analysis status
```bash
docker-compose exec playlist-app playlist analysis status
```

### FAISS Operations

#### Build FAISS index
```bash
docker-compose exec playlist-app playlist faiss build --include-tensorflow --force
```

#### Find similar tracks
```bash
docker-compose exec playlist-app playlist faiss similar --query /path/to/track.mp3 --top-n 5
```

#### Generate playlist
```bash
docker-compose exec playlist-app playlist faiss playlist --seed /path/to/track.mp3 --length 10
```

### Configuration Operations

#### List available configurations
```bash
docker-compose exec playlist-app playlist config list
```

#### Show specific configuration
```bash
docker-compose exec playlist-app playlist config show discovery
```

#### Validate configurations
```bash
docker-compose exec playlist-app playlist config validate
```

#### Reload configurations
```bash
docker-compose exec playlist-app playlist config reload
```

### Metadata Operations

#### Get metadata statistics
```bash
docker-compose exec playlist-app playlist metadata stats
```

#### Search metadata
```bash
docker-compose exec playlist-app playlist metadata search --query "love" --artist "artist_name" --limit 20
```

### Track Operations

#### List tracks
```bash
docker-compose exec playlist-app playlist tracks list --limit 100 --analyzed-only --format summary
```

### Database Operations

#### Get database status
```bash
docker-compose exec playlist-app playlist database status
```

#### Reset database (direct)
```bash
docker-compose exec playlist-app playlist database reset --confirm
```

#### Reset database via API
```bash
docker-compose exec playlist-app playlist database reset-api --confirm
```

## Command Options

### Global Options

All commands support these global options:

- `--url <url>`: Specify API base URL (default: http://localhost:8000)
- `--json`: Output raw JSON instead of formatted text

### Common Parameters

- `--limit <number>`: Number of items to return
- `--offset <number>`: Number of items to skip
- `--confirm`: Confirm destructive operations (required for database reset)

## Examples

### Basic workflow
```bash
# 1. Check system health
docker-compose exec playlist-app playlist health

# 2. Scan for new files
docker-compose exec playlist-app playlist discovery scan

# 3. Start analysis
docker-compose exec playlist-app playlist analysis start --include-tensorflow

# 4. Check analysis progress
docker-compose exec playlist-app playlist analysis status

# 5. Build FAISS index
docker-compose exec playlist-app playlist faiss build

# 6. Generate a playlist
docker-compose exec playlist-app playlist faiss playlist --seed /music/track.mp3 --length 10
```

### Monitoring and debugging
```bash
# Check all system statuses
docker-compose exec playlist-app playlist status

# Get detailed discovery stats
docker-compose exec playlist-app playlist discovery stats

# Get analysis statistics
docker-compose exec playlist-app playlist analysis stats

# Check database status
docker-compose exec playlist-app playlist database status

# List recent tracks
docker-compose exec playlist-app playlist tracks list --limit 20 --analyzed-only
```

### Configuration management
```bash
# List all configurations
docker-compose exec playlist-app playlist config list

# View discovery configuration
docker-compose exec playlist-app playlist config show discovery

# Validate all configurations
docker-compose exec playlist-app playlist config validate

# Reload configurations
docker-compose exec playlist-app playlist config reload
```

## Troubleshooting

### Common Issues

1. **Command not found**: Make sure you're using the correct command structure with `playlist` as the main command
2. **Connection refused**: Ensure the server is running with `docker-compose up`
3. **Permission denied**: Some operations require confirmation with `--confirm`
4. **Timeout errors**: Increase timeout for long-running operations

### Getting Help

To see all available commands:
```bash
docker-compose exec playlist-app playlist --help
```

To see help for a specific command:
```bash
docker-compose exec playlist-app playlist <command> --help
```

### JSON Output

For programmatic access, use the `--json` flag:
```bash
docker-compose exec playlist-app playlist health --json
```

This will output raw JSON that can be parsed by other tools.

## API Endpoints

The CLI commands correspond to these API endpoints:

- Health: `GET /health`
- Discovery: `POST /api/discovery/scan`, `GET /api/discovery/status`, etc.
- Analysis: `POST /api/analyzer/analyze-batches`, `GET /api/analyzer/status`, etc.
- FAISS: `POST /api/faiss/build-index`, `GET /api/faiss/similar-tracks`, etc.
- Configuration: `GET /config/list`, `GET /config/{section}`, etc.
- Metadata: `GET /api/metadata/search`, `GET /api/metadata/stats/overview`, etc.
- Tracks: `GET /api/tracks/`, etc.
- Database: `POST /database/reset`, etc.

You can also access these endpoints directly via HTTP requests to `http://localhost:8000`.
