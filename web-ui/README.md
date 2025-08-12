# Playlist App Web UI

A modern React-based web interface for the Essentia-Tensorflow playlist application.

## Features

- **Dashboard**: Real-time system overview with statistics
- **File Discovery**: Trigger music file discovery
- **Audio Analysis**: Start batch analysis of discovered files
- **System Monitoring**: Health checks and status indicators
- **Responsive Design**: Works on desktop and mobile devices

## Setup

### Prerequisites

- Node.js 16+ 
- npm or yarn
- Backend API running on `http://localhost:8000`

### Installation

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

3. Open your browser to `http://localhost:3000`

### Building for Production

```bash
npm run build
```

The built files will be in the `dist` directory.

## Configuration

The web UI is configured to proxy API requests to the backend at `http://localhost:8000`. This is configured in `vite.config.ts`.

## Troubleshooting

### Common Issues

1. **API Connection Errors**
   - Ensure the backend is running on port 8000
   - Check that CORS is properly configured on the backend
   - Verify the proxy settings in `vite.config.ts`

2. **TypeScript Errors**
   - Run `npm install` to ensure all dependencies are installed
   - Check that `@types/react` and `@types/react-dom` are installed

3. **Slow Performance**
   - The dashboard makes API calls every 30-60 seconds
   - Reduce the `refetchInterval` in the Dashboard component if needed
   - Check backend performance and database queries

4. **Analysis Failures**
   - Check backend logs for detailed error messages
   - Ensure audio files are accessible to the backend
   - Verify that Essentia and TensorFlow are properly installed

### Development

- The UI uses React Query for data fetching and caching
- Tailwind CSS for styling
- Lucide React for icons
- TypeScript for type safety

### API Endpoints Used

- `GET /api/health` - System health check
- `GET /api/tracks/` - Get track information
- `POST /api/discovery/trigger` - Trigger file discovery
- `GET /api/discovery/stats` - Get discovery statistics
- `POST /api/analyzer/analyze-batches` - Start batch analysis
- `GET /api/analyzer/statistics` - Get analysis statistics

## Performance Optimizations

- Reduced API call frequency (30-60 second intervals)
- Error handling with fallback values
- Loading states for better UX
- Retry logic for failed requests
- Timeout handling for long-running operations
