#!/bin/bash
set -e

echo "Building complete Docker setup..."

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

# Build the base image
print_status "Step 1: Building base image (playlist-base:latest)"
print_status "This includes: Python 3.11, PostgreSQL, TensorFlow 2.11.0, Essentia with TensorFlow support"
echo "This may take 10-15 minutes..."

docker build -f Dockerfile -t playlist-base:latest .

if [ $? -eq 0 ]; then
    print_status "✅ Base image built successfully!"
else
    print_error "❌ Base image build failed!"
    exit 1
fi

# Build the app image
print_status "Step 2: Building app image (playlist-app:latest)"
print_status "This includes: Application code, FastAPI, additional dependencies"

docker build -f Dockerfile.app -t playlist-app:latest .

if [ $? -eq 0 ]; then
    print_status "✅ App image built successfully!"
else
    print_error "❌ App image build failed!"
    exit 1
fi

# Show built images
print_status "Step 3: Built images summary"
echo ""
docker images | grep -E "(playlist-base|playlist-app)"
echo ""

print_status "🎉 All images built successfully!"
print_status "You can now run the application with:"
echo "  docker-compose up -d"
echo "  or"
echo "  docker run -d --name playlist-app -p 8000:8000 -p 5432:5432 playlist-app:latest"
