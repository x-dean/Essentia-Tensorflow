import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getHealth, triggerDiscovery, analyzeBatches, getTracks, getDiscoveryStatus, triggerAnalysis, getAnalysisStatus, getAnalysisConfig, forceReanalyze, forceReenrichMetadata, toggleTensorFlow, toggleFAISS, getAnalysisModulesStatus, toggleAnalysisModule } from '../services/api';
import { REFRESH_INTERVALS, FORCE_ENRICH_LIMIT, TRACKS_LIMIT, RECENT_TRACKS_LIMIT } from '../types/dashboard';
import { useState, useEffect } from 'react';

export const useDashboardData = () => {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [backgroundDiscovery, setBackgroundDiscovery] = useState(false);
  const [backgroundAnalysis, setBackgroundAnalysis] = useState(false);

  // Health check
  const { data: health, isLoading: healthLoading, error: healthError } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: REFRESH_INTERVALS.HEALTH,
    retry: 2,
    retryDelay: 5000,
  });

  // Discovery status
  const { data: discoveryStatus, isLoading: discoveryStatusLoading } = useQuery({
    queryKey: ['discovery-status'],
    queryFn: getDiscoveryStatus,
    refetchInterval: backgroundDiscovery ? REFRESH_INTERVALS.DISCOVERY : false,
    retry: 2,
    retryDelay: 1000,
    enabled: backgroundDiscovery,
  });

  // Analysis status
  const { data: analysisStatus, isLoading: analysisStatusLoading } = useQuery({
    queryKey: ['analysis-status'],
    queryFn: getAnalysisStatus,
    refetchInterval: backgroundAnalysis ? REFRESH_INTERVALS.ANALYSIS : false,
    retry: 2,
    retryDelay: 1000,
    enabled: backgroundAnalysis,
  });

  // Basic stats
  const { data: tracksData, isLoading: tracksLoading, error: tracksError } = useQuery({
    queryKey: ['tracks-summary'],
    queryFn: () => getTracks(TRACKS_LIMIT, 0, false, false, 'summary'),
    refetchInterval: REFRESH_INTERVALS.TRACKS,
    retry: 2,
    retryDelay: 5000,
  });

  // Recent tracks
  const { data: recentTracksData, isLoading: recentTracksLoading, error: recentTracksError } = useQuery({
    queryKey: ['recent-tracks'],
    queryFn: () => getTracks(RECENT_TRACKS_LIMIT, 0, false, false, 'summary'),
    refetchInterval: REFRESH_INTERVALS.TRACKS,
    retry: 2,
    retryDelay: 5000,
  });

  // Analysis configuration
  const { data: analysisConfig, isLoading: analysisConfigLoading } = useQuery({
    queryKey: ['analysis-config'],
    queryFn: getAnalysisConfig,
    refetchInterval: REFRESH_INTERVALS.CONFIG,
    retry: 2,
    retryDelay: 5000,
  });

  // Module status
  const { data: moduleStatus, isLoading: moduleStatusLoading } = useQuery({
    queryKey: ['analysis-modules-status'],
    queryFn: getAnalysisModulesStatus,
    refetchInterval: REFRESH_INTERVALS.MODULES,
    retry: 2,
    retryDelay: 5000,
  });

  // Mutations
  const discoveryMutation = useMutation({
    mutationFn: triggerDiscovery,
    onSuccess: () => {
      setError(null);
      setBackgroundDiscovery(true);
      queryClient.invalidateQueries({ queryKey: ['health'] });
      queryClient.invalidateQueries({ queryKey: ['tracks-summary'] });
      queryClient.invalidateQueries({ queryKey: ['recent-tracks'] });
    },
    onError: (error: any) => {
      setError(`Discovery failed: ${error.response?.data?.detail || (error instanceof Error ? error.message : 'Unknown error')}`);
      setBackgroundDiscovery(false);
    },
  });

  const analysisMutation = useMutation({
    mutationFn: () => {
      const enableTensorflow = analysisConfig?.config?.essentia?.algorithms?.enable_tensorflow ?? false;
      return triggerAnalysis(enableTensorflow);
    },
    onSuccess: () => {
      setError(null);
      setBackgroundAnalysis(true);
      queryClient.invalidateQueries({ queryKey: ['health'] });
      queryClient.invalidateQueries({ queryKey: ['tracks-summary'] });
      queryClient.invalidateQueries({ queryKey: ['recent-tracks'] });
    },
    onError: (error: any) => {
      setError(`Analysis failed: ${error.response?.data?.detail || (error instanceof Error ? error.message : 'Unknown error')}`);
      setBackgroundAnalysis(false);
    },
  });

  const forceReanalyzeMutation = useMutation({
    mutationFn: () => {
      const enableTensorflow = analysisConfig?.config?.essentia?.algorithms?.enable_tensorflow ?? false;
      return forceReanalyze(enableTensorflow);
    },
    onSuccess: () => {
      setError(null);
      setBackgroundAnalysis(true);
      queryClient.invalidateQueries({ queryKey: ['health'] });
      queryClient.invalidateQueries({ queryKey: ['tracks-summary'] });
      queryClient.invalidateQueries({ queryKey: ['recent-tracks'] });
    },
    onError: (error: any) => {
      setError(`Force reanalysis failed: ${error.response?.data?.detail || (error instanceof Error ? error.message : 'Unknown error')}`);
      setBackgroundAnalysis(false);
    },
  });

  const forceEnrichMutation = useMutation({
    mutationFn: () => forceReenrichMetadata(FORCE_ENRICH_LIMIT),
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries({ queryKey: ['tracks-summary'] });
      queryClient.invalidateQueries({ queryKey: ['recent-tracks'] });
    },
    onError: (error: any) => {
      setError(`Force enrichment failed: ${error.response?.data?.detail || (error instanceof Error ? error.message : 'Unknown error')}`);
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

  // Update background states based on status
  useEffect(() => {
    if (discoveryStatus) {
      const status = discoveryStatus.discovery || discoveryStatus;
      if (status) {
        if (status.status === "completed" || status.status === "failed" || status.status === "idle") {
          setBackgroundDiscovery(false);
          queryClient.invalidateQueries({ queryKey: ['tracks-summary'] });
          queryClient.invalidateQueries({ queryKey: ['recent-tracks'] });
          queryClient.invalidateQueries({ queryKey: ['discovery-status'] });
        } else if (status.status === "running") {
          setBackgroundDiscovery(true);
        }
      }
    }
  }, [discoveryStatus, queryClient]);

  useEffect(() => {
    if (analysisStatus) {
      const status = analysisStatus.analysis || analysisStatus;
      if (status) {
        if (status.status === "completed" || status.status === "failed" || status.status === "idle") {
          setBackgroundAnalysis(false);
          queryClient.invalidateQueries({ queryKey: ['tracks-summary'] });
          queryClient.invalidateQueries({ queryKey: ['recent-tracks'] });
          queryClient.invalidateQueries({ queryKey: ['analysis-status'] });
        } else if (status.status === "running") {
          setBackgroundAnalysis(true);
        }
      }
    }
  }, [analysisStatus, queryClient]);

  // Clear error when component unmounts or when operations complete
  useEffect(() => {
    if (!backgroundDiscovery && !backgroundAnalysis) {
      setError(null);
    }
  }, [backgroundDiscovery, backgroundAnalysis]);

  return {
    // Data
    health,
    healthLoading,
    healthError,
    discoveryStatus,
    discoveryStatusLoading,
    analysisStatus,
    analysisStatusLoading,
    tracksData,
    tracksLoading,
    tracksError,
    recentTracksData,
    recentTracksLoading,
    recentTracksError,
    analysisConfig,
    analysisConfigLoading,
    moduleStatus,
    moduleStatusLoading,
    
    // State
    error,
    backgroundDiscovery,
    backgroundAnalysis,
    
    // Mutations
    discoveryMutation,
    analysisMutation,
    forceReanalyzeMutation,
    forceEnrichMutation,
    toggleModuleMutation,
    
    // Actions
    setError,
  };
};
