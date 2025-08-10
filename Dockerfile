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
    # Database and system libraries
    postgresql \
    postgresql-contrib \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    # Runtime libraries
    libfftw3-single3 \
    libfftw3-double3 \
    libsamplerate0 \
    libyaml-0-2 \
    libtag1v5 \
    libchromaprint1 \
    libsndfile1 \
    libmad0 \
    libvorbis0a \
    libvorbisenc2 \
    libflac12 \
    libvamp-sdk2v5 \
    libpq5 \
    libssl3 \
    libffi8 \
 && rm -rf /var/lib/apt/lists/*

# TensorFlow C API (CPU)
ARG TF_VERSION=2.11.0
RUN wget -qO /tmp/libtensorflow.tar.gz \
      https://storage.googleapis.com/tensorflow/libtensorflow/libtensorflow-cpu-linux-x86_64-${TF_VERSION}.tar.gz \
  && tar -C /usr/local -xzf /tmp/libtensorflow.tar.gz \
  && ldconfig \
  && rm -f /tmp/libtensorflow.tar.gz

# Install core Python dependencies (needed for Essentia build)
RUN pip install --no-cache-dir \
    numpy six pyyaml \
    tensorflow-cpu==2.11.0

# Build Essentia with TensorFlow support
WORKDIR /opt
ARG ESSENTIA_REF=
RUN git clone --depth 1 https://github.com/MTG/essentia.git
WORKDIR /opt/essentia
RUN if [ -n "$ESSENTIA_REF" ]; then \
      git fetch --depth 1 origin "$ESSENTIA_REF" && git checkout "$ESSENTIA_REF"; \
    fi

# Setup TensorFlow for Essentia (using Python mode)
RUN src/3rdparty/tensorflow/setup_from_python.sh

# Configure, build, install — lightweight with TensorFlow support
RUN python3 waf configure \
      --mode=release \
      --with-python \
      --with-tensorflow \
      --lightweight=libsamplerate,taglib,yaml,fftw,libchromaprint \
      --fft=FFTW \
  && python3 waf -v \
  && python3 waf install \
  # Verify installation
  && ls -la /usr/local/lib/python3.11/site-packages/ \
  && find /usr/local/lib/python3.11/site-packages -name "essentia*.so" \
  && find /usr/local/lib -name "libessentia*" \
  && find /usr/local/bin -name "*essentia*"

RUN ldconfig

# Install remaining Python dependencies for playlist app
RUN pip install --no-cache-dir \
    # Core audio processing
    librosa \
    soundfile \
    pydub \
    scipy \
    # Data processing and visualization
    pandas \
    matplotlib \
    seaborn \
    plotly \
    # Web framework and API
    flask \
    fastapi \
    uvicorn[standard] \
    gunicorn \
    # Database and caching
    sqlalchemy \
    psycopg2-binary \
    redis \
    celery \
    # HTTP and networking
    requests \
    aiohttp \
    httpx \
    # File handling and utilities
    python-multipart \
    python-jose[cryptography] \
    passlib[bcrypt] \
    # Development and testing
    pytest \
    pytest-asyncio \
    black \
    flake8 \
    # Additional useful libraries
    python-dotenv \
    pydantic \
    alembic \
    # Audio fingerprinting and similarity
    dejavu \
    # Machine learning utilities
    scikit-learn \
    joblib

# Setup PostgreSQL
RUN mkdir -p /var/lib/postgresql/data && \
    chown -R postgres:postgres /var/lib/postgresql/data && \
    su - postgres -c '/usr/lib/postgresql/15/bin/initdb -D /var/lib/postgresql/data --locale=C'

# Copy startup scripts
COPY scripts/startup.sh /usr/local/bin/startup.sh
COPY scripts/startup-postgre.sh /usr/local/bin/startup-postgre.sh
RUN chmod +x /usr/local/bin/startup.sh /usr/local/bin/startup-postgre.sh

WORKDIR /workspace

# Set default command to run startup script with main app
CMD ["/usr/local/bin/startup.sh", "python", "main.py"]
