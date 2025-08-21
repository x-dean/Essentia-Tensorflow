import React from 'react';
import { AlertCircle } from 'lucide-react';

interface ErrorDisplayProps {
  error: string | null;
}

const ErrorDisplay: React.FC<ErrorDisplayProps> = ({ error }) => {
  if (!error) return null;

  return (
    <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-4">
      <div className="flex">
        <AlertCircle className="w-5 h-5 text-red-400 mr-2" />
        <div className="text-sm text-red-700 dark:text-red-300">{error}</div>
      </div>
    </div>
  );
};

export default ErrorDisplay;
