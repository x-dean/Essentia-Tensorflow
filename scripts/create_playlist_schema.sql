-- Ultimate Playlist Generator Database Schema
-- This script creates a comprehensive schema structure for the playlist generation system

-- Create schemas for different functional areas
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS analysis;
CREATE SCHEMA IF NOT EXISTS playlists;
CREATE SCHEMA IF NOT EXISTS recommendations;
CREATE SCHEMA IF NOT EXISTS ui;

-- ========================================
-- CORE SCHEMA - Basic file and metadata
-- ========================================

-- Move existing files table to core schema
CREATE TABLE IF NOT EXISTS core.files (
    id SERIAL PRIMARY KEY,
    file_path TEXT UNIQUE NOT NULL,
    file_name TEXT NOT NULL,
    file_size BIGINT,
    file_extension TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Playlist generation fields
    is_favorite BOOLEAN DEFAULT FALSE,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    tags TEXT[] DEFAULT '{}',
    notes TEXT,
    is_hidden BOOLEAN DEFAULT FALSE,
    custom_metadata JSONB DEFAULT '{}'
);

-- Move existing audio_metadata table to core schema
CREATE TABLE IF NOT EXISTS core.audio_metadata (
    id SERIAL PRIMARY KEY,
    file_id INTEGER NOT NULL REFERENCES core.files(id) ON DELETE CASCADE,
    title TEXT,
    artist TEXT,
    album TEXT,
    year INTEGER,
    genre TEXT,
    duration FLOAT,
    bitrate INTEGER,
    sample_rate INTEGER,
    channels INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(file_id)
);

-- ========================================
-- ANALYSIS SCHEMA - Musical analysis data
-- ========================================

-- Move existing track_analysis_summary table to analysis schema
CREATE TABLE IF NOT EXISTS analysis.track_analysis_summary (
    id SERIAL PRIMARY KEY,
    file_id INTEGER NOT NULL REFERENCES core.files(id) ON DELETE CASCADE,
    
    -- Essentia analysis results
    bpm FLOAT,
    key TEXT,
    scale TEXT,
    energy FLOAT,
    danceability FLOAT,
    valence FLOAT,
    acousticness FLOAT,
    instrumentalness FLOAT,
    speechiness FLOAT,
    liveness FLOAT,
    
    -- TensorFlow analysis results
    tensorflow_bpm FLOAT,
    tensorflow_key TEXT,
    tensorflow_scale TEXT,
    tensorflow_energy FLOAT,
    tensorflow_danceability FLOAT,
    tensorflow_valence FLOAT,
    tensorflow_acousticness FLOAT,
    tensorflow_instrumentalness FLOAT,
    tensorflow_speechiness FLOAT,
    tensorflow_liveness FLOAT,
    
    -- Analysis metadata
    analysis_status TEXT DEFAULT 'pending',
    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    analysis_duration FLOAT,
    analysis_errors TEXT,
    
    -- Quality control for playlist generation
    analysis_quality_score FLOAT,
    confidence_threshold FLOAT DEFAULT 0.7,
    manual_override BOOLEAN DEFAULT FALSE,
    override_reason TEXT,
    
    UNIQUE(file_id)
);

-- ========================================
-- PLAYLISTS SCHEMA - Playlist management
-- ========================================

-- Move existing playlists table to playlists schema
CREATE TABLE IF NOT EXISTS playlists.playlists (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT TRUE,
    cover_image_url TEXT,
    
    -- Playlist statistics
    total_duration INTEGER DEFAULT 0, -- in seconds
    track_count INTEGER DEFAULT 0,
    rating_avg FLOAT DEFAULT 0.0,
    
    -- Generation metadata
    generation_type TEXT, -- "manual", "template", "smart", "similarity"
    generation_parameters JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Move existing playlist_tracks table to playlists schema
CREATE TABLE IF NOT EXISTS playlists.playlist_tracks (
    id SERIAL PRIMARY KEY,
    playlist_id INTEGER NOT NULL REFERENCES playlists.playlists(id) ON DELETE CASCADE,
    file_id INTEGER NOT NULL REFERENCES core.files(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    
    -- Track-specific data for playlist generation
    notes TEXT,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Generation metadata
    selection_reason TEXT, -- "manual", "template_match", "similarity", "recommendation"
    selection_score FLOAT, -- Confidence score for why this track was selected
    
    UNIQUE(playlist_id, position)
);

-- Move existing playlist_templates table to playlists schema
CREATE TABLE IF NOT EXISTS playlists.playlist_templates (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    template_type TEXT NOT NULL, -- energy, mood, genre, custom
    parameters JSONB NOT NULL, -- Template parameters
    is_system_template BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Generated playlists tracking table
CREATE TABLE IF NOT EXISTS playlists.generated_playlists (
    id SERIAL PRIMARY KEY,
    playlist_id INTEGER NOT NULL REFERENCES playlists.playlists(id) ON DELETE CASCADE,
    template_id INTEGER NOT NULL REFERENCES playlists.playlist_templates(id),
    generation_parameters JSONB NOT NULL,
    generation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    generation_duration FLOAT,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    
    -- Generation quality metrics
    quality_score FLOAT, -- How well the generation matched criteria
    user_feedback INTEGER CHECK (user_feedback >= 1 AND user_feedback <= 5),
    regeneration_count INTEGER DEFAULT 0 -- How many times regenerated
);

-- ========================================
-- RECOMMENDATIONS SCHEMA - Similarity and recommendations
-- ========================================

-- Move existing track_similarity_cache table to recommendations schema
CREATE TABLE IF NOT EXISTS recommendations.track_similarity_cache (
    id SERIAL PRIMARY KEY,
    source_file_id INTEGER NOT NULL REFERENCES core.files(id) ON DELETE CASCADE,
    target_file_id INTEGER NOT NULL REFERENCES core.files(id) ON DELETE CASCADE,
    similarity_score FLOAT NOT NULL,
    similarity_type TEXT NOT NULL, -- essentia, tensorflow, combined
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(source_file_id, target_file_id, similarity_type)
);

-- Playlist recommendations table
CREATE TABLE IF NOT EXISTS recommendations.playlist_recommendations (
    id SERIAL PRIMARY KEY,
    playlist_id INTEGER NOT NULL REFERENCES playlists.playlists(id) ON DELETE CASCADE,
    recommended_file_id INTEGER NOT NULL REFERENCES core.files(id) ON DELETE CASCADE,
    recommendation_score FLOAT NOT NULL,
    recommendation_reason TEXT, -- "similar_to_track_1", "fits_energy_profile", etc.
    recommendation_type TEXT, -- "similarity", "template_match", "collaborative"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- UI SCHEMA - User interface state and preferences
-- ========================================

-- UI state persistence table
CREATE TABLE IF NOT EXISTS ui.ui_state (
    id SERIAL PRIMARY KEY,
    session_id TEXT UNIQUE NOT NULL,
    state_data JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Application preferences table
CREATE TABLE IF NOT EXISTS ui.app_preferences (
    id SERIAL PRIMARY KEY,
    key TEXT UNIQUE NOT NULL,
    value JSONB NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- INDEXES FOR PERFORMANCE
-- ========================================

-- Core schema indexes
CREATE INDEX IF NOT EXISTS idx_core_files_path ON core.files(file_path);
CREATE INDEX IF NOT EXISTS idx_core_files_favorite ON core.files(is_favorite) WHERE is_favorite = TRUE;
CREATE INDEX IF NOT EXISTS idx_core_files_rating ON core.files(rating) WHERE rating IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_core_files_hidden ON core.files(is_hidden) WHERE is_hidden = FALSE;

-- Analysis schema indexes
CREATE INDEX IF NOT EXISTS idx_analysis_status ON analysis.track_analysis_summary(analysis_status);
CREATE INDEX IF NOT EXISTS idx_analysis_quality ON analysis.track_analysis_summary(analysis_quality_score) WHERE analysis_quality_score IS NOT NULL;

-- Playlists schema indexes
CREATE INDEX IF NOT EXISTS idx_playlists_public ON playlists.playlists(is_public) WHERE is_public = TRUE;
CREATE INDEX IF NOT EXISTS idx_playlists_generation_type ON playlists.playlists(generation_type);
CREATE INDEX IF NOT EXISTS idx_playlist_tracks_position ON playlists.playlist_tracks(playlist_id, position);
CREATE INDEX IF NOT EXISTS idx_playlist_tracks_file ON playlists.playlist_tracks(file_id);
CREATE INDEX IF NOT EXISTS idx_generated_playlists_date ON playlists.generated_playlists(generation_date);
CREATE INDEX IF NOT EXISTS idx_generated_playlists_quality ON playlists.generated_playlists(quality_score) WHERE quality_score IS NOT NULL;

-- Recommendations schema indexes
CREATE INDEX IF NOT EXISTS idx_similarity_source ON recommendations.track_similarity_cache(source_file_id, similarity_score);
CREATE INDEX IF NOT EXISTS idx_similarity_target ON recommendations.track_similarity_cache(target_file_id, similarity_score);
CREATE INDEX IF NOT EXISTS idx_recommendations_playlist ON recommendations.playlist_recommendations(playlist_id, recommendation_score);
CREATE INDEX IF NOT EXISTS idx_recommendations_type ON recommendations.playlist_recommendations(recommendation_type);

-- UI schema indexes
CREATE INDEX IF NOT EXISTS idx_ui_state_session ON ui.ui_state(session_id);
CREATE INDEX IF NOT EXISTS idx_app_preferences_key ON ui.app_preferences(key);

-- ========================================
-- VIEWS FOR COMMON QUERIES
-- ========================================

-- View for tracks with complete information
CREATE OR REPLACE VIEW core.tracks_with_metadata AS
SELECT 
    f.id,
    f.file_path,
    f.file_name,
    f.is_favorite,
    f.rating,
    f.tags,
    f.notes,
    am.title,
    am.artist,
    am.album,
    am.genre,
    am.duration,
    tas.bpm,
    tas.energy,
    tas.danceability,
    tas.valence,
    tas.analysis_quality_score
FROM core.files f
LEFT JOIN core.audio_metadata am ON f.id = am.file_id
LEFT JOIN analysis.track_analysis_summary tas ON f.id = tas.file_id
WHERE f.is_active = TRUE AND f.is_hidden = FALSE;

-- View for playlist statistics
CREATE OR REPLACE VIEW playlists.playlist_stats AS
SELECT 
    p.id,
    p.name,
    p.track_count,
    p.total_duration,
    p.rating_avg,
    p.generation_type,
    COUNT(pt.id) as actual_track_count,
    COALESCE(SUM(am.duration), 0) as actual_duration,
    COALESCE(AVG(pt.rating), 0) as actual_rating_avg
FROM playlists.playlists p
LEFT JOIN playlists.playlist_tracks pt ON p.id = pt.playlist_id
LEFT JOIN core.audio_metadata am ON pt.file_id = am.file_id
GROUP BY p.id, p.name, p.track_count, p.total_duration, p.rating_avg, p.generation_type;

-- ========================================
-- FUNCTIONS FOR COMMON OPERATIONS
-- ========================================

-- Function to update playlist statistics
CREATE OR REPLACE FUNCTION playlists.update_playlist_stats(playlist_id INTEGER)
RETURNS VOID AS $$
BEGIN
    UPDATE playlists.playlists 
    SET 
        track_count = (
            SELECT COUNT(*) 
            FROM playlists.playlist_tracks 
            WHERE playlist_id = $1
        ),
        total_duration = (
            SELECT COALESCE(SUM(am.duration), 0)
            FROM playlists.playlist_tracks pt
            JOIN core.audio_metadata am ON pt.file_id = am.file_id
            WHERE pt.playlist_id = $1
        ),
        rating_avg = (
            SELECT COALESCE(AVG(pt.rating), 0)
            FROM playlists.playlist_tracks pt
            WHERE pt.playlist_id = $1 AND pt.rating IS NOT NULL
        ),
        updated_at = CURRENT_TIMESTAMP
    WHERE id = $1;
END;
$$ LANGUAGE plpgsql;

-- Function to get similar tracks
CREATE OR REPLACE FUNCTION recommendations.get_similar_tracks(
    file_id INTEGER, 
    similarity_type TEXT DEFAULT 'combined',
    limit_count INTEGER DEFAULT 10
)
RETURNS TABLE(
    target_file_id INTEGER,
    similarity_score FLOAT,
    title TEXT,
    artist TEXT,
    album TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        tsc.target_file_id,
        tsc.similarity_score,
        am.title,
        am.artist,
        am.album
    FROM recommendations.track_similarity_cache tsc
    JOIN core.audio_metadata am ON tsc.target_file_id = am.file_id
    WHERE tsc.source_file_id = $1 
    AND tsc.similarity_type = $2
    ORDER BY tsc.similarity_score DESC
    LIMIT $3;
END;
$$ LANGUAGE plpgsql;
