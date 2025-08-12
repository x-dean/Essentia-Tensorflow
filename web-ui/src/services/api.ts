import axios from 'axios';
import { TracksResponse, HealthResponse, DiscoveryStats } from '../types/api';

const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // Increased timeout to 60 seconds
});

// Add request interceptor for better error handling
api.interceptors.request.use(
  (config) => {
    // Add timestamp to prevent caching issues
    if (config.method === 'get') {
      config.params = { ...config.params, _t: Date.now() };
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor for better error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// Health check
export const getHealth = async (): Promise<HealthResponse> => {
  try {
    const response = await api.get('/health');
    return response.data;
  } catch (error) {
    console.error('Health check failed:', error);
    // Return a default unhealthy response
    return {
      status: 'unhealthy',
      database: 'disconnected',
      background_discovery: false,
      essentia_version: 'unknown',
      tensorflow_algorithms: []
    };
  }
};

// Tracks
export const getTracks = async (
  limit: number = 100,
  offset: number = 0,
  analyzedOnly: boolean = false,
  hasMetadata: boolean = false,
  format: string = 'summary'
): Promise<TracksResponse> => {
  try {
    const response = await api.get('/tracks/', {
      params: {
        limit,
        offset,
        analyzed_only: analyzedOnly,
        has_metadata: hasMetadata,
        format,
      },
    });
    return response.data;
  } catch (error) {
    console.error('Failed to fetch tracks:', error);
    // Return empty response on error
    return {
      total_count: 0,
      returned_count: 0,
      offset,
      limit,
      tracks: []
    };
  }
};

// Discovery
export const triggerDiscovery = async (): Promise<any> => {
  try {
    const response = await api.post('/discovery/trigger');
    return response.data;
  } catch (error) {
    console.error('Discovery trigger failed:', error);
    throw error;
  }
};

export const getDiscoveryStats = async (): Promise<DiscoveryStats> => {
  try {
    const response = await api.get('/discovery/stats');
    return response.data;
  } catch (error) {
    console.error('Failed to fetch discovery stats:', error);
    // Return default stats on error
    return {
      total_files: 0,
      analyzed_files: 0,
      unanalyzed_files: 0,
      categories: {
        normal: 0,
        long: 0,
        very_long: 0,
      }
    };
  }
};

// Analyzer
export const analyzeBatches = async (includeTensorflow: boolean = false): Promise<any> => {
  try {
    const response = await api.post('/analyzer/analyze-batches', null, {
      params: { include_tensorflow: includeTensorflow },
      timeout: 300000, // 5 minutes timeout for analysis
    });
    return response.data;
  } catch (error) {
    console.error('Analysis failed:', error);
    throw error;
  }
};

export const getAnalyzerStatistics = async (): Promise<any> => {
  try {
    const response = await api.get('/analyzer/statistics');
    return response.data;
  } catch (error) {
    console.error('Failed to fetch analyzer stats:', error);
    // Return default stats on error
    return {
      total_files: 0,
      analyzed_files: 0,
      unanalyzed_files: 0,
      processing_time: 0,
      files_per_second: 0
    };
  }
};

// FAISS
export const buildIndex = async (includeTensorflow: boolean = true): Promise<any> => {
  try {
    const response = await api.post('/faiss/build-index', null, {
      params: { include_tensorflow: includeTensorflow },
      timeout: 300000, // 5 minutes timeout
    });
    return response.data;
  } catch (error) {
    console.error('FAISS index build failed:', error);
    throw error;
  }
};

export const getIndexStatistics = async (): Promise<any> => {
  try {
    const response = await api.get('/faiss/statistics');
    return response.data;
  } catch (error) {
    console.error('Failed to fetch FAISS stats:', error);
    return {
      index_size: 0,
      index_coverage: 0,
      last_built: null
    };
  }
};
