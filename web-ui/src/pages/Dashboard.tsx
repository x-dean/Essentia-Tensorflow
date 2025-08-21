import React, { useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { getDiscoveryStatus, getAnalysisStatus } from '../services/api';
import { useDashboardData } from '../hooks/useDashboardData';
import {
  DashboardHeader,
  DiscoveryCard,
  AnalysisCard,
  StatisticsGrid,
  SystemStatus,
  ModuleStatus,
  RecentTracks,
  ErrorDisplay,
} from '../components/dashboard';
import { DashboardStats } from '../types/dashboard';

const Dashboard: React.FC = () => {
  const queryClient = useQueryClient();
  
  const {
    // Data
    health,
    healthLoading,
    discoveryStatus,
    analysisStatus,
    tracksData,
    tracksLoading,
    recentTracksData,
    recentTracksLoading,
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
  } = useDashboardData();

  // Local state for button interactions
  const [isTriggeringDiscovery, setIsTriggeringDiscovery] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isForceReanalyzing, setIsForceReanalyzing] = useState(false);
  const [isForceEnriching, setIsForceEnriching] = useState(false);

  // Calculate stats from tracks data
  const basicStats: DashboardStats | null = tracksData ? {
    total_files: tracksData.total_count,
    analyzed_files: tracksData.tracks ? tracksData.tracks.filter((t: any) => t && (t.analysis_status === "complete" || t.analysis_status === "tensorflow_completed")).length : 0,
    unanalyzed_files: tracksData.tracks ? tracksData.tracks.filter((t: any) => t && t.analysis_status !== "complete" && t.analysis_status !== "tensorflow_completed").length : 0,
    files_with_metadata: tracksData.tracks ? tracksData.tracks.filter((t: any) => t && t.has_metadata).length : 0
  } : null;

  const recentTracks = recentTracksData?.tracks || [];

  // Calculate totals
  const totalTracks = basicStats?.total_files || 0;
  const analyzedTracks = basicStats?.analyzed_files || 0;
  const pendingTracks = basicStats?.unanalyzed_files || 0;
  const tracksWithMetadata = basicStats?.files_with_metadata || 0;

  // Toggle handlers
  const handleToggleTensorFlow = () => {
    const currentState = analysisConfig?.config?.essentia?.algorithms?.enable_tensorflow ?? false;
    toggleModuleMutation.mutate({ moduleName: 'tensorflow', enabled: !currentState });
  };

  const handleToggleFAISS = () => {
    const currentState = analysisConfig?.config?.essentia?.algorithms?.enable_faiss ?? false;
    toggleModuleMutation.mutate({ moduleName: 'faiss', enabled: !currentState });
  };

  // Action handlers
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

  // Manual refresh function to force refresh all data
  const handleRefreshAll = async () => {
    try {
      setError(null);
      
      // Invalidate all queries to force fresh data fetch
      await queryClient.invalidateQueries({ queryKey: ['health'] });
      await queryClient.invalidateQueries({ queryKey: ['tracks-summary'] });
      await queryClient.invalidateQueries({ queryKey: ['recent-tracks'] });
      await queryClient.invalidateQueries({ queryKey: ['discovery-status'] });
      await queryClient.invalidateQueries({ queryKey: ['analysis-status'] });
      await queryClient.invalidateQueries({ queryKey: ['analysis-config'] });
      await queryClient.invalidateQueries({ queryKey: ['analysis-modules-status'] });
      
      console.log('All dashboard data refreshed');
    } catch (error) {
      console.warn('Failed to refresh data:', error);
      setError('Failed to refresh dashboard data');
    }
  };

  // Additional effect to check initial status on component mount
  useEffect(() => {
    const checkInitialStatus = async () => {
      try {
        // Check discovery status
      const discoveryResponse = await getDiscoveryStatus();
      const discoveryData = discoveryResponse.discovery || discoveryResponse;
      if (discoveryData && (discoveryData.status === "completed" || discoveryData.status === "failed" || discoveryData.status === "idle")) {
        setIsTriggeringDiscovery(false);
      } else if (discoveryData && discoveryData.status === "running") {
          // Background state will be updated by the hook
      }

        // Check analysis status
      const analysisResponse = await getAnalysisStatus();
      const analysisData = analysisResponse.analysis || analysisResponse;
      if (analysisData && (analysisData.status === "completed" || analysisData.status === "failed" || analysisData.status === "idle")) {
        setIsAnalyzing(false);
      } else if (analysisData && analysisData.status === "running") {
          // Background state will be updated by the hook
        }
      } catch (error) {
        console.warn('Failed to check initial status:', error);
      }
    };

    checkInitialStatus();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <DashboardHeader
        health={health}
        healthLoading={healthLoading}
        onRefresh={handleRefreshAll}
      />

      {/* Error Display */}
      <ErrorDisplay error={error} />

      {/* Main Action Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <DiscoveryCard
          isTriggering={isTriggeringDiscovery}
          backgroundDiscovery={backgroundDiscovery}
          discoveryStatus={discoveryStatus?.discovery || discoveryStatus}
          discoveryCount={discoveryStatus?.discovery?.discovered_count || discoveryStatus?.discovered_count || 0}
          isDisabled={backgroundAnalysis}
          onTriggerDiscovery={handleTriggerDiscovery}
          onForceEnrich={handleForceEnrich}
          isForceEnriching={isForceEnriching}
          tracksWithMetadata={tracksWithMetadata}
        />

        <AnalysisCard
          isAnalyzing={isAnalyzing}
          backgroundAnalysis={backgroundAnalysis}
          analysisStatus={analysisStatus?.analysis || analysisStatus}
          pendingTracks={pendingTracks}
          isDisabled={isTriggeringDiscovery || backgroundDiscovery}
          onStartAnalysis={handleStartAnalysis}
          onForceReanalyze={handleForceReanalyze}
          isForceReanalyzing={isForceReanalyzing}
          totalTracks={totalTracks}
          analysisConfig={analysisConfig}
          analysisConfigLoading={analysisConfigLoading}
          onToggleTensorFlow={handleToggleTensorFlow}
          onToggleFAISS={handleToggleFAISS}
          toggleModuleMutation={toggleModuleMutation}
        />
      </div>

      {/* Statistics Grid */}
      <StatisticsGrid stats={basicStats} isLoading={tracksLoading} />

      {/* System Status */}
      <SystemStatus health={health} healthLoading={healthLoading} />



      {/* Recent Tracks */}
      <RecentTracks tracks={recentTracks} isLoading={recentTracksLoading} />
    </div>
  );
};

export default Dashboard;
