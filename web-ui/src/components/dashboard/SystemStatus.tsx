import React from 'react';
import { Database, Activity } from 'lucide-react';
import LoadingSpinner from '../LoadingSpinner';
import { HealthStatus } from '../../types/dashboard';

interface SystemStatusProps {
  health: HealthStatus | undefined;
  healthLoading: boolean;
}

const SystemStatus: React.FC<SystemStatusProps> = ({ health, healthLoading }) => {
  return (
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
  );
};

export default SystemStatus;
