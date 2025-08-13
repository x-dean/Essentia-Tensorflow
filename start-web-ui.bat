@echo off
echo Starting Playlist App Web UI...
echo.
echo Prerequisites:
echo - Node.js 16+ must be installed
echo - Backend must be running on localhost:8000
echo.
echo Starting development server...
cd web-ui
npm install
npm run dev
