# syntax=docker/dockerfile:1

FROM python:3.11-slim

# Set the image name for the base image
ARG IMAGE_NAME=essentia-tensorflow-base
ARG IMAGE_TAG=latest

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    LC_ALL=C \
    LANG=C

# Install all dependencies (build + runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git pkg-config wget cmake \
    python3-dev python3-numpy cython3 \
    libeigen3-dev libfftw3-dev libsamplerate0-dev libyaml-dev libtag1-dev \
    libchromaprint-dev libsndfile1-dev libmad0-dev libvorbis-dev libflac-dev \
    libvamp-sdk2v5 \
    libboost-all-dev \
    # Additional audio/video libraries
    ffmpeg \
    libavcodec-extra \
    libavformat-dev \
    libavutil-dev \
    libswresample-dev \
    libswscale-dev \
    # System libraries
    libpq-dev \
    libssl-dev \
    libffi-dev \
    # Runtime libraries
    libfftw3-single3 \
    libfftw3-double3 \
    libsamplerate0 \
    libyaml-0-2 \
    libtag2 \
    libchromaprint1 \
    libsndfile1 \
    libmad0 \
    libvorbis0a \
    libvorbisenc2 \
    libflac14 \
    libvamp-sdk2v5 \
    libpq5 \
    libssl3 \
    libffi8 \
 && rm -rf /var/lib/apt/lists/*

# Create directories for models and data
RUN mkdir -p /workspace/models /workspace/data

# Install Python dependencies
RUN pip install --no-cache-dir \
    # Core Essentia and TensorFlow
    essentia-tensorflow \
    # Web framework and API
    fastapi==0.104.1 \
    uvicorn==0.24.0 \
    gunicorn \
    # Database
    sqlalchemy==2.0.23 \
    psycopg2-binary==2.9.9 \
    redis \
    celery \
    # Audio processing
    librosa \
    soundfile \
    pydub \
    mutagen \
    # Data processing and visualization
    pandas \
    matplotlib \
    seaborn \
    plotly \
    # HTTP and networking
    requests \
    aiohttp \
    httpx \
    # File handling and utilities
    python-jose[cryptography] \
    passlib[bcrypt] \
    pydantic==2.5.0 \
    python-dotenv==1.0.0 \
    python-multipart==0.0.6 \
    # Development and testing
    pytest \
    pytest-asyncio \
    black \
    flake8 \
    # Additional useful libraries
    alembic \
    dejavu \
    scikit-learn \
    joblib \
    jsonschema \
    # FAISS for vector similarity search
    faiss-cpu>=1.7.4

WORKDIR /workspace