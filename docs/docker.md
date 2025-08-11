# Docker Setup Guide

This guide explains how to run the Playlist App using Docker and Docker Compose.

## Prerequisites

- Docker and Docker Compose installed
- The `playlista-base:latest` image available (from your existing setup)
- Music directories to mount

## Quick Start

### 1. Basic Setup

1. **Copy environment template:**
   ```bash
   cp env.example .env
   ```

2. **Edit `.env` file with your music directories:**
   ```bash
   # Set your music directories
   MUSIC_DIRECTORY=/path/to/your/music
   AUDIO_DIRECTORY=/path/to/your/audio
   ```

3. **Build and run:**
   ```bash
   docker-compose up -d
   ```

4. **Access the API:**
   - API: http://localhost:8000
   - Health check: http://localhost:8000/health
   - API docs: http://localhost:8000/docs

### 2. Development Setup

For development with live reload:

```bash
docker-compose -f docker-compose.dev.yml up -d
```

### 3. Production Setup

For production with PostgreSQL and Redis:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Docker Compose Configurations

### Basic Configuration (`docker-compose.yml`)

- **SQLite database** (stored in persistent volume)
- **Music directory mounting**
- **Health checks**
- **Automatic restarts**

### Development Configuration (`docker-compose.dev.yml`)

- **Live code reload** with uvicorn --reload
- **Source code mounting** for development
- **Debug logging**
- **CLI service** for running commands
- **Additional debugging port** (8001)

### Production Configuration (`docker-compose.prod.yml`)

- **PostgreSQL database** for better performance
- **Redis caching** for improved speed
- **Nginx reverse proxy** (optional)
- **Production logging**
- **Health checks for all services**

## Environment Variables

### Music Directories

```bash
# Required: Main music directories
MUSIC_DIRECTORY=/path/to/your/music
AUDIO_DIRECTORY=/path/to/your/audio

# Optional: Additional directories
EXTRA_MUSIC_DIRS=/path/to/extra/music1,/path/to/extra/music2
```

### Database Configuration

```bash
# SQLite (default)
DATABASE_URL=sqlite:////data/playlist_app.db

# PostgreSQL (production)
DATABASE_URL=postgresql://playlist_user:playlist_password@postgres:5432/playlist_db
```

### Discovery Settings

```bash
SEARCH_DIRECTORIES=/music,/audio
DISCOVERY_CACHE_TTL=3600
DISCOVERY_BATCH_SIZE=100
```

### Logging

```bash
# Development
LOG_LEVEL=DEBUG

# Production
LOG_LEVEL=INFO
```

## Usage Examples

### Running the Application

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f playlist-app

# Stop services
docker-compose down
```

### Using the CLI

```bash
# Run CLI commands
docker-compose -f docker-compose.dev.yml --profile cli run playlist-cli scan
docker-compose -f docker-compose.dev.yml --profile cli run playlist-cli list
docker-compose -f docker-compose.dev.yml --profile cli run playlist-cli stats
```

### Development Commands

```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up -d

# Run tests
docker-compose -f docker-compose.dev.yml exec playlist-app-dev python -m pytest

# Access container shell
docker-compose -f docker-compose.dev.yml exec playlist-app-dev bash
```

### Production Commands

```bash
# Start production environment
docker-compose -f docker-compose.prod.yml up -d

# View all service logs
docker-compose -f docker-compose.prod.yml logs -f

# Scale services (if needed)
docker-compose -f docker-compose.prod.yml up -d --scale playlist-app=2
```

## Volume Mounts

### Music Directories

```yaml
volumes:
  - ${MUSIC_DIRECTORY:-./music}:/music:ro
  - ${AUDIO_DIRECTORY:-./audio}:/audio:ro
```

- **Read-only mounting** (`:ro`) for security
- **Environment variable substitution** for flexibility
- **Default fallback** to local directories

### Data Persistence

```yaml
volumes:
  - playlist_data:/data  # SQLite database
  - postgres_data:/var/lib/postgresql/data  # PostgreSQL
  - redis_data:/data  # Redis cache
```

### Development Mounts

```yaml
volumes:
  - ./src:/app/src  # Source code for live reload
  - ./main.py:/app/main.py
  - ./scripts:/app/scripts
  - ./tests:/app/tests
```

## Health Checks

All services include health checks:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

## Networking

- **Default network**: `playlist-network`
- **Service discovery**: Services can communicate by name
- **Port exposure**: Only necessary ports are exposed

## Security Considerations

### Read-Only Mounts

Music directories are mounted as read-only to prevent accidental modifications.

### Environment Variables

Sensitive data should be stored in environment variables, not in the compose files.

### Network Isolation

Services are isolated in their own network with only necessary ports exposed.

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   # Check directory permissions
   ls -la /path/to/your/music
   
   # Fix permissions if needed
   chmod 755 /path/to/your/music
   ```

2. **Port Already in Use**
   ```bash
   # Check what's using the port
   lsof -i :8000
   
   # Change port in docker-compose.yml
   ports:
     - "8001:8000"  # Use different host port
   ```

3. **Database Connection Issues**
   ```bash
   # Check database service
   docker-compose logs postgres
   
   # Restart database service
   docker-compose restart postgres
   ```

### Debug Commands

```bash
# Check container status
docker-compose ps

# View detailed logs
docker-compose logs -f --tail=100

# Access container shell
docker-compose exec playlist-app bash

# Check volume mounts
docker-compose exec playlist-app ls -la /music
```

### Performance Optimization

1. **Use production configuration** for large music libraries
2. **Enable Redis caching** for better performance
3. **Use PostgreSQL** for better database performance
4. **Mount SSDs** for music directories if available

## Backup and Restore

### Database Backup

```bash
# SQLite backup
docker-compose exec playlist-app cp /data/playlist_app.db /data/playlist_app.db.backup

# PostgreSQL backup
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U playlist_user playlist_db > backup.sql
```

### Volume Backup

```bash
# Backup volumes
docker run --rm -v playlist_data:/data -v $(pwd):/backup alpine tar czf /backup/playlist_data.tar.gz -C /data .

# Restore volumes
docker run --rm -v playlist_data:/data -v $(pwd):/backup alpine tar xzf /backup/playlist_data.tar.gz -C /data
```

## Monitoring

### Log Monitoring

```bash
# Follow all logs
docker-compose logs -f

# Follow specific service
docker-compose logs -f playlist-app

# View recent logs
docker-compose logs --tail=50
```

### Resource Monitoring

```bash
# Check resource usage
docker stats

# Check disk usage
docker system df
```

## Scaling

### Horizontal Scaling

```bash
# Scale the application
docker-compose -f docker-compose.prod.yml up -d --scale playlist-app=3
```

### Load Balancing

Use the nginx service in production configuration for load balancing:

```bash
docker-compose -f docker-compose.prod.yml --profile nginx up -d
```




