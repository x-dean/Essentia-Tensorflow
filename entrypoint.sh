#!/bin/bash

# Entrypoint script for Essentia-Tensorflow Playlist App
# Handles both web server startup and CLI commands

set -e

# Function to run CLI commands
run_cli() {
    cd /app
    python scripts/master_cli.py "$@"
}

# Function to start the web server
start_server() {
    cd /app
    exec uvicorn main:app --host 0.0.0.0 --port 8000
}

# Check if we're running a CLI command
if [ "$1" = "playlist" ]; then
    # Remove 'playlist' from arguments and pass the rest to the master CLI
    shift
    run_cli "$@"
else
    # Default: start the web server
    start_server
fi
