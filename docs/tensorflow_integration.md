# TensorFlow Integration with Mood Analysis

## Overview

The enhanced TensorFlow integration provides MusicNN-based music classification and mood analysis as part of the audio values extraction pipeline. This system combines machine learning predictions with emotional analysis to provide comprehensive music understanding.

## Features

### 1. MusicNN Model Integration
- **Pre-trained Model**: Uses the MSD MusicNN model for music tag prediction
- **50 Music Tags**: Predicts 50 different music characteristics and genres
- **Confidence Scores**: Provides confidence scores for each prediction
- **High-Confidence Filtering**: Identifies predictions above confidence thresholds

### 2. Mood Analysis
- **12 Mood Categories**: Energetic, calm, happy, sad, aggressive, peaceful, romantic, nostalgic, modern, acoustic, vocal, instrumental
- **Emotional Dimensions**: 
  - **Valence**: Positive vs negative emotion (-1 to 1)
  - **Arousal**: High vs low energy (0 to 1)
  - **Energy Level**: Overall energy assessment (0 to 1)
- **Primary Mood Detection**: Identifies the dominant mood with confidence scoring

### 3. Integration with Audio Pipeline
- **Modular Design**: Can be enabled/disabled independently
- **Database Storage**: Results stored in dedicated database columns
- **CLI Commands**: Easy-to-use command-line interface
- **API Integration**: RESTful API endpoints for programmatic access

## Configuration

### Analysis Configuration (`config/analysis_config.json`)

```json
{
  "essentia": {
    "algorithms": {
      "enable_tensorflow": true
    }
  },
  "tensorflow": {
    "models_directory": "models",
    "enable_musicnn": true,
    "musicnn_settings": {
      "input_frames": 187,
      "input_mels": 96,
      "sample_rate": 16000
    },
    "mood_analysis": {
      "enabled": true,
      "confidence_threshold": 0.3,
      "enable_valence_arousal": true,
      "enable_energy_level": true
    }
  }
}
```

### Model Requirements

The system requires the MusicNN model files in the `models/` directory:
- `msd-musicnn-1.pb` - TensorFlow model file (3MB)
- `msd-musicnn-1.json` - Model configuration and tag definitions

## Usage

### Command Line Interface

#### TensorFlow Analysis Only
```bash
# Analyze files with TensorFlow/MusicNN and mood detection
python scripts/master_cli.py tensorflow analyze --files music/track1.mp3 music/track2.wav

# Force re-analysis
python scripts/master_cli.py tensorflow analyze --files music/track.mp3 --force
```

#### Complete Audio Values Extraction
```bash
# Run complete pipeline (Essentia + TensorFlow + Mood)
python scripts/master_cli.py audio-values analyze --files music/track.mp3

# Batch processing
python scripts/master_cli.py audio-values analyze --files music/*.mp3
```

### Python API

#### Direct TensorFlow Analysis
```python
from src.playlist_app.services.tensorflow_analyzer import tensorflow_analyzer

# Analyze single file
results = tensorflow_analyzer.analyze_audio_file("music/track.mp3")

# Access MusicNN predictions
musicnn_results = results["tensorflow_analysis"]["musicnn"]
top_predictions = musicnn_results["top_predictions"]

# Access mood analysis
mood_data = results["mood_analysis"]
primary_mood = mood_data["primary_mood"]
emotions = mood_data["emotions"]
```

#### Complete Pipeline
```python
from src.playlist_app.services.modular_analysis_service import modular_analysis_service

# Run complete analysis
results = modular_analysis_service.analyze_file(
    file_path="music/track.mp3",
    enable_essentia=True,
    enable_tensorflow=True,
    enable_faiss=False
)
```

### Demo Script

```bash
# Run the demonstration script
python examples/tensorflow_mood_demo.py music/track.mp3
```

## Output Format

### TensorFlow Analysis Results

```json
{
  "tensorflow_analysis": {
    "musicnn": {
      "top_predictions": [
        {"tag": "rock", "confidence": 0.85, "index": 0},
        {"tag": "guitar", "confidence": 0.72, "index": 31},
        {"tag": "male vocalists", "confidence": 0.68, "index": 13}
      ],
      "high_confidence_predictions": [...],
      "statistics": {
        "mean_confidence": 0.23,
        "max_confidence": 0.85,
        "prediction_entropy": 2.45,
        "high_confidence_count": 8
      },
      "all_predictions": [0.85, 0.12, 0.34, ...],
      "tag_names": ["rock", "pop", "alternative", ...]
    }
  },
  "mood_analysis": {
    "mood_scores": {
      "energetic": 0.75,
      "aggressive": 0.68,
      "calm": 0.12,
      "happy": 0.45
    },
    "dominant_moods": [
      {"mood": "energetic", "confidence": 0.75},
      {"mood": "aggressive", "confidence": 0.68}
    ],
    "emotions": {
      "valence": 0.45,
      "arousal": 0.82,
      "energy_level": 0.78
    },
    "primary_mood": "energetic",
    "mood_confidence": 0.75
  }
}
```

## Database Schema

### New Columns in `audio_analysis` Table

```sql
-- TensorFlow features
tensorflow_features TEXT,        -- Complete TensorFlow analysis JSON
tensorflow_summary TEXT,         -- Summary of top predictions

-- Mood analysis features  
mood_analysis TEXT,              -- Complete mood analysis JSON
primary_mood VARCHAR,            -- Primary mood (energetic, calm, etc.)
mood_confidence FLOAT            -- Confidence score for primary mood
```

## Mood Categories

### Primary Moods
1. **Energetic**: High-energy, dynamic music (dance, party, rock)
2. **Calm**: Relaxing, peaceful music (chill, ambient, easy listening)
3. **Happy**: Positive, uplifting music (happy, catchy, party)
4. **Sad**: Melancholic, emotional music (sad, mellow)
5. **Aggressive**: Intense, powerful music (metal, punk, hard rock)
6. **Peaceful**: Serene, tranquil music (ambient, beautiful)
7. **Romantic**: Intimate, emotional music (sexy, soul, rnb)
8. **Nostalgic**: Retro, vintage music (oldies, 60s, 70s, 80s)
9. **Modern**: Contemporary electronic music (electronic, house, techno)
10. **Acoustic**: Natural, organic music (acoustic, folk, country)
11. **Vocal**: Voice-focused music (female/male vocalists)
12. **Instrumental**: Music without vocals (instrumental, guitar)

### Emotional Dimensions

#### Valence (-1 to 1)
- **Positive**: happy, beautiful, catchy, sexy, party
- **Negative**: sad, aggressive, dark

#### Arousal (0 to 1)
- **High Energy**: dance, rock, metal, party, catchy
- **Low Energy**: chill, ambient, mellow, easy listening

#### Energy Level (0 to 1)
- **High Energy**: dance, rock, metal, party, catchy, fast
- **Low Energy**: chill, ambient, mellow, slow

## Performance Considerations

### Memory Usage
- **Model Loading**: ~50MB for MusicNN model
- **Processing**: ~100-200MB per audio file
- **Batch Processing**: Configure `memory_limit_mb` in performance settings

### Processing Speed
- **Single File**: 2-5 seconds depending on file length
- **Batch Processing**: Use parallel workers for efficiency
- **GPU Acceleration**: Automatic if CUDA is available

### Optimization Tips
1. **Sample Rate**: MusicNN expects 16kHz, automatic resampling
2. **Input Shape**: Automatic padding/truncation to 187x96 frames
3. **Caching**: Results cached to avoid re-processing
4. **Parallel Processing**: Use multiple workers for batch analysis

## Troubleshooting

### Common Issues

#### TensorFlow Not Available
```
Error: TensorFlow analysis not available
```
**Solution**: Install TensorFlow
```bash
pip install tensorflow
```

#### Model Files Missing
```
Warning: MusicNN model not found
```
**Solution**: Ensure model files are in `models/` directory
```bash
ls models/
# Should show: msd-musicnn-1.pb, msd-musicnn-1.json
```

#### Memory Errors
```
Error: Failed to load TensorFlow model
```
**Solution**: Reduce memory usage
```json
{
  "performance": {
    "parallel_processing": {
      "memory_limit_mb": 256
    }
  }
}
```

### Debug Mode

Enable detailed logging:
```python
import logging
logging.getLogger('src.playlist_app.services.tensorflow_analyzer').setLevel(logging.DEBUG)
```

## Integration Examples

### Playlist Generation by Mood
```python
# Find tracks with specific mood
def find_tracks_by_mood(mood, limit=10):
    with get_db_session() as db:
        tracks = db.query(AudioAnalysis).filter(
            AudioAnalysis.primary_mood == mood,
            AudioAnalysis.mood_confidence > 0.5
        ).limit(limit).all()
        return tracks

# Generate energetic playlist
energetic_tracks = find_tracks_by_mood("energetic")
```

### Mood-Based Recommendations
```python
# Recommend tracks based on emotional profile
def recommend_by_emotions(target_valence, target_arousal, limit=5):
    # Find tracks with similar emotional characteristics
    # Implementation depends on your recommendation algorithm
    pass
```

### Batch Analysis with Progress
```python
from src.playlist_app.services.modular_analysis_service import modular_analysis_service

# Analyze multiple files with progress tracking
results = modular_analysis_service.analyze_files_batch(
    file_paths=["track1.mp3", "track2.mp3", "track3.mp3"],
    enable_essentia=True,
    enable_tensorflow=True,
    enable_faiss=False
)

print(f"Processed: {results['successful']}/{results['total_files']} files")
```

## Future Enhancements

### Planned Features
1. **Additional Models**: VGGish, TempoCNN, FSD-SINet integration
2. **Custom Mood Models**: Train custom mood classification models
3. **Real-time Analysis**: Stream processing for live audio
4. **Advanced Emotions**: More granular emotional dimensions
5. **Cross-modal Analysis**: Combine audio with lyrics/metadata

### Extensibility
The modular design allows easy addition of new TensorFlow models and analysis types. The system is designed to be extensible for future machine learning enhancements.
