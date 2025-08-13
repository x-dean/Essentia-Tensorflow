# Modular Analysis System

## Overview

The analysis system has been refactored into a modular architecture with three independent modules:

1. **Essentia Module** - Audio feature extraction
2. **TensorFlow Module** - Machine learning classification (MusicNN)
3. **FAISS Module** - Vector similarity search

Each module can be enabled/disabled independently through configuration, CLI, API, or UI.

## Module Architecture

### 1. Essentia Module (`essentia_analyzer.py`)

**Purpose**: Pure audio feature extraction using Essentia library

**Features**:
- Basic audio features (loudness, dynamic complexity, spectral complexity)
- Spectral features (centroid, rolloff, bandwidth, flatness)
- Rhythm features (BPM, beat tracking, rhythm confidence)
- Harmonic features (key detection, chord detection)
- MFCC features (mel-frequency cepstral coefficients)

**Configuration**: `config/analysis_config.json` → `essentia` section
- Audio processing parameters (sample rate, frame size, etc.)
- Spectral analysis settings
- Algorithm enable/disable flags

**Status**: Always available and enabled by default

### 2. TensorFlow Module (`tensorflow_analyzer.py`)

**Purpose**: Machine learning classification using TensorFlow models

**Features**:
- MusicNN model for music tag prediction
- Support for additional models (VGGish, TempoCNN, FSD-SINet)
- Mel-spectrogram extraction for model input
- Top prediction results with confidence scores

**Configuration**: `config/analysis_config.json` → `tensorflow` section
- Models directory path
- Model enable/disable flags
- Audio processing parameters for TensorFlow

**Status**: Available when TensorFlow is installed and models are present

### 3. FAISS Module (`faiss_service.py`)

**Purpose**: Vector similarity search and indexing

**Features**:
- Vector indexing of audio features
- Similarity search capabilities
- Index persistence and management
- Integration with database storage

**Configuration**: `config/analysis_config.json` → `faiss` section
- Index type and parameters
- Normalization settings
- Index name and metadata

**Status**: Available when FAISS is installed

## Coordination Service

### Modular Analysis Service (`modular_analysis_service.py`)

**Purpose**: Coordinates all three modules and manages the analysis workflow

**Features**:
- Module status checking and reporting
- Independent module enable/disable
- Batch analysis with selective module usage
- Database integration and result storage
- Error handling and fallback mechanisms

**Key Methods**:
- `get_module_status()` - Returns status of all modules
- `analyze_file()` - Analyze single file with enabled modules
- `analyze_files_batch()` - Batch analysis with module selection

## Configuration

### Module Control

```json
{
  "modules": {
    "enable_essentia": true,
    "enable_tensorflow": true,
    "enable_faiss": true
  }
}
```

### Individual Module Settings

Each module has its own configuration section:

```json
{
  "essentia": { /* Essentia-specific settings */ },
  "tensorflow": { /* TensorFlow-specific settings */ },
  "faiss": { /* FAISS-specific settings */ }
}
```

## API Endpoints

### Module Status
- `GET /analysis/modules/status` - Get status of all modules
- `POST /analysis/modules/toggle` - Toggle module on/off

### Analysis Control
- `POST /analysis/trigger` - Trigger analysis with current module settings
- `GET /analysis/status` - Get analysis progress

## Web UI Integration

### Module Status Display
- Real-time module availability and status
- Enable/disable toggles for each module
- Visual indicators for module health

### Analysis Control
- Analysis trigger with current module configuration
- Progress tracking and status updates
- Error reporting and recovery

## CLI Integration

### Module Control
```bash
# Check module status
playlist modules status

# Toggle modules
playlist modules enable tensorflow
playlist modules disable faiss

# Analyze with specific modules
playlist analyze --essentia --tensorflow --no-faiss
```

## Benefits of Modular System

### 1. Independence
- Each module can be developed, tested, and deployed independently
- Failures in one module don't affect others
- Different teams can work on different modules

### 2. Flexibility
- Users can enable only the modules they need
- Resource usage can be optimized per use case
- Different analysis strategies for different scenarios

### 3. Maintainability
- Clear separation of concerns
- Easier debugging and troubleshooting
- Simplified testing and validation

### 4. Scalability
- Modules can be distributed across different services
- Independent scaling based on demand
- Better resource utilization

## Migration from Old System

### Changes Made
1. **Essentia Analyzer**: Removed TensorFlow dependencies, focused on pure audio analysis
2. **New TensorFlow Module**: Created dedicated module for ML classification
3. **Modular Service**: New coordination layer for all modules
4. **Configuration**: Updated to support module-level control
5. **API**: Added module status and control endpoints
6. **UI**: Added module status display and controls

### Backward Compatibility
- Existing analysis results are preserved
- Database schema remains unchanged
- API endpoints maintain compatibility where possible

## Testing

### Test Script
Run `test_modular_analysis.py` to verify the modular system:

```bash
python test_modular_analysis.py
```

This script tests:
- Module initialization and status
- Individual module functionality
- Configuration loading
- Error handling

### Manual Testing
1. **Essentia Only**: Disable TensorFlow and FAISS, run analysis
2. **TensorFlow Only**: Disable Essentia and FAISS, run analysis
3. **FAISS Only**: Disable Essentia and TensorFlow, run analysis
4. **All Modules**: Enable all modules, run analysis

## Troubleshooting

### Common Issues

1. **Analysis Stuck at "Preparing to Analyze"**
   - Check module availability and configuration
   - Verify database connectivity
   - Check logs for specific module errors

2. **TensorFlow Module Not Available**
   - Ensure TensorFlow is installed
   - Check model files are present in `models/` directory
   - Verify model file permissions

3. **FAISS Module Not Available**
   - Ensure FAISS is installed (`pip install faiss-cpu`)
   - Check FAISS configuration settings
   - Verify index directory permissions

4. **Module Toggle Not Working**
   - Check configuration file permissions
   - Verify API endpoint is accessible
   - Check logs for configuration update errors

### Debug Commands
```bash
# Check module status
curl http://localhost:8000/analysis/modules/status

# Test individual modules
python -c "from src.playlist_app.services.essentia_analyzer import essentia_analyzer; print('Essentia OK')"
python -c "from src.playlist_app.services.tensorflow_analyzer import tensorflow_analyzer; print('TensorFlow OK')"
python -c "from src.playlist_app.services.faiss_service import faiss_service; print('FAISS OK')"
```

## Future Enhancements

### Planned Features
1. **Module Hot-Reloading**: Enable/disable modules without restart
2. **Module Metrics**: Performance monitoring for each module
3. **Plugin System**: Support for custom analysis modules
4. **Distributed Modules**: Run modules on separate services
5. **Module Versioning**: Support for different module versions

### Integration Opportunities
1. **External APIs**: Integration with music metadata services
2. **Cloud Services**: AWS, Google Cloud, Azure integration
3. **Real-time Analysis**: Streaming audio analysis
4. **Batch Processing**: Large-scale analysis workflows
