@echo off
setlocal enabledelayedexpansion

echo 🚀 Building Essentia-Tensorflow Playlist App...

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running. Please start Docker and try again.
    exit /b 1
)

REM Build base image
echo [INFO] Building base image (essentia-tensorflow-base:latest)...
docker build -f Dockerfile -t essentia-tensorflow-base:latest .

if errorlevel 1 (
    echo [ERROR] Failed to build base image
    exit /b 1
) else (
    echo [INFO] ✅ Base image built successfully
)

REM Build application image
echo [INFO] Building application image...
docker-compose build

if errorlevel 1 (
    echo [ERROR] Failed to build application image
    exit /b 1
) else (
    echo [INFO] ✅ Application image built successfully
)

echo [INFO] 🎉 All builds completed successfully!
echo [INFO] You can now run: docker-compose up -d
