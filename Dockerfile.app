# Use the base image with Essentia and TensorFlow support
FROM essentia-tensorflow-base:latest



# Set working directory
WORKDIR /app

# Copy application files
COPY main.py .

# Copy source code
COPY src/ ./src/

# Copy scripts and tests
COPY scripts/ ./scripts/
COPY tests/ ./tests/

# Make CLI scripts executable and create symlinks for easy access
RUN chmod +x scripts/*.py && \
    ln -sf /app/scripts/playlist_cli.py /usr/local/bin/playlist && \
    ln -sf /app/scripts/batch_analyzer_cli.py /usr/local/bin/analyze && \
    ln -sf /app/scripts/cli.py /usr/local/bin/db && \
    ln -sf /app/scripts/database_cli.py /usr/local/bin/database

# Models directory will be mounted at runtime if needed



# Copy documentation
COPY docs/ ./docs/

# Copy configuration files
COPY .gitignore .

# Create directories for music and data
RUN mkdir -p /music /audio /data /logs

# Set environment variables
ENV PYTHONPATH=/app/src
ENV SEARCH_DIRECTORIES=/music,/audio
ENV LOG_LEVEL=INFO

# Expose port for FastAPI
EXPOSE 8000

# Default command
CMD ["python", "main.py"]

