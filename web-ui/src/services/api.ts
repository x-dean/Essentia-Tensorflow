import axios from 'axios';
import { TracksResponse, HealthResponse, DiscoveryStats } from '../types/api';

// Use relative URL for API calls - this works with both development proxy and production nginx
const API_BASE_URL = '/api';

// Default timeouts - will be updated from config
let apiTimeouts = {
  default: 60000,
  analysis: 300000,
  faiss: 300000,
  discovery: 120000
};

// Load timeouts from configuration
const loadApiTimeouts = async () => {
  try {
    const response = await axios.get('/api/config/api-timeouts');
    if (response.data.status === 'success') {
      apiTimeouts = response.data.timeouts;
      // Convert seconds to milliseconds
      Object.keys(apiTimeouts).forEach(key => {
        apiTimeouts[key as keyof typeof apiTimeouts] *= 1000;
      });
    }
  } catch (error) {
    console.warn('Failed to load API timeouts from config, using defaults');
  }
};

// Load timeouts on module initialization
loadApiTimeouts();

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: apiTimeouts.default,
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

export const getDiscoveryStatus = async (): Promise<any> => {
  try {
    const response = await api.get('/discovery/status');
    return response.data;
  } catch (error) {
    console.error('Failed to fetch discovery status:', error);
    return {
      status: 'unknown',
      message: 'Could not fetch discovery status'
    };
  }
};

export const triggerAnalysis = async (includeTensorflow = false, maxWorkers?: number, maxFiles?: number): Promise<any> => {
  try {
    const params = new URLSearchParams();
    if (includeTensorflow) params.append('include_tensorflow', 'true');
    if (maxWorkers) params.append('max_workers', maxWorkers.toString());
    if (maxFiles) params.append('max_files', maxFiles.toString());
    
    const response = await api.post(`/analysis/trigger?${params.toString()}`, null, {
      timeout: apiTimeouts.analysis,
    });
    return response.data;
  } catch (error) {
    console.error('Failed to trigger analysis:', error);
    throw error;
  }
};

export const forceReanalyze = async (includeTensorflow = false, maxWorkers?: number, maxFiles?: number): Promise<any> => {
  try {
    const params = new URLSearchParams();
    if (includeTensorflow) params.append('include_tensorflow', 'true');
    if (maxWorkers) params.append('max_workers', maxWorkers.toString());
    if (maxFiles) params.append('max_files', maxFiles.toString());
    
    const response = await api.post(`/analyzer/force-reanalyze?${params.toString()}`, null, {
      timeout: apiTimeouts.analysis,
    });
    return response.data;
  } catch (error) {
    console.error('Failed to force reanalyze:', error);
    throw error;
  }
};

export const enrichGenres = async (filePaths?: string[], forceReenrich = false, maxFiles?: number): Promise<any> => {
  try {
    const response = await api.post('/metadata/enrich-genres', {
      file_paths: filePaths || [],
      force_reenrich: forceReenrich,
      max_files: maxFiles
    });
    return response.data;
  } catch (error) {
    console.error('Failed to enrich genres:', error);
    throw error;
  }
};

export const forceReenrichMetadata = async (maxFiles?: number): Promise<any> => {
  try {
    const params = new URLSearchParams();
    if (maxFiles) params.append('max_files', maxFiles.toString());
    
    const response = await api.post(`/metadata/force-reenrich?${params.toString()}`);
    return response.data;
  } catch (error) {
    console.error('Failed to force reenrich metadata:', error);
    throw error;
  }
};

export const getAnalysisStatus = async (): Promise<any> => {
  try {
    const response = await api.get('/analysis/status');
    return response.data;
  } catch (error) {
    console.error('Failed to fetch analysis status:', error);
    return {
      status: 'unknown',
      message: 'Could not fetch analysis status'
    };
  }
};

// Configuration API
export const getConfig = async (): Promise<any> => {
  const response = await api.get('/config/all');
  return response.data;
};

export const getConsolidatedConfig = async (): Promise<any> => {
  const response = await api.get('/config/consolidated');
  return response.data;
};

export const getDiscoveryConfig = async (): Promise<any> => {
  const response = await api.get('/config/discovery');
  return response.data;
};

export const getAnalysisConfig = async (): Promise<any> => {
  const response = await api.get('/config/analysis');
  return response.data;
};

export const updateAnalysisConfig = async (data: any): Promise<any> => {
  const response = await api.post('/config/analysis/update', data);
  return response.data;
};

export const toggleTensorFlow = async (enabled: boolean): Promise<any> => {
  const response = await api.post('/config/analysis/toggle-tensorflow', { enabled });
  return response.data;
};

export const toggleFAISS = async (enabled: boolean): Promise<any> => {
  const response = await api.post('/config/analysis/toggle-faiss', { enabled });
  return response.data;
};

// Module status and control
export const getAnalysisModulesStatus = async (): Promise<any> => {
  try {
    const response = await api.get('/analysis/modules/status');
    return response.data;
  } catch (error) {
    console.error('Failed to fetch module status:', error);
    return {
      status: 'error',
      modules: {
        essentia: { enabled: true, available: true, description: 'Audio feature extraction' },
        tensorflow: { enabled: false, available: false, description: 'Machine learning classification' },
        faiss: { enabled: false, available: false, description: 'Vector similarity search' }
      }
    };
  }
};

export const toggleAnalysisModule = async (moduleName: string, enabled: boolean): Promise<any> => {
  try {
    const response = await api.post('/analysis/modules/toggle', null, {
      params: { module_name: moduleName, enabled }
    });
    return response.data;
  } catch (error) {
    console.error(`Failed to toggle module ${moduleName}:`, error);
    throw error;
  }
};

export const updateConfig = async (section: string, data: any): Promise<any> => {
  const response = await api.post('/config/update', {
    section,
    data
  });
  return response.data;
};

export const backupConfigs = async (): Promise<Blob> => {
  try {
    console.log('Making backup request to /config/backup');
    const response = await api.post('/config/backup', {}, {
      responseType: 'blob'
    });
    console.log('Backup response received:', response);
    return response.data;
  } catch (error) {
    console.error('Backup API error:', error);
    throw error;
  }
};

export const restoreConfigs = async (file: File): Promise<any> => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await api.post('/config/restore', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const listConfigs = async (): Promise<any> => {
  const response = await api.get('/config/list');
  return response.data;
};

export const deleteConfig = async (section: string): Promise<any> => {
  const response = await api.delete(`/config/${section}`);
  return response.data;
};

export const reloadConfigs = async (): Promise<any> => {
  const response = await api.post('/config/reload');
  return response.data;
};

export const validateConfigs = async (): Promise<any> => {
  const response = await api.get('/config/validate');
  return response.data;
};

export const getConfigHealth = async (): Promise<any> => {
  const response = await api.get('/config/monitor/health');
  return response.data;
};

export const getConfigMetrics = async (configName?: string): Promise<any> => {
  const params = configName ? { config_name: configName } : {};
  const response = await api.get('/config/monitor/metrics', { params });
  return response.data;
};

export const getConfigHistory = async (configName?: string, hours?: number): Promise<any> => {
  const params: any = {};
  if (configName) params.config_name = configName;
  if (hours) params.hours = hours;
  
  const response = await api.get('/config/monitor/history', { params });
  return response.data;
};

export const getConfigSchemas = async (): Promise<any> => {
  const response = await api.get('/config/schemas');
  return response.data;
};

export const resetConfigMetrics = async (configName?: string): Promise<any> => {
  const params = configName ? { config_name: configName } : {};
  const response = await api.post('/config/monitor/reset', {}, { params });
  return response.data;
};

export const clearConfigHistory = async (): Promise<any> => {
  const response = await api.post('/config/monitor/clear-history');
  return response.data;
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
      timeout: apiTimeouts.analysis,
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
      timeout: apiTimeouts.faiss,
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
