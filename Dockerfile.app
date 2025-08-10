# Use the base image with Essentia and TensorFlow support
FROM essentia-tensorflow-base:latest

# Set working directory
WORKDIR /app

# Copy application files
COPY requirements.txt .
COPY setup.py .
COPY main.py .
COPY playlist_cli.py .

# Copy source code
COPY src/ ./src/

# Copy scripts and tests
COPY scripts/ ./scripts/
COPY tests/ ./tests/

# Copy startup script to the base image location
COPY scripts/startup.sh /usr/local/bin/startup.sh
RUN chmod +x /usr/local/bin/startup.sh

# Copy documentation
COPY docs/ ./docs/

# Copy configuration files
COPY .gitignore .
COPY PROJECT_STRUCTURE.md .

# Create directories for music and data
RUN mkdir -p /music /audio /data /logs

# Set environment variables
ENV PYTHONPATH=/app/src
ENV DATABASE_URL=postgresql://playlist_user:playlist_password@localhost:5432/playlist_db
ENV SEARCH_DIRECTORIES=/music,/audio
ENV LOG_LEVEL=INFO

# Expose port for FastAPI
EXPOSE 8000

# Default command (can be overridden)
CMD ["/usr/local/bin/startup.sh", "python", "main.py"]

