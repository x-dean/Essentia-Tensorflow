@echo off
setlocal enabledelayedexpansion

echo Building complete Docker setup...

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running. Please start Docker and try again.
    exit /b 1
)

REM Build the base image
echo [INFO] Step 1: Building base image (playlist-base:latest)
echo [INFO] This includes: Python 3.11, PostgreSQL, TensorFlow 2.11.0, Essentia with TensorFlow support
echo This may take 10-15 minutes...

docker build -f Dockerfile -t playlist-base:latest .

if %errorlevel% equ 0 (
    echo ✅ Base image built successfully!
) else (
    echo ❌ Base image build failed!
    exit /b 1
)

REM Build the app image
echo [INFO] Step 2: Building app image (playlist-app:latest)
echo [INFO] This includes: Application code, FastAPI, additional dependencies

docker build -f Dockerfile.app -t playlist-app:latest .

if %errorlevel% equ 0 (
    echo ✅ App image built successfully!
) else (
    echo ❌ App image build failed!
    exit /b 1
)

REM Show built images
echo [INFO] Step 3: Built images summary
echo.
docker images | findstr /i "playlist-base playlist-app"
echo.

echo 🎉 All images built successfully!
echo [INFO] You can now run the application with:
echo   docker-compose up -d
echo   or
echo   docker run -d --name playlist-app -p 8000:8000 -p 5432:5432 playlist-app:latest
