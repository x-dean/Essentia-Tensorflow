# Fallback Values Quick Reference

##  Core Principle
All failed extractions use **`-999`** as the standardized fallback value.

##  Fallback Values Summary

| Data Type | Fallback Value | Example Fields |
|-----------|----------------|----------------|
| **Integer** | `-999` | `year`, `track_number`, `disc_number`, `bitrate`, `sample_rate`, `channels`, `rating` |
| **Float** | `-999.0` | `duration`, `bpm`, `rms`, `energy`, `loudness`, `spectral_*`, `estimated_bpm`, `key_strength` |
| **String** | `"unknown"` | `key`, `scale` |
| **Array** | `[-999.0] * 40` | `mfcc_mean`, `mfcc_bands_mean` |
| **TensorFlow** | `[-999.0]` | Model outputs |

##  Quick Queries

### Find All Failed Extractions
```sql
SELECT DISTINCT f.file_path 
FROM files f
LEFT JOIN audio_metadata m ON f.id = m.file_id
LEFT JOIN audio_analysis a ON f.id = a.file_id
WHERE m.duration = -999.0 OR a.rms = -999.0;
```

### Find Only Valid Files
```sql
SELECT f.file_path 
FROM files f
LEFT JOIN audio_metadata m ON f.id = m.file_id
LEFT JOIN audio_analysis a ON f.id = a.file_id
WHERE m.duration > 0 AND a.rms > 0;
```

### Count Failures
```sql
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN duration = -999.0 THEN 1 ELSE 0 END) as duration_failures,
    SUM(CASE WHEN rms = -999.0 THEN 1 ELSE 0 END) as rms_failures
FROM audio_metadata m
JOIN audio_analysis a ON m.file_id = a.file_id;
```

##  Python Usage

### Check for Failed Extractions
```python
# Check if analysis failed
if analysis_result['rms'] == -999.0:
    print("RMS extraction failed")

# Filter valid results
valid_results = [r for r in results if r['rms'] > 0]
```

### Handle Fallback Values
```python
def process_analysis(analysis_result):
    if analysis_result['estimated_bpm'] == -999.0:
        # Handle tempo estimation failure
        logger.warning("Tempo estimation failed")
        return None
    
    # Process valid result
    return analysis_result
```

##  Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `duration = -999.0` | File corrupted/unsupported | Check file format and codecs |
| `estimated_bpm = -999.0` | Audio too short/silent | Verify audio has sufficient content |
| `key = "unknown"` | Non-musical audio | Check if file contains music |
| Multiple `-999.0` values | System resource issues | Check CPU/memory during processing |

##  Monitoring

### Daily Quality Check
```sql
-- Run this daily to monitor data quality
SELECT 
    COUNT(*) as total_files,
    SUM(CASE WHEN duration = -999.0 THEN 1 ELSE 0 END) as failed_metadata,
    SUM(CASE WHEN rms = -999.0 THEN 1 ELSE 0 END) as failed_analysis
FROM audio_metadata m
JOIN audio_analysis a ON m.file_id = a.file_id;
```

### Alert Threshold
```python
# Alert if failure rate > 5%
failure_rate = failed_count / total_count
if failure_rate > 0.05:
    send_alert(f"High failure rate: {failure_rate:.2%}")
```

---

** Full Documentation**: [Fallback Values System](Fallback_Values_System.md)  
** Version**: 1.0  
** Last Updated**: 2025-01-11
