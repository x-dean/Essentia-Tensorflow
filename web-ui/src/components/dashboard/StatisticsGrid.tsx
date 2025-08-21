import React from 'react';
import { Music, CheckCircle, Clock, Database, BarChart3 } from 'lucide-react';
import LoadingSpinner from '../LoadingSpinner';
import { DashboardStats } from '../../types/dashboard';

interface StatisticsGridProps {
  stats: DashboardStats | null;
  isLoading: boolean;
}

const StatisticsGrid: React.FC<StatisticsGridProps> = ({ stats, isLoading }) => {
  const totalTracks = stats?.total_files || 0;
  const analyzedTracks = stats?.analyzed_files || 0;
  const pendingTracks = stats?.unanalyzed_files || 0;
  const tracksWithMetadata = stats?.files_with_metadata || 0;

  const StatCard: React.FC<{
    icon: React.ComponentType<{ className?: string }>;
    title: string;
    value: React.ReactNode;
    iconColor: string;
  }> = ({ icon: Icon, title, value, iconColor }) => (
    <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
      <div className="flex items-center">
        <div className="flex-shrink-0">
          <Icon className={`w-8 h-8 ${iconColor}`} />
        </div>
        <div className="ml-4">
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{title}</p>
          <p className="text-2xl font-semibold text-gray-900 dark:text-white">
            {isLoading ? <LoadingSpinner size="sm" text="" /> : value}
          </p>
        </div>
      </div>
    </div>
  );

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
      <StatCard
        icon={Music}
        title="Total Tracks"
        value={totalTracks}
        iconColor="text-indigo-600"
      />
      <StatCard
        icon={CheckCircle}
        title="Analyzed"
        value={analyzedTracks}
        iconColor="text-green-600"
      />
      <StatCard
        icon={Clock}
        title="Pending"
        value={pendingTracks}
        iconColor="text-yellow-600"
      />
      <StatCard
        icon={Database}
        title="With Metadata"
        value={tracksWithMetadata}
        iconColor="text-purple-600"
      />
      <StatCard
        icon={BarChart3}
        title="Progress"
        value={totalTracks > 0 ? `${Math.round((analyzedTracks / totalTracks) * 100)}%` : '0%'}
        iconColor="text-blue-600"
      />
    </div>
  );
};

export default StatisticsGrid;
