#!/bin/bash

# Essentia-Tensorflow Playlist App Build Script
# This script builds both the base image and the application

set -e

echo "🚀 Building Essentia-Tensorflow Playlist App..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Build base image
print_status "Building base image (essentia-tensorflow-base:latest)..."
docker build -f Dockerfile -t essentia-tensorflow-base:latest .

if [ $? -eq 0 ]; then
    print_status "✅ Base image built successfully"
else
    print_error "❌ Failed to build base image"
    exit 1
fi

# Build application image
print_status "Building application image..."
docker-compose build

if [ $? -eq 0 ]; then
    print_status "✅ Application image built successfully"
else
    print_error "❌ Failed to build application image"
    exit 1
fi

print_status "🎉 All builds completed successfully!"
print_status "You can now run: docker-compose up -d"
