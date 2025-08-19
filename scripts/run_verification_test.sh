#!/bin/bash

# Docker-based Analyzer Verification Test Runner
# This script runs the comprehensive analyzer verification test inside the Docker container

echo "=================================================="
echo "Essentia-Tensorflow Analyzer Verification Test"
echo "=================================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if the container is running
CONTAINER_NAME="essentia-tensorflow-app"
if ! docker ps | grep -q $CONTAINER_NAME; then
    echo "Starting Docker container..."
    docker-compose up -d
    sleep 10  # Wait for container to be ready
fi

echo "Running analyzer verification test in Docker container..."

# Run the verification test inside the container
docker exec -it $CONTAINER_NAME python /workspace/scripts/analyzer_verification_docker.py

# Check if the test report was generated
if docker exec $CONTAINER_NAME test -f /workspace/analyzer_verification_report.json; then
    echo ""
    echo "Test report generated successfully!"
    echo "To view the full report, run:"
    echo "docker exec $CONTAINER_NAME cat /workspace/analyzer_verification_report.json | jq '.'"
    echo ""
    echo "Or copy the report to your local machine:"
    echo "docker cp $CONTAINER_NAME:/workspace/analyzer_verification_report.json ./"
else
    echo "Warning: Test report not found. Check the test output above for errors."
fi

echo "=================================================="
echo "Verification test completed!"
echo "=================================================="
