import React from 'react';
import StatusIndicator from '../StatusIndicator';
import { AnalysisModulesStatus } from '../../types/dashboard';

interface ModuleStatusProps {
  moduleStatus: AnalysisModulesStatus | undefined;
  moduleStatusLoading: boolean;
  onToggleModule: (params: { moduleName: string; enabled: boolean }) => void;
  toggleModuleMutation: any;
}

const ModuleStatus: React.FC<ModuleStatusProps> = ({
  moduleStatus,
  moduleStatusLoading,
  onToggleModule,
  toggleModuleMutation,
}) => {
  if (moduleStatusLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
        <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white mb-4">
          Analysis Modules
        </h3>
        <div className="flex items-center justify-center py-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        </div>
      </div>
    );
  }

  const modules = [
    {
      name: 'essentia',
      title: 'Essentia',
      description: 'Audio feature extraction',
      module: moduleStatus?.modules?.essentia,
    },
    {
      name: 'tensorflow',
      title: 'TensorFlow',
      description: 'Machine learning classification',
      module: moduleStatus?.modules?.tensorflow,
    },
    {
      name: 'faiss',
      title: 'FAISS',
      description: 'Vector similarity search',
      module: moduleStatus?.modules?.faiss,
    },
  ];

  return (
    <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
      <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white mb-4">
        Analysis Modules
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {modules.map(({ name, title, description, module }) => (
          <div key={name} className="p-4 border rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-medium text-gray-900 dark:text-white">{title}</h4>
              <StatusIndicator status={module?.available ? 'healthy' : 'unhealthy'} />
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
              {module?.description || description}
            </p>
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <span className="text-xs text-gray-500 dark:text-gray-400 mr-2">Status:</span>
                <span className={`text-xs px-2 py-1 rounded ${
                  module?.enabled 
                    ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
                    : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400'
                }`}>
                  {module?.enabled ? 'Enabled' : 'Disabled'}
                </span>
              </div>
              {name !== 'essentia' && (
                <button
                  onClick={() => onToggleModule({ moduleName: name, enabled: !module?.enabled })}
                  disabled={!module?.available || toggleModuleMutation.isPending}
                  className={`text-xs px-2 py-1 rounded ${
                    module?.enabled
                      ? 'bg-red-100 text-red-800 hover:bg-red-200 dark:bg-red-900/20 dark:text-red-400'
                      : 'bg-green-100 text-green-800 hover:bg-green-200 dark:bg-green-900/20 dark:text-green-400'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  {toggleModuleMutation.isPending ? '...' : (module?.enabled ? 'Disable' : 'Enable')}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ModuleStatus;
