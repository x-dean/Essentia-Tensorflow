import React from 'react';
import { Music } from 'lucide-react';
import LoadingSpinner from '../LoadingSpinner';
import { Track } from '../../types/dashboard';

interface RecentTracksProps {
  tracks: Track[];
  isLoading: boolean;
}

const RecentTracks: React.FC<RecentTracksProps> = ({ tracks, isLoading }) => {
  const formatDuration = (duration?: number) => {
    if (!duration) return '';
    const minutes = Math.floor(duration / 60);
    const seconds = Math.floor(duration % 60);
    return `${minutes}:${String(seconds).padStart(2, '0')}`;
  };

  const getStatusBadge = (track: Track) => {
    const status = track.status || track.analysis_status;
    if (status === 'analyzed' || status === 'faiss_analyzed') {
      return (
        <span className="px-1 py-0.5 rounded bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 text-xs">
          ✓
        </span>
      );
    } else if (status === 'has_metadata') {
      return (
        <span className="px-1 py-0.5 rounded bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs">
          ℹ
        </span>
      );
    } else {
      return (
        <span className="px-1 py-0.5 rounded bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 text-xs">
          ⏳
        </span>
      );
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 shadow rounded-lg">
      <div className="px-3 py-2">
        <h3 className="text-xs font-medium text-gray-900 dark:text-white mb-2">
          Recent Tracks
        </h3>
        <div className="flow-root">
          {isLoading ? (
            <div className="flex items-center justify-center py-2">
              <LoadingSpinner size="sm" text="" />
            </div>
          ) : tracks && tracks.length > 0 ? (
            <div className="space-y-1">
              {tracks.slice(0, 3).map((track) => (
                <div key={track.id} className="flex items-center justify-between py-1 px-2 bg-gray-50 dark:bg-gray-700 rounded text-xs">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-1">
                      <Music className="w-2 h-2 text-gray-400 flex-shrink-0" />
                      <span className="font-medium text-gray-900 dark:text-white truncate">
                        {track.title || track.file_name}
                      </span>
                    </div>
                    <div className="flex items-center space-x-2 mt-0.5">
                      <span className="text-gray-500 dark:text-gray-400">
                        {track.artist || 'Unknown'}
                      </span>
                      {track.duration && (
                        <span className="text-gray-400 dark:text-gray-500">
                          {formatDuration(track.duration)}
                        </span>
                      )}
                      <span className="text-gray-400 dark:text-gray-500">
                        {track.file_extension?.toUpperCase()}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center space-x-1 ml-1">
                    {track.tempo && (
                      <span className="px-1 py-0.5 rounded bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs">
                        {Math.round(track.tempo)}
                      </span>
                    )}
                    {getStatusBadge(track)}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-2">
              <p className="text-xs text-gray-500 dark:text-gray-400">No tracks</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default RecentTracks;
