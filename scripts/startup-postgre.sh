#!/bin/bash
set -e

echo "Starting PostgreSQL..."

# Check if PostgreSQL data directory is initialized
if [ ! -f /var/lib/postgresql/data/PG_VERSION ]; then
    echo "Initializing PostgreSQL data directory..."
    su - postgres -c '/usr/lib/postgresql/15/bin/initdb -D /var/lib/postgresql/data --locale=C'
fi

# Start PostgreSQL
echo "Starting PostgreSQL service..."
su - postgres -c '/usr/lib/postgresql/15/bin/pg_ctl -D /var/lib/postgresql/data -l /var/lib/postgresql/data/postgres.log start'

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

echo "PostgreSQL is ready and running!"

# Keep the script running to maintain PostgreSQL
echo "PostgreSQL is running. Press Ctrl+C to stop."
tail -f /var/lib/postgresql/data/postgres.log
