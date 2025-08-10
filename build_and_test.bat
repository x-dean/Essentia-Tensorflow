@echo off
setlocal enabledelayedexpansion

echo Building and testing Docker setup...

REM Build the base image first
echo 1. Building base image...
docker build -f Dockerfile -t playlist-base:latest .

if %errorlevel% neq 0 (
    echo ❌ Base image build failed!
    exit /b 1
)

REM Build the app image
echo 2. Building app image...
docker build -f Dockerfile.app -t playlist-app:latest .

if %errorlevel% neq 0 (
    echo ❌ Docker build failed!
    exit /b 1
)

REM Run the container in detached mode
echo 3. Starting container...
docker run -d --name playlist-test ^
    -p 8000:8000 ^
    -p 5432:5432 ^
    -v %cd%/music:/music:ro ^
    -v %cd%/audio:/audio:ro ^
    -v %cd%/data:/app/data ^
    -v %cd%/logs:/app/logs ^
    playlist-app:latest

if %errorlevel% neq 0 (
    echo ❌ Failed to start container!
    exit /b 1
)

REM Wait for services to start
echo 4. Waiting for services to start...
timeout /t 30 /nobreak >nul

REM Test the container
echo 5. Testing container...
docker exec playlist-test python test_tensorflow_essentia.py

REM Check if tests passed
if %errorlevel% equ 0 (
    echo ✅ All tests passed!
    
    echo 6. Container logs:
    docker logs playlist-test
    
    echo 7. Stopping and cleaning up...
    docker stop playlist-test
    docker rm playlist-test
    
    echo 🎉 Docker setup is working correctly!
) else (
    echo ❌ Tests failed!
    echo Container logs:
    docker logs playlist-test
    
    echo Cleaning up...
    docker stop playlist-test 2>nul
    docker rm playlist-test 2>nul
    
    exit /b 1
)
