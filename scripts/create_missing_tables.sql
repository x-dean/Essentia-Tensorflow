-- Create missing tables for the ultimate playlist generator

-- Generated Playlists table
CREATE TABLE IF NOT EXISTS generated_playlists (
    id SERIAL PRIMARY KEY,
    playlist_id INTEGER NOT NULL REFERENCES playlists(id),
    template_id INTEGER NOT NULL REFERENCES playlist_templates(id),
    generation_parameters JSONB NOT NULL,
    generation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    generation_duration FLOAT,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    quality_score FLOAT,
    user_feedback INTEGER,
    regeneration_count INTEGER DEFAULT 0
);

-- Playlist Recommendations table
CREATE TABLE IF NOT EXISTS playlist_recommendations (
    id SERIAL PRIMARY KEY,
    playlist_id INTEGER NOT NULL REFERENCES playlists(id),
    recommended_file_id INTEGER NOT NULL REFERENCES files(id),
    recommendation_score FLOAT NOT NULL,
    recommendation_reason TEXT,
    recommendation_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- UI State table
CREATE TABLE IF NOT EXISTS ui_state (
    id SERIAL PRIMARY KEY,
    session_id TEXT UNIQUE NOT NULL,
    state_data JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- App Preferences table
CREATE TABLE IF NOT EXISTS app_preferences (
    id SERIAL PRIMARY KEY,
    key TEXT UNIQUE NOT NULL,
    value JSONB NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for the new tables
CREATE INDEX IF NOT EXISTS idx_generated_playlists_playlist ON generated_playlists(playlist_id);
CREATE INDEX IF NOT EXISTS idx_generated_playlists_template ON generated_playlists(template_id);
CREATE INDEX IF NOT EXISTS idx_generated_playlists_date ON generated_playlists(generation_date);

CREATE INDEX IF NOT EXISTS idx_playlist_recommendations_playlist ON playlist_recommendations(playlist_id, recommendation_score);
CREATE INDEX IF NOT EXISTS idx_playlist_recommendations_file ON playlist_recommendations(recommended_file_id);

CREATE INDEX IF NOT EXISTS idx_ui_state_session ON ui_state(session_id);
CREATE INDEX IF NOT EXISTS idx_app_preferences_key ON app_preferences(key);
