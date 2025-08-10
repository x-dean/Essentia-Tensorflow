# Docker Setup Guide

This guide explains how to build and run the playlist application with TensorFlow support and PostgreSQL database using Docker.

## Overview

The Docker setup includes:
- **Python 3.11** with all necessary dependencies
- **PostgreSQL 15** database server
- **TensorFlow 2.11.0** for machine learning
- **Essentia** audio analysis library with TensorFlow support
- **FastAPI** web framework

## Prerequisites

- Docker and Docker Compose installed
- At least 4GB of available RAM
- 10GB of free disk space

## Quick Start

### 1. Build and Test (Windows)
```batch
build_and_test.bat
```

### 2. Build and Test (Linux/Mac)
```bash
chmod +x build_and_test.sh
./build_and_test.sh
```

### 3. Manual Setup

#### Build the base image first:
```bash
docker build -f Dockerfile -t playlist-base:latest .
```

#### Build the app image:
```bash
docker build -f Dockerfile.app -t playlist-app:latest .
```

#### Run with Docker Compose:
```bash
docker-compose up -d
```

#### Run manually:
```bash
docker run -d --name playlist-app \
    -p 8000:8000 \
    -p 5432:5432 \
    -v $(pwd)/music:/music:ro \
    -v $(pwd)/audio:/audio:ro \
    -v $(pwd)/data:/app/data \
    -v $(pwd)/logs:/app/logs \
    playlist-app:latest
```

## Configuration

### Environment Variables

Create a `.env` file based on `env.example`:

```bash
# Database Configuration
DATABASE_URL=postgresql://playlist_user:playlist_password@localhost:5432/playlist_db
POSTGRES_DB=playlist_db
POSTGRES_USER=playlist_user
POSTGRES_PASSWORD=playlist_password

# Music Directories
MUSIC_DIRECTORY=./music
AUDIO_DIRECTORY=./audio

# API Settings
API_HOST=0.0.0.0
API_PORT=8000

# Logging
LOG_LEVEL=INFO
```

### Directory Structure

Ensure these directories exist:
```
Essentia-Tensorflow/
├── music/          # Your music files
├── audio/          # Additional audio files
├── data/           # Application data
├── logs/           # Log files
├── cache/          # Cache directory
└── config/         # Configuration files
```

## Testing

### Run the test script:
```bash
docker exec playlist-app python test_tensorflow_essentia.py
```

This will test:
- TensorFlow installation and version
- Essentia with TensorFlow support
- PostgreSQL connection
- SQLAlchemy integration

### Manual Testing

#### Test PostgreSQL:
```bash
docker exec -it playlist-app psql -U playlist_user -d playlist_db
```

#### Test TensorFlow:
```bash
docker exec -it playlist-app python -c "import tensorflow as tf; print(tf.__version__)"
```

#### Test Essentia:
```bash
docker exec -it playlist-app python -c "import essentia; print(essentia.__version__)"
```

## Troubleshooting

### Common Issues

#### 1. PostgreSQL won't start
- Check if port 5432 is already in use
- Verify data directory permissions
- Check logs: `docker logs playlist-app`

#### 2. TensorFlow import errors
- Ensure you have enough RAM (TensorFlow requires ~2GB)
- Check if the build completed successfully
- Verify TensorFlow version compatibility

#### 3. Essentia TensorFlow algorithms not available
- Ensure Essentia was built with `--with-tensorflow` flag
- Check if TensorFlow C API is properly installed
- Verify library paths are correct

### Logs

View application logs:
```bash
docker logs playlist-app
```

View PostgreSQL logs:
```bash
docker exec playlist-app cat /var/lib/postgresql/data/postgres.log
```

### Cleanup

Remove containers and images:
```bash
docker stop playlist-app
docker rm playlist-app
docker rmi playlist-app:latest
```

## Architecture

### Dockerfile (Base Image)
- Based on Python 3.11 slim image
- Installs PostgreSQL and all system dependencies
- Builds Essentia with TensorFlow support
- Installs TensorFlow and audio processing libraries
- Sets up PostgreSQL database and user

### Dockerfile.app (Application Image)
- Based on playlist-base:latest
- Copies application code and configuration
- Installs application-specific Python dependencies
- Configures startup scripts and environment

### Startup Process
1. PostgreSQL initialization (if needed)
2. Database and user creation
3. Application startup
4. Health checks

### Volume Mounts
- `/music` - Read-only music files
- `/audio` - Read-only audio files  
- `/app/data` - Application data
- `/app/logs` - Log files
- `/var/lib/postgresql/data` - Database files

## Performance

### Resource Requirements
- **CPU**: 2+ cores recommended
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 10GB for base image + music files
- **Network**: Standard internet connection for initial build

### Optimization Tips
- Use `.dockerignore` to exclude unnecessary files
- Mount music directories as read-only
- Use volume mounts for persistent data
- Consider using multi-stage builds for production

## Security

### Database Security
- Default credentials are for development only
- Change passwords in production
- Use environment variables for secrets
- Consider using Docker secrets for production

### Network Security
- Only expose necessary ports (8000, 5432)
- Use internal networks for container communication
- Consider using reverse proxy for production

## Development

### Adding Dependencies
1. Update `requirements.txt`
2. Rebuild the Docker image
3. Test the new dependencies

### Modifying Configuration
1. Update `.env` file
2. Restart the container
3. Verify changes take effect

### Debugging
```bash
# Enter the container
docker exec -it playlist-app bash

# Check running processes
docker exec playlist-app ps aux

# Check network connections
docker exec playlist-app netstat -tulpn
```
