# Configuration System

This directory contains JSON configuration files for the Playlist App. The configuration system supports both file-based configuration and environment variable fallbacks.

## Configuration Files

### 📁 `discovery.json`
Discovery system configuration including search directories, supported file extensions, and scan settings.

**Key Settings:**
- `search_directories`: List of directories to scan for audio files
- `supported_extensions`: Audio file extensions to process
- `cache_settings`: Discovery cache configuration
- `scan_settings`: File scanning behavior
- `hash_settings`: File hash calculation settings

### 🗄️ `database.json`
Database connection and configuration settings.

**Key Settings:**
- `connection`: Database connection parameters
- `tables`: Table configuration
- `migration`: Database migration settings

### 📝 `logging.json`
Logging configuration for different components.

**Key Settings:**
- `level`: Global log level
- `handlers`: Console and file logging settings
- `loggers`: Component-specific logging configuration

### ⚙️ `app_settings.json`
General application settings and API configuration.

**Key Settings:**
- `api`: API server configuration
- `performance`: Performance tuning parameters
- `discovery`: Background discovery settings
- `paths`: Application directory paths

## Usage

### API Endpoints

The configuration can be accessed via REST API endpoints:

```bash
# List available configurations
GET /api/config/

# Get specific configuration
GET /api/config/discovery
GET /api/config/database
GET /api/config/logging
GET /api/config/app

# Get all configurations
GET /api/config/all

# Validate configurations
GET /api/config/validate

# Reload configurations
POST /api/config/reload
```

### CLI Commands

```bash
# Show all configuration
python playlist_cli.py config

# Validate search directories
python playlist_cli.py validate
```

### Environment Variables

If configuration files are not present, the system falls back to environment variables:

```bash
# Discovery
SEARCH_DIRECTORIES=/music,/audio
DISCOVERY_CACHE_TTL=3600
DISCOVERY_BATCH_SIZE=100

# Database
DATABASE_URL=postgresql://user:pass@localhost/db

# Logging
LOG_LEVEL=INFO

# Application
PYTHONPATH=/app/src
```

## Configuration Priority

1. **Configuration Files** (highest priority)
   - JSON files in `/app/config/`
   - Supports complex nested configurations
   - Can be reloaded without restart

2. **Environment Variables** (fallback)
   - Simple key-value pairs
   - Requires container restart to change

## Hot Reloading

Configuration files can be modified and reloaded without restarting the application:

1. Edit the JSON configuration file
2. Call the reload endpoint: `POST /api/config/reload`
3. Configuration changes take effect immediately

## Validation

The system validates configurations to ensure:
- Required fields are present
- Data types are correct
- Values are within acceptable ranges
- Dependencies are satisfied

## Examples

### Adding a New Search Directory

1. Edit `config/discovery.json`:
```json
{
  "search_directories": [
    "/music",
    "/audio",
    "/new_music_directory"
  ]
}
```

2. Reload configuration:
```bash
curl -X POST http://localhost:8000/api/config/reload
```

### Changing Log Level

1. Edit `config/logging.json`:
```json
{
  "level": "DEBUG",
  "handlers": {
    "console": {
      "enabled": true,
      "level": "DEBUG"
    }
  }
}
```

2. Reload configuration:
```bash
curl -X POST http://localhost:8000/api/config/reload
```

## Best Practices

1. **Backup Configurations**: Keep backups of working configurations
2. **Version Control**: Include configuration files in version control
3. **Environment-Specific**: Use different configs for dev/staging/production
4. **Validation**: Always validate configurations after changes
5. **Documentation**: Document custom configurations

## Troubleshooting

### Configuration Not Loading
- Check file permissions
- Verify JSON syntax
- Check file paths

### Changes Not Taking Effect
- Call reload endpoint
- Check for syntax errors
- Verify configuration validation

### Fallback to Environment Variables
- Check if config files exist
- Verify file paths
- Check JSON syntax
