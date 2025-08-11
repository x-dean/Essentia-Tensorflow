# MusiCNN Models Setup

This document explains how to set up MusiCNN models for enhanced audio analysis with genre and mood classification.

## Required Files

You need to provide the following files in the `models/` directory:

### 1. Model File
- **File**: `msd-musicnn-1.pb`
- **Description**: The pre-trained MusiCNN TensorFlow model for autotagging
- **Size**: ~50MB
- **Source**: [Essentia Models Repository](https://essentia.upf.edu/models/autotagging/msd/msd-musicnn-1.pb)

### 2. Model Metadata
- **File**: `msd-musicnn-1.json`
- **Description**: JSON file containing model metadata and class labels
- **Source**: [Essentia Models Repository](https://essentia.upf.edu/models/autotagging/msd/msd-musicnn-1.json)
- **Content**: Contains the list of music tags/classes that the model can predict

## Directory Structure

Create the following directory structure in your project root:

```
Essentia-Tensorflow/
├── models/
│   ├── msd-musicnn-1.pb
│   └── msd-musicnn-1.json
├── src/
├── docker-compose.yml
└── ...
```

## Setup Instructions

### Option 1: Local Models Directory

1. Create a `models/` directory in your project root:
   ```bash
   mkdir models
   ```

2. Place the required files in the `models/` directory

3. The models will be automatically mounted into the Docker container

### Option 2: Custom Models Directory

1. Set the `MODELS_DIRECTORY` environment variable to point to your models:
   ```bash
   export MODELS_DIRECTORY=/path/to/your/models
   ```

2. Or add it to your `.env` file:
   ```
   MODELS_DIRECTORY=/path/to/your/models
   ```

## Obtaining the Models

### Official Sources

The MusiCNN models can be obtained from:

1. **Essentia Models Repository**: https://essentia.upf.edu/models/
2. **MusiCNN Paper**: https://github.com/MTG/musicnn

### Download Commands

You can download the models using these commands:

```bash
# Create models directory
mkdir -p models

# Download the model file
wget -O models/msd-musicnn-1.pb https://essentia.upf.edu/models/autotagging/msd/msd-musicnn-1.pb

# Download the model metadata
wget -O models/msd-musicnn-1.json https://essentia.upf.edu/models/autotagging/msd/msd-musicnn-1.json
```

Or use the provided Python script:

```bash
python download_models.py
```

## Verification

After setting up the models, you can verify they're working by:

1. Rebuilding the Docker container:
   ```bash
   docker-compose build playlist-app
   ```

2. Running the application and checking the logs for:
   ```
   MusiCNN model loaded successfully from /app/models/msd-musicnn-1.pb
   MusiCNN model loaded successfully with X labels
   ```

## Usage

Once the models are loaded, they will be automatically used when:

- Analyzing audio files with `include_tensorflow=True`
- Extracting feature vectors for similarity search
- Performing genre and mood classification

The models will enhance the feature vectors with genre and mood probabilities, improving the quality of similarity search and playlist generation.

## Troubleshooting

### Models Not Loading

If you see "No MusiCNN models found" in the logs:

1. Check that the files exist in the correct location
2. Verify file permissions (should be readable)
3. Check the Docker volume mount is working correctly

### File Not Found Errors

If you get "MusiCNN model files not found" errors:

1. Ensure the `models/` directory exists
2. Verify the file names match exactly
3. Check that the files are not corrupted

### Performance Notes

- The MusiCNN models add ~50MB to the container size
- Model loading takes a few seconds on first startup
- Analysis with TensorFlow models is slower but provides richer features
