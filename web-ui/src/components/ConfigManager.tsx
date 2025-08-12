import React, { useState, useEffect } from 'react';
import axios from 'axios';

interface ConfigMetrics {
  load_count: number;
  error_count: number;
  last_load_time: string | null;
  last_error_time: string | null;
  average_load_time: number;
  validation_errors_count?: number;
  validation_errors?: string[];
  success_rate: number;
}

interface ConfigHealth {
  uptime_seconds: number;
  total_config_loads: number;
  total_errors: number;
  overall_success_rate: number;
  recent_changes_last_hour: number;
  monitored_configs: number;
  change_history_size: number;
  status: 'healthy' | 'degraded' | 'unhealthy';
}

interface ConfigChangeEvent {
  timestamp: string;
  config_name: string;
  change_type: string;
  old_hash: string | null;
  new_hash: string | null;
  details: {
    config_keys: string[];
    config_size: number;
  };
}

const ConfigManager: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'overview' | 'metrics' | 'history' | 'validation'>('overview');
  const [health, setHealth] = useState<ConfigHealth | null>(null);
  const [metrics, setMetrics] = useState<Record<string, ConfigMetrics>>({});
  const [history, setHistory] = useState<ConfigChangeEvent[]>([]);
  const [validation, setValidation] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = async () => {
    try {
      const response = await axios.get('/api/config/monitor/health');
      setHealth(response.data.health);
    } catch (err) {
      setError('Failed to fetch health status');
    }
  };

  const fetchMetrics = async () => {
    try {
      const response = await axios.get('/api/config/monitor/metrics');
      setMetrics(response.data.metrics);
    } catch (err) {
      setError('Failed to fetch metrics');
    }
  };

  const fetchHistory = async () => {
    try {
      const response = await axios.get('/api/config/monitor/history?hours=24');
      setHistory(response.data.history);
    } catch (err) {
      setError('Failed to fetch history');
    }
  };

  const fetchValidation = async () => {
    try {
      const response = await axios.get('/api/config/validate');
      setValidation(response.data);
    } catch (err) {
      setError('Failed to fetch validation results');
    }
  };

  const resetMetrics = async () => {
    try {
      setLoading(true);
      await axios.post('/api/config/monitor/reset');
      await fetchMetrics();
      setError(null);
    } catch (err) {
      setError('Failed to reset metrics');
    } finally {
      setLoading(false);
    }
  };

  const clearHistory = async () => {
    try {
      setLoading(true);
      await axios.post('/api/config/monitor/clear-history');
      await fetchHistory();
      setError(null);
    } catch (err) {
      setError('Failed to clear history');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    fetchMetrics();
    fetchHistory();
    fetchValidation();
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'text-green-600';
      case 'degraded': return 'text-yellow-600';
      case 'unhealthy': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  const formatUptime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  const formatDateTime = (dateString: string | null) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleString();
  };

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <div className="flex">
          <div className="text-red-600">{error}</div>
          <button
            onClick={() => setError(null)}
            className="ml-auto text-red-600 hover:text-red-800"
          >
            ×
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Configuration Manager</h2>
        <div className="flex space-x-2">
          <button
            onClick={resetMetrics}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            Reset Metrics
          </button>
          <button
            onClick={clearHistory}
            disabled={loading}
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
          >
            Clear History
          </button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'overview', label: 'Overview' },
            { id: 'metrics', label: 'Metrics' },
            { id: 'history', label: 'History' },
            { id: 'validation', label: 'Validation' }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="mt-6">
        {activeTab === 'overview' && health && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-lg font-medium text-gray-900">System Health</h3>
              <div className="mt-4 space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-600">Status:</span>
                  <span className={`font-medium ${getStatusColor(health.status)}`}>
                    {health.status}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Uptime:</span>
                  <span className="font-medium">{formatUptime(health.uptime_seconds)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Success Rate:</span>
                  <span className="font-medium">{health.overall_success_rate.toFixed(1)}%</span>
                </div>
              </div>
            </div>

            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-lg font-medium text-gray-900">Load Statistics</h3>
              <div className="mt-4 space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-600">Total Loads:</span>
                  <span className="font-medium">{health.total_config_loads}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Total Errors:</span>
                  <span className="font-medium">{health.total_errors}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Monitored Configs:</span>
                  <span className="font-medium">{health.monitored_configs}</span>
                </div>
              </div>
            </div>

            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-lg font-medium text-gray-900">Recent Activity</h3>
              <div className="mt-4 space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-600">Changes (1h):</span>
                  <span className="font-medium">{health.recent_changes_last_hour}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">History Size:</span>
                  <span className="font-medium">{health.change_history_size}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'metrics' && (
          <div className="space-y-6">
            {Object.entries(metrics).map(([configName, configMetrics]) => (
              <div key={configName} className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-lg font-medium text-gray-900 capitalize">
                  {configName.replace('_', ' ')}
                </h3>
                <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <span className="text-sm text-gray-600">Load Count</span>
                    <div className="text-lg font-medium">{configMetrics.load_count}</div>
                  </div>
                  <div>
                    <span className="text-sm text-gray-600">Error Count</span>
                    <div className="text-lg font-medium">{configMetrics.error_count}</div>
                  </div>
                  <div>
                    <span className="text-sm text-gray-600">Success Rate</span>
                    <div className="text-lg font-medium">{configMetrics.success_rate.toFixed(1)}%</div>
                  </div>
                  <div>
                    <span className="text-sm text-gray-600">Avg Load Time</span>
                    <div className="text-lg font-medium">{(configMetrics.average_load_time * 1000).toFixed(1)}ms</div>
                  </div>
                </div>
                <div className="mt-4 text-sm text-gray-600">
                  <div>Last Load: {formatDateTime(configMetrics.last_load_time)}</div>
                  {configMetrics.last_error_time && (
                    <div>Last Error: {formatDateTime(configMetrics.last_error_time)}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'history' && (
          <div className="space-y-4">
            {history.map((event, index) => (
              <div key={index} className="bg-white p-4 rounded-lg shadow">
                <div className="flex justify-between items-start">
                  <div>
                    <h4 className="font-medium text-gray-900 capitalize">
                      {event.config_name.replace('_', ' ')} - {event.change_type}
                    </h4>
                    <p className="text-sm text-gray-600">
                      {formatDateTime(event.timestamp)}
                    </p>
                  </div>
                  <span className={`px-2 py-1 text-xs rounded ${
                    event.change_type === 'modified' ? 'bg-yellow-100 text-yellow-800' :
                    event.change_type === 'added' ? 'bg-green-100 text-green-800' :
                    'bg-red-100 text-red-800'
                  }`}>
                    {event.change_type}
                  </span>
                </div>
                <div className="mt-2 text-sm text-gray-600">
                  <div>Config Keys: {event.details.config_keys.join(', ')}</div>
                  <div>Size: {event.details.config_size} bytes</div>
                </div>
              </div>
            ))}
            {history.length === 0 && (
              <div className="text-center text-gray-500 py-8">
                No configuration changes in the last 24 hours
              </div>
            )}
          </div>
        )}

        {activeTab === 'validation' && validation && (
          <div className="space-y-6">
            {Object.entries(validation.validation_results).map(([configName, result]: [string, any]) => (
              <div key={configName} className="bg-white p-6 rounded-lg shadow">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-medium text-gray-900 capitalize">
                    {configName.replace('_', ' ')}
                  </h3>
                  <span className={`px-3 py-1 text-sm rounded ${
                    result.valid ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {result.valid ? 'Valid' : 'Invalid'}
                  </span>
                </div>
                {!result.valid && result.errors && (
                  <div className="mt-4">
                    <h4 className="font-medium text-red-800">Validation Errors:</h4>
                    <ul className="mt-2 space-y-1">
                      {result.errors.map((error: string, index: number) => (
                        <li key={index} className="text-sm text-red-600">• {error}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {result.config_keys && (
                  <div className="mt-4">
                    <h4 className="font-medium text-gray-800">Configuration Keys:</h4>
                    <div className="mt-2 text-sm text-gray-600">
                      {result.config_keys.join(', ')}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ConfigManager;
