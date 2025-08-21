export interface Track {
  id: number;
  file_path: string;
  file_name: string;
  file_size: number;
  file_extension: string;
  discovered_at: string;
  last_modified: string;
  analysis_status: string;
  is_active: boolean;
  metadata?: {
    title?: string;
    artist?: string;
    album?: string;
    album_artist?: string;
    year?: number;
    genre?: string;
    duration?: number;
    bpm?: number;
    key?: string;
    mood?: string;
    bitrate?: number;
    sample_rate?: number;
    channels?: number;
    file_format?: string;
    created_at?: string;
    updated_at?: string;
  };
  analysis?: {
    analysis_status?: string;
    analysis_date?: string;
    analysis_duration?: number;
    analysis_errors?: string;
    tempo?: number;
    key?: string;
    scale?: string;
    energy?: number;
    danceability?: number;
    loudness?: number;
    dynamic_complexity?: number;
    rhythm_confidence?: number;
    key_strength?: number;
    valence?: number;
    acousticness?: number;
    instrumentalness?: number;
    speechiness?: number;
    liveness?: number;
    analysis_quality_score?: number;
    confidence_threshold?: number;
    tensorflow_predictions?: {
      top_predictions?: Array<{
        tag: string;
        confidence: number;
        index: number;
      }>;
      genre_scores?: Record<string, number>;
      mood_scores?: Record<string, number>;
      dominant_genres?: Array<{
        genre: string;
        score: number;
      }>;
      dominant_moods?: Array<{
        mood: string;
        score: number;
      }>;
      emotion_dimensions?: {
        valence: number;
        arousal: number;
        energy_level: number;
      };
      model_used?: string;
      analysis_timestamp?: string;
      analysis_duration?: number;
    };
  };
}

export interface TracksResponse {
  total_count: number;
  returned_count: number;
  offset: number;
  limit: number;
  tracks: Track[];
}

export interface HealthResponse {
  status: string;
  database: string;
  background_discovery: boolean;
  essentia_version: string;
  tensorflow_algorithms: string[];
}

export interface DiscoveryStats {
  total_files: number;
  analyzed_files: number;
  unanalyzed_files: number;
  categories: {
    normal: number;
    long: number;
    very_long: number;
  };
}
