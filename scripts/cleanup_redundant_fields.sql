-- Cleanup redundant and unused fields from track_analysis_summary
-- This removes fields that are either redundant or not actually used

-- Remove redundant fields (these are duplicated in tensorflow_* fields)
ALTER TABLE analysis.track_analysis_summary DROP COLUMN IF EXISTS valence;
ALTER TABLE analysis.track_analysis_summary DROP COLUMN IF EXISTS acousticness;
ALTER TABLE analysis.track_analysis_summary DROP COLUMN IF EXISTS instrumentalness;
ALTER TABLE analysis.track_analysis_summary DROP COLUMN IF EXISTS speechiness;
ALTER TABLE analysis.track_analysis_summary DROP COLUMN IF EXISTS liveness;

-- Remove TensorFlow fields that don't actually exist in TensorFlow output
ALTER TABLE analysis.track_analysis_summary DROP COLUMN IF EXISTS tensorflow_bpm;
ALTER TABLE analysis.track_analysis_summary DROP COLUMN IF EXISTS tensorflow_key;
ALTER TABLE analysis.track_analysis_summary DROP COLUMN IF EXISTS tensorflow_scale;
ALTER TABLE analysis.track_analysis_summary DROP COLUMN IF EXISTS tensorflow_energy;
ALTER TABLE analysis.track_analysis_summary DROP COLUMN IF EXISTS tensorflow_danceability;

-- Add comment to document the cleaned schema
COMMENT ON TABLE analysis.track_analysis_summary IS 'Cleaned schema with only relevant fields:
- Essentia fields: bpm, key, scale, energy, danceability, loudness, dynamic_complexity, rhythm_confidence, key_strength
- TensorFlow fields: tensorflow_valence, tensorflow_acousticness, tensorflow_instrumentalness, tensorflow_speechiness, tensorflow_liveness
- Metadata fields: analysis_status, analysis_date, analysis_duration, analysis_errors, analysis_quality_score, confidence_threshold, manual_override, override_reason';

-- Verify the cleaned schema
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_schema = 'analysis' 
AND table_name = 'track_analysis_summary' 
ORDER BY ordinal_position;
