# Essentia Analysis Features Reference

This document provides a comprehensive reference for all audio features extracted by the Essentia analyzer in the playlist application.

## Overview

The Essentia analyzer extracts three main categories of features:

1. **Basic Features** - Fundamental audio characteristics
2. **Rhythm Features** - Tempo, beat tracking, and rhythmic patterns
3. **Harmonic Features** - Pitch, key, chords, and harmonic content

## Basic Features

### Energy and Loudness
- **`rms`** - Root Mean Square energy (average power)
- **`energy`** - Total energy content
- **`loudness`** - Perceived loudness in dB
- **`energy_variance`** - Variance in energy over time
- **`energy_mean`** - Average energy level
- **`energy_std`** - Standard deviation of energy

### Spectral Characteristics
- **`spectral_contrast_mean`** - Average spectral contrast (brightness vs darkness)
- **`spectral_contrast_std`** - Standard deviation of spectral contrast
- **`spectral_complexity_mean`** - Average spectral complexity
- **`spectral_complexity_std`** - Standard deviation of spectral complexity
- **`spectral_centroid_mean`** - Average spectral centroid (brightness)
- **`spectral_centroid_std`** - Standard deviation of spectral centroid
- **`spectral_rolloff_mean`** - Average spectral rolloff frequency
- **`spectral_rolloff_std`** - Standard deviation of spectral rolloff

### MFCC Features
- **`mfcc_mean`** - Mean Mel-frequency cepstral coefficients (40 values)
- **`mfcc_bands_mean`** - Mean mel band energies (40 values)

## Rhythm Features

### Tempo Analysis
- **`estimated_bpm`** - Estimated tempo in BPM (from simple analysis)
- **`tempo_confidence`** - Confidence in tempo estimation
- **`tempo_methods_used`** - Number of tempo estimation methods used
- **`rhythm_bpm`** - BPM from RhythmExtractor2013
- **`rhythm_confidence`** - Confidence from RhythmExtractor2013
- **`rhythm_estimates`** - Multiple tempo estimates
- **`rhythm_estimates_confidence`** - Confidence for each estimate
- **`tempo_tap_bpm`** - BPM from TempoTap algorithm
- **`tempo_tap_confidence`** - Confidence from TempoTap

### Beat Tracking
- **`beats`** - Array of beat timestamps
- **`beat_confidence`** - Overall confidence in beat tracking
- **`beat_intervals_mean`** - Average time between beats
- **`beat_intervals_std`** - Standard deviation of beat intervals
- **`num_beats`** - Total number of detected beats

### Onset Detection
- **`onset_strength_mean`** - Average onset strength
- **`onset_strength_std`** - Standard deviation of onset strength
- **`onset_strength_max`** - Maximum onset strength
- **`onset_count`** - Number of strong onsets detected

### Spectral Rhythm
- **`spectral_centroid_variance`** - Variance in spectral centroid (rhythmic brightness changes)

## Harmonic Features

### Key and Scale
- **`key`** - Detected musical key (e.g., "C", "F#")
- **`scale`** - Detected scale (e.g., "major", "minor")
- **`key_strength`** - Confidence in key detection

### Chromagram Analysis
- **`chromagram`** - Full chromagram matrix
- **`chromagram_mean`** - Average chroma values for each note
- **`chromagram_std`** - Standard deviation of chroma values
- **`chromagram_max`** - Maximum chroma values
- **`dominant_chroma`** - Most prominent note (e.g., "C", "F#")
- **`dominant_chroma_strength`** - Strength of dominant chroma

### Chord Detection
- **`chords`** - Array of detected chords
- **`chord_strength`** - Confidence for each chord
- **`chord_count`** - Total number of chords detected
- **`chord_strength_mean`** - Average chord confidence
- **`chord_strength_std`** - Standard deviation of chord confidence
- **`most_common_chord`** - Most frequently detected chord
- **`most_common_chord_count`** - Count of most common chord

### Pitch Analysis
- **`pitch_yin`** - Pitch values from Yin algorithm
- **`pitch_yin_confidence`** - Confidence for Yin pitch detection
- **`pitch_mean`** - Average pitch frequency
- **`pitch_std`** - Standard deviation of pitch
- **`pitch_min`** - Minimum pitch frequency
- **`pitch_max`** - Maximum pitch frequency
- **`pitch_median`** - Median pitch frequency
- **`most_common_note`** - Most frequent note name
- **`most_common_note_count`** - Count of most common note

### Melody Analysis
- **`pitch_melodia`** - Melody pitch values
- **`pitch_melodia_confidence`** - Confidence for melody detection
- **`melody_mean`** - Average melody pitch
- **`melody_std`** - Standard deviation of melody
- **`melody_range`** - Range of melody frequencies

### Harmonic Content
- **`spectral_peaks_count`** - Number of spectral peak frames
- **`harmonic_frequencies_mean`** - Average harmonic frequencies
- **`harmonic_frequencies_std`** - Standard deviation of harmonic frequencies
- **`harmonic_magnitudes_mean`** - Average harmonic magnitudes
- **`harmonic_magnitudes_std`** - Standard deviation of harmonic magnitudes
- **`strong_harmonics_count`** - Number of strong harmonics

## Configuration

### Algorithm Enablement

The following algorithms can be enabled/disabled in `config/analysis_config.json`:

```json
{
  "essentia": {
    "algorithms": {
      "enable_tensorflow": false,
      "enable_complex_rhythm": true,
      "enable_complex_harmonic": true,
      "enable_beat_tracking": true,
      "enable_tempo_tap": true,
      "enable_rhythm_extractor": true,
      "enable_pitch_analysis": true,
      "enable_chord_detection": true
    }
  }
}
```

### Performance Profiles

Three performance profiles are available:

1. **High Accuracy** - Maximum accuracy, slower processing
2. **Balanced** - Good balance of accuracy and speed (default)
3. **High Speed** - Faster processing, reduced accuracy

## Usage Examples

### Basic Analysis
```python
from src.playlist_app.services.essentia_analyzer import essentia_analyzer

# Analyze audio file
results = essentia_analyzer.analyze_audio_file("track.mp3")

# Access features
basic_features = results['basic_features']
rhythm_features = results['rhythm_features']
harmonic_features = results['harmonic_features']

# Get key information
print(f"Tempo: {rhythm_features.get('estimated_bpm', 'Unknown')} BPM")
print(f"Key: {harmonic_features.get('key', 'Unknown')} {harmonic_features.get('scale', '')}")
print(f"Energy: {basic_features.get('energy', 'Unknown')}")
```

### Feature Interpretation

#### Tempo Analysis
- **60-80 BPM**: Slow tempo (ballads, ambient)
- **80-120 BPM**: Medium tempo (pop, rock)
- **120-160 BPM**: Fast tempo (dance, electronic)
- **160+ BPM**: Very fast tempo (hardcore, drum & bass)

#### Key Detection
- **Major keys**: Bright, happy, uplifting
- **Minor keys**: Dark, sad, melancholic
- **Key strength > 0.7**: High confidence
- **Key strength < 0.3**: Low confidence

#### Energy Levels
- **RMS > 0.1**: High energy
- **RMS 0.01-0.1**: Medium energy
- **RMS < 0.01**: Low energy

#### Spectral Characteristics
- **High spectral centroid**: Bright, treble-heavy
- **Low spectral centroid**: Dark, bass-heavy
- **High spectral complexity**: Complex timbre
- **Low spectral complexity**: Simple timbre

## Error Handling

When algorithms fail, the system returns standardized fallback values:

- **Numerical features**: `-999.0`
- **String features**: `"unknown"`
- **Array features**: Empty arrays or arrays with fallback values

This ensures consistent data structure even when analysis fails.

## Performance Considerations

### Memory Usage
- **Short tracks (< 5 min)**: ~100-200MB
- **Medium tracks (5-10 min)**: ~200-500MB
- **Long tracks (> 10 min)**: ~500MB-1GB

### Processing Time
- **Basic features only**: ~10-30 seconds per track
- **Full analysis**: ~1-5 minutes per track
- **With TensorFlow**: ~2-10 minutes per track

### Optimization Tips
1. Use appropriate performance profile
2. Disable unused algorithms
3. Process tracks in batches
4. Use chunked analysis for long tracks
5. Enable caching for repeated analysis

## Troubleshooting

### Common Issues

1. **Memory errors**: Reduce batch size or use high-speed profile
2. **Slow processing**: Disable complex algorithms or use chunked analysis
3. **Inaccurate results**: Check audio quality and enable more algorithms
4. **Missing features**: Verify algorithm enablement in configuration

### Debug Mode

Enable debug logging to see detailed analysis progress:

```bash
export LOG_LEVEL=DEBUG
```

This will show which algorithms are running and their results.

