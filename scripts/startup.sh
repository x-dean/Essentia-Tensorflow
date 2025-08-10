#!/bin/bash
set -e

echo "Starting PostgreSQL and Playlist App..."

# Check if PostgreSQL is already running
if ! su - postgres -c "/usr/lib/postgresql/15/bin/pg_isready -h localhost -p 5432" >/dev/null 2>&1; then
    echo "Starting PostgreSQL..."
    su - postgres -c "/usr/lib/postgresql/15/bin/pg_ctl -D /var/lib/postgresql/data -l /var/lib/postgresql/data/postgres.log start"
    
    # Wait for PostgreSQL to be ready
    echo "Waiting for PostgreSQL to be ready..."
    until su - postgres -c "/usr/lib/postgresql/15/bin/pg_isready -h localhost -p 5432"; do
      echo "Waiting for PostgreSQL..."
      sleep 1
    done
    
    # Create database and user if they don't exist (only on first run)
    echo "Setting up database and user..."
    su - postgres -c "/usr/lib/postgresql/15/bin/psql -h localhost -c \"CREATE USER playlist_user WITH PASSWORD 'playlist_password';\" 2>/dev/null || true"
    su - postgres -c "/usr/lib/postgresql/15/bin/psql -h localhost -c \"CREATE DATABASE playlist_db OWNER playlist_user;\" 2>/dev/null || true"
else
    echo "PostgreSQL is already running"
fi

echo "PostgreSQL is ready!"

# Execute the original command (usually python main.py)
echo "Starting application..."
exec "$@"
