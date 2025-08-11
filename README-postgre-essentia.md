# Essentia-TensorFlow Base Image

A Docker base image containing PostgreSQL and Essentia with TensorFlow support for audio processing applications.

## Components

- **Python 3.11** - Base runtime
- **PostgreSQL 15.13** - Database server and client
- **Essentia 2.1-beta6-dev** - Audio analysis library with TensorFlow support
- **TensorFlow** - Machine learning framework (CPU optimized)

## Quick Start

```bash
# Build the base image
docker build -f Dockerfile -t essentia-tensorflow-base:latest .

# Test Essentia
docker run --rm essentia-tensorflow-base:latest python3 -c "import essentia; print(f'Essentia version: {essentia.__version__}')"

# Test PostgreSQL
docker run --rm essentia-tensorflow-base:latest psql --version
```

## Architecture

This is a **base image** that provides core dependencies. The application Dockerfile (`Dockerfile.app`) builds on top of this base image and handles:

- PostgreSQL initialization and setup
- Application-specific configuration
- Startup scripts
- Database schema creation

## Multi-stage Build

```
essentia-tensorflow-base:latest (base image)
├── Python 3.11
├── PostgreSQL 15.13
├── Essentia with TensorFlow
└── Core Python dependencies

playlist-app:latest (application image)
├── FROM essentia-tensorflow-base:latest
├── Application code
├── PostgreSQL setup
└── Startup scripts
```

## Build Commands

```bash
# Build base image only
docker build -f Dockerfile -t essentia-tensorflow-base:latest .

# Build application image
docker build -f Dockerfile.app -t playlist-app:latest .

# Build both (using docker-compose)
docker-compose build
```

## Verification

The base image includes verification steps to ensure:
- Essentia loads with TensorFlow support
- PostgreSQL client and server are available
- Python drivers (psycopg2) are working

## Notes

- CUDA warnings are normal (CPU-only setup)
- Base image is optimized with single pip install layer
- PostgreSQL setup is handled in application image
- TensorFlow integration is provided by `essentia-tensorflow` package

