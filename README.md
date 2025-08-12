# Essentia-Tensorflow Playlist App

A comprehensive music analysis and playlist management system that combines Essentia audio analysis with TensorFlow machine learning capabilities.

## Features

- **Audio Analysis**: Extract musical features using Essentia
- **Machine Learning**: TensorFlow-based music classification
- **Database Storage**: PostgreSQL for track metadata and analysis results
- **Web Interface**: React-based dashboard for managing and exploring music
- **CLI Tools**: Command-line interface for batch operations
- **Docker Support**: Complete containerized deployment

## Quick Start with Docker

The easiest way to run the application is using Docker containers.

### Prerequisites

- Docker and Docker Compose installed
- Music files to analyze (optional)

### Running the Application

1. **Production Mode** (recommended for most users):
   ```bash
   docker-compose up --build
   ```

2. **Development Mode** (for developers with hot reloading):
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
   ```

3. **Stop the application**:
   ```bash
   docker-compose down
   ```

4. **Clean up everything**:
   ```bash
   docker-compose down -v --remove-orphans
   docker system prune -f
   ```

### Accessing the Application

- **Web UI**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **Backend API**: http://localhost:8000

### Docker Services

The application runs as three separate services:

1. **postgres**: PostgreSQL database
2. **playlist-app**: FastAPI backend with Essentia and TensorFlow
3. **web-ui**: React frontend with API-based data access

## Manual Setup (Alternative)

If you prefer to run without Docker, see the detailed setup instructions below.

### Prerequisites

- Python 3.8+
- Node.js 18+
- PostgreSQL 12+
- FFmpeg

### Backend Setup

1. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup database**:
   ```bash
   # Create database and user
   createdb playlist_db
   createuser playlist_user
   psql -d playlist_db -c "ALTER USER playlist_user WITH PASSWORD 'playlist_password';"
   psql -d playlist_db -c "GRANT ALL PRIVILEGES ON DATABASE playlist_db TO playlist_user;"
   ```

3. **Configure environment**:
   ```bash
   cp env.example .env
   # Edit .env with your database settings
   ```

4. **Start the backend**:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

### Frontend Setup

1. **Install dependencies**:
   ```bash
   cd web-ui
   npm install
   ```

2. **Configure API connection**:
   The frontend connects to the backend API at `http://localhost:8000`. Make sure the backend is running.

3. **Start the frontend**:
   ```bash
   npm run dev
   ```

## Usage

### Web Interface

1. Open http://localhost:3000 in your browser
2. Use the dashboard to:
   - Monitor system health
   - Trigger music discovery
   - Start audio analysis
   - Browse and search tracks
   - View analysis statistics

### Command Line Interface

The application provides several CLI tools:

```bash
# Discover music files
playlist discover

# Analyze audio files
playlist analyze

# Database operations
db-cli --help

# Batch analysis
batch-analyzer --help
```

### API Endpoints

- `GET /health` - System health check
- `GET /tracks` - List all tracks
- `POST /discovery/trigger` - Start music discovery
- `POST /analyzer/analyze-batches` - Start audio analysis
- `GET /analyzer/statistics` - Get analysis statistics

## Configuration

### Environment Variables

Key environment variables:

- `DATABASE_URL`: PostgreSQL connection string
- `MUSIC_DIRECTORY`: Path to music files
- `AUDIO_DIRECTORY`: Path to audio files
- `MODELS_DIRECTORY`: Path to TensorFlow models

### Database Configuration

The application uses PostgreSQL with the following default settings:

- Database: `playlist_db`
- User: `playlist_user`
- Password: `playlist_password`
- Host: `localhost` (or `postgres` in Docker)

## Development

### Project Structure

```
├── src/                    # Backend source code
│   ├── playlist_app/       # Main application package
│   │   ├── api/           # API endpoints
│   │   ├── core/          # Core functionality
│   │   ├── models/        # Database models
│   │   ├── services/      # Business logic
│   │   └── utils/         # Utilities
├── web-ui/                # Frontend React application
│   ├── src/               # React source code
│   ├── public/            # Static assets
│   └── package.json       # Frontend dependencies
├── scripts/               # CLI tools
├── config/                # Configuration files
├── docs/                  # Documentation
└── docker-compose.yml     # Docker configuration
```

### Development Workflow

1. **Start in development mode**:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
   ```

2. **Make changes** to source code
3. **Hot reloading** will automatically update the UI
4. **Restart backend** if needed for Python changes

### Testing

```bash
# Run backend tests
python -m pytest tests/

# Run frontend tests
cd web-ui
npm test
```

## Troubleshooting

### Common Issues

1. **Database connection errors**:
   - Check if PostgreSQL is running
   - Verify connection settings in `.env`
   - Ensure database and user exist

2. **Audio analysis failures**:
   - Check if FFmpeg is installed
   - Verify audio file formats are supported
   - Check TensorFlow model files are present

3. **Web UI not loading**:
   - Check if both backend and frontend are running
   - Verify ports 3000 and 8000 are available
   - Check browser console for errors

### Logs

- **Backend logs**: `./logs/`
- **Database logs**: `./logs/postgres/`
- **Docker logs**: `docker-compose logs [service-name]`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

