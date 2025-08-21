import React from 'react';
import { Search, RefreshCw, Loader2 } from 'lucide-react';
import { DiscoveryStatus } from '../../types/dashboard';

interface DiscoveryCardProps {
  isTriggering: boolean;
  backgroundDiscovery: boolean;
  discoveryStatus: DiscoveryStatus | undefined;
  discoveryCount: number;
  isDisabled: boolean;
  onTriggerDiscovery: () => void;
  onForceEnrich: () => void;
  isForceEnriching: boolean;
  tracksWithMetadata: number;
}

const DiscoveryCard: React.FC<DiscoveryCardProps> = ({
  isTriggering,
  backgroundDiscovery,
  discoveryStatus,
  discoveryCount,
  isDisabled,
  onTriggerDiscovery,
  onForceEnrich,
  isForceEnriching,
  tracksWithMetadata,
}) => {
  const discoveryProgress = discoveryStatus?.progress || 0;
  const discoveryMessage = discoveryStatus?.message || "";

  return (
    <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-gray-900 dark:text-white">Music Discovery</h3>
        <Search className="w-4 h-4 text-indigo-600" />
      </div>
      
      <div className="space-y-3">
        <div className="relative">
          <button
            onClick={onTriggerDiscovery}
            disabled={isTriggering || backgroundDiscovery || isDisabled}
            className="w-full inline-flex items-center justify-center px-3 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:bg-gray-400 disabled:cursor-not-allowed disabled:hover:bg-gray-400 transition-colors"
          >
            {isTriggering || backgroundDiscovery ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Search className="w-4 h-4 mr-2" />
            )}
            {isTriggering ? 'Discovering...' : 
             backgroundDiscovery ? (discoveryMessage || 'Discovery in Progress...') : 
             'Discover Music Files'}
          </button>
          
          {/* Progress indicator */}
          {(isTriggering || backgroundDiscovery) && (
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
            onClick={onForceEnrich}
            disabled={isForceEnriching || tracksWithMetadata === 0}
            className="inline-flex items-center px-2 py-1 border border-gray-300 dark:border-gray-600 shadow-sm text-xs font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Force re-enrich metadata (useful when enabling new external APIs)"
          >
            {isForceEnriching ? (
              <Loader2 className="w-3 h-3 mr-1 animate-spin" />
            ) : (
              <RefreshCw className="w-3 h-3 mr-1" />
            )}
            {isForceEnriching ? 'Enriching...' : 'Force Enrich'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default DiscoveryCard;
