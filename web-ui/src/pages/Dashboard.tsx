import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getHealth, triggerDiscovery, analyzeBatches, getTracks } from '../services/api';
import { Activity, Database, Music, Search, Play, Pause, RefreshCw, AlertCircle, CheckCircle, Clock, BarChart3, Loader2 } from 'lucide-react';
import LoadingSpinner from '../components/LoadingSpinner';
import StatusIndicator from '../components/StatusIndicator';

const Dashboard: React.FC = () => {
  const queryClient = useQueryClient();
  const [isTriggeringDiscovery, setIsTriggeringDiscovery] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [discoveryProgress, setDiscoveryProgress] = useState(0);
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [backgroundDiscovery, setBackgroundDiscovery] = useState(false);
  const [backgroundAnalysis, setBackgroundAnalysis] = useState(false);

  // Health check - API call for system status
  const { data: health, isLoading: healthLoading, error: healthError } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 60000, // Refresh every 60 seconds
    retry: 2,
    retryDelay: 5000,
  });

  // Basic stats - API call
  const { data: tracksData, isLoading: tracksLoading, error: tracksError } = useQuery({
    queryKey: ['tracks-summary'],
    queryFn: () => getTracks(1000, 0, false, false, 'summary'),
    refetchInterval: 30000, // Refresh every 30 seconds
    retry: 2,
    retryDelay: 5000,
  });

  // Recent tracks - API call
  const { data: recentTracksData, isLoading: recentTracksLoading, error: recentTracksError } = useQuery({
    queryKey: ['recent-tracks'],
    queryFn: () => getTracks(10, 0, false, false, 'summary'),
    refetchInterval: 30000, // Refresh every 30 seconds
    retry: 2,
    retryDelay: 5000,
  });

  // Calculate stats from tracks data
  const basicStats = tracksData && tracksData.tracks ? {
    total_files: tracksData.total_count,
    analyzed_files: tracksData.tracks.filter((t: any) => t && t.is_analyzed).length,
    unanalyzed_files: tracksData.tracks.filter((t: any) => t && !t.is_analyzed).length,
    files_with_metadata: tracksData.tracks.filter((t: any) => t && (t.title || t.artist)).length
  } : null;

  const recentTracks = recentTracksData?.tracks || [];

  // Mutations for write operations (API calls)
  const discoveryMutation = useMutation({
    mutationFn: triggerDiscovery,
    onSuccess: () => {
      setError(null);
      setBackgroundDiscovery(true);
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['health'] });
      queryClient.invalidateQueries({ queryKey: ['tracks-summary'] });
      queryClient.invalidateQueries({ queryKey: ['recent-tracks'] });
    },
    onError: (error: any) => {
      setError(`Discovery failed: ${error.response?.data?.detail || (error instanceof Error ? error.message : 'Unknown error')}`);
    },
  });

  const analysisMutation = useMutation({
    mutationFn: () => analyzeBatches(false), // Don't include TensorFlow by default for speed
    onSuccess: () => {
      setError(null);
      setBackgroundAnalysis(true);
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['health'] });
      queryClient.invalidateQueries({ queryKey: ['tracks-summary'] });
      queryClient.invalidateQueries({ queryKey: ['recent-tracks'] });
    },
    onError: (error: any) => {
      setError(`Analysis failed: ${error.response?.data?.detail || (error instanceof Error ? error.message : 'Unknown error')}`);
    },
  });

  // Simulate discovery progress
  useEffect(() => {
    let interval: number;
    if (isTriggeringDiscovery) {
      setDiscoveryProgress(0);
      interval = setInterval(() => {
        setDiscoveryProgress(prev => {
          if (prev >= 95) return prev; // Don't go to 100% until actually complete
          return prev + Math.random() * 15;
        });
      }, 1000);
    } else {
      setDiscoveryProgress(0);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isTriggeringDiscovery]);

  // Simulate analysis progress
  useEffect(() => {
    let interval: number;
    if (isAnalyzing) {
      setAnalysisProgress(0);
      interval = setInterval(() => {
        setAnalysisProgress(prev => {
          if (prev >= 95) return prev; // Don't go to 100% until actually complete
          return prev + Math.random() * 10;
        });
      }, 1500);
    } else {
      setAnalysisProgress(0);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isAnalyzing]);

  // Monitor background processes and reset when complete
  useEffect(() => {
    if (backgroundDiscovery && tracksData && tracksData.total_count > 0) {
      // Discovery likely completed when we have tracks
      const timer = setTimeout(() => {
        setBackgroundDiscovery(false);
      }, 5000); // Wait 5 seconds to ensure it's really done
      return () => clearTimeout(timer);
    }
  }, [backgroundDiscovery, tracksData]);

  useEffect(() => {
    if (backgroundAnalysis && basicStats && basicStats.analyzed_files > 0) {
      // Analysis likely completed when we have analyzed files
      const timer = setTimeout(() => {
        setBackgroundAnalysis(false);
      }, 5000); // Wait 5 seconds to ensure it's really done
      return () => clearTimeout(timer);
    }
  }, [backgroundAnalysis, basicStats]);

  const handleTriggerDiscovery = async () => {
    setIsTriggeringDiscovery(true);
    setError(null);
    try {
      await discoveryMutation.mutateAsync();
    } catch (error) {
      // Error is handled by mutation onError
    } finally {
      setIsTriggeringDiscovery(false);
    }
  };

  const handleStartAnalysis = async () => {
    setIsAnalyzing(true);
    setError(null);
    try {
      await analysisMutation.mutateAsync();
    } catch (error) {
      // Error is handled by mutation onError
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Calculate totals
  const totalTracks = basicStats?.total_files || 0;
  const analyzedTracks = basicStats?.analyzed_files || 0;
  const pendingTracks = basicStats?.unanalyzed_files || 0;
  const tracksWithMetadata = basicStats?.files_with_metadata || 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="mt-1 text-sm text-gray-500">
            Monitor your music library and analysis progress
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <StatusIndicator 
            status={healthLoading ? 'loading' : (health?.status === 'healthy' ? 'healthy' : 'unhealthy')}
            text={healthLoading ? 'Loading...' : (health?.status === 'healthy' ? 'System Healthy' : 'System Issues')}
          />
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <AlertCircle className="w-5 h-5 text-red-400 mr-2" />
            <div className="text-sm text-red-700">{error}</div>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="bg-white shadow rounded-lg p-6">
        <div className="flex flex-wrap gap-4">
          <div className="relative">
            <button
              onClick={handleTriggerDiscovery}
              disabled={isTriggeringDiscovery || backgroundDiscovery || isAnalyzing || backgroundAnalysis}
              className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:bg-gray-400 disabled:cursor-not-allowed disabled:hover:bg-gray-400"
            >
              {isTriggeringDiscovery || backgroundDiscovery ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Search className="w-4 h-4 mr-2" />
              )}
              {isTriggeringDiscovery ? 'Discovering...' : backgroundDiscovery ? 'Discovery in Progress...' : (isAnalyzing || backgroundAnalysis) ? 'Waiting for Analysis...' : 'Discover Files'}
            </button>
            
            {/* Progress indicator */}
            {(isTriggeringDiscovery || backgroundDiscovery) && (
              <div className="absolute -bottom-1 left-0 right-0 h-1 bg-gray-200 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-indigo-500 transition-all duration-300 ease-out"
                  style={{ width: `${discoveryProgress}%` }}
                />
              </div>
            )}
          </div>

          <div className="relative">
            <button
              onClick={handleStartAnalysis}
              disabled={isAnalyzing || backgroundAnalysis || pendingTracks === 0 || isTriggeringDiscovery || backgroundDiscovery}
              className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:bg-gray-400 disabled:cursor-not-allowed disabled:hover:bg-gray-400"
            >
              {isAnalyzing || backgroundAnalysis ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Play className="w-4 h-4 mr-2" />
              )}
              {isAnalyzing ? 'Analyzing...' : backgroundAnalysis ? 'Analysis in Progress...' : (isTriggeringDiscovery || backgroundDiscovery) ? 'Waiting for Discovery...' : `Analyze Files (${pendingTracks})`}
            </button>
            
            {/* Progress indicator */}
            {(isAnalyzing || backgroundAnalysis) && (
              <div className="absolute -bottom-1 left-0 right-0 h-1 bg-gray-200 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-green-500 transition-all duration-300 ease-out"
                  style={{ width: `${analysisProgress}%` }}
                />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Statistics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        {/* Total Tracks */}
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Music className="w-8 h-8 text-indigo-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Total Tracks</p>
              <p className="text-2xl font-semibold text-gray-900">
                {tracksLoading ? <LoadingSpinner size="sm" text="" /> : totalTracks}
              </p>
            </div>
          </div>
        </div>

        {/* Analyzed Tracks */}
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <CheckCircle className="w-8 h-8 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Analyzed</p>
              <p className="text-2xl font-semibold text-gray-900">
                {tracksLoading ? <LoadingSpinner size="sm" text="" /> : analyzedTracks}
              </p>
            </div>
          </div>
        </div>

        {/* Pending Analysis */}
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Clock className="w-8 h-8 text-yellow-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Pending</p>
              <p className="text-2xl font-semibold text-gray-900">
                {tracksLoading ? <LoadingSpinner size="sm" text="" /> : pendingTracks}
              </p>
            </div>
          </div>
        </div>

        {/* With Metadata */}
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Database className="w-8 h-8 text-purple-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">With Metadata</p>
              <p className="text-2xl font-semibold text-gray-900">
                {tracksLoading ? <LoadingSpinner size="sm" text="" /> : tracksWithMetadata}
              </p>
            </div>
          </div>
        </div>

        {/* Analysis Progress */}
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <BarChart3 className="w-8 h-8 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Progress</p>
              <p className="text-2xl font-semibold text-gray-900">
                {tracksLoading ? (
                  <LoadingSpinner size="sm" text="" />
                ) : totalTracks > 0 ? (
                  `${Math.round((analyzedTracks / totalTracks) * 100)}%`
                ) : (
                  '0%'
                )}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* System Status */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
          System Status
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-3 bg-blue-50 rounded-lg">
            <div className="flex items-center">
              <Database className="w-4 h-4 text-blue-500 mr-2" />
              <span className="text-sm font-medium text-blue-900">Database</span>
            </div>
            <div className="mt-1 text-sm text-blue-700">
              {healthLoading ? (
                <LoadingSpinner size="sm" text="" />
              ) : (
                health?.database || 'Unknown'
              )}
            </div>
          </div>

          <div className="p-3 bg-purple-50 rounded-lg">
            <div className="flex items-center">
              <Activity className="w-4 h-4 text-purple-500 mr-2" />
              <span className="text-sm font-medium text-purple-900">Essentia</span>
            </div>
            <div className="mt-1 text-sm text-purple-700">
              {healthLoading ? (
                <LoadingSpinner size="sm" text="" />
              ) : (
                health?.essentia_version || 'Unknown'
              )}
            </div>
          </div>

          <div className="p-3 bg-green-50 rounded-lg">
            <div className="flex items-center">
              <Activity className="w-4 h-4 text-green-500 mr-2" />
              <span className="text-sm font-medium text-green-900">TensorFlow</span>
            </div>
            <div className="mt-1 text-sm text-green-700">
              {healthLoading ? (
                <LoadingSpinner size="sm" text="" />
              ) : (
                `${health?.tensorflow_algorithms?.length || 0} models`
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Recent Tracks */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-3 py-2">
          <h3 className="text-xs font-medium text-gray-900 mb-2">
            Recent Tracks
          </h3>
          <div className="flow-root">
            {recentTracksLoading ? (
              <div className="flex items-center justify-center py-2">
                <LoadingSpinner size="sm" text="" />
              </div>
            ) : recentTracks && recentTracks.length > 0 ? (
              <div className="space-y-1">
                {recentTracks.slice(0, 3).map((track: any) => (
                  <div key={track.id} className="flex items-center justify-between py-1 px-2 bg-gray-50 rounded text-xs">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-1">
                        <Music className="w-2 h-2 text-gray-400 flex-shrink-0" />
                        <span className="font-medium text-gray-900 truncate">
                          {track.title || track.file_name}
                        </span>
                      </div>
                      <div className="flex items-center space-x-2 mt-0.5">
                        <span className="text-gray-500">
                          {track.artist || 'Unknown'}
                        </span>
                        {track.duration && (
                          <span className="text-gray-400">
                            {Math.floor(track.duration / 60)}:{String(Math.floor(track.duration % 60)).padStart(2, '0')}
                          </span>
                        )}
                        <span className="text-gray-400">
                          {track.file_extension?.toUpperCase()}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center space-x-1 ml-1">
                      {track.tempo && (
                        <span className="px-1 py-0.5 rounded bg-blue-100 text-blue-700 text-xs">
                          {Math.round(track.tempo)}
                        </span>
                      )}
                      <span
                        className={`px-1 py-0.5 rounded text-xs font-medium ${
                          track.status === 'analyzed' || track.status === 'faiss_analyzed'
                            ? 'bg-green-100 text-green-700'
                            : track.status === 'has_metadata'
                            ? 'bg-blue-100 text-blue-700'
                            : 'bg-yellow-100 text-yellow-700'
                        }`}
                      >
                        {track.status === 'analyzed' || track.status === 'faiss_analyzed' ? '✓' : 
                         track.status === 'has_metadata' ? 'ℹ' : '⏳'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-2">
                <p className="text-xs text-gray-500">No tracks</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
