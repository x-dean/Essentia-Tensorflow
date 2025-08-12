# Use the base image with Essentia and TensorFlow support
FROM essentia-tensorflow-base:latest

# Set working directory
WORKDIR /app

# Copy application files
COPY main.py .

# Copy source code
COPY src/ ./src/

# Copy scripts
COPY scripts/ ./scripts/

# Copy tests
COPY tests/ ./tests/

# Make scripts executable and create symlinks
RUN chmod +x scripts/*.py && \
    ln -sf /app/scripts/playlist_cli.py /usr/local/bin/playlist && \
    ln -sf /app/scripts/batch_analyzer_cli.py /usr/local/bin/batch-analyzer && \
    ln -sf /app/scripts/database_cli.py /usr/local/bin/db-cli

# Copy documentation
COPY docs/ ./docs/

# Copy gitignore
COPY .gitignore .

# Create necessary directories
RUN mkdir -p /music /audio /data /logs

# Expose port
EXPOSE 8000

# Start the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

