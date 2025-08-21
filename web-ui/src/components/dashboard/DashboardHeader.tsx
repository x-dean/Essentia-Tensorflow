import React from 'react';
import { RefreshCw } from 'lucide-react';
import StatusIndicator from '../StatusIndicator';
import { HealthStatus } from '../../types/dashboard';

interface DashboardHeaderProps {
  health: HealthStatus | undefined;
  healthLoading: boolean;
  onRefresh: () => void;
}

const DashboardHeader: React.FC<DashboardHeaderProps> = ({
  health,
  healthLoading,
  onRefresh,
}) => {
  return (
    <div className="flex justify-between items-center">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Monitor your music library and analysis progress
        </p>
      </div>
      <div className="flex items-center space-x-4">
        <button
          onClick={onRefresh}
          className="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 shadow-sm text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          title="Refresh all data"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
        <StatusIndicator 
          status={healthLoading ? 'loading' : (health?.status === 'healthy' ? 'healthy' : 'unhealthy')}
          text={healthLoading ? 'Loading...' : (health?.status === 'healthy' ? 'System Healthy' : 'System Issues')}
        />
      </div>
    </div>
  );
};

export default DashboardHeader;
