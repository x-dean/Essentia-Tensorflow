#!/bin/bash
set -e

echo "Building and testing Docker setup..."

# Build the base image first
echo "1. Building base image..."
docker build -f Dockerfile -t playlist-base:latest .

if [ $? -ne 0 ]; then
    echo "❌ Base image build failed!"
    exit 1
fi

# Build the app image
echo "2. Building app image..."
docker build -f Dockerfile.app -t playlist-app:latest .

# Run the container in detached mode
echo "3. Starting container..."
docker run -d --name playlist-test \
    -p 8000:8000 \
    -p 5432:5432 \
    -v $(pwd)/music:/music:ro \
    -v $(pwd)/audio:/audio:ro \
    -v $(pwd)/data:/app/data \
    -v $(pwd)/logs:/app/logs \
    playlist-app:latest

# Wait for services to start
echo "4. Waiting for services to start..."
sleep 30

# Test the container
echo "5. Testing container..."
docker exec playlist-test python test_tensorflow_essentia.py

# Check if tests passed
if [ $? -eq 0 ]; then
    echo "✅ All tests passed!"
    
    echo "6. Container logs:"
    docker logs playlist-test
    
    echo "7. Stopping and cleaning up..."
    docker stop playlist-test
    docker rm playlist-test
    
    echo "🎉 Docker setup is working correctly!"
else
    echo "❌ Tests failed!"
    echo "Container logs:"
    docker logs playlist-test
    
    echo "Cleaning up..."
    docker stop playlist-test || true
    docker rm playlist-test || true
    
    exit 1
fi
