-- Cleanup redundant fields from audio_metadata table
-- Remove fields that are better provided by TensorFlow analysis

-- Remove redundant fields (these are better provided by TensorFlow)
ALTER TABLE core.audio_metadata DROP COLUMN IF EXISTS valence;
ALTER TABLE core.audio_metadata DROP COLUMN IF EXISTS energy;
ALTER TABLE core.audio_metadata DROP COLUMN IF EXISTS danceability;

-- Add comment to document the cleaned schema
COMMENT ON TABLE core.audio_metadata IS 'Cleaned schema with only essential metadata fields:
- Basic metadata: title, artist, album, album_artist, year, genre, duration, bpm, key
- Technical metadata: bitrate, sample_rate, channels, file_format
- Mood: mood (basic mood from tags)
- Timestamps: created_at, updated_at

Note: valence, energy, danceability are now provided by TensorFlow analysis in track_analysis_summary';

-- Verify the cleaned schema
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_schema = 'core' 
AND table_name = 'audio_metadata' 
ORDER BY ordinal_position;
