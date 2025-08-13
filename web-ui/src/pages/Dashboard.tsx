import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getHealth, triggerDiscovery, analyzeBatches, getTracks, getDiscoveryStatus, triggerAnalysis, getAnalysisStatus, getAnalysisConfig, forceReanalyze, forceReenrichMetadata, toggleTensorFlow, toggleFAISS, getAnalysisModulesStatus, toggleAnalysisModule } from '../services/api';
import { Activity, Database, Music, Search, Play, Pause, RefreshCw, AlertCircle, CheckCircle, Clock, BarChart3, Loader2, Zap, RefreshCw as RefreshIcon, Settings, Power, PowerOff } from 'lucide-react';
import LoadingSpinner from '../components/LoadingSpinner';
import StatusIndicator from '../components/StatusIndicator';

const Dashboard: React.FC = () => {
  const queryClient = useQueryClient();
  const [isTriggeringDiscovery, setIsTriggeringDiscovery] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [discoveryProgress, setDiscoveryProgress] = useState(0);
  const [discoveryMessage, setDiscoveryMessage] = useState("");
  const [discoveryCount, setDiscoveryCount] = useState(0);
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [analysisMessage, setAnalysisMessage] = useState("");
  const [analysisCount, setAnalysisCount] = useState(0);
  const [backgroundDiscovery, setBackgroundDiscovery] = useState(false);
  const [backgroundAnalysis, setBackgroundAnalysis] = useState(false);
  const [isForceReanalyzing, setIsForceReanalyzing] = useState(false);
  const [isForceEnriching, setIsForceEnriching] = useState(false);

  // Health check - API call for system status
  const { data: health, isLoading: healthLoading, error: healthError } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 60000, // Refresh every 60 seconds
    retry: 2,
    retryDelay: 5000,
  });

  // Discovery status - API call for real progress
  const { data: discoveryStatus, isLoading: discoveryStatusLoading } = useQuery({
    queryKey: ['discovery-status'],
    queryFn: getDiscoveryStatus,
    refetchInterval: backgroundDiscovery ? 2000 : false, // Poll every 2 seconds when discovery is running
    retry: 2,
    retryDelay: 1000,
    enabled: backgroundDiscovery, // Only poll when discovery is active
  });

  // Analysis status - API call for real progress
  const { data: analysisStatus, isLoading: analysisStatusLoading } = useQuery({
    queryKey: ['analysis-status'],
    queryFn: getAnalysisStatus,
    refetchInterval: backgroundAnalysis ? 2000 : false, // Poll every 2 seconds when analysis is running
    retry: 2,
    retryDelay: 1000,
    enabled: backgroundAnalysis, // Only poll when analysis is active
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

  // Analysis configuration - API call to get TensorFlow setting
  const { data: analysisConfig, isLoading: analysisConfigLoading } = useQuery({
    queryKey: ['analysis-config'],
    queryFn: getAnalysisConfig,
    refetchInterval: 60000, // Refresh every 60 seconds
    retry: 2,
    retryDelay: 5000,
  });

  // Module status - API call to get module availability and status
  const { data: moduleStatus, isLoading: moduleStatusLoading } = useQuery({
    queryKey: ['analysis-modules-status'],
    queryFn: getAnalysisModulesStatus,
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
      setIsTriggeringDiscovery(false); // Button is no longer being clicked
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['health'] });
      queryClient.invalidateQueries({ queryKey: ['tracks-summary'] });
      queryClient.invalidateQueries({ queryKey: ['recent-tracks'] });
    },
    onError: (error: any) => {
      setError(`Discovery failed: ${error.response?.data?.detail || (error instanceof Error ? error.message : 'Unknown error')}`);
      setBackgroundDiscovery(false);
      setIsTriggeringDiscovery(false);
    },
  });

  const analysisMutation = useMutation({
    mutationFn: () => {
      // Use TensorFlow setting from configuration, default to false if not available
      const enableTensorflow = analysisConfig?.config?.essentia?.algorithms?.enable_tensorflow ?? false;
      return triggerAnalysis(enableTensorflow);
    },
    onSuccess: () => {
      setError(null);
      setBackgroundAnalysis(true);
      setIsAnalyzing(false); // Button is no longer being clicked
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['health'] });
      queryClient.invalidateQueries({ queryKey: ['tracks-summary'] });
      queryClient.invalidateQueries({ queryKey: ['recent-tracks'] });
    },
    onError: (error: any) => {
      setError(`Analysis failed: ${error.response?.data?.detail || (error instanceof Error ? error.message : 'Unknown error')}`);
      setBackgroundAnalysis(false);
      setIsAnalyzing(false);
    },
  });

  const forceReanalyzeMutation = useMutation({
    mutationFn: () => {
      // Use TensorFlow setting from configuration, default to false if not available
      const enableTensorflow = analysisConfig?.config?.essentia?.algorithms?.enable_tensorflow ?? false;
      return forceReanalyze(enableTensorflow);
    },
    onSuccess: () => {
      setError(null);
      setBackgroundAnalysis(true);
      setIsForceReanalyzing(false);
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['health'] });
      queryClient.invalidateQueries({ queryKey: ['tracks-summary'] });
      queryClient.invalidateQueries({ queryKey: ['recent-tracks'] });
    },
    onError: (error: any) => {
      setError(`Force reanalysis failed: ${error.response?.data?.detail || (error instanceof Error ? error.message : 'Unknown error')}`);
      setBackgroundAnalysis(false);
      setIsForceReanalyzing(false);
    },
  });

  const forceEnrichMutation = useMutation({
    mutationFn: () => forceReenrichMetadata(50), // Force enrich up to 50 files
    onSuccess: () => {
      setError(null);
      setIsForceEnriching(false);
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['tracks-summary'] });
      queryClient.invalidateQueries({ queryKey: ['recent-tracks'] });
    },
    onError: (error: any) => {
      setError(`Force enrichment failed: ${error.response?.data?.detail || (error instanceof Error ? error.message : 'Unknown error')}`);
      setIsForceEnriching(false);
    },
  });

  // Toggle mutations
  const toggleTensorFlowMutation = useMutation({
    mutationFn: (enabled: boolean) => toggleTensorFlow(enabled),
    onSuccess: () => {
      setError(null);
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['analysis-config'] });
      queryClient.invalidateQueries({ queryKey: ['health'] });
    },
    onError: (error: any) => {
      setError(`TensorFlow toggle failed: ${error.response?.data?.detail || (error instanceof Error ? error.message : 'Unknown error')}`);
    },
  });

  const toggleFAISSMutation = useMutation({
    mutationFn: (enabled: boolean) => toggleFAISS(enabled),
    onSuccess: () => {
      setError(null);
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['analysis-config'] });
      queryClient.invalidateQueries({ queryKey: ['health'] });
    },
    onError: (error: any) => {
      setError(`FAISS toggle failed: ${error.response?.data?.detail || (error instanceof Error ? error.message : 'Unknown error')}`);
    },
  });

  const toggleModuleMutation = useMutation({
    mutationFn: ({ moduleName, enabled }: { moduleName: string; enabled: boolean }) => 
      toggleAnalysisModule(moduleName, enabled),
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries({ queryKey: ['analysis-modules-status'] });
      queryClient.invalidateQueries({ queryKey: ['analysis-config'] });
    },
    onError: (error: any) => {
      setError(`Module toggle failed: ${error.response?.data?.detail || (error instanceof Error ? error.message : 'Unknown error')}`);
    },
  });

  // Toggle handlers
  const handleToggleTensorFlow = () => {
    const currentState = analysisConfig?.config?.essentia?.algorithms?.enable_tensorflow ?? false;
    toggleTensorFlowMutation.mutate(!currentState);
  };

  const handleToggleFAISS = () => {
    const currentState = analysisConfig?.config?.essentia?.algorithms?.enable_faiss ?? true;
    toggleFAISSMutation.mutate(!currentState);
  };

  // Update discovery progress from real API data
  useEffect(() => {
    if (discoveryStatus) {
      // Handle different response structures
      const status = discoveryStatus.discovery || discoveryStatus;
      
      if (status) {
        setDiscoveryProgress(status.progress || 0);
        setDiscoveryMessage(status.message || "");
        setDiscoveryCount(status.discovered_count || 0);
        
        // Update background state based on status
        if (status.status === "completed" || status.status === "failed" || status.status === "idle") {
          setBackgroundDiscovery(false);
          setIsTriggeringDiscovery(false);
          
          // Refresh data after completion
          queryClient.invalidateQueries({ queryKey: ['tracks-summary'] });
          queryClient.invalidateQueries({ queryKey: ['recent-tracks'] });
          queryClient.invalidateQueries({ queryKey: ['discovery-status'] });
        } else if (status.status === "running") {
          setBackgroundDiscovery(true);
        }
      }
    }
  }, [discoveryStatus, queryClient]);

  // Update analysis progress from real API data
  useEffect(() => {
    if (analysisStatus) {
      // Handle different response structures
      const status = analysisStatus.analysis || analysisStatus;
      
      if (status) {
        setAnalysisProgress(status.progress || 0);
        setAnalysisMessage(status.message || "");
        setAnalysisCount(status.completed_files || 0);
        
        // Update background state based on status
        if (status.status === "completed" || status.status === "failed" || status.status === "idle") {
          setBackgroundAnalysis(false);
          setIsAnalyzing(false);
          
          // Refresh data after completion
          queryClient.invalidateQueries({ queryKey: ['tracks-summary'] });
          queryClient.invalidateQueries({ queryKey: ['recent-tracks'] });
          queryClient.invalidateQueries({ queryKey: ['analysis-status'] });
        } else if (status.status === "running") {
          setBackgroundAnalysis(true);
        }
      }
    }
  }, [analysisStatus, queryClient]);

  // Additional effect to check initial status on component mount
  useEffect(() => {
    const checkInitialStatus = async () => {
      try {
        // Check discovery status
        const discoveryResponse = await getDiscoveryStatus();
        const discoveryData = discoveryResponse.discovery || discoveryResponse;
        if (discoveryData && (discoveryData.status === "completed" || discoveryData.status === "failed" || discoveryData.status === "idle")) {
          setBackgroundDiscovery(false);
          setIsTriggeringDiscovery(false);
        } else if (discoveryData && discoveryData.status === "running") {
          setBackgroundDiscovery(true);
        }

        // Check analysis status
        const analysisResponse = await getAnalysisStatus();
        const analysisData = analysisResponse.analysis || analysisResponse;
        if (analysisData && (analysisData.status === "completed" || analysisData.status === "failed" || analysisData.status === "idle")) {
          setBackgroundAnalysis(false);
          setIsAnalyzing(false);
        } else if (analysisData && analysisData.status === "running") {
          setBackgroundAnalysis(true);
        }
      } catch (error) {
        console.warn('Failed to check initial status:', error);
      }
    };

    checkInitialStatus();
  }, []);

  // Force refresh status when background processes change
  useEffect(() => {
    if (!backgroundDiscovery) {
      // When discovery stops, invalidate the status query to clear any cached data
      queryClient.invalidateQueries({ queryKey: ['discovery-status'] });
    }
  }, [backgroundDiscovery, queryClient]);

  useEffect(() => {
    if (!backgroundAnalysis) {
      // When analysis stops, invalidate the status query to clear any cached data
      queryClient.invalidateQueries({ queryKey: ['analysis-status'] });
    }
  }, [backgroundAnalysis, queryClient]);

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

  const handleForceReanalyze = async () => {
    setIsForceReanalyzing(true);
    setError(null);
    try {
      await forceReanalyzeMutation.mutateAsync();
    } catch (error) {
      // Error is handled by mutation onError
    } finally {
      setIsForceReanalyzing(false);
    }
  };

  const handleForceEnrich = async () => {
    setIsForceEnriching(true);
    setError(null);
    try {
      await forceEnrichMutation.mutateAsync();
    } catch (error) {
      // Error is handled by mutation onError
    } finally {
      setIsForceEnriching(false);
    }
  };

  // Manual refresh function to force check status
  const handleRefreshStatus = async () => {
    try {
      // Force check discovery status
      const discoveryResponse = await getDiscoveryStatus();
      const discoveryData = discoveryResponse.discovery || discoveryResponse;
      if (discoveryData && (discoveryData.status === "completed" || discoveryData.status === "failed" || discoveryData.status === "idle")) {
        setBackgroundDiscovery(false);
        setIsTriggeringDiscovery(false);
      } else if (discoveryData && discoveryData.status === "running") {
        setBackgroundDiscovery(true);
      }

      // Force check analysis status
      const analysisResponse = await getAnalysisStatus();
      const analysisData = analysisResponse.analysis || analysisResponse;
      if (analysisData && (analysisData.status === "completed" || analysisData.status === "failed" || analysisData.status === "idle")) {
        setBackgroundAnalysis(false);
        setIsAnalyzing(false);
      } else if (analysisData && analysisData.status === "running") {
        setBackgroundAnalysis(true);
      }

      // Refresh all data
      queryClient.invalidateQueries({ queryKey: ['tracks-summary'] });
      queryClient.invalidateQueries({ queryKey: ['recent-tracks'] });
      queryClient.invalidateQueries({ queryKey: ['discovery-status'] });
      queryClient.invalidateQueries({ queryKey: ['analysis-status'] });
    } catch (error) {
      console.warn('Failed to refresh status:', error);
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
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Monitor your music library and analysis progress
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <button
            onClick={handleRefreshStatus}
            className="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 shadow-sm text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            title="Refresh status"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <StatusIndicator 
            status={healthLoading ? 'loading' : (health?.status === 'healthy' ? 'healthy' : 'unhealthy')}
            text={healthLoading ? 'Loading...' : (health?.status === 'healthy' ? 'System Healthy' : 'System Issues')}
          />
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-4">
          <div className="flex">
            <AlertCircle className="w-5 h-5 text-red-400 mr-2" />
            <div className="text-sm text-red-700 dark:text-red-300">{error}</div>
          </div>
        </div>
      )}

      {/* Main Action Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Discovery Card */}
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-gray-900 dark:text-white">Music Discovery</h3>
            <Search className="w-4 h-4 text-indigo-600" />
          </div>
          
          <div className="space-y-3">
            <div className="relative">
              <button
                onClick={handleTriggerDiscovery}
                disabled={isTriggeringDiscovery || backgroundDiscovery || backgroundAnalysis}
                className="w-full inline-flex items-center justify-center px-3 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:bg-gray-400 disabled:cursor-not-allowed disabled:hover:bg-gray-400 transition-colors"
              >
                {isTriggeringDiscovery || backgroundDiscovery ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Search className="w-4 h-4 mr-2" />
                )}
                {isTriggeringDiscovery ? 'Discovering...' : 
                 backgroundDiscovery ? (discoveryMessage || 'Discovery in Progress...') : 
                 'Discover Music Files'}
              </button>
              
              {/* Progress indicator */}
              {(isTriggeringDiscovery || backgroundDiscovery) && (
                <div className="absolute -bottom-1 left-0 right-0 h-1 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-indigo-500 transition-all duration-300 ease-out"
                    style={{ width: `${discoveryProgress}%` }}
                  />
                </div>
              )}
            </div>
            
            <div className="text-xs text-gray-600 dark:text-gray-400">
              <p>Scans your music directory for new files and enriches metadata automatically.</p>
              {discoveryCount > 0 && (
                <p className="mt-1 font-medium text-indigo-600 dark:text-indigo-400">
                  Found {discoveryCount} files
                </p>
              )}
            </div>

            {/* Force Enrich under Discovery */}
            <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={handleForceEnrich}
                disabled={isForceEnriching || tracksWithMetadata === 0}
                className="inline-flex items-center px-2 py-1 border border-gray-300 dark:border-gray-600 shadow-sm text-xs font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                title="Force re-enrich metadata (useful when enabling new external APIs)"
              >
                {isForceEnriching ? (
                  <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                ) : (
                  <RefreshIcon className="w-3 h-3 mr-1" />
                )}
                {isForceEnriching ? 'Enriching...' : 'Force Enrich'}
              </button>
            </div>
          </div>
        </div>

        {/* Analysis Card */}
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-gray-900 dark:text-white">Audio Analysis</h3>
            <BarChart3 className="w-4 h-4 text-green-600" />
          </div>
          
          <div className="space-y-3">
            <div className="relative">
              <button
                onClick={handleStartAnalysis}
                disabled={isAnalyzing || backgroundAnalysis || pendingTracks === 0 || isTriggeringDiscovery || backgroundDiscovery}
                className="w-full inline-flex items-center justify-center px-3 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:bg-gray-400 disabled:cursor-not-allowed disabled:hover:bg-gray-400 transition-colors"
              >
                {isAnalyzing || backgroundAnalysis ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Play className="w-4 h-4 mr-2" />
                )}
                {isAnalyzing ? 'Analyzing...' : 
                 backgroundAnalysis ? (analysisMessage || 'Analysis in Progress...') : 
                 (isTriggeringDiscovery || backgroundDiscovery) ? 'Waiting for Discovery...' : 
                 `Analyze Files (${pendingTracks} pending)`}
              </button>
              
              {/* Progress indicator */}
              {(isAnalyzing || backgroundAnalysis) && (
                <div className="absolute -bottom-1 left-0 right-0 h-1 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-green-500 transition-all duration-300 ease-out"
                    style={{ width: `${analysisProgress}%` }}
                  />
                </div>
              )}
            </div>
            
            <div className="text-xs text-gray-600 dark:text-gray-400">
              <p>Extracts audio features and musical characteristics from your tracks.</p>
              {analysisConfigLoading ? (
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300">
                  <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                  Loading...
                </span>
              ) : (
                <div className="flex flex-wrap gap-2 mt-1">
                  <button
                    onClick={handleToggleTensorFlow}
                    disabled={toggleTensorFlowMutation.isPending}
                    className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium transition-colors ${
                      analysisConfig?.config?.essentia?.algorithms?.enable_tensorflow 
                        ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-900/50' 
                        : 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                    } ${toggleTensorFlowMutation.isPending ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                    title={`Click to ${analysisConfig?.config?.essentia?.algorithms?.enable_tensorflow ? 'disable' : 'enable'} TensorFlow`}
                  >
                    {toggleTensorFlowMutation.isPending ? (
                      <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                    ) : analysisConfig?.config?.essentia?.algorithms?.enable_tensorflow ? (
                      <Power className="w-3 h-3 mr-1" />
                    ) : (
                      <PowerOff className="w-3 h-3 mr-1" />
                    )}
                    {analysisConfig?.config?.essentia?.algorithms?.enable_tensorflow ? 'TensorFlow Enabled' : 'TensorFlow Disabled'}
                  </button>
                  <button
                    onClick={handleToggleFAISS}
                    disabled={toggleFAISSMutation.isPending}
                    className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium transition-colors ${
                      analysisConfig?.config?.essentia?.algorithms?.enable_faiss 
                        ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 hover:bg-green-200 dark:hover:bg-green-900/50' 
                        : 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                    } ${toggleFAISSMutation.isPending ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                    title={`Click to ${analysisConfig?.config?.essentia?.algorithms?.enable_faiss ? 'disable' : 'enable'} FAISS`}
                  >
                    {toggleFAISSMutation.isPending ? (
                      <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                    ) : analysisConfig?.config?.essentia?.algorithms?.enable_faiss ? (
                      <Power className="w-3 h-3 mr-1" />
                    ) : (
                      <PowerOff className="w-3 h-3 mr-1" />
                    )}
                    {analysisConfig?.config?.essentia?.algorithms?.enable_faiss ? 'FAISS Enabled' : 'FAISS Disabled'}
                  </button>
                </div>
              )}
            </div>

            {/* Force Re-analyze under Analysis */}
            <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={handleForceReanalyze}
                disabled={isForceReanalyzing || backgroundAnalysis || totalTracks === 0 || isTriggeringDiscovery || backgroundDiscovery}
                className="inline-flex items-center px-2 py-1 border border-gray-300 dark:border-gray-600 shadow-sm text-xs font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-orange-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                title="Force re-analyze all files (overwrites existing analysis)"
              >
                {isForceReanalyzing ? (
                  <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                ) : (
                  <Zap className="w-3 h-3 mr-1" />
                )}
                {isForceReanalyzing ? 'Re-analyzing...' : 'Force Re-analyze'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Statistics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        {/* Total Tracks */}
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Music className="w-8 h-8 text-indigo-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Total Tracks</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                {tracksLoading ? <LoadingSpinner size="sm" text="" /> : totalTracks}
              </p>
            </div>
          </div>
        </div>

        {/* Analyzed Tracks */}
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <CheckCircle className="w-8 h-8 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Analyzed</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                {tracksLoading ? <LoadingSpinner size="sm" text="" /> : analyzedTracks}
              </p>
            </div>
          </div>
        </div>

        {/* Pending Analysis */}
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Clock className="w-8 h-8 text-yellow-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Pending</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                {tracksLoading ? <LoadingSpinner size="sm" text="" /> : pendingTracks}
              </p>
            </div>
          </div>
        </div>

        {/* With Metadata */}
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Database className="w-8 h-8 text-purple-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">With Metadata</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                {tracksLoading ? <LoadingSpinner size="sm" text="" /> : tracksWithMetadata}
              </p>
            </div>
          </div>
        </div>

        {/* Analysis Progress */}
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <BarChart3 className="w-8 h-8 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Progress</p>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">
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
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
        <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white mb-4">
          System Status
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
            <div className="flex items-center">
              <Database className="w-4 h-4 text-blue-500 mr-2" />
              <span className="text-sm font-medium text-blue-900 dark:text-blue-100">Database</span>
            </div>
            <div className="mt-1 text-sm text-blue-700 dark:text-blue-300">
              {healthLoading ? (
                <LoadingSpinner size="sm" text="" />
              ) : (
                health?.database || 'Unknown'
              )}
            </div>
          </div>

          <div className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
            <div className="flex items-center">
              <Activity className="w-4 h-4 text-purple-500 mr-2" />
              <span className="text-sm font-medium text-purple-900 dark:text-purple-100">Essentia</span>
            </div>
            <div className="mt-1 text-sm text-purple-700 dark:text-purple-300">
              {healthLoading ? (
                <LoadingSpinner size="sm" text="" />
              ) : (
                health?.essentia_version || 'Unknown'
              )}
            </div>
          </div>

          <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
            <div className="flex items-center">
              <Activity className="w-4 h-4 text-green-500 mr-2" />
              <span className="text-sm font-medium text-green-900 dark:text-green-100">TensorFlow</span>
            </div>
            <div className="mt-1 text-sm text-green-700 dark:text-green-300">
              {healthLoading ? (
                <LoadingSpinner size="sm" text="" />
              ) : (
                `${health?.tensorflow_algorithms?.length || 0} models`
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Analysis Modules Status */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
        <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white mb-4">
          Analysis Modules
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Essentia Module */}
          <div className="p-4 border rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-medium text-gray-900 dark:text-white">Essentia</h4>
              <StatusIndicator status={moduleStatus?.modules?.essentia?.available ? 'healthy' : 'unhealthy'} />
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
              {moduleStatus?.modules?.essentia?.description || 'Audio feature extraction'}
            </p>
            <div className="flex items-center">
              <span className="text-xs text-gray-500 dark:text-gray-400 mr-2">Status:</span>
              <span className={`text-xs px-2 py-1 rounded ${
                moduleStatus?.modules?.essentia?.enabled 
                  ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
                  : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400'
              }`}>
                {moduleStatus?.modules?.essentia?.enabled ? 'Enabled' : 'Disabled'}
              </span>
            </div>
          </div>

          {/* TensorFlow Module */}
          <div className="p-4 border rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-medium text-gray-900 dark:text-white">TensorFlow</h4>
              <StatusIndicator status={moduleStatus?.modules?.tensorflow?.available ? 'healthy' : 'unhealthy'} />
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
              {moduleStatus?.modules?.tensorflow?.description || 'Machine learning classification'}
            </p>
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <span className="text-xs text-gray-500 dark:text-gray-400 mr-2">Status:</span>
                <span className={`text-xs px-2 py-1 rounded ${
                  moduleStatus?.modules?.tensorflow?.enabled 
                    ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
                    : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400'
                }`}>
                  {moduleStatus?.modules?.tensorflow?.enabled ? 'Enabled' : 'Disabled'}
                </span>
              </div>
              <button
                onClick={() => toggleModuleMutation.mutate({ 
                  moduleName: 'tensorflow', 
                  enabled: !moduleStatus?.modules?.tensorflow?.enabled 
                })}
                disabled={!moduleStatus?.modules?.tensorflow?.available || toggleModuleMutation.isPending}
                className={`text-xs px-2 py-1 rounded ${
                  moduleStatus?.modules?.tensorflow?.enabled
                    ? 'bg-red-100 text-red-800 hover:bg-red-200 dark:bg-red-900/20 dark:text-red-400'
                    : 'bg-green-100 text-green-800 hover:bg-green-200 dark:bg-green-900/20 dark:text-green-400'
                } disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                {toggleModuleMutation.isPending ? '...' : (moduleStatus?.modules?.tensorflow?.enabled ? 'Disable' : 'Enable')}
              </button>
            </div>
          </div>

          {/* FAISS Module */}
          <div className="p-4 border rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-medium text-gray-900 dark:text-white">FAISS</h4>
              <StatusIndicator status={moduleStatus?.modules?.faiss?.available ? 'healthy' : 'unhealthy'} />
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
              {moduleStatus?.modules?.faiss?.description || 'Vector similarity search'}
            </p>
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <span className="text-xs text-gray-500 dark:text-gray-400 mr-2">Status:</span>
                <span className={`text-xs px-2 py-1 rounded ${
                  moduleStatus?.modules?.faiss?.enabled 
                    ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
                    : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400'
                }`}>
                  {moduleStatus?.modules?.faiss?.enabled ? 'Enabled' : 'Disabled'}
                </span>
              </div>
              <button
                onClick={() => toggleModuleMutation.mutate({ 
                  moduleName: 'faiss', 
                  enabled: !moduleStatus?.modules?.faiss?.enabled 
                })}
                disabled={!moduleStatus?.modules?.faiss?.available || toggleModuleMutation.isPending}
                className={`text-xs px-2 py-1 rounded ${
                  moduleStatus?.modules?.faiss?.enabled
                    ? 'bg-red-100 text-red-800 hover:bg-red-200 dark:bg-red-900/20 dark:text-red-400'
                    : 'bg-green-100 text-green-800 hover:bg-green-200 dark:bg-green-900/20 dark:text-green-400'
                } disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                {toggleModuleMutation.isPending ? '...' : (moduleStatus?.modules?.faiss?.enabled ? 'Disable' : 'Enable')}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Tracks */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg">
        <div className="px-3 py-2">
          <h3 className="text-xs font-medium text-gray-900 dark:text-white mb-2">
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
                  <div key={track.id} className="flex items-center justify-between py-1 px-2 bg-gray-50 dark:bg-gray-700 rounded text-xs">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-1">
                        <Music className="w-2 h-2 text-gray-400 flex-shrink-0" />
                        <span className="font-medium text-gray-900 dark:text-white truncate">
                          {track.title || track.file_name}
                        </span>
                      </div>
                      <div className="flex items-center space-x-2 mt-0.5">
                        <span className="text-gray-500 dark:text-gray-400">
                          {track.artist || 'Unknown'}
                        </span>
                        {track.duration && (
                          <span className="text-gray-400 dark:text-gray-500">
                            {Math.floor(track.duration / 60)}:{String(Math.floor(track.duration % 60)).padStart(2, '0')}
                          </span>
                        )}
                        <span className="text-gray-400 dark:text-gray-500">
                          {track.file_extension?.toUpperCase()}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center space-x-1 ml-1">
                      {track.tempo && (
                        <span className="px-1 py-0.5 rounded bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs">
                          {Math.round(track.tempo)}
                        </span>
                      )}
                      <span
                        className={`px-1 py-0.5 rounded text-xs font-medium ${
                          track.status === 'analyzed' || track.status === 'faiss_analyzed'
                            ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                            : track.status === 'has_metadata'
                            ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                            : 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300'
                        }`}
                      >
                        {track.status === 'analyzed' || track.status === 'faiss_analyzed' ? '' : 
                         track.status === 'has_metadata' ? 'ℹ' : ''}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-2">
                <p className="text-xs text-gray-500 dark:text-gray-400">No tracks</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
