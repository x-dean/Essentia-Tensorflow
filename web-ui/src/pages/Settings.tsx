import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getConfig, updateConfig, getDiscoveryConfig, getAnalysisConfig, backupConfigs, restoreConfigs, listConfigs, deleteConfig, reloadConfigs } from '../services/api';
import { Settings as SettingsIcon, Save, RefreshCw, Database, Search, Play, AlertCircle, CheckCircle, Loader2, Globe, Music, ExternalLink, BarChart3, FileText } from 'lucide-react';
import LoadingSpinner from '../components/LoadingSpinner';
import ConfigManager from '../components/ConfigManager';

const Settings: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('app-settings');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Fetch configuration data
  const { data: config, isLoading: configLoading, error: configError } = useQuery({
    queryKey: ['config'],
    queryFn: getConfig,
    retry: 2,
    retryDelay: 5000,
  });

  const { data: discoveryConfig, isLoading: discoveryConfigLoading } = useQuery({
    queryKey: ['discovery-config'],
    queryFn: getDiscoveryConfig,
    retry: 2,
    retryDelay: 5000,
  });

  const { data: analysisConfig, isLoading: analysisConfigLoading } = useQuery({
    queryKey: ['analysis-config'],
    queryFn: getAnalysisConfig,
    retry: 2,
    retryDelay: 5000,
  });

  // Update configuration mutation
  const updateConfigMutation = useMutation({
    mutationFn: updateConfig,
    onSuccess: async () => {
      setSuccess('Configuration updated successfully!');
      setError(null);
      
      // Force refetch all configuration data immediately
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['config'] }),
        queryClient.invalidateQueries({ queryKey: ['discovery-config'] }),
        queryClient.invalidateQueries({ queryKey: ['analysis-config'] })
      ]);
      
      // Force immediate refetch to get fresh data
      await Promise.all([
        queryClient.refetchQueries({ queryKey: ['config'] }),
        queryClient.refetchQueries({ queryKey: ['discovery-config'] }),
        queryClient.refetchQueries({ queryKey: ['analysis-config'] })
      ]);
      
      setTimeout(() => setSuccess(null), 3000);
    },
    onError: (error: any) => {
      setError(`Failed to update configuration: ${error.response?.data?.detail || (error instanceof Error ? error.message : 'Unknown error')}`);
      setSuccess(null);
    },
  });

  const handleSaveConfig = async (section: string, data: any) => {
    await updateConfigMutation.mutateAsync({ section, data });
    
    // Reload configs on the backend
    try {
      await reloadConfigs();
    } catch (error) {
      console.warn('Failed to reload configs on backend:', error);
    }
    
    // Invalidate and refetch the specific config based on section
    if (section === 'analysis_config') {
      await queryClient.invalidateQueries({ queryKey: ['analysis-config'] });
      await queryClient.refetchQueries({ queryKey: ['analysis-config'] });
    } else if (section === 'discovery') {
      await queryClient.invalidateQueries({ queryKey: ['discovery-config'] });
      await queryClient.refetchQueries({ queryKey: ['discovery-config'] });
    } else {
      // For other sections, invalidate the main config
      await queryClient.invalidateQueries({ queryKey: ['config'] });
      await queryClient.refetchQueries({ queryKey: ['config'] });
    }
  };

  const [isBackingUp, setIsBackingUp] = useState(false);

  const handleBackup = async () => {
    setIsBackingUp(true);
    try {
      const blob = await backupConfigs();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `config_backup_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.zip`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      setSuccess('Configuration backup downloaded successfully!');
      setError(null);
      setTimeout(() => setSuccess(null), 3000);
    } catch (error: any) {
      setError(`Failed to download backup: ${error.response?.data?.detail || (error instanceof Error ? error.message : 'Unknown error')}`);
      setSuccess(null);
    } finally {
      setIsBackingUp(false);
    }
  };

  const handleRestore = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      restoreConfigMutation.mutate(file);
      // Reset the input
      event.target.value = '';
    }
  };

  const restoreConfigMutation = useMutation({
    mutationFn: restoreConfigs,
    onSuccess: () => {
      setSuccess('Configuration restored successfully!');
      setError(null);
      queryClient.invalidateQueries({ queryKey: ['config'] });
      queryClient.invalidateQueries({ queryKey: ['discovery-config'] });
      queryClient.invalidateQueries({ queryKey: ['analysis-config'] });
      setTimeout(() => setSuccess(null), 3000);
    },
    onError: (error: any) => {
      setError(`Failed to restore configuration: ${error.response?.data?.detail || (error instanceof Error ? error.message : 'Unknown error')}`);
      setSuccess(null);
    },
  });

  const tabs = [
    { id: 'app-settings', name: 'App Settings', icon: SettingsIcon, description: 'Core application configuration' },
    { id: 'discovery', name: 'Discovery', icon: Search, description: 'File discovery and scanning settings' },
    { id: 'analysis', name: 'Analysis', icon: Play, description: 'Audio analysis and processing settings' },
    { id: 'database', name: 'Database', icon: Database, description: 'Database connection and pool settings' },
    { id: 'logging', name: 'Logging', icon: FileText, description: 'Logging configuration and suppression' },
    { id: 'external', name: 'External APIs', icon: Globe, description: 'External API integrations' },
    { id: 'config-manager', name: 'Config Manager', icon: BarChart3, description: 'Advanced configuration management' },
  ];

  if (configLoading || discoveryConfigLoading || analysisConfigLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" text="Loading settings..." />
      </div>
    );
  }

  if (configError) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="mx-auto h-12 w-12 text-red-500 mb-4" />
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">Error Loading Settings</h2>
        <p className="text-gray-600 dark:text-gray-400">Failed to load configuration settings.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Configure application settings and preferences
          </p>
        </div>
        
        {/* Configuration Management Buttons */}
        <div className="flex space-x-2">
          <button
            onClick={handleBackup}
            disabled={isBackingUp}
            className="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 shadow-sm text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
          >
            {isBackingUp ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4 mr-2" />
            )}
            Backup
          </button>
          
          <label className="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 shadow-sm text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 cursor-pointer">
            {restoreConfigMutation.isPending ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Database className="w-4 h-4 mr-2" />
            )}
            Restore
            <input
              type="file"
              accept=".zip"
              onChange={handleRestore}
              className="hidden"
              disabled={restoreConfigMutation.isPending}
            />
          </label>
        </div>
      </div>

      {/* Error/Success Messages */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-4">
          <div className="flex">
            <AlertCircle className="w-5 h-5 text-red-400 mr-2" />
            <div className="text-sm text-red-700 dark:text-red-300">{error}</div>
          </div>
        </div>
      )}

      {success && (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-md p-4">
          <div className="flex">
            <CheckCircle className="w-5 h-5 text-green-400 mr-2" />
            <div className="text-sm text-green-700 dark:text-green-300">{success}</div>
          </div>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex space-x-8 overflow-x-auto">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-2 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 whitespace-nowrap ${
                  activeTab === tab.id
                    ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                    : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
                }`}
                title={tab.description}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.name}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg">
        {activeTab === 'app-settings' && (
          <AppSettings 
            key={`app-settings-${JSON.stringify(config?.configs?.app_settings)}`}
            config={config?.configs?.app_settings} 
            onSave={(data) => handleSaveConfig('app_settings', data)}
            isLoading={updateConfigMutation.isPending}
          />
        )}
        
        {activeTab === 'discovery' && (
          <DiscoverySettings 
            key={`discovery-${JSON.stringify(discoveryConfig)}`}
            config={discoveryConfig} 
            onSave={(data) => handleSaveConfig('discovery', data)}
            isLoading={updateConfigMutation.isPending}
          />
        )}
        
        {activeTab === 'analysis' && (
          <AnalysisSettings 
            key={`analysis-${JSON.stringify(analysisConfig)}`}
            config={analysisConfig} 
            onSave={(data) => handleSaveConfig('analysis_config', data)}
            isLoading={updateConfigMutation.isPending}
          />
        )}
        
        {activeTab === 'database' && (
          <DatabaseSettings 
            key={`database-${JSON.stringify(config?.configs?.database)}`}
            config={config?.configs?.database} 
            onSave={(data) => handleSaveConfig('database', data)}
            isLoading={updateConfigMutation.isPending}
          />
        )}

        {activeTab === 'logging' && (
          <LoggingSettings 
            key={`logging-${JSON.stringify(config?.configs?.logging)}`}
            config={config?.configs?.logging} 
            onSave={(data) => handleSaveConfig('logging', data)}
            isLoading={updateConfigMutation.isPending}
          />
        )}

        {activeTab === 'external' && (
          <ExternalAPISettings 
            key={`external-${JSON.stringify(config?.configs?.app_settings?.external_apis)}`}
            config={config?.configs?.app_settings?.external_apis} 
            onSave={(data) => handleSaveConfig('app_settings', { ...config?.configs?.app_settings, external_apis: data })}
            isLoading={updateConfigMutation.isPending}
          />
        )}

        {activeTab === 'config-manager' && (
          <div className="p-6">
            <ConfigManager />
          </div>
        )}
      </div>
    </div>
  );
};

// App Settings Component
const AppSettings: React.FC<{ config: any; onSave: (data: any) => void; isLoading: boolean }> = ({ config, onSave, isLoading }) => {
  const [settings, setSettings] = useState({
    api: {
      host: config?.api?.host ?? '0.0.0.0',
      port: config?.api?.port ?? 8000,
      workers: config?.api?.workers ?? 1,
      reload: config?.api?.reload ?? false,
      timeouts: {
        default: config?.api?.timeouts?.default ?? 60,
        analysis: config?.api?.timeouts?.analysis ?? 300,
        faiss: config?.api?.timeouts?.faiss ?? 300,
        discovery: config?.api?.timeouts?.discovery ?? 120
      },
      cors: {
        enabled: config?.api?.cors?.enabled ?? true,
        origins: config?.api?.cors?.origins ?? ['*'],
        methods: config?.api?.cors?.methods ?? ['GET', 'POST', 'PUT', 'DELETE'],
        headers: config?.api?.cors?.headers ?? ['*']
      }
    },
    performance: {
      max_concurrent_requests: config?.performance?.max_concurrent_requests ?? 100,
      request_timeout: config?.performance?.request_timeout ?? 30,
      background_tasks: {
        enabled: config?.performance?.background_tasks?.enabled ?? true,
        max_workers: config?.performance?.background_tasks?.max_workers ?? 4
      }
    },
    discovery: {
      background_enabled: config?.discovery?.background_enabled ?? false,
      interval: config?.discovery?.interval ?? 300,
      auto_scan_on_startup: config?.discovery?.auto_scan_on_startup ?? true,
      supported_extensions: config?.discovery?.supported_extensions ?? ['.mp3', '.wav', '.flac'],
      cache_ttl: config?.discovery?.cache_ttl ?? 3600,
      batch_size: config?.discovery?.batch_size ?? 100,
      hash_algorithm: config?.discovery?.hash_algorithm ?? 'md5'
    },
    paths: {
      python_path: config?.paths?.python_path ?? '/app/src',
      data_directory: config?.paths?.data_directory ?? '/app/data',
      cache_directory: config?.paths?.cache_directory ?? '/app/cache',
      logs_directory: config?.paths?.logs_directory ?? '/app/logs'
    },
    faiss: {
      index_name: config?.faiss?.index_name ?? 'music_library',
      vector_dimension: config?.faiss?.vector_dimension ?? 128,
      similarity_threshold: config?.faiss?.similarity_threshold ?? 0.8
    },
    external_apis: {
      musicbrainz: {
        enabled: config?.external_apis?.external_apis?.musicbrainz?.enabled ?? true,
        rateLimit: config?.external_apis?.external_apis?.musicbrainz?.rateLimit ?? 1,
        timeout: config?.external_apis?.external_apis?.musicbrainz?.timeout ?? 10,
        userAgent: config?.external_apis?.external_apis?.musicbrainz?.userAgent ?? 'PlaylistApp/1.0 (dean@example.com)'
      },
      lastfm: {
        enabled: config?.external_apis?.external_apis?.lastfm?.enabled ?? true,
        apiKey: config?.external_apis?.external_apis?.lastfm?.apiKey ?? '',
        baseUrl: config?.external_apis?.external_apis?.lastfm?.baseUrl ?? 'https://ws.audioscrobbler.com/2.0/',
        rateLimit: config?.external_apis?.external_apis?.lastfm?.rateLimit ?? 0.5,
        timeout: config?.external_apis?.external_apis?.lastfm?.timeout ?? 10
      },
      discogs: {
        enabled: config?.external_apis?.external_apis?.discogs?.enabled ?? true,
        apiKey: config?.external_apis?.external_apis?.discogs?.apiKey ?? '',
        baseUrl: config?.external_apis?.external_apis?.discogs?.baseUrl ?? 'https://api.discogs.com/',
        rateLimit: config?.external_apis?.external_apis?.discogs?.rateLimit ?? 1,
        timeout: config?.external_apis?.external_apis?.discogs?.timeout ?? 10,
        userAgent: config?.external_apis?.external_apis?.discogs?.userAgent ?? 'PlaylistApp/1.0'
      }
    }
  });

  React.useEffect(() => {
    setSettings({
      api: {
        host: config?.api?.host ?? '0.0.0.0',
        port: config?.api?.port ?? 8000,
        workers: config?.api?.workers ?? 1,
        reload: config?.api?.reload ?? false,
        timeouts: {
          default: config?.api?.timeouts?.default ?? 60,
          analysis: config?.api?.timeouts?.analysis ?? 300,
          faiss: config?.api?.timeouts?.faiss ?? 300,
          discovery: config?.api?.timeouts?.discovery ?? 120
        },
        cors: {
          enabled: config?.api?.cors?.enabled ?? true,
          origins: config?.api?.cors?.origins ?? ['*'],
          methods: config?.api?.cors?.methods ?? ['GET', 'POST', 'PUT', 'DELETE'],
          headers: config?.api?.cors?.headers ?? ['*']
        }
      },
      performance: {
        max_concurrent_requests: config?.performance?.max_concurrent_requests ?? 100,
        request_timeout: config?.performance?.request_timeout ?? 30,
        background_tasks: {
          enabled: config?.performance?.background_tasks?.enabled ?? true,
          max_workers: config?.performance?.background_tasks?.max_workers ?? 4
        }
      },
      discovery: {
        background_enabled: config?.discovery?.background_enabled ?? false,
        interval: config?.discovery?.interval ?? 300,
        auto_scan_on_startup: config?.discovery?.auto_scan_on_startup ?? true,
        supported_extensions: config?.discovery?.supported_extensions ?? ['.mp3', '.wav', '.flac'],
        cache_ttl: config?.discovery?.cache_ttl ?? 3600,
        batch_size: config?.discovery?.batch_size ?? 100,
        hash_algorithm: config?.discovery?.hash_algorithm ?? 'md5'
      },
      paths: {
        python_path: config?.paths?.python_path ?? '/app/src',
        data_directory: config?.paths?.data_directory ?? '/app/data',
        cache_directory: config?.paths?.cache_directory ?? '/app/cache',
        logs_directory: config?.paths?.logs_directory ?? '/app/logs'
      },
      faiss: {
        index_name: config?.faiss?.index_name ?? 'music_library',
        vector_dimension: config?.faiss?.vector_dimension ?? 128,
        similarity_threshold: config?.faiss?.similarity_threshold ?? 0.8
      },
      external_apis: {
        musicbrainz: {
          enabled: config?.external_apis?.external_apis?.musicbrainz?.enabled ?? true,
          rateLimit: config?.external_apis?.external_apis?.musicbrainz?.rateLimit ?? 1,
          timeout: config?.external_apis?.external_apis?.musicbrainz?.timeout ?? 10,
          userAgent: config?.external_apis?.external_apis?.musicbrainz?.userAgent ?? 'PlaylistApp/1.0 (dean@example.com)'
        },
        lastfm: {
          enabled: config?.external_apis?.external_apis?.lastfm?.enabled ?? true,
          apiKey: config?.external_apis?.external_apis?.lastfm?.apiKey ?? '',
          baseUrl: config?.external_apis?.external_apis?.lastfm?.baseUrl ?? 'https://ws.audioscrobbler.com/2.0/',
          rateLimit: config?.external_apis?.external_apis?.lastfm?.rateLimit ?? 0.5,
          timeout: config?.external_apis?.external_apis?.lastfm?.timeout ?? 10
        },
        discogs: {
          enabled: config?.external_apis?.external_apis?.discogs?.enabled ?? true,
          apiKey: config?.external_apis?.external_apis?.discogs?.apiKey ?? '',
          baseUrl: config?.external_apis?.external_apis?.discogs?.baseUrl ?? 'https://api.discogs.com/',
          rateLimit: config?.external_apis?.external_apis?.discogs?.rateLimit ?? 1,
          timeout: config?.external_apis?.external_apis?.discogs?.timeout ?? 10,
          userAgent: config?.external_apis?.external_apis?.discogs?.userAgent ?? 'PlaylistApp/1.0'
        }
      }
    });
  }, [config]);

  const handleSave = () => {
    onSave(settings);
  };

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-lg font-medium text-gray-900 dark:text-white">Application Settings</h2>
      
      {/* API Settings */}
      <div className="space-y-4">
        <h3 className="text-md font-medium text-gray-900 dark:text-white">API Configuration</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Host
            </label>
            <input
              type="text"
              value={settings.api.host}
              onChange={(e) => setSettings({ ...settings, api: { ...settings.api, host: e.target.value } })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Port
            </label>
            <input
              type="number"
              value={settings.api.port}
              onChange={(e) => setSettings({ ...settings, api: { ...settings.api, port: parseInt(e.target.value) } })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
              min="1"
              max="65535"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Workers
            </label>
            <input
              type="number"
              value={settings.api.workers}
              onChange={(e) => setSettings({ ...settings, api: { ...settings.api, workers: parseInt(e.target.value) } })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
              min="1"
              max="16"
            />
          </div>
          <div className="flex items-center">
            <input
              type="checkbox"
              checked={settings.api.reload}
              onChange={(e) => setSettings({ ...settings, api: { ...settings.api, reload: e.target.checked } })}
              className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
            />
            <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Auto Reload</span>
          </div>
        </div>
      </div>

      {/* Performance Settings */}
      <div className="space-y-4">
        <h3 className="text-md font-medium text-gray-900 dark:text-white">Performance</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Max Concurrent Requests
            </label>
            <input
              type="number"
              value={settings.performance.max_concurrent_requests}
              onChange={(e) => setSettings({ ...settings, performance: { ...settings.performance, max_concurrent_requests: parseInt(e.target.value) } })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
              min="1"
              max="1000"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Request Timeout (seconds)
            </label>
            <input
              type="number"
              value={settings.performance.request_timeout}
              onChange={(e) => setSettings({ ...settings, performance: { ...settings.performance, request_timeout: parseInt(e.target.value) } })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
              min="1"
              max="300"
            />
          </div>
        </div>
      </div>

      {/* FAISS Settings */}
      <div className="space-y-4">
        <h3 className="text-md font-medium text-gray-900 dark:text-white">FAISS Configuration</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Index Name
            </label>
            <input
              type="text"
              value={settings.faiss.index_name}
              onChange={(e) => setSettings({ ...settings, faiss: { ...settings.faiss, index_name: e.target.value } })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Vector Dimension
            </label>
            <input
              type="number"
              value={settings.faiss.vector_dimension}
              onChange={(e) => setSettings({ ...settings, faiss: { ...settings.faiss, vector_dimension: parseInt(e.target.value) } })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
              min="64"
              max="512"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Similarity Threshold
            </label>
            <input
              type="number"
              step="0.1"
              value={settings.faiss.similarity_threshold}
              onChange={(e) => setSettings({ ...settings, faiss: { ...settings.faiss, similarity_threshold: parseFloat(e.target.value) } })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
              min="0.0"
              max="1.0"
            />
          </div>
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={isLoading}
          className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <Save className="w-4 h-4 mr-2" />
          )}
          Save Settings
        </button>
      </div>
    </div>
  );
};

// Discovery Settings Component
const DiscoverySettings: React.FC<{ config: any; onSave: (data: any) => void; isLoading: boolean }> = ({ config, onSave, isLoading }) => {
  const [settings, setSettings] = useState({
    supported_extensions: config?.config?.supported_extensions?.join(', ') || '.mp3,.wav,.flac',
    batch_size: config?.config?.batch_size || 125,
  });

  React.useEffect(() => {
    setSettings({
      supported_extensions: config?.config?.supported_extensions?.join(', ') || '.mp3,.wav,.flac',
      batch_size: config?.config?.batch_size || 125,
    });
  }, [config]);

  const handleSave = () => {
    onSave({
      supported_extensions: settings.supported_extensions.split(',').map((ext: string) => ext.trim()),
      batch_size: settings.batch_size,
    });
  };

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-lg font-medium text-gray-900 dark:text-white">Discovery Settings</h2>
      
      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Supported Extensions (comma-separated)
          </label>
          <input
            type="text"
            value={settings.supported_extensions}
            onChange={(e) => setSettings({ ...settings, supported_extensions: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
            placeholder=".mp3,.wav,.flac,.ogg,.m4a"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Batch Size
          </label>
          <input
            type="number"
            value={settings.batch_size}
            onChange={(e) => setSettings({ ...settings, batch_size: parseInt(e.target.value) })}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
            min="1"
            max="1000"
          />
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={isLoading}
          className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <Save className="w-4 h-4 mr-2" />
          )}
          Save Settings
        </button>
      </div>
    </div>
  );
};

// Analysis Settings Component
const AnalysisSettings: React.FC<{ config: any; onSave: (data: any) => void; isLoading: boolean }> = ({ config, onSave, isLoading }) => {
  // Get the analysis config from the config response
  const analysisConfig = config?.config || config || {};
  
  const [settings, setSettings] = useState({
    // Performance settings
    maxWorkers: analysisConfig?.performance?.parallel_processing?.max_workers ?? 4,
    chunkSize: analysisConfig?.performance?.parallel_processing?.chunk_size ?? 25,
    timeoutPerFile: analysisConfig?.performance?.parallel_processing?.timeout_per_file ?? 600,
    memoryLimitMB: analysisConfig?.performance?.parallel_processing?.memory_limit_mb ?? 512,
    
    // Essentia algorithms
    enableTensorflow: analysisConfig?.essentia?.algorithms?.enable_tensorflow ?? true,
    enableComplexRhythm: analysisConfig?.essentia?.algorithms?.enable_complex_rhythm ?? true,
    enableComplexHarmonic: analysisConfig?.essentia?.algorithms?.enable_complex_harmonic ?? true,
    enableBeatTracking: analysisConfig?.essentia?.algorithms?.enable_beat_tracking ?? true,
    enableTempoTap: analysisConfig?.essentia?.algorithms?.enable_tempo_tap ?? true,
    enableRhythmExtractor: analysisConfig?.essentia?.algorithms?.enable_rhythm_extractor ?? true,
    enablePitchAnalysis: analysisConfig?.essentia?.algorithms?.enable_pitch_analysis ?? true,
    enableChordDetection: analysisConfig?.essentia?.algorithms?.enable_chord_detection ?? true,
    
    // Audio processing
    sampleRate: analysisConfig?.essentia?.audio_processing?.sample_rate ?? 44100,
    channels: analysisConfig?.essentia?.audio_processing?.channels ?? 1,
    frameSize: analysisConfig?.essentia?.audio_processing?.frame_size ?? 2048,
    hopSize: analysisConfig?.essentia?.audio_processing?.hop_size ?? 1024,
    
    // Quality settings
    minConfidenceThreshold: analysisConfig?.quality?.min_confidence_threshold ?? 0.3,
    defaultTempo: analysisConfig?.quality?.fallback_values?.tempo ?? 120.0,
    defaultKey: analysisConfig?.quality?.fallback_values?.key ?? 'C',
    defaultScale: analysisConfig?.quality?.fallback_values?.scale ?? 'major',
  });

  // Update local state when config changes
  React.useEffect(() => {
    const analysisConfig = config?.config || config || {};
    setSettings({
      // Performance settings
      maxWorkers: analysisConfig?.performance?.parallel_processing?.max_workers ?? 4,
      chunkSize: analysisConfig?.performance?.parallel_processing?.chunk_size ?? 25,
      timeoutPerFile: analysisConfig?.performance?.parallel_processing?.timeout_per_file ?? 600,
      memoryLimitMB: analysisConfig?.performance?.parallel_processing?.memory_limit_mb ?? 512,
      
      // Essentia algorithms
      enableTensorflow: analysisConfig?.essentia?.algorithms?.enable_tensorflow ?? true,
      enableComplexRhythm: analysisConfig?.essentia?.algorithms?.enable_complex_rhythm ?? true,
      enableComplexHarmonic: analysisConfig?.essentia?.algorithms?.enable_complex_harmonic ?? true,
      enableBeatTracking: analysisConfig?.essentia?.algorithms?.enable_beat_tracking ?? true,
      enableTempoTap: analysisConfig?.essentia?.algorithms?.enable_tempo_tap ?? true,
      enableRhythmExtractor: analysisConfig?.essentia?.algorithms?.enable_rhythm_extractor ?? true,
      enablePitchAnalysis: analysisConfig?.essentia?.algorithms?.enable_pitch_analysis ?? true,
      enableChordDetection: analysisConfig?.essentia?.algorithms?.enable_chord_detection ?? true,
      
      // Audio processing
      sampleRate: analysisConfig?.essentia?.audio_processing?.sample_rate ?? 44100,
      channels: analysisConfig?.essentia?.audio_processing?.channels ?? 1,
      frameSize: analysisConfig?.essentia?.audio_processing?.frame_size ?? 2048,
      hopSize: analysisConfig?.essentia?.audio_processing?.hop_size ?? 1024,
      
      // Quality settings
      minConfidenceThreshold: analysisConfig?.quality?.min_confidence_threshold ?? 0.3,
      defaultTempo: analysisConfig?.quality?.fallback_values?.tempo ?? 120.0,
      defaultKey: analysisConfig?.quality?.fallback_values?.key ?? 'C',
      defaultScale: analysisConfig?.quality?.fallback_values?.scale ?? 'major',
    });
  }, [config]);

  const handleSave = () => {
    onSave({
      performance: {
        parallel_processing: {
          max_workers: settings.maxWorkers,
          chunk_size: settings.chunkSize,
          timeout_per_file: settings.timeoutPerFile,
          memory_limit_mb: settings.memoryLimitMB,
        }
      },
      essentia: {
        audio_processing: {
          sample_rate: settings.sampleRate,
          channels: settings.channels,
          frame_size: settings.frameSize,
          hop_size: settings.hopSize,
        },
        algorithms: {
          enable_tensorflow: settings.enableTensorflow,
          enable_complex_rhythm: settings.enableComplexRhythm,
          enable_complex_harmonic: settings.enableComplexHarmonic,
          enable_beat_tracking: settings.enableBeatTracking,
          enable_tempo_tap: settings.enableTempoTap,
          enable_rhythm_extractor: settings.enableRhythmExtractor,
          enable_pitch_analysis: settings.enablePitchAnalysis,
          enable_chord_detection: settings.enableChordDetection,
        }
      },
      quality: {
        min_confidence_threshold: settings.minConfidenceThreshold,
        fallback_values: {
          tempo: settings.defaultTempo,
          key: settings.defaultKey,
          scale: settings.defaultScale,
        }
      }
    });
  };

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-lg font-medium text-gray-900 dark:text-white">Analysis Settings</h2>
      
      {/* Performance Settings */}
      <div className="space-y-4">
        <h3 className="text-md font-medium text-gray-900 dark:text-white">Performance</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Max Workers
            </label>
            <input
              type="number"
              value={settings.maxWorkers}
              onChange={(e) => setSettings({ ...settings, maxWorkers: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
              min="1"
              max="16"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Chunk Size
            </label>
            <input
              type="number"
              value={settings.chunkSize}
              onChange={(e) => setSettings({ ...settings, chunkSize: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
              min="1"
              max="100"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Timeout Per File (seconds)
            </label>
            <input
              type="number"
              value={settings.timeoutPerFile}
              onChange={(e) => setSettings({ ...settings, timeoutPerFile: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
              min="30"
              max="1800"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Memory Limit (MB)
            </label>
            <input
              type="number"
              value={settings.memoryLimitMB}
              onChange={(e) => setSettings({ ...settings, memoryLimitMB: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
              min="128"
              max="4096"
            />
          </div>
        </div>
      </div>

      {/* Audio Processing Settings */}
      <div className="space-y-4">
        <h3 className="text-md font-medium text-gray-900 dark:text-white">Audio Processing</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Sample Rate
            </label>
            <input
              type="number"
              value={settings.sampleRate}
              onChange={(e) => setSettings({ ...settings, sampleRate: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
              min="8000"
              max="96000"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Channels
            </label>
            <input
              type="number"
              value={settings.channels}
              onChange={(e) => setSettings({ ...settings, channels: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
              min="1"
              max="2"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Frame Size
            </label>
            <input
              type="number"
              value={settings.frameSize}
              onChange={(e) => setSettings({ ...settings, frameSize: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
              min="512"
              max="8192"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Hop Size
            </label>
            <input
              type="number"
              value={settings.hopSize}
              onChange={(e) => setSettings({ ...settings, hopSize: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
              min="256"
              max="4096"
            />
          </div>
        </div>
      </div>

      {/* Algorithms */}
      <div className="space-y-4">
        <h3 className="text-md font-medium text-gray-900 dark:text-white">Algorithms</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-3">
            <div className="flex items-center">
              <input
                type="checkbox"
                checked={settings.enableTensorflow}
                onChange={(e) => setSettings({ ...settings, enableTensorflow: e.target.checked })}
                className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Enable TensorFlow</span>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                checked={settings.enableComplexRhythm}
                onChange={(e) => setSettings({ ...settings, enableComplexRhythm: e.target.checked })}
                className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Complex Rhythm Analysis</span>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                checked={settings.enableComplexHarmonic}
                onChange={(e) => setSettings({ ...settings, enableComplexHarmonic: e.target.checked })}
                className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Complex Harmonic Analysis</span>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                checked={settings.enableBeatTracking}
                onChange={(e) => setSettings({ ...settings, enableBeatTracking: e.target.checked })}
                className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Beat Tracking</span>
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center">
              <input
                type="checkbox"
                checked={settings.enableTempoTap}
                onChange={(e) => setSettings({ ...settings, enableTempoTap: e.target.checked })}
                className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Tempo Tap</span>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                checked={settings.enableRhythmExtractor}
                onChange={(e) => setSettings({ ...settings, enableRhythmExtractor: e.target.checked })}
                className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Rhythm Extractor</span>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                checked={settings.enablePitchAnalysis}
                onChange={(e) => setSettings({ ...settings, enablePitchAnalysis: e.target.checked })}
                className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Pitch Analysis</span>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                checked={settings.enableChordDetection}
                onChange={(e) => setSettings({ ...settings, enableChordDetection: e.target.checked })}
                className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Chord Detection</span>
            </div>
          </div>
        </div>
      </div>

      {/* Quality Settings */}
      <div className="space-y-4">
        <h3 className="text-md font-medium text-gray-900 dark:text-white">Quality Settings</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Min Confidence Threshold
            </label>
            <input
              type="number"
              step="0.1"
              value={settings.minConfidenceThreshold}
              onChange={(e) => setSettings({ ...settings, minConfidenceThreshold: parseFloat(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
              min="0.0"
              max="1.0"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Default Tempo
            </label>
            <input
              type="number"
              step="0.1"
              value={settings.defaultTempo}
              onChange={(e) => setSettings({ ...settings, defaultTempo: parseFloat(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
              min="20"
              max="300"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Default Key
            </label>
            <input
              type="text"
              value={settings.defaultKey}
              onChange={(e) => setSettings({ ...settings, defaultKey: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
              maxLength={2}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Default Scale
            </label>
            <select
              value={settings.defaultScale}
              onChange={(e) => setSettings({ ...settings, defaultScale: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
            >
              <option value="major">Major</option>
              <option value="minor">Minor</option>
            </select>
          </div>
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={isLoading}
          className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <Save className="w-4 h-4 mr-2" />
          )}
          Save Settings
        </button>
      </div>
    </div>
  );
};

// Database Settings Component
const DatabaseSettings: React.FC<{ config: any; onSave: (data: any) => void; isLoading: boolean }> = ({ config, onSave, isLoading }) => {
  // Get the database config from the config response
  const databaseConfig = config?.config || config || {};
  
  const [settings, setSettings] = useState({
    poolSize: databaseConfig?.pool_size ?? 25,
    maxOverflow: databaseConfig?.max_overflow ?? 35,
    poolTimeout: databaseConfig?.pool_timeout ?? 45,
    poolRecycle: databaseConfig?.pool_recycle ?? 7200,
    maxRetries: databaseConfig?.retry_settings?.max_retries ?? 3,
    initialDelay: databaseConfig?.retry_settings?.initial_delay ?? 1,
    backoffMultiplier: databaseConfig?.retry_settings?.backoff_multiplier ?? 2,
    maxDelay: databaseConfig?.retry_settings?.max_delay ?? 30,
    connectionTimeout: databaseConfig?.connection_timeout ?? 30,
  });

  // Update local state when config changes
  React.useEffect(() => {
    const databaseConfig = config?.config || config || {};
    setSettings({
      poolSize: databaseConfig?.pool_size ?? 25,
      maxOverflow: databaseConfig?.max_overflow ?? 35,
      poolTimeout: databaseConfig?.pool_timeout ?? 45,
      poolRecycle: databaseConfig?.pool_recycle ?? 7200,
      maxRetries: databaseConfig?.retry_settings?.max_retries ?? 3,
      initialDelay: databaseConfig?.retry_settings?.initial_delay ?? 1,
      backoffMultiplier: databaseConfig?.retry_settings?.backoff_multiplier ?? 2,
      maxDelay: databaseConfig?.retry_settings?.max_delay ?? 30,
      connectionTimeout: databaseConfig?.connection_timeout ?? 30,
    });
  }, [config]);

  const handleSave = () => {
    onSave({
      pool_size: settings.poolSize,
      max_overflow: settings.maxOverflow,
      pool_timeout: settings.poolTimeout,
      pool_recycle: settings.poolRecycle,
      retry_settings: {
        max_retries: settings.maxRetries,
        initial_delay: settings.initialDelay,
        backoff_multiplier: settings.backoffMultiplier,
        max_delay: settings.maxDelay,
      },
      connection_timeout: settings.connectionTimeout,
    });
  };

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-lg font-medium text-gray-900 dark:text-white">Database Settings</h2>
      
      <div className="space-y-6">
        {/* Connection Pool Settings */}
        <div className="space-y-4">
          <h3 className="text-md font-medium text-gray-900 dark:text-white">Connection Pool</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Pool Size
              </label>
              <input
                type="number"
                value={settings.poolSize}
                onChange={(e) => setSettings({ ...settings, poolSize: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                min="5"
                max="100"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Max Overflow
              </label>
              <input
                type="number"
                value={settings.maxOverflow}
                onChange={(e) => setSettings({ ...settings, maxOverflow: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                min="5"
                max="100"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Pool Timeout (seconds)
              </label>
              <input
                type="number"
                value={settings.poolTimeout}
                onChange={(e) => setSettings({ ...settings, poolTimeout: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                min="10"
                max="300"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Pool Recycle (seconds)
              </label>
              <input
                type="number"
                value={settings.poolRecycle}
                onChange={(e) => setSettings({ ...settings, poolRecycle: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                min="300"
                max="7200"
              />
            </div>
          </div>
        </div>

        {/* Retry Settings */}
        <div className="space-y-4">
          <h3 className="text-md font-medium text-gray-900 dark:text-white">Retry Settings</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Max Retries
              </label>
              <input
                type="number"
                value={settings.maxRetries}
                onChange={(e) => setSettings({ ...settings, maxRetries: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                min="1"
                max="10"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Initial Delay (seconds)
              </label>
              <input
                type="number"
                value={settings.initialDelay}
                onChange={(e) => setSettings({ ...settings, initialDelay: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                min="1"
                max="60"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Backoff Multiplier
              </label>
              <input
                type="number"
                step="0.1"
                value={settings.backoffMultiplier}
                onChange={(e) => setSettings({ ...settings, backoffMultiplier: parseFloat(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                min="1.0"
                max="5.0"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Max Delay (seconds)
              </label>
              <input
                type="number"
                value={settings.maxDelay}
                onChange={(e) => setSettings({ ...settings, maxDelay: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                min="5"
                max="300"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Connection Timeout (seconds)
              </label>
              <input
                type="number"
                value={settings.connectionTimeout}
                onChange={(e) => setSettings({ ...settings, connectionTimeout: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                min="5"
                max="300"
              />
            </div>
          </div>
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={isLoading}
          className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <Save className="w-4 h-4 mr-2" />
          )}
          Save Settings
        </button>
      </div>
    </div>
  );
};

// Logging Settings Component
const LoggingSettings: React.FC<{ config: any; onSave: (data: any) => void; isLoading: boolean }> = ({ config, onSave, isLoading }) => {
  // Get the logging config from the config response
  const loggingConfig = config?.config || config || {};
  
  const [settings, setSettings] = useState({
    logLevel: loggingConfig?.log_level ?? 'DEBUG',
    maxFileSize: loggingConfig?.max_file_size ?? 20480, // 20MB
    maxBackups: loggingConfig?.max_backups ?? 10,
    compress: loggingConfig?.compress ?? true,
    suppressTensorflow: loggingConfig?.suppression?.tensorflow ?? true,
    suppressEssentia: loggingConfig?.suppression?.essentia ?? true,
    suppressLibrosa: loggingConfig?.suppression?.librosa ?? true,
    suppressMatplotlib: loggingConfig?.suppression?.matplotlib ?? true,
    suppressPil: loggingConfig?.suppression?.pil ?? true,
  });

  // Update local state when config changes
  React.useEffect(() => {
    const loggingConfig = config?.config || config || {};
    setSettings({
      logLevel: loggingConfig?.log_level ?? 'DEBUG',
      maxFileSize: loggingConfig?.max_file_size ?? 20480, // 20MB
      maxBackups: loggingConfig?.max_backups ?? 10,
      compress: loggingConfig?.compress ?? true,
      suppressTensorflow: loggingConfig?.suppression?.tensorflow ?? true,
      suppressEssentia: loggingConfig?.suppression?.essentia ?? true,
      suppressLibrosa: loggingConfig?.suppression?.librosa ?? true,
      suppressMatplotlib: loggingConfig?.suppression?.matplotlib ?? true,
      suppressPil: loggingConfig?.suppression?.pil ?? true,
    });
  }, [config]);

  const handleSave = () => {
    onSave({
      log_level: settings.logLevel,
      max_file_size: settings.maxFileSize,
      max_backups: settings.maxBackups,
      compress: settings.compress,
      suppression: {
        tensorflow: settings.suppressTensorflow,
        essentia: settings.suppressEssentia,
        librosa: settings.suppressLibrosa,
        matplotlib: settings.suppressMatplotlib,
        pil: settings.suppressPil,
      },
    });
  };

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-lg font-medium text-gray-900 dark:text-white">Logging Settings</h2>
      
      <div className="space-y-6">
        {/* Basic Logging Settings */}
        <div className="space-y-4">
          <h3 className="text-md font-medium text-gray-900 dark:text-white">Basic Settings</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Log Level
              </label>
              <select
                value={settings.logLevel}
                onChange={(e) => setSettings({ ...settings, logLevel: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
              >
                <option value="DEBUG">DEBUG</option>
                <option value="INFO">INFO</option>
                <option value="WARNING">WARNING</option>
                <option value="ERROR">ERROR</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Max File Size (KB)
              </label>
              <input
                type="number"
                value={settings.maxFileSize}
                onChange={(e) => setSettings({ ...settings, maxFileSize: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                min="1024"
                max="1048576"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Max Backups
              </label>
              <input
                type="number"
                value={settings.maxBackups}
                onChange={(e) => setSettings({ ...settings, maxBackups: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                min="1"
                max="100"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Compress Backups
              </label>
              <div className="flex items-center">
                <input
                  type="checkbox"
                  checked={settings.compress}
                  onChange={(e) => setSettings({ ...settings, compress: e.target.checked })}
                  className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                />
                <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Compress backup files</span>
              </div>
            </div>
          </div>
        </div>

        {/* Log Suppression Settings */}
        <div className="space-y-4">
          <h3 className="text-md font-medium text-gray-900 dark:text-white">Log Suppression</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-center">
              <input
                type="checkbox"
                checked={settings.suppressTensorflow}
                onChange={(e) => setSettings({ ...settings, suppressTensorflow: e.target.checked })}
                className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Suppress TensorFlow logs</span>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                checked={settings.suppressEssentia}
                onChange={(e) => setSettings({ ...settings, suppressEssentia: e.target.checked })}
                className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Suppress Essentia logs</span>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                checked={settings.suppressLibrosa}
                onChange={(e) => setSettings({ ...settings, suppressLibrosa: e.target.checked })}
                className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Suppress Librosa logs</span>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                checked={settings.suppressMatplotlib}
                onChange={(e) => setSettings({ ...settings, suppressMatplotlib: e.target.checked })}
                className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Suppress Matplotlib logs</span>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                checked={settings.suppressPil}
                onChange={(e) => setSettings({ ...settings, suppressPil: e.target.checked })}
                className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Suppress PIL logs</span>
            </div>
          </div>
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={isLoading}
          className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <Save className="w-4 h-4 mr-2" />
          )}
          Save Settings
        </button>
      </div>
    </div>
  );
};

// External APIs Settings Component
const ExternalAPISettings: React.FC<{ config: any; onSave: (data: any) => void; isLoading: boolean }> = ({ config, onSave, isLoading }) => {
  // Get the external config from app_settings configuration
  const externalConfig = config || {};
  
  const [settings, setSettings] = useState({
    musicbrainz: {
      enabled: externalConfig?.external_apis?.musicbrainz?.enabled ?? true,
      rateLimit: externalConfig?.external_apis?.musicbrainz?.rateLimit ?? 1.0,
      timeout: externalConfig?.external_apis?.musicbrainz?.timeout ?? 10,
      userAgent: externalConfig?.external_apis?.musicbrainz?.userAgent ?? "PlaylistApp/1.0 (dean@example.com)"
    },
    lastfm: {
      enabled: externalConfig?.external_apis?.lastfm?.enabled ?? true,
      apiKey: externalConfig?.external_apis?.lastfm?.apiKey ?? "2b07c1e8a2d308a749760ab8d579baa8",
      baseUrl: externalConfig?.external_apis?.lastfm?.baseUrl ?? "https://ws.audioscrobbler.com/2.0/",
      rateLimit: externalConfig?.external_apis?.lastfm?.rateLimit ?? 0.5,
      timeout: externalConfig?.external_apis?.lastfm?.timeout ?? 10
    },
    discogs: {
      enabled: externalConfig?.external_apis?.discogs?.enabled ?? false,
      apiKey: externalConfig?.external_apis?.discogs?.apiKey ?? "fHtjqUtbbXdHMqMBqvblPvKpOCInINhDTUCHvgcS",
      baseUrl: externalConfig?.external_apis?.discogs?.baseUrl ?? "https://api.discogs.com/",
      rateLimit: externalConfig?.external_apis?.discogs?.rateLimit ?? 1.0,
      timeout: externalConfig?.external_apis?.discogs?.timeout ?? 10,
      userAgent: externalConfig?.external_apis?.discogs?.userAgent ?? "PlaylistApp/1.0"
    }
  });

  // Update local state when config changes
  React.useEffect(() => {
    const externalConfig = config || {};
    setSettings({
      musicbrainz: {
        enabled: externalConfig?.external_apis?.external_apis?.musicbrainz?.enabled ?? true,
        rateLimit: externalConfig?.external_apis?.external_apis?.musicbrainz?.rateLimit ?? 1.0,
        timeout: externalConfig?.external_apis?.external_apis?.musicbrainz?.timeout ?? 10,
        userAgent: externalConfig?.external_apis?.external_apis?.musicbrainz?.userAgent ?? "PlaylistApp/1.0 (dean@example.com)"
      },
      lastfm: {
        enabled: externalConfig?.external_apis?.external_apis?.lastfm?.enabled ?? true,
        apiKey: externalConfig?.external_apis?.external_apis?.lastfm?.apiKey ?? "2b07c1e8a2d308a749760ab8d579baa8",
        baseUrl: externalConfig?.external_apis?.external_apis?.lastfm?.baseUrl ?? "https://ws.audioscrobbler.com/2.0/",
        rateLimit: externalConfig?.external_apis?.external_apis?.lastfm?.rateLimit ?? 0.5,
        timeout: externalConfig?.external_apis?.external_apis?.lastfm?.timeout ?? 10
      },
      discogs: {
        enabled: externalConfig?.external_apis?.external_apis?.discogs?.enabled ?? false,
        apiKey: externalConfig?.external_apis?.external_apis?.discogs?.apiKey ?? "fHtjqUtbbXdHMqMBqvblPvKpOCInINhDTUCHvgcS",
        baseUrl: externalConfig?.external_apis?.external_apis?.discogs?.baseUrl ?? "https://api.discogs.com/",
        rateLimit: externalConfig?.external_apis?.external_apis?.discogs?.rateLimit ?? 1.0,
        timeout: externalConfig?.external_apis?.external_apis?.discogs?.timeout ?? 10,
        userAgent: externalConfig?.external_apis?.external_apis?.discogs?.userAgent ?? "PlaylistApp/1.0"
      }
    });
  }, [config]);

  const handleSave = () => {
    onSave({
      external_apis: settings
    });
  };

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-lg font-medium text-gray-900 dark:text-white">External APIs</h2>
      
      <div className="space-y-8">
        {/* MusicBrainz */}
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
          <div className="flex items-center mb-4">
            <Music className="w-5 h-5 text-blue-500 mr-2" />
            <h3 className="text-md font-medium text-gray-900 dark:text-white">MusicBrainz</h3>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-center">
              <input
                type="checkbox"
                checked={settings.musicbrainz.enabled}
                onChange={(e) => setSettings({
                  ...settings,
                  musicbrainz: { ...settings.musicbrainz, enabled: e.target.checked }
                })}
                className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Enable MusicBrainz</span>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Rate Limit (requests/sec)
              </label>
              <input
                type="number"
                step="0.1"
                value={settings.musicbrainz.rateLimit}
                onChange={(e) => setSettings({
                  ...settings,
                  musicbrainz: { ...settings.musicbrainz, rateLimit: parseFloat(e.target.value) }
                })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                min="0.1"
                max="10"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Timeout (seconds)
              </label>
              <input
                type="number"
                value={settings.musicbrainz.timeout}
                onChange={(e) => setSettings({
                  ...settings,
                  musicbrainz: { ...settings.musicbrainz, timeout: parseInt(e.target.value) }
                })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                min="1"
                max="60"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                User Agent
              </label>
              <input
                type="text"
                value={settings.musicbrainz.userAgent}
                onChange={(e) => setSettings({
                  ...settings,
                  musicbrainz: { ...settings.musicbrainz, userAgent: e.target.value }
                })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
              />
            </div>
          </div>
        </div>

        {/* Last.fm */}
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
          <div className="flex items-center mb-4">
            <ExternalLink className="w-5 h-5 text-red-500 mr-2" />
            <h3 className="text-md font-medium text-gray-900 dark:text-white">Last.fm</h3>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-center">
              <input
                type="checkbox"
                checked={settings.lastfm.enabled}
                onChange={(e) => setSettings({
                  ...settings,
                  lastfm: { ...settings.lastfm, enabled: e.target.checked }
                })}
                className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Enable Last.fm</span>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                API Key
              </label>
              <input
                type="text"
                value={settings.lastfm.apiKey}
                onChange={(e) => setSettings({
                  ...settings,
                  lastfm: { ...settings.lastfm, apiKey: e.target.value }
                })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Rate Limit (requests/sec)
              </label>
              <input
                type="number"
                step="0.1"
                value={settings.lastfm.rateLimit}
                onChange={(e) => setSettings({
                  ...settings,
                  lastfm: { ...settings.lastfm, rateLimit: parseFloat(e.target.value) }
                })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                min="0.1"
                max="10"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Timeout (seconds)
              </label>
              <input
                type="number"
                value={settings.lastfm.timeout}
                onChange={(e) => setSettings({
                  ...settings,
                  lastfm: { ...settings.lastfm, timeout: parseInt(e.target.value) }
                })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                min="1"
                max="60"
              />
            </div>
          </div>
        </div>

        {/* Discogs */}
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
          <div className="flex items-center mb-4">
            <ExternalLink className="w-5 h-5 text-green-500 mr-2" />
            <h3 className="text-md font-medium text-gray-900 dark:text-white">Discogs</h3>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-center">
              <input
                type="checkbox"
                checked={settings.discogs.enabled}
                onChange={(e) => setSettings({
                  ...settings,
                  discogs: { ...settings.discogs, enabled: e.target.checked }
                })}
                className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Enable Discogs</span>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                API Key
              </label>
              <input
                type="text"
                value={settings.discogs.apiKey}
                onChange={(e) => setSettings({
                  ...settings,
                  discogs: { ...settings.discogs, apiKey: e.target.value }
                })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Rate Limit (requests/sec)
              </label>
              <input
                type="number"
                step="0.1"
                value={settings.discogs.rateLimit}
                onChange={(e) => setSettings({
                  ...settings,
                  discogs: { ...settings.discogs, rateLimit: parseFloat(e.target.value) }
                })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                min="0.1"
                max="10"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Timeout (seconds)
              </label>
              <input
                type="number"
                value={settings.discogs.timeout}
                onChange={(e) => setSettings({
                  ...settings,
                  discogs: { ...settings.discogs, timeout: parseInt(e.target.value) }
                })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                min="1"
                max="60"
              />
            </div>
          </div>
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={isLoading}
          className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <Save className="w-4 h-4 mr-2" />
          )}
          Save Settings
        </button>
      </div>
    </div>
  );
};



export default Settings;
