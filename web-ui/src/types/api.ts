export interface Track {
  id: number;
  file_path: string;
  file_name: string;
  file_size: number;
  file_extension: string;
  discovered_at: string;
  status?: string;
  is_analyzed: boolean;
  has_metadata: boolean;
  has_audio_analysis: boolean;
  is_active: boolean;
  title?: string;
  artist?: string;
  album?: string;
  track_number?: number;
  year?: number;
  genre?: string;
  duration?: number;
  bpm?: number;
  key?: string;
  bitrate?: number;
  sample_rate?: number;
  tempo?: number;
  key_analysis?: string;
  scale?: string;
  key_strength?: number;
  energy?: number;
  loudness?: number;
  analysis_timestamp?: string;
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
