import React from 'react';
import { CheckCircle, AlertCircle, Clock } from 'lucide-react';

interface StatusIndicatorProps {
  status: 'healthy' | 'unhealthy' | 'loading' | 'unknown';
  text?: string;
  size?: 'sm' | 'md' | 'lg';
}

const StatusIndicator: React.FC<StatusIndicatorProps> = ({ 
  status, 
  text, 
  size = 'md' 
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6'
  };

  const getStatusConfig = () => {
    switch (status) {
      case 'healthy':
        return {
          icon: CheckCircle,
          color: 'text-green-500',
          bgColor: 'bg-green-100',
          textColor: 'text-green-800',
          label: 'Healthy'
        };
      case 'unhealthy':
        return {
          icon: AlertCircle,
          color: 'text-red-500',
          bgColor: 'bg-red-100',
          textColor: 'text-red-800',
          label: 'Unhealthy'
        };
      case 'loading':
        return {
          icon: Clock,
          color: 'text-yellow-500',
          bgColor: 'bg-yellow-100',
          textColor: 'text-yellow-800',
          label: 'Loading'
        };
      default:
        return {
          icon: Clock,
          color: 'text-gray-500',
          bgColor: 'bg-gray-100',
          textColor: 'text-gray-800',
          label: 'Unknown'
        };
    }
  };

  const config = getStatusConfig();
  const Icon = config.icon;

  return (
    <div className="flex items-center space-x-2">
      <Icon className={`${sizeClasses[size]} ${config.color}`} />
      {text && (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.bgColor} ${config.textColor}`}>
          {text}
        </span>
      )}
    </div>
  );
};

export default StatusIndicator;
