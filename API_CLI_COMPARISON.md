# API vs CLI Feature Comparison and Gap Analysis

## Overview

This document provides a comprehensive comparison between the available API endpoints and CLI commands, identifying missing features and providing recommendations for improvement.

## Current API Endpoints

### Discovery API (`/api/discovery`)
-  `POST /scan` - Scan for new files
-  `GET /files` - List discovered files
-  `GET /files/{file_hash}` - Get file by hash
-  `GET /status` - Get discovery status
-  `GET /stats` - Get discovery statistics
-  `POST /init` - Initialize database
-  `POST /re-discover` - Re-discover all files
-  `GET /config` - Get discovery configuration

### Analyzer API (`/api/analyzer`)
-  `GET /status` - Get analyzer status
-  `POST /analyze-batches` - Analyze all batches
-  `POST /analyze-category/{category}` - Analyze by category
-  `GET /categorize` - Categorize files by length
-  `GET /length-stats` - Get length statistics
-  `GET /categories` - Get available categories
-  `POST /analyze-file` - Analyze single file
-  `POST /analyze-files` - Analyze multiple files
-  `GET /analysis/{file_path}` - Get analysis results
-  `GET /analysis-summary/{file_path}` - Get analysis summary
-  `GET /unanalyzed-files` - Get unanalyzed files
-  `GET /statistics` - Get analysis statistics
-  `POST /force-reanalyze` - Force re-analyze all files
-  `DELETE /analysis/{file_path}` - Delete analysis
-  `GET /config` - Get analyzer configuration
-  `POST /config/reload` - Reload configuration
-  `GET /config/performance` - Get performance config
-  `GET /config/essentia` - Get Essentia config

### FAISS API (`/api/faiss`)
-  `GET /status` - Get FAISS status
-  `POST /build-index` - Build FAISS index
-  `GET /statistics` - Get index statistics
-  `POST /add-track` - Add track to index
-  `GET /similar-tracks` - Find similar tracks
-  `POST /similar-by-vector` - Find similar by vector
-  `POST /extract-vector` - Extract feature vector
-  `POST /generate-playlist` - Generate playlist
-  `POST /save-index` - Save index to disk
-  `POST /load-index` - Load index from database

### Tracks API (`/api/tracks`)
-  `GET /` - Get all tracks (with filtering and formatting)

### Metadata API (`/api/metadata`)
-  `GET /search` - Search metadata
-  `GET /{file_id}` - Get file metadata
-  `GET /stats/overview` - Get metadata statistics

### Configuration API (`/api/config`)
-  `GET /` - Get available configs
-  `GET /consolidated` - Get consolidated config
-  `GET /discovery` - Get discovery config
-  `GET /database` - Get database config
-  `GET /logging` - Get logging config
-  `GET /app` - Get app settings
-  `GET /api-timeouts` - Get API timeouts
-  `GET /analysis` - Get analysis config
-  `GET /all` - Get all configs
-  `POST /update` - Update configuration
-  `POST /backup` - Backup configurations
-  `POST /restore` - Restore configurations
-  `GET /list` - List configs
-  `DELETE /{section}` - Delete config section
-  `POST /reload` - Reload configs
-  `GET /validate` - Validate configs
-  `GET /monitor/health` - Get config health
-  `GET /monitor/metrics` - Get config metrics
-  `GET /monitor/history` - Get config history
-  `GET /schemas` - Get config schemas
-  `POST /monitor/reset` - Reset config metrics
-  `POST /monitor/clear-history` - Clear config history

## Current CLI Commands

### Main Playlist CLI (`playlist`)
-  `scan` - Scan for new files
-  `list` - List discovered files
-  `stats` - Show statistics
-  `config` - Show configuration
-  `validate` - Validate directories
-  `re-discover` - Re-discover all files
-  `search` - Search metadata
-  `enrich-genres` - Enrich genres
-  `categorize` - Categorize files
-  `analyze` - Analyze files
-  `force-reanalyze` - Force re-analyze
-  `analysis-config` - Show analysis config
-  `reload-config` - Reload configuration
-  `length-stats` - Show length statistics

### Batch Analyzer CLI (`analyze`)
-  `categorize` - Get file categorization
-  `length-stats` - Get length statistics
-  `categories` - Get available categories
-  `statistics` - Get analysis statistics
-  `analyze-file` - Analyze single file
-  `analyze-files` - Analyze multiple files
-  `analyze-all` - Analyze all batches
-  `analyze-category` - Analyze by category
-  `get-analysis` - Get analysis results
-  `get-summary` - Get analysis summary
-  `unanalyzed` - Get unanalyzed files
-  `delete-analysis` - Delete analysis

### Database CLI (`db`)
-  `status` - Get database status
-  `reset` - Reset database
-  `backup` - Create backup
-  `restore` - Restore from backup
-  `list-backups` - List available backups

## Missing CLI Features

### 1. FAISS Operations
**Missing CLI commands for FAISS functionality:**
-  `faiss status` - Check FAISS service status
-  `faiss build-index` - Build FAISS index
-  `faiss statistics` - Get index statistics
-  `faiss add-track` - Add track to index
-  `faiss similar-tracks` - Find similar tracks
-  `faiss generate-playlist` - Generate playlist
-  `faiss extract-vector` - Extract feature vector

### 2. Configuration Management
**Missing CLI commands for configuration:**
-  `config list` - List available configurations
-  `config show <section>` - Show specific configuration
-  `config update <section>` - Update configuration
-  `config backup` - Backup configurations
-  `config restore` - Restore configurations
-  `config validate` - Validate configurations
-  `config monitor` - Monitor configuration health

### 3. Advanced Metadata Operations
**Missing CLI commands for metadata:**
-  `metadata show <file_id>` - Show metadata for specific file
-  `metadata stats` - Show metadata statistics
-  `metadata export` - Export metadata to file
-  `metadata import` - Import metadata from file

### 4. Health and Monitoring
**Missing CLI commands for system health:**
-  `health` - Check system health
-  `status` - Get overall system status
-  `monitor` - Monitor system metrics

### 5. File Management
**Missing CLI commands for file operations:**
-  `files show <file_id>` - Show detailed file information
-  `files delete <file_id>` - Delete file from database
-  `files export` - Export file list
-  `files import` - Import file list

## Missing API Features

### 1. Health and Monitoring
**Missing API endpoints:**
-  `GET /health` - System health check (exists but not comprehensive)
-  `GET /status` - Overall system status
-  `GET /metrics` - System metrics
-  `GET /monitor` - Real-time monitoring

### 2. File Management
**Missing API endpoints:**
-  `DELETE /tracks/{track_id}` - Delete track
-  `PUT /tracks/{track_id}` - Update track
-  `POST /tracks/export` - Export tracks
-  `POST /tracks/import` - Import tracks

### 3. Advanced Search
**Missing API endpoints:**
-  `POST /tracks/search` - Advanced search with filters
-  `GET /tracks/similar/{track_id}` - Find similar tracks
-  `GET /tracks/recommendations` - Get recommendations

### 4. Batch Operations
**Missing API endpoints:**
-  `POST /tracks/batch-delete` - Batch delete tracks
-  `POST /tracks/batch-update` - Batch update tracks
-  `POST /tracks/batch-analyze` - Batch analyze tracks

## Recommendations

### 1. Create Unified CLI Tool
Create a comprehensive CLI tool that provides access to all API functionality:

```bash
# Example unified CLI structure
playlist-cli health                    # System health
playlist-cli status                    # System status
playlist-cli discovery scan            # Discovery operations
playlist-cli discovery list            # List files
playlist-cli analysis start            # Start analysis
playlist-cli analysis status           # Analysis status
playlist-cli faiss build               # FAISS operations
playlist-cli faiss search              # Similarity search
playlist-cli config show               # Configuration
playlist-cli config update             # Update config
playlist-cli metadata search           # Metadata search
playlist-cli tracks list               # Track operations
```

### 2. Add Missing API Endpoints
Implement the missing API endpoints for complete functionality:

```python
# Health and monitoring
@router.get("/health")
@router.get("/status") 
@router.get("/metrics")

# File management
@router.delete("/tracks/{track_id}")
@router.put("/tracks/{track_id}")
@router.post("/tracks/export")
@router.post("/tracks/import")

# Advanced search
@router.post("/tracks/search")
@router.get("/tracks/similar/{track_id}")
@router.get("/tracks/recommendations")

# Batch operations
@router.post("/tracks/batch-delete")
@router.post("/tracks/batch-update")
@router.post("/tracks/batch-analyze")
```

### 3. Improve CLI Documentation
- Add comprehensive help for all commands
- Provide examples for common workflows
- Include troubleshooting guides

### 4. Add Interactive CLI Mode
Create an interactive CLI mode for easier usage:

```bash
playlist-cli interactive
# Enters interactive mode with command completion
```

### 5. Add CLI Configuration
Allow CLI configuration for:
- Default API endpoints
- Authentication
- Output formatting
- Verbosity levels

## Priority Implementation Order

### High Priority
1. **Health and monitoring endpoints** - Essential for system management
2. **FAISS CLI commands** - Important for similarity search functionality
3. **Configuration CLI commands** - Needed for system administration

### Medium Priority
1. **Advanced search endpoints** - Improves user experience
2. **Batch operations** - Useful for large-scale operations
3. **File management endpoints** - Basic CRUD operations

### Low Priority
1. **Interactive CLI mode** - Nice-to-have feature
2. **Advanced monitoring** - For power users
3. **Export/import functionality** - For data portability

## Conclusion

The API is more comprehensive than the CLI, with many endpoints that don't have corresponding CLI commands. The main gaps are in FAISS operations, configuration management, and system monitoring. Implementing the missing CLI commands would provide users with complete command-line access to all system functionality.
