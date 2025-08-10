# 🎵 Playlista Base Image

A comprehensive Docker base image for building playlist applications with advanced audio processing capabilities, powered by Essentia and TensorFlow.

## 🚀 Features

### 🎵 **Audio Processing**
- **Essentia 2.1-beta6-dev** - 251 audio analysis algorithms
- **TensorFlow Integration** - 4 pre-trained audio models
- **Librosa 0.11.0** - Advanced audio analysis
- **FFmpeg** - Multimedia processing
- **Multiple audio formats** - MP3, WAV, FLAC, OGG, etc.

### 🌐 **Web Development**
- **FastAPI** - High-performance API framework
- **Flask** - Web framework
- **Uvicorn & Gunicorn** - ASGI/WSGI servers
- **HTTP clients** - Requests, Aiohttp, Httpx

### 🗄️ **Database & Caching**
- **SQLAlchemy** - ORM framework
- **PostgreSQL** - Database support (psycopg2)
- **Redis** - In-memory caching
- **Celery** - Background task processing

### 📊 **Data Science & ML**
- **Pandas 2.3.1** - Data manipulation
- **NumPy 2.2.6** - Numerical computing
- **Scikit-learn** - Machine learning
- **Matplotlib, Seaborn, Plotly** - Visualization

## 📦 Image Details

- **Base:** Python 3.11-slim
- **Size:** 4.59GB
- **Architecture:** Linux x86_64
- **Status:** Production-ready

## 🛠️ Quick Start

### 1. Pull the Image
```bash
docker pull playlista-base:latest
```

### 2. Run Interactive Shell
```bash
docker run -it --rm playlista-base python3
```

### 3. Test Audio Processing
```bash
docker run --rm playlista-base test-essentia
```

### 4. Check Dependencies
```bash
docker run --rm playlista-base test-playlist-deps
```

## 🎯 Usage Examples

### Basic Audio Analysis
```python
import essentia.standard as es
import numpy as np

# Generate test audio
sr = 44100
t = np.linspace(0, 1, sr)
sine = np.sin(2 * np.pi * 440 * t).astype(np.float32)

# Extract features
mfcc = es.MFCC()
mfcc_values, mfcc_bands = mfcc(sine)

rms = es.RMS()
rms_value = rms(sine)

print(f"MFCC shape: {mfcc_values.shape}")
print(f"RMS: {rms_value}")
```

### FastAPI Audio Processing API
```python
from fastapi import FastAPI, UploadFile, File
import essentia.standard as es
import soundfile as sf
import numpy as np

app = FastAPI()

@app.post("/analyze-audio")
async def analyze_audio(file: UploadFile = File(...)):
    # Read audio file
    audio, sr = sf.read(file.file)
    
    # Convert to mono if stereo
    if len(audio.shape) > 1:
        audio = np.mean(audio, axis=1)
    
    # Extract features
    mfcc = es.MFCC()
    mfcc_values, _ = mfcc(audio.astype(np.float32))
    
    return {
        "filename": file.filename,
        "duration": len(audio) / sr,
        "mfcc_shape": mfcc_values.shape,
        "mfcc_mean": float(np.mean(mfcc_values))
    }
```

### TensorFlow Audio Models
```python
import essentia.standard as es

# Available TensorFlow algorithms
tensorflow_algorithms = [
    "TensorflowInputFSDSINet",    # Sound event detection
    "TensorflowInputMusiCNN",     # Music analysis
    "TensorflowInputTempoCNN",    # Tempo estimation
    "TensorflowInputVGGish"       # Audio feature extraction
]

# Example usage
vggish = es.TensorflowInputVGGish()
# Process audio with VGGish model
```

## 🏗️ Building Your Application

### Using as Base Image
```dockerfile
FROM playlista-base:latest

WORKDIR /app

# Copy your application code
COPY requirements.txt .
COPY src/ ./src/

# Install additional dependencies
RUN pip install -r requirements.txt

# Expose port
EXPOSE 8000

# Run your application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Development with Volume Mount
```bash
docker run -it --rm \
  -v $(pwd):/app \
  -p 8000:8000 \
  playlista-base \
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 📋 Available Algorithms

### Audio Analysis (Essentia)
- **MFCC & Spectral:** MFCC, SpectralCentroid, SpectralComplexity, SpectralContrast
- **Pitch Analysis:** PitchMelodia, PitchYin, MultiPitchKlapuri, PitchSalience
- **Rhythm & Tempo:** BeatTrackerDegara, TempoTap, RhythmExtractor, OnsetDetection
- **Harmonic Analysis:** Chromagram, ChordsDetection, KeyExtractor, Scale
- **Energy & Loudness:** RMS, Energy, BeatsLoudness, SingleBeatLoudness

### Machine Learning (TensorFlow)
- **FSDSINet** - Sound event detection
- **MusiCNN** - Music analysis with CNN
- **TempoCNN** - Tempo estimation
- **VGGish** - Audio feature extraction

## 🗄️ Database Integration

### PostgreSQL with SQLAlchemy
```python
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database connection
engine = create_engine("postgresql://user:pass@localhost/playlist_db")
Session = sessionmaker(bind=engine)

# Model definition
Base = declarative_base()

class AudioFeatures(Base):
    __tablename__ = "audio_features"
    
    id = Column(Integer, primary_key=True)
    filename = Column(String)
    mfcc_features = Column(String)  # JSON string
    duration = Column(Float)
```

### Redis Caching
```python
import redis
import json

# Redis connection
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Cache audio features
def cache_features(filename, features):
    redis_client.setex(
        f"audio_features:{filename}",
        3600,  # 1 hour TTL
        json.dumps(features)
    )
```

### Celery Background Tasks
```python
from celery import Celery

celery = Celery('tasks', broker='redis://localhost:6379/0')

@celery.task
def process_audio_async(audio_file_path):
    """Process audio file in background"""
    import essentia.standard as es
    import soundfile as sf
    
    audio, sr = sf.read(audio_file_path)
    # Process audio...
    return features
```

## 🧪 Testing

### Run Built-in Tests
```bash
# Test Essentia functionality
docker run --rm playlista-base test-essentia

# Test all dependencies
docker run --rm playlista-base test-playlist-deps
```

### Custom Testing
```python
import pytest
import essentia.standard as es
import numpy as np

def test_mfcc_extraction():
    """Test MFCC feature extraction"""
    # Generate test audio
    sr = 44100
    t = np.linspace(0, 1, sr)
    sine = np.sin(2 * np.pi * 440 * t).astype(np.float32)
    
    # Extract MFCC
    mfcc = es.MFCC()
    mfcc_values, _ = mfcc(sine)
    
    assert mfcc_values.shape == (40,)
    assert not np.isnan(mfcc_values).any()
```

## 📊 Performance

### Audio Processing Benchmarks
- **MFCC extraction:** ~0.1s for 1 minute audio
- **Pitch analysis:** ~0.5s for 1 minute audio
- **Tempo detection:** ~1.0s for 1 minute audio
- **TensorFlow models:** ~2-5s depending on model

### Memory Usage
- **Base image:** ~4.59GB
- **Runtime memory:** ~512MB-2GB depending on audio processing load

## 🔧 Configuration

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/playlist_db
REDIS_URL=redis://localhost:6379/0

# Audio processing
AUDIO_SAMPLE_RATE=44100
AUDIO_CHANNELS=1

# API settings
API_HOST=0.0.0.0
API_PORT=8000
```

### Docker Compose Example
```yaml
version: '3.8'

services:
  playlista-app:
    image: playlista-base:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres/playlist_db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    volumes:
      - ./app:/app

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: playlist_db
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Essentia** - Audio analysis library by MTG-UPF
- **TensorFlow** - Machine learning framework by Google
- **Librosa** - Audio analysis library
- **FastAPI** - Modern web framework

## 📞 Support

For questions and support:
- Create an issue on GitHub
- Check the documentation
- Review the examples

---

**Built with ❤️ for the music and audio processing community**

