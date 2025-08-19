-- Migration script to clean up duplicate tables and use organized schemas
-- This script removes old tables from public schema and ensures proper schema usage

-- ========================================
-- STEP 1: Backup existing data (if any)
-- ========================================

-- Create backup tables in case we need to restore data
CREATE TABLE IF NOT EXISTS backup_files AS SELECT * FROM public.files;
CREATE TABLE IF NOT EXISTS backup_audio_metadata AS SELECT * FROM public.audio_metadata;
CREATE TABLE IF NOT EXISTS backup_track_analysis_summary AS SELECT * FROM public.track_analysis_summary;
CREATE TABLE IF NOT EXISTS backup_playlists AS SELECT * FROM public.playlists;
CREATE TABLE IF NOT EXISTS backup_playlist_tracks AS SELECT * FROM public.playlist_tracks;
CREATE TABLE IF NOT EXISTS backup_playlist_templates AS SELECT * FROM public.playlist_templates;
CREATE TABLE IF NOT EXISTS backup_track_similarity_cache AS SELECT * FROM public.track_similarity_cache;

-- ========================================
-- STEP 2: Migrate data from public to organized schemas
-- ========================================

-- Migrate files data (only if core.files is empty)
INSERT INTO core.files (id, file_path, file_name, file_size, file_extension, is_active, created_at, updated_at, is_favorite, rating, tags, notes, is_hidden, custom_metadata)
SELECT id, file_path, file_name, file_size, file_extension, is_active, created_at, updated_at, 
       COALESCE(is_favorite, FALSE), rating, COALESCE(tags, '{}'), notes, COALESCE(is_hidden, FALSE), COALESCE(custom_metadata, '{}')
FROM public.files
WHERE NOT EXISTS (SELECT 1 FROM core.files WHERE core.files.id = public.files.id);

-- Migrate audio_metadata data
INSERT INTO core.audio_metadata (id, file_id, title, artist, album, year, genre, duration, bitrate, sample_rate, channels, created_at, updated_at)
SELECT id, file_id, title, artist, album, year, genre, duration, bitrate, sample_rate, channels, created_at, updated_at
FROM public.audio_metadata
WHERE NOT EXISTS (SELECT 1 FROM core.audio_metadata WHERE core.audio_metadata.file_id = public.audio_metadata.file_id);

-- Migrate track_analysis_summary data
INSERT INTO analysis.track_analysis_summary (
    id, file_id, bpm, key, scale, energy, danceability, valence, acousticness, instrumentalness, speechiness, liveness,
    tensorflow_bpm, tensorflow_key, tensorflow_scale, tensorflow_energy, tensorflow_danceability, tensorflow_valence,
    tensorflow_acousticness, tensorflow_instrumentalness, tensorflow_speechiness, tensorflow_liveness,
    analysis_status, analysis_date, analysis_duration, analysis_errors,
    analysis_quality_score, confidence_threshold, manual_override, override_reason
)
SELECT id, file_id, bpm, key, scale, energy, danceability, valence, acousticness, instrumentalness, speechiness, liveness,
       tensorflow_bpm, tensorflow_key, tensorflow_scale, tensorflow_energy, tensorflow_danceability, tensorflow_valence,
       tensorflow_acousticness, tensorflow_instrumentalness, tensorflow_speechiness, tensorflow_liveness,
       COALESCE(analysis_status, 'pending'), analysis_date, analysis_duration, analysis_errors,
       analysis_quality_score, COALESCE(confidence_threshold, 0.7), COALESCE(manual_override, FALSE), override_reason
FROM public.track_analysis_summary
WHERE NOT EXISTS (SELECT 1 FROM analysis.track_analysis_summary WHERE analysis.track_analysis_summary.file_id = public.track_analysis_summary.file_id);

-- Migrate playlists data
INSERT INTO playlists.playlists (id, name, description, is_public, cover_image_url, total_duration, track_count, rating_avg, generation_type, generation_parameters, created_at, updated_at)
SELECT id, name, description, COALESCE(is_public, TRUE), cover_image_url, 
       COALESCE(total_duration, 0), COALESCE(track_count, 0), COALESCE(rating_avg, 0.0),
       COALESCE(generation_type, 'manual'), COALESCE(generation_parameters, '{}'), created_at, updated_at
FROM public.playlists
WHERE NOT EXISTS (SELECT 1 FROM playlists.playlists WHERE playlists.playlists.id = public.playlists.id);

-- Migrate playlist_tracks data
INSERT INTO playlists.playlist_tracks (id, playlist_id, file_id, position, notes, rating, added_at, selection_reason, selection_score)
SELECT id, playlist_id, file_id, position, notes, rating, added_at, 
       COALESCE(selection_reason, 'manual'), selection_score
FROM public.playlist_tracks
WHERE NOT EXISTS (SELECT 1 FROM playlists.playlist_tracks WHERE playlists.playlist_tracks.id = public.playlist_tracks.id);

-- Migrate playlist_templates data
INSERT INTO playlists.playlist_templates (id, name, description, template_type, parameters, is_system_template, is_active, created_at, updated_at)
SELECT id, name, description, template_type, parameters, 
       COALESCE(is_system_template, FALSE), COALESCE(is_active, TRUE), created_at, updated_at
FROM public.playlist_templates
WHERE NOT EXISTS (SELECT 1 FROM playlists.playlist_templates WHERE playlists.playlist_templates.id = public.playlist_templates.id);

-- Migrate track_similarity_cache data
INSERT INTO recommendations.track_similarity_cache (id, source_file_id, target_file_id, similarity_score, similarity_type, created_at)
SELECT id, source_file_id, target_file_id, similarity_score, 
       COALESCE(similarity_type, 'combined'), created_at
FROM public.track_similarity_cache
WHERE NOT EXISTS (
    SELECT 1 FROM recommendations.track_similarity_cache 
    WHERE recommendations.track_similarity_cache.source_file_id = public.track_similarity_cache.source_file_id
    AND recommendations.track_similarity_cache.target_file_id = public.track_similarity_cache.target_file_id
    AND recommendations.track_similarity_cache.similarity_type = COALESCE(public.track_similarity_cache.similarity_type, 'combined')
);

-- ========================================
-- STEP 3: Update sequences to match migrated data
-- ========================================

-- Update sequences to avoid conflicts
SELECT setval('core.files_id_seq', COALESCE((SELECT MAX(id) FROM core.files), 1));
SELECT setval('core.audio_metadata_id_seq', COALESCE((SELECT MAX(id) FROM core.audio_metadata), 1));
SELECT setval('analysis.track_analysis_summary_id_seq', COALESCE((SELECT MAX(id) FROM analysis.track_analysis_summary), 1));
SELECT setval('playlists.playlists_id_seq', COALESCE((SELECT MAX(id) FROM playlists.playlists), 1));
SELECT setval('playlists.playlist_tracks_id_seq', COALESCE((SELECT MAX(id) FROM playlists.playlist_tracks), 1));
SELECT setval('playlists.playlist_templates_id_seq', COALESCE((SELECT MAX(id) FROM playlists.playlist_templates), 1));
SELECT setval('recommendations.track_similarity_cache_id_seq', COALESCE((SELECT MAX(id) FROM recommendations.track_similarity_cache), 1));

-- ========================================
-- STEP 4: Drop old tables from public schema
-- ========================================

-- Drop old tables (only after successful migration)
DROP TABLE IF EXISTS public.track_similarity_cache CASCADE;
DROP TABLE IF EXISTS public.playlist_templates CASCADE;
DROP TABLE IF EXISTS public.playlist_tracks CASCADE;
DROP TABLE IF EXISTS public.playlists CASCADE;
DROP TABLE IF EXISTS public.track_analysis_summary CASCADE;
DROP TABLE IF EXISTS public.audio_metadata CASCADE;
DROP TABLE IF EXISTS public.files CASCADE;

-- ========================================
-- STEP 5: Create schema-specific permissions
-- ========================================

-- Grant permissions to playlist_user for all schemas
GRANT USAGE ON SCHEMA core TO playlist_user;
GRANT USAGE ON SCHEMA analysis TO playlist_user;
GRANT USAGE ON SCHEMA playlists TO playlist_user;
GRANT USAGE ON SCHEMA recommendations TO playlist_user;
GRANT USAGE ON SCHEMA ui TO playlist_user;

-- Grant permissions on all tables in each schema
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA core TO playlist_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA analysis TO playlist_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA playlists TO playlist_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA recommendations TO playlist_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA ui TO playlist_user;

-- Grant permissions on sequences
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA core TO playlist_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analysis TO playlist_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA playlists TO playlist_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA recommendations TO playlist_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA ui TO playlist_user;

-- Grant permissions on views
GRANT SELECT ON ALL TABLES IN SCHEMA core TO playlist_user;
GRANT SELECT ON ALL TABLES IN SCHEMA playlists TO playlist_user;

-- ========================================
-- STEP 6: Verification
-- ========================================

-- Verify migration was successful
DO $$
DECLARE
    core_files_count INTEGER;
    analysis_tracks_count INTEGER;
    playlists_count INTEGER;
    recommendations_count INTEGER;
    ui_count INTEGER;
BEGIN
    -- Count tables in each schema
    SELECT COUNT(*) INTO core_files_count FROM core.files;
    SELECT COUNT(*) INTO analysis_tracks_count FROM analysis.track_analysis_summary;
    SELECT COUNT(*) INTO playlists_count FROM playlists.playlists;
    SELECT COUNT(*) INTO recommendations_count FROM recommendations.track_similarity_cache;
    SELECT COUNT(*) INTO ui_count FROM ui.app_preferences;
    
    -- Log results
    RAISE NOTICE 'Migration verification:';
    RAISE NOTICE 'Core files: %', core_files_count;
    RAISE NOTICE 'Analysis tracks: %', analysis_tracks_count;
    RAISE NOTICE 'Playlists: %', playlists_count;
    RAISE NOTICE 'Similarity cache: %', recommendations_count;
    RAISE NOTICE 'UI preferences: %', ui_count;
    
    -- Verify no old tables exist
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('files', 'audio_metadata', 'track_analysis_summary', 'playlists', 'playlist_tracks', 'playlist_templates', 'track_similarity_cache')) THEN
        RAISE WARNING 'Old tables still exist in public schema!';
    ELSE
        RAISE NOTICE 'Old tables successfully removed from public schema';
    END IF;
END $$;
