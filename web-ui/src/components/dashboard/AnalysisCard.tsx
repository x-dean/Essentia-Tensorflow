import React from 'react';
import { BarChart3, Play, Loader2, Zap, Power, PowerOff } from 'lucide-react';
import { AnalysisStatus, AnalysisConfig } from '../../types/dashboard';

interface AnalysisCardProps {
  isAnalyzing: boolean;
  backgroundAnalysis: boolean;
  analysisStatus: AnalysisStatus | undefined;
  pendingTracks: number;
  isDisabled: boolean;
  onStartAnalysis: () => void;
  onForceReanalyze: () => void;
  isForceReanalyzing: boolean;
  totalTracks: number;
  analysisConfig: AnalysisConfig | undefined;
  analysisConfigLoading: boolean;
  onToggleTensorFlow: () => void;
  onToggleFAISS: () => void;
  toggleModuleMutation: any;
}

const AnalysisCard: React.FC<AnalysisCardProps> = ({
  isAnalyzing,
  backgroundAnalysis,
  analysisStatus,
  pendingTracks,
  isDisabled,
  onStartAnalysis,
  onForceReanalyze,
  isForceReanalyzing,
  totalTracks,
  analysisConfig,
  analysisConfigLoading,
  onToggleTensorFlow,
  onToggleFAISS,
  toggleModuleMutation,
}) => {
  const analysisProgress = analysisStatus?.progress || 0;
  const analysisMessage = analysisStatus?.message || "";

  return (
    <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-gray-900 dark:text-white">Audio Analysis</h3>
        <BarChart3 className="w-4 h-4 text-green-600" />
      </div>
      
      <div className="space-y-3">
        <div className="relative">
          <button
            onClick={onStartAnalysis}
            disabled={isAnalyzing || backgroundAnalysis || pendingTracks === 0 || isDisabled}
            className="w-full inline-flex items-center justify-center px-3 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:bg-gray-400 disabled:cursor-not-allowed disabled:hover:bg-gray-400 transition-colors"
          >
            {isAnalyzing || backgroundAnalysis ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Play className="w-4 h-4 mr-2" />
            )}
            {isAnalyzing ? 'Analyzing...' : 
             backgroundAnalysis ? (analysisMessage || 'Analysis in Progress...') : 
             isDisabled ? 'Waiting for Discovery...' : 
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
                onClick={onToggleTensorFlow}
                disabled={toggleModuleMutation.isPending}
                className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium transition-colors ${
                  analysisConfig?.config?.essentia?.algorithms?.enable_tensorflow 
                    ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-900/50' 
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                } ${toggleModuleMutation.isPending ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                title={`Click to ${analysisConfig?.config?.essentia?.algorithms?.enable_tensorflow ? 'disable' : 'enable'} TensorFlow`}
              >
                {toggleModuleMutation.isPending ? (
                  <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                ) : analysisConfig?.config?.essentia?.algorithms?.enable_tensorflow ? (
                  <Power className="w-3 h-3 mr-1" />
                ) : (
                  <PowerOff className="w-3 h-3 mr-1" />
                )}
                {analysisConfig?.config?.essentia?.algorithms?.enable_tensorflow ? 'TensorFlow Enabled' : 'TensorFlow Disabled'}
              </button>
              <button
                onClick={onToggleFAISS}
                disabled={toggleModuleMutation.isPending}
                className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium transition-colors ${
                  analysisConfig?.config?.essentia?.algorithms?.enable_faiss 
                    ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 hover:bg-green-200 dark:hover:bg-green-900/50' 
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                } ${toggleModuleMutation.isPending ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                title={`Click to ${analysisConfig?.config?.essentia?.algorithms?.enable_faiss ? 'disable' : 'enable'} FAISS`}
              >
                {toggleModuleMutation.isPending ? (
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
            onClick={onForceReanalyze}
            disabled={isForceReanalyzing || backgroundAnalysis || totalTracks === 0 || isDisabled}
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
  );
};

export default AnalysisCard;
