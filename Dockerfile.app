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

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Copy wrapper script
COPY playlist /usr/local/bin/playlist
RUN chmod +x /usr/local/bin/playlist

# Fix line endings and make scripts executable
RUN find scripts/ -name "*.py" -exec sed -i 's/\r$//' {} \; && \
    chmod +x scripts/*.py

# Create symlinks for CLI commands
RUN ln -sf /app/scripts/master_cli.py /usr/local/bin/master && \
    ln -sf /app/scripts/master_cli.py /usr/local/bin/database && \
    ln -sf /app/scripts/master_cli.py /usr/local/bin/playlist && \
    ln -sf /app/scripts/master_cli.py /usr/local/bin/analyzer && \
    ln -sf /app/scripts/master_cli.py /usr/local/bin/discovery && \
    ln -sf /app/scripts/master_cli.py /usr/local/bin/tracks && \
    ln -sf /app/scripts/master_cli.py /usr/local/bin/metadata && \
    ln -sf /app/scripts/master_cli.py /usr/local/bin/config && \
    ln -sf /app/scripts/master_cli.py /usr/local/bin/health && \
    ln -sf /app/scripts/master_cli.py /usr/local/bin/status && \
    ln -sf /app/scripts/batch_analyzer_cli.py /usr/local/bin/batch-analyzer && \
    ln -sf /app/scripts/database_cli.py /usr/local/bin/db-cli

# Copy documentation
COPY docs/ ./docs/

# Copy gitignore
COPY .gitignore .

# Create necessary directories
RUN mkdir -p /music /audio /data /logs /app/temp_backups

# Expose port
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Start the application (default command)
CMD []

