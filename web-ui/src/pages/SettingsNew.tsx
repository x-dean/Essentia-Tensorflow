import React, { useState } from 'react';
import { useConfig, useConfigSection } from '../contexts/ConfigContext';
import { Save, Loader2, AlertCircle, CheckCircle, Download, Upload } from 'lucide-react';
import { backupConfigs, restoreConfigs } from '../services/api';

const SettingsNew: React.FC = () => {
  const { state, clearError } = useConfig();
  const [success, setSuccess] = useState<string | null>(null);
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
      setTimeout(() => setSuccess(null), 3000);
    } catch (error: any) {
      console.error('Backup failed:', error);
    } finally {
      setIsBackingUp(false);
    }
  };

  const handleRestore = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      restoreConfigs(file)
        .then(() => {
          setSuccess('Configuration restored successfully!');
          setTimeout(() => setSuccess(null), 3000);
        })
        .catch((error) => {
          console.error('Restore failed:', error);
        });
      event.target.value = '';
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
            Configuration Settings
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Manage application configuration settings for discovery, analysis, database, and logging.
          </p>
        </div>

        {/* Backup/Restore Controls */}
        <div className="mb-6 flex gap-4">
          <button
            onClick={handleBackup}
            disabled={isBackingUp}
            className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
          >
            {isBackingUp ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Download className="w-4 h-4 mr-2" />
            )}
            Backup Configurations
          </button>

          <label className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 cursor-pointer">
            <Upload className="w-4 h-4 mr-2" />
            Restore Configurations
            <input
              type="file"
              accept=".zip"
              onChange={handleRestore}
              className="hidden"
            />
          </label>
        </div>

        {/* Error/Success Messages */}
        {state.error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-4 mb-6">
            <div className="flex">
              <AlertCircle className="w-5 h-5 text-red-400 mr-2" />
              <div className="text-sm text-red-700 dark:text-red-300">{state.error}</div>
              <button
                onClick={clearError}
                className="ml-auto text-red-400 hover:text-red-600"
              >
                ×
              </button>
            </div>
          </div>
        )}

        {success && (
          <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-md p-4 mb-6">
            <div className="flex">
              <CheckCircle className="w-5 h-5 text-green-400 mr-2" />
              <div className="text-sm text-green-700 dark:text-green-300">{success}</div>
            </div>
          </div>
        )}

        {/* Configuration Sections */}
        <div className="space-y-6">
          <AnalysisSettings />
          <DatabaseSettings />
          <LoggingSettings />
          <DiscoverySettings />
        </div>
      </div>
    </div>
  );
};

// Analysis Settings Component
const AnalysisSettings: React.FC = () => {
  const { config, isLoading, updateConfig } = useConfigSection('analysis');
  const [settings, setSettings] = useState<any>({});

  React.useEffect(() => {
    if (config) {
      setSettings({
        maxWorkers: config?.performance?.parallel_processing?.max_workers ?? 4,
        chunkSize: config?.performance?.parallel_processing?.chunk_size ?? 25,
        timeoutPerFile: config?.performance?.parallel_processing?.timeout_per_file ?? 600,
        memoryLimitMB: config?.performance?.parallel_processing?.memory_limit_mb ?? 512,
        enableTensorflow: config?.essentia?.algorithms?.enable_tensorflow ?? true,
        enableComplexRhythm: config?.essentia?.algorithms?.enable_complex_rhythm ?? true,
        enableComplexHarmonic: config?.essentia?.algorithms?.enable_complex_harmonic ?? true,
        enableBeatTracking: config?.essentia?.algorithms?.enable_beat_tracking ?? true,
        enableTempoTap: config?.essentia?.algorithms?.enable_tempo_tap ?? true,
        enableRhythmExtractor: config?.essentia?.algorithms?.enable_rhythm_extractor ?? true,
        enablePitchAnalysis: config?.essentia?.algorithms?.enable_pitch_analysis ?? true,
        enableChordDetection: config?.essentia?.algorithms?.enable_chord_detection ?? true,
        sampleRate: config?.essentia?.audio_processing?.sample_rate ?? 44100,
        channels: config?.essentia?.audio_processing?.channels ?? 1,
        frameSize: config?.essentia?.audio_processing?.frame_size ?? 2048,
        hopSize: config?.essentia?.audio_processing?.hop_size ?? 1024,
        minConfidenceThreshold: config?.quality?.min_confidence_threshold ?? 0.3,
        defaultTempo: config?.quality?.fallback_values?.tempo ?? 120.0,
        defaultKey: config?.quality?.fallback_values?.key ?? 'C',
        defaultScale: config?.quality?.fallback_values?.scale ?? 'major',
      });
    }
  }, [config]);

  const handleSave = async () => {
    await updateConfig({
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

  if (!config) return null;

  return (
    <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
      <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Analysis Settings</h2>
      
      <div className="space-y-6">
        {/* Performance Settings */}
        <div>
          <h3 className="text-md font-medium text-gray-900 dark:text-white mb-3">Performance</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
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
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
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
          </div>
        </div>

        {/* Algorithm Settings */}
        <div>
          <h3 className="text-md font-medium text-gray-900 dark:text-white mb-3">Algorithms</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              { key: 'enableTensorflow', label: 'Enable TensorFlow' },
              { key: 'enableComplexRhythm', label: 'Enable Complex Rhythm' },
              { key: 'enableComplexHarmonic', label: 'Enable Complex Harmonic' },
              { key: 'enableBeatTracking', label: 'Enable Beat Tracking' },
              { key: 'enableTempoTap', label: 'Enable Tempo Tap' },
              { key: 'enableRhythmExtractor', label: 'Enable Rhythm Extractor' },
              { key: 'enablePitchAnalysis', label: 'Enable Pitch Analysis' },
              { key: 'enableChordDetection', label: 'Enable Chord Detection' },
            ].map(({ key, label }) => (
              <div key={key} className="flex items-center">
                <input
                  type="checkbox"
                  id={key}
                  checked={settings[key]}
                  onChange={(e) => setSettings({ ...settings, [key]: e.target.checked })}
                  className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                />
                <label htmlFor={key} className="ml-2 block text-sm text-gray-900 dark:text-white">
                  {label}
                </label>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-6 flex justify-end">
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
          Save Analysis Settings
        </button>
      </div>
    </div>
  );
};

// Database Settings Component
const DatabaseSettings: React.FC = () => {
  const { config, isLoading, updateConfig } = useConfigSection('database');
  const [settings, setSettings] = useState<any>({});

  React.useEffect(() => {
    if (config) {
      setSettings({
        poolSize: config?.pool_size ?? 10,
        maxOverflow: config?.max_overflow ?? 20,
        poolTimeout: config?.pool_timeout ?? 30,
        poolRecycle: config?.pool_recycle ?? 3600,
        maxRetries: config?.retry_settings?.max_retries ?? 3,
        initialDelay: config?.retry_settings?.initial_delay ?? 1,
        backoffMultiplier: config?.retry_settings?.backoff_multiplier ?? 2,
        maxDelay: config?.retry_settings?.max_delay ?? 30,
        connectionTimeout: config?.connection_timeout ?? 30,
      });
    }
  }, [config]);

  const handleSave = async () => {
    await updateConfig({
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

  if (!config) return null;

  return (
    <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
      <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Database Settings</h2>
      
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
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
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
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
        </div>
      </div>

      <div className="mt-6 flex justify-end">
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
          Save Database Settings
        </button>
      </div>
    </div>
  );
};

// Logging Settings Component
const LoggingSettings: React.FC = () => {
  const { config, isLoading, updateConfig } = useConfigSection('logging');
  const [settings, setSettings] = useState<any>({});

  React.useEffect(() => {
    if (config) {
      setSettings({
        logLevel: config?.level ?? 'INFO',
        maxFileSize: config?.handlers?.file?.max_size ?? 10485760,
        maxBackups: config?.handlers?.file?.backup_count ?? 5,
        compress: config?.handlers?.file?.compress ?? true,
        suppressTensorflow: config?.suppression?.tensorflow ?? true,
        suppressEssentia: config?.suppression?.essentia ?? true,
        suppressLibrosa: config?.suppression?.librosa ?? true,
        suppressMatplotlib: config?.suppression?.matplotlib ?? true,
        suppressPil: config?.suppression?.pil ?? true,
      });
    }
  }, [config]);

  const handleSave = async () => {
    await updateConfig({
      level: settings.logLevel,
      handlers: {
        file: {
          max_size: settings.maxFileSize,
          backup_count: settings.maxBackups,
          compress: settings.compress,
        }
      },
      suppression: {
        tensorflow: settings.suppressTensorflow,
        essentia: settings.suppressEssentia,
        librosa: settings.suppressLibrosa,
        matplotlib: settings.suppressMatplotlib,
        pil: settings.suppressPil,
      },
    });
  };

  if (!config) return null;

  return (
    <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
      <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Logging Settings</h2>
      
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
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
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Max File Size (bytes)
            </label>
            <input
              type="number"
              value={settings.maxFileSize}
              onChange={(e) => setSettings({ ...settings, maxFileSize: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
              min="1024"
              max="104857600"
            />
          </div>
        </div>
      </div>

      <div className="mt-6 flex justify-end">
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
          Save Logging Settings
        </button>
      </div>
    </div>
  );
};

// Discovery Settings Component
const DiscoverySettings: React.FC = () => {
  const { config, isLoading, updateConfig } = useConfigSection('discovery');
  const [settings, setSettings] = useState<any>({});

  React.useEffect(() => {
    if (config) {
      setSettings({
        supportedExtensions: config?.supported_extensions?.join(', ') || '.mp3,.wav,.flac',
        batchSize: config?.scan_settings?.batch_size || 100,
        recursive: config?.scan_settings?.recursive ?? true,
        followSymlinks: config?.scan_settings?.follow_symlinks ?? false,
        maxFileSize: config?.scan_settings?.max_file_size ?? 1073741824,
      });
    }
  }, [config]);

  const handleSave = async () => {
    await updateConfig({
      supported_extensions: settings.supportedExtensions.split(',').map((ext: string) => ext.trim()),
      scan_settings: {
        batch_size: settings.batchSize,
        recursive: settings.recursive,
        follow_symlinks: settings.followSymlinks,
        max_file_size: settings.maxFileSize,
      },
    });
  };

  if (!config) return null;

  return (
    <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
      <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Discovery Settings</h2>
      
      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Supported Extensions (comma-separated)
          </label>
          <input
            type="text"
            value={settings.supportedExtensions}
            onChange={(e) => setSettings({ ...settings, supportedExtensions: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
            placeholder=".mp3,.wav,.flac,.ogg,.m4a"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Batch Size
            </label>
            <input
              type="number"
              value={settings.batchSize}
              onChange={(e) => setSettings({ ...settings, batchSize: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
              min="1"
              max="1000"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Max File Size (bytes)
            </label>
            <input
              type="number"
              value={settings.maxFileSize}
              onChange={(e) => setSettings({ ...settings, maxFileSize: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
              min="1024"
              max="2147483648"
            />
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center">
            <input
              type="checkbox"
              id="recursive"
              checked={settings.recursive}
              onChange={(e) => setSettings({ ...settings, recursive: e.target.checked })}
              className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
            />
            <label htmlFor="recursive" className="ml-2 block text-sm text-gray-900 dark:text-white">
              Recursive scanning
            </label>
          </div>
          <div className="flex items-center">
            <input
              type="checkbox"
              id="followSymlinks"
              checked={settings.followSymlinks}
              onChange={(e) => setSettings({ ...settings, followSymlinks: e.target.checked })}
              className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
            />
            <label htmlFor="followSymlinks" className="ml-2 block text-sm text-gray-900 dark:text-white">
              Follow symbolic links
            </label>
          </div>
        </div>
      </div>

      <div className="mt-6 flex justify-end">
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
          Save Discovery Settings
        </button>
      </div>
    </div>
  );
};

export default SettingsNew;
