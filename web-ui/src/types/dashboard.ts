import { HealthResponse } from './api';

export interface DashboardStats {
  total_files: number;
  analyzed_files: number;
  unanalyzed_files: number;
  files_with_metadata: number;
}

export interface Track {
  id: number;
  title?: string;
  artist?: string;
  file_name: string;
  file_extension?: string;
  duration?: number;
  tempo?: number;
  status?: string;
  analysis_status?: string;
}

export interface DiscoveryStatus {
  status: 'running' | 'completed' | 'failed' | 'idle';
  progress: number;
  message: string;
  discovered_count: number;
}

export interface AnalysisStatus {
  status: 'running' | 'completed' | 'failed' | 'idle';
  progress: number;
  message: string;
  completed_files: number;
}

export interface ModuleStatus {
  available: boolean;
  enabled: boolean;
  description?: string;
}

export interface AnalysisModulesStatus {
  modules: {
    essentia: ModuleStatus;
    tensorflow: ModuleStatus;
    faiss: ModuleStatus;
  };
}

export interface AnalysisConfig {
  config: {
    essentia: {
      algorithms: {
        enable_tensorflow: boolean;
        enable_faiss: boolean;
      };
    };
  };
}

// Use the existing HealthResponse type instead of creating a new one
export type HealthStatus = HealthResponse;

// Constants for the dashboard
export const REFRESH_INTERVALS = {
  HEALTH: 60000,
  TRACKS: 30000,
  DISCOVERY: 2000,
  ANALYSIS: 2000,
  MODULES: 30000,
  CONFIG: 60000,
} as const;

export const FORCE_ENRICH_LIMIT = 50;
export const TRACKS_LIMIT = 0; // 0 means no limit - get all tracks
export const RECENT_TRACKS_LIMIT = 10;
