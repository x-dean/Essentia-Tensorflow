# Fallback Values System Documentation

## Overview

The audio analysis system uses **standardized fallback values** to handle extraction failures and invalid data. This ensures consistent data quality and enables simple querying to identify problematic files.

## Standardized Fallback Values

### Core Principle
All failed extractions use **`-999`** as the standardized fallback value, making it easy to filter out invalid data with simple database queries.

### Metadata Fallback Values

#### Integer Fields
- **Fields**: `year`, `track_number`, `disc_number`, `bitrate`, `sample_rate`, `channels`, `rating`
- **Fallback Value**: `-999`
- **Example**: `track_number = -999` indicates track number extraction failed

#### Float Fields
- **Fields**: `duration`, `bpm`, `replaygain_track_gain`, `replaygain_album_gain`, `replaygain_track_peak`, `replaygain_album_peak`
- **Fallback Value**: `-999.0`
- **Example**: `duration = -999.0` indicates duration extraction failed

#### String Fields
- **Fields**: `key`, `scale`
- **Fallback Value**: `"unknown"`
- **Example**: `key = "unknown"` indicates key detection failed

### Essentia Analysis Fallback Values

#### Basic Features
- **Fields**: `duration`, `rms`, `energy`, `loudness`
- **Fallback Value**: `-999.0`
- **Example**: `rms = -999.0` indicates RMS calculation failed

#### Spectral Features
- **Fields**: `spectral_contrast_mean`, `spectral_contrast_std`, `spectral_complexity_mean`, `spectral_complexity_std`, `spectral_centroid_mean`, `spectral_centroid_std`, `spectral_rolloff_mean`, `spectral_rolloff_std`
- **Fallback Value**: `-999.0`
- **Example**: `spectral_centroid_mean = -999.0` indicates spectral analysis failed

#### Rhythm Features
- **Fields**: `estimated_bpm`, `energy_variance`, `energy_mean`
- **Fallback Value**: `-999.0`
- **Example**: `estimated_bpm = -999.0` indicates tempo estimation failed

#### Harmonic Features
- **Fields**: `key_strength`
- **Fallback Value**: `-999.0`
- **Example**: `key_strength = -999.0` indicates key strength calculation failed

#### Key/Scale Detection
- **Fields**: `key`, `scale`
- **Fallback Value**: `"unknown"`
- **Example**: `key = "unknown"` indicates key detection failed

#### MFCC Features
- **Fields**: `mfcc_mean`, `mfcc_bands_mean`
- **Fallback Value**: `[-999.0] * 40` (array of 40 -999.0 values)
- **Example**: `mfcc_mean = [-999.0, -999.0, ...]` indicates MFCC extraction failed

#### TensorFlow Features
- **Fields**: Model outputs (musicnn, tempo_cnn, vggish, etc.)
- **Fallback Value**: `[-999.0]`
- **Example**: `musicnn = [-999.0]` indicates TensorFlow model failed

## Database Query Examples

### Find Files with Failed Metadata Extraction

```sql
-- Find files with any failed metadata field
SELECT file_path FROM audio_metadata 
WHERE duration = -999.0 
   OR track_number = -999 
   OR year = -999 
   OR bpm = -999.0;
```

### Find Files with Failed Essentia Analysis

```sql
-- Find files with any failed analysis field
SELECT file_path FROM audio_analysis 
WHERE rms = -999.0 
   OR estimated_bpm = -999.0 
   OR key_strength = -999.0;
```

### Find All Files with Any Failed Extraction

```sql
-- Comprehensive query for all failed extractions
SELECT DISTINCT f.file_path 
FROM files f
LEFT JOIN audio_metadata m ON f.id = m.file_id
LEFT JOIN audio_analysis a ON f.id = a.file_id
WHERE m.duration = -999.0 
   OR m.track_number = -999 
   OR m.year = -999
   OR a.rms = -999.0 
   OR a.estimated_bpm = -999.0;
```

### Find Only Valid Files (Exclude All Failed Extractions)

```sql
-- Find files with all valid extractions
SELECT f.file_path 
FROM files f
LEFT JOIN audio_metadata m ON f.id = m.file_id
LEFT JOIN audio_analysis a ON f.id = a.file_id
WHERE m.duration > 0 
   AND m.track_number > 0 
   AND m.year > 0
   AND a.rms > 0 
   AND a.estimated_bpm > 0;
```

### Count Failed Extractions by Type

```sql
-- Count metadata failures
SELECT 
    COUNT(*) as total_files,
    SUM(CASE WHEN duration = -999.0 THEN 1 ELSE 0 END) as duration_failures,
    SUM(CASE WHEN track_number = -999 THEN 1 ELSE 0 END) as track_number_failures,
    SUM(CASE WHEN year = -999 THEN 1 ELSE 0 END) as year_failures
FROM audio_metadata;
```

### Find Files with Specific Failure Types

```sql
-- Find files with duration extraction failures
SELECT file_path FROM audio_metadata WHERE duration = -999.0;

-- Find files with tempo estimation failures
SELECT file_path FROM audio_analysis WHERE estimated_bpm = -999.0;

-- Find files with key detection failures
SELECT file_path FROM audio_analysis WHERE key = 'unknown';
```

## Implementation Details

### Metadata Extraction (`src/playlist_app/services/metadata.py`)

The `_convert_data_types` method handles fallback values:

```python
# Integer fields
except (ValueError, IndexError):
    converted['track_number'] = -999  # Standardized fallback

# Float fields  
except ValueError:
    converted['duration'] = -999.0  # Standardized fallback

# String fields
except Exception as e:
    features['key'] = 'unknown'  # Standardized fallback
```

### Essentia Analysis (`src/playlist_app/services/essentia_analyzer.py`)

The analysis methods handle fallback values:

```python
# Basic features
except Exception as e:
    return {
        'duration': -999.0,
        'rms': -999.0,
        'energy': -999.0,
        'loudness': -999.0
    }

# Rhythm features
except Exception as e:
    return {'estimated_bpm': -999.0, 'energy_variance': -999.0}

# Harmonic features
except Exception as e:
    return {
        'key': 'unknown',
        'scale': 'unknown', 
        'key_strength': -999.0
    }
```

## Benefits

### 1. **Simple Filtering**
- Single condition queries to exclude invalid data
- No complex logic needed to identify failed extractions

### 2. **Data Quality Assurance**
- Clear distinction between valid and invalid data
- Easy identification of problematic files

### 3. **Performance**
- Efficient database queries with simple conditions
- No need for complex validation logic

### 4. **Debugging**
- Quick identification of extraction failures
- Easy to spot patterns in failed extractions

### 5. **Consistency**
- Uniform approach across all data types
- Predictable behavior for data processing

## Best Practices

### 1. **Always Check for Fallback Values**
When processing analysis results, always check for `-999` values:

```python
if analysis_result['rms'] == -999.0:
    # Handle failed extraction
    logger.warning("RMS extraction failed")
```

### 2. **Use Simple Queries**
Leverage the standardized values for simple filtering:

```python
# Get only valid analysis results
valid_results = [r for r in results if r['rms'] > 0]
```

### 3. **Monitor Data Quality**
Regularly check for failed extractions:

```sql
-- Daily quality check
SELECT COUNT(*) as failed_extractions 
FROM audio_analysis 
WHERE rms = -999.0 OR estimated_bpm = -999.0;
```

### 4. **Document Failures**
When fallback values are used, log the reason:

```python
logger.warning(f"Key detection failed for {file_path}: {e}")
features['key'] = 'unknown'
```

## Troubleshooting

### Common Issues

1. **Files with Many Fallback Values**
   - Check if the file is corrupted or in unsupported format
   - Verify that required codecs are installed

2. **Specific Field Failures**
   - Duration failures: Check if FFmpeg can read the file
   - Tempo failures: Audio might be too short or silent
   - Key detection failures: Audio might be noise or speech

3. **Batch Processing Issues**
   - Check system resources during batch processing
   - Verify database connection stability

### Debugging Queries

```sql
-- Find files with multiple failures
SELECT file_path, 
       CASE WHEN duration = -999.0 THEN 1 ELSE 0 END as duration_failed,
       CASE WHEN estimated_bpm = -999.0 THEN 1 ELSE 0 END as tempo_failed,
       CASE WHEN key = 'unknown' THEN 1 ELSE 0 END as key_failed
FROM audio_metadata m
JOIN audio_analysis a ON m.file_id = a.file_id
WHERE duration = -999.0 OR estimated_bpm = -999.0 OR key = 'unknown';
```

## Migration Notes

### From Previous Versions
If migrating from a system with different fallback values:

1. **Update existing data**:
```sql
-- Convert old fallback values to new standardized values
UPDATE audio_metadata SET duration = -999.0 WHERE duration = -1.0;
UPDATE audio_analysis SET rms = -999.0 WHERE rms = -1.0;
```

2. **Update application code** to use new fallback values
3. **Test thoroughly** to ensure all fallback scenarios work correctly

---

**Version**: 1.0  
**Last Updated**: 2025-01-11  
**Maintainer**: Audio Analysis Team
