@echo off
setlocal enabledelayedexpansion

echo Building base image with Essentia and TensorFlow support...

REM Build the base image
echo 1. Building essentia-tensorflow-base image...
docker build -f Dockerfile -t essentia-tensorflow-base:latest .

if %errorlevel% equ 0 (
    echo ✅ Base image built successfully!
    echo Image: essentia-tensorflow-base:latest
    echo Contains: Python 3.11, PostgreSQL, TensorFlow 2.19.0, Essentia with TensorFlow support
) else (
    echo ❌ Base image build failed!
    exit /b 1
)
