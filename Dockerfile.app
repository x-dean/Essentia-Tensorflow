# Use the base image with Essentia and TensorFlow support
FROM essentia-tensorflow-base:latest



# Set working directory
WORKDIR /app

# Copy application files
COPY main.py .
COPY playlist_cli.py .

# Copy source code
COPY src/ ./src/

# Copy scripts and tests
COPY scripts/ ./scripts/
COPY tests/ ./tests/



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

