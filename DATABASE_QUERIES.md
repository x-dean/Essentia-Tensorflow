# Database Queries Reference

This document contains useful SQL queries for the Essentia-TensorFlow Playlist Generation System.

## Table of Contents
- [Schema Overview](#schema-overview)
- [File Discovery Queries](#file-discovery-queries)
- [Analysis Status Queries](#analysis-status-queries)
- [Playlist Generation Queries](#playlist-generation-queries)
- [Recommendation Queries](#recommendation-queries)
- [Data Quality Queries](#data-quality-queries)
- [Performance Queries](#performance-queries)

## Schema Overview

### Core Tables
- `core.files` - Main file registry
- `core.audio_metadata` - Basic metadata from tags
- `core.discovery_cache` - File discovery cache

### Analysis Tables
- `analysis.track_analysis_summary` - Combined analysis results
- `analysis.essentia_analysis_results` - Detailed Essentia analysis
- `analysis.tensorflow_analysis_results` - Detailed TensorFlow analysis
- `analysis.faiss_analysis_results` - FAISS vector analysis
- `analysis.essentia_analysis_status` - Essentia processing status
- `analysis.tensorflow_analysis_status` - TensorFlow processing status
- `analysis.faiss_analysis_status` - FAISS processing status

### Playlist Tables
- `playlists.playlists` - Generated playlists
- `playlists.playlist_tracks` - Tracks in playlists
- `playlists.playlist_templates` - Playlist generation templates
- `playlists.generated_playlists` - Playlist generation history

### Recommendation Tables
- `recommendations.track_similarity_cache` - Cached similarity scores
- `recommendations.playlist_recommendations` - Track recommendations
- `recommendations.faiss_index_metadata` - FAISS index information

### UI Tables
- `ui.ui_state` - UI state persistence
- `ui.app_preferences` - Application preferences

---

## File Discovery Queries

### Get All Active Files
```sql
SELECT 
    f.id,
    f.file_name,
    f.file_path,
    f.file_size,
    f.file_extension,
    f.is_active,
    f.discovered_at,
    f.has_metadata
FROM core.files f
WHERE f.is_active = true
ORDER BY f.discovered_at DESC;
```

### Get Files with Metadata
```sql
SELECT 
    f.id,
    f.file_name,
    am.title,
    am.artist,
    am.album,
    am.genre,
    am.duration,
    am.bpm,
    am.key
FROM core.files f
JOIN core.audio_metadata am ON f.id = am.file_id
WHERE f.has_metadata = true
ORDER BY am.artist, am.album, am.title;
```

### Get Files by Genre
```sql
SELECT 
    am.genre,
    COUNT(*) as track_count,
    AVG(am.duration) as avg_duration,
    AVG(am.bpm) as avg_bpm
FROM core.audio_metadata am
WHERE am.genre IS NOT NULL
GROUP BY am.genre
ORDER BY track_count DESC;
```

### Get Recently Discovered Files
```sql
SELECT 
    f.file_name,
    f.discovered_at,
    f.file_size,
    f.has_metadata
FROM core.files f
WHERE f.discovered_at >= NOW() - INTERVAL '24 hours'
ORDER BY f.discovered_at DESC;
```

---

## Analysis Status Queries

### Get Analysis Status Overview
```sql
SELECT 
    'Essentia' as analyzer,
    COUNT(*) as total_files,
    COUNT(CASE WHEN status = 'analyzed' THEN 1 END) as analyzed,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending
FROM analysis.essentia_analysis_status
UNION ALL
SELECT 
    'TensorFlow' as analyzer,
    COUNT(*) as total_files,
    COUNT(CASE WHEN status = 'analyzed' THEN 1 END) as analyzed,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending
FROM analysis.tensorflow_analysis_status
UNION ALL
SELECT 
    'FAISS' as analyzer,
    COUNT(*) as total_files,
    COUNT(CASE WHEN status = 'analyzed' THEN 1 END) as analyzed,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending
FROM analysis.faiss_analysis_status;
```

### Get Failed Analysis
```sql
SELECT 
    f.file_name,
    eas.status as essentia_status,
    eas.error_message as essentia_error,
    tas.status as tensorflow_status,
    tas.error_message as tensorflow_error,
    fas.status as faiss_status,
    fas.error_message as faiss_error
FROM core.files f
LEFT JOIN analysis.essentia_analysis_status eas ON f.id = eas.file_id
LEFT JOIN analysis.tensorflow_analysis_status tas ON f.id = tas.file_id
LEFT JOIN analysis.faiss_analysis_status fas ON f.id = fas.file_id
WHERE eas.status = 'failed' OR tas.status = 'failed' OR fas.status = 'failed';
```

### Get Analysis Progress
```sql
SELECT 
    f.file_name,
    eas.completed_at as essentia_completed,
    tas.completed_at as tensorflow_completed,
    fas.completed_at as faiss_completed,
    CASE 
        WHEN eas.status = 'analyzed' AND tas.status = 'analyzed' AND fas.status = 'analyzed' 
        THEN 'Complete'
        ELSE 'Incomplete'
    END as overall_status
FROM core.files f
LEFT JOIN analysis.essentia_analysis_status eas ON f.id = eas.file_id
LEFT JOIN analysis.tensorflow_analysis_status tas ON f.id = tas.file_id
LEFT JOIN analysis.faiss_analysis_status fas ON f.id = fas.file_id
ORDER BY overall_status, f.file_name;
```

---

## Playlist Generation Queries

### Get All Playlists
```sql
SELECT 
    p.id,
    p.name,
    p.description,
    p.generation_type,
    p.track_count,
    p.total_duration,
    p.rating_avg,
    p.created_at
FROM playlists.playlists p
ORDER BY p.created_at DESC;
```

### Get Playlist Tracks with Analysis
```sql
SELECT 
    p.name as playlist_name,
    pt.position,
    am.title,
    am.artist,
    am.album,
    tas.energy,
    tas.danceability,
    tas.tensorflow_valence,
    tas.tensorflow_acousticness,
    pt.selection_reason,
    pt.selection_score
FROM playlists.playlists p
JOIN playlists.playlist_tracks pt ON p.id = pt.playlist_id
JOIN core.files f ON pt.file_id = f.id
JOIN core.audio_metadata am ON f.id = am.file_id
LEFT JOIN analysis.track_analysis_summary tas ON f.id = tas.file_id
WHERE p.id = 1  -- Replace with playlist ID
ORDER BY pt.position;
```

### Get Playlist Statistics
```sql
SELECT 
    p.name,
    COUNT(pt.id) as track_count,
    AVG(tas.energy) as avg_energy,
    AVG(tas.danceability) as avg_danceability,
    AVG(tas.tensorflow_valence) as avg_valence,
    AVG(tas.tensorflow_acousticness) as avg_acousticness,
    AVG(am.duration) as avg_duration,
    SUM(am.duration) as total_duration
FROM playlists.playlists p
JOIN playlists.playlist_tracks pt ON p.id = pt.playlist_id
JOIN core.audio_metadata am ON pt.file_id = am.file_id
LEFT JOIN analysis.track_analysis_summary tas ON pt.file_id = tas.file_id
GROUP BY p.id, p.name
ORDER BY p.created_at DESC;
```

### Get Playlist Templates
```sql
SELECT 
    pt.id,
    pt.name,
    pt.description,
    pt.template_type,
    pt.parameters,
    pt.is_system_template,
    pt.is_active
FROM playlists.playlist_templates pt
ORDER BY pt.is_system_template DESC, pt.name;
```

---

## Recommendation Queries

### Get Similar Tracks
```sql
SELECT 
    f1.file_name as source_track,
    f2.file_name as similar_track,
    tsc.similarity_score,
    tsc.similarity_type,
    am1.artist as source_artist,
    am2.artist as similar_artist
FROM recommendations.track_similarity_cache tsc
JOIN core.files f1 ON tsc.source_file_id = f1.id
JOIN core.files f2 ON tsc.target_file_id = f2.id
JOIN core.audio_metadata am1 ON f1.id = am1.file_id
JOIN core.audio_metadata am2 ON f2.id = am2.file_id
WHERE tsc.source_file_id = 1  -- Replace with source file ID
ORDER BY tsc.similarity_score DESC
LIMIT 10;
```

### Get Track Recommendations for Playlist
```sql
SELECT 
    f.file_name,
    am.artist,
    am.album,
    pr.recommendation_score,
    pr.recommendation_reason,
    pr.recommendation_type,
    tas.energy,
    tas.danceability,
    tas.tensorflow_valence
FROM recommendations.playlist_recommendations pr
JOIN core.files f ON pr.recommended_file_id = f.id
JOIN core.audio_metadata am ON f.id = am.file_id
LEFT JOIN analysis.track_analysis_summary tas ON f.id = tas.file_id
WHERE pr.playlist_id = 1  -- Replace with playlist ID
ORDER BY pr.recommendation_score DESC;
```

### Get FAISS Index Information
```sql
SELECT 
    index_name,
    index_type,
    dimension,
    total_vectors,
    is_trained,
    index_size_bytes,
    created_at,
    updated_at
FROM recommendations.faiss_index_metadata
ORDER BY created_at DESC;
```

---

## Data Quality Queries

### Check for Missing Analysis
```sql
SELECT 
    f.file_name,
    CASE WHEN eas.status IS NULL THEN 'Missing' ELSE eas.status END as essentia_status,
    CASE WHEN tas.status IS NULL THEN 'Missing' ELSE tas.status END as tensorflow_status,
    CASE WHEN fas.status IS NULL THEN 'Missing' ELSE fas.status END as faiss_status
FROM core.files f
LEFT JOIN analysis.essentia_analysis_status eas ON f.id = eas.file_id
LEFT JOIN analysis.tensorflow_analysis_status tas ON f.id = tas.file_id
LEFT JOIN analysis.faiss_analysis_status fas ON f.id = fas.file_id
WHERE eas.status IS NULL OR tas.status IS NULL OR fas.status IS NULL;
```

### Check for Inconsistent Data
```sql
SELECT 
    f.file_name,
    tas.bpm as analysis_bpm,
    am.bpm as metadata_bpm,
    ABS(tas.bpm - am.bpm) as bpm_difference
FROM core.files f
JOIN core.audio_metadata am ON f.id = am.file_id
JOIN analysis.track_analysis_summary tas ON f.id = tas.file_id
WHERE am.bpm IS NOT NULL 
  AND tas.bpm IS NOT NULL 
  AND ABS(tas.bpm - am.bpm) > 5;
```

### Get Analysis Quality Metrics
```sql
SELECT 
    COUNT(*) as total_files,
    COUNT(CASE WHEN tas.analysis_quality_score >= 0.8 THEN 1 END) as high_quality,
    COUNT(CASE WHEN tas.analysis_quality_score >= 0.6 AND tas.analysis_quality_score < 0.8 THEN 1 END) as medium_quality,
    COUNT(CASE WHEN tas.analysis_quality_score < 0.6 THEN 1 END) as low_quality,
    AVG(tas.analysis_quality_score) as avg_quality_score
FROM analysis.track_analysis_summary tas
WHERE tas.analysis_quality_score IS NOT NULL;
```

---

## Performance Queries

### Get Analysis Duration Statistics
```sql
SELECT 
    'Essentia' as analyzer,
    COUNT(*) as total_analyses,
    AVG(analysis_duration) as avg_duration,
    MAX(analysis_duration) as max_duration,
    MIN(analysis_duration) as min_duration
FROM analysis.essentia_analysis_results
UNION ALL
SELECT 
    'TensorFlow' as analyzer,
    COUNT(*) as total_analyses,
    AVG(analysis_duration) as avg_duration,
    MAX(analysis_duration) as max_duration,
    MIN(analysis_duration) as min_duration
FROM analysis.tensorflow_analysis_results
UNION ALL
SELECT 
    'FAISS' as analyzer,
    COUNT(*) as total_analyses,
    AVG(analysis_duration) as avg_duration,
    MAX(analysis_duration) as max_duration,
    MIN(analysis_duration) as min_duration
FROM analysis.faiss_analysis_results;
```

### Get Database Size Information
```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname IN ('core', 'analysis', 'playlists', 'recommendations', 'ui')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Get Index Usage Statistics
```sql
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes 
WHERE schemaname IN ('core', 'analysis', 'playlists', 'recommendations', 'ui')
ORDER BY idx_scan DESC;
```

---

## Utility Queries

### Backup Database Schema
```sql
-- Export schema only
pg_dump -h localhost -U playlist_user -d playlist_db --schema-only > schema_backup.sql

-- Export data only
pg_dump -h localhost -U playlist_user -d playlist_db --data-only > data_backup.sql

-- Export everything
pg_dump -h localhost -U playlist_user -d playlist_db > full_backup.sql
```

### Reset Database
```bash
# Using the CLI tool
docker exec playlist-app python scripts/master_cli.py database reset --confirm
```

### Check Database Health
```sql
-- Check for orphaned records
SELECT COUNT(*) as orphaned_metadata
FROM core.audio_metadata am
LEFT JOIN core.files f ON am.file_id = f.id
WHERE f.id IS NULL;

-- Check for duplicate files
SELECT file_hash, COUNT(*) as duplicate_count
FROM core.files
WHERE file_hash IS NOT NULL
GROUP BY file_hash
HAVING COUNT(*) > 1;
```

---

## Notes

- Replace placeholder values (like playlist ID = 1) with actual values
- All timestamps are in UTC
- File paths are relative to the container's `/music` directory
- Analysis scores are typically between 0 and 1
- Duration is stored in seconds
- File sizes are in bytes

For more complex queries or custom analysis, consider creating database views or stored procedures.
