import React from 'react';
import { X, Music, Clock, FileText, Database, CheckCircle, AlertCircle, BarChart3, Heart, Share2, Download, Play } from 'lucide-react';

interface TrackDetailsModalProps {
  track: any;
  isOpen: boolean;
  onClose: () => void;
}

const TrackDetailsModal: React.FC<TrackDetailsModalProps> = ({ track, isOpen, onClose }) => {
  if (!isOpen || !track) return null;

  const formatDuration = (duration?: number) => {
    if (!duration) return '--:--';
    const minutes = Math.floor(duration / 60);
    const seconds = Math.floor(duration % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const getStatusInfo = (track: any) => {
    const status = track.analysis_status || track.status;
    const configs = {
      complete: { label: 'Analyzed', icon: CheckCircle, color: 'text-green-600', bgColor: 'bg-green-50' },
      failed: { label: 'Failed', icon: AlertCircle, color: 'text-red-600', bgColor: 'bg-red-50' },
      has_metadata: { label: 'Has Metadata', icon: Database, color: 'text-blue-600', bgColor: 'bg-blue-50' },
      discovered: { label: 'Discovered', icon: FileText, color: 'text-gray-600', bgColor: 'bg-gray-50' }
    };
    
    return configs[status as keyof typeof configs] || configs.discovered;
  };

  const statusInfo = getStatusInfo(track);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-4">
            <div className="h-12 w-12 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
              <Music className="h-6 w-6 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                {track.metadata?.title || track.file_name}
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {track.metadata?.artist || 'Unknown Artist'}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
              <Heart className="w-5 h-5" />
            </button>
            <button className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
              <Share2 className="w-5 h-5" />
            </button>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="overflow-y-auto max-h-[calc(90vh-120px)]">
          <div className="p-6 space-y-6">
            {/* Basic Information */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
                  <FileText className="w-5 h-5 mr-2" />
                  Basic Information
                </h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-sm font-medium text-gray-500 dark:text-gray-400">Title</span>
                    <span className="text-sm text-gray-900 dark:text-white">{track.metadata?.title || 'Unknown'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-medium text-gray-500 dark:text-gray-400">Artist</span>
                    <span className="text-sm text-gray-900 dark:text-white">{track.metadata?.artist || 'Unknown'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-medium text-gray-500 dark:text-gray-400">Album</span>
                    <span className="text-sm text-gray-900 dark:text-white">{track.metadata?.album || 'Unknown'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-medium text-gray-500 dark:text-gray-400">Genre</span>
                    <span className="text-sm text-gray-900 dark:text-white">{track.metadata?.genre || 'Unknown'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-medium text-gray-500 dark:text-gray-400">Year</span>
                    <span className="text-sm text-gray-900 dark:text-white">{track.metadata?.year || 'Unknown'}</span>
                  </div>

                </div>
              </div>

              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
                  <Clock className="w-5 h-5 mr-2" />
                  File Information
                </h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-sm font-medium text-gray-500 dark:text-gray-400">Duration</span>
                    <span className="text-sm text-gray-900 dark:text-white">{formatDuration(track.metadata?.duration)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-medium text-gray-500 dark:text-gray-400">File Size</span>
                    <span className="text-sm text-gray-900 dark:text-white">{formatFileSize(track.file_size)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-medium text-gray-500 dark:text-gray-400">Format</span>
                    <span className="text-sm text-gray-900 dark:text-white">{track.file_extension?.toUpperCase()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-medium text-gray-500 dark:text-gray-400">Bitrate</span>
                    <span className="text-sm text-gray-900 dark:text-white">
                      {track.metadata?.bitrate ? (track.metadata.bitrate < 1000 ? `${track.metadata.bitrate} bps` : `${Math.round(track.metadata.bitrate / 1000)} kbps`) : 'Unknown'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-medium text-gray-500 dark:text-gray-400">Sample Rate</span>
                    <span className="text-sm text-gray-900 dark:text-white">
                      {track.metadata?.sample_rate ? `${track.metadata.sample_rate} Hz` : 'Unknown'}
                    </span>
                  </div>
                  
                </div>
              </div>
            </div>

            {/* Analysis Information */}
            {track.analysis?.tempo && (
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
                  <BarChart3 className="w-5 h-5 mr-2" />
                  Audio Analysis
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                    <div className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">
                      {Math.round(track.analysis.tempo)}
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">BPM</div>
                  </div>
                  {track.analysis?.key && (
                    <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                      <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                        {track.analysis.key}{track.analysis?.scale === 'minor' ? 'm' : ''}
                      </div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">Key</div>
                    </div>
                  )}
                  {track.analysis?.energy && (
                    <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                      <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
                        {Math.round(track.analysis.energy * 100)}%
                      </div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">Energy</div>
                    </div>
                  )}
                  {track.analysis?.loudness && (
                    <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                      <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                        {track.analysis.loudness.toFixed(1)}
                      </div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">dB</div>
                    </div>
                  )}
                </div>
                
                {/* Additional Analysis Metrics */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  {track.danceability && (
                    <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-lg">
                      <div className="text-lg font-bold text-purple-600 dark:text-purple-400">
                        {Math.round(track.danceability * 100)}%
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">Danceability</div>
                    </div>
                  )}
                  {track.valence && (
                    <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-lg">
                      <div className="text-lg font-bold text-pink-600 dark:text-pink-400">
                        {Math.round(track.valence * 100)}%
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">Positivity</div>
                    </div>
                  )}
                  {track.acousticness && (
                    <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-lg">
                      <div className="text-lg font-bold text-blue-600 dark:text-blue-400">
                        {Math.round(track.acousticness * 100)}%
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">Acoustic</div>
                    </div>
                  )}
                  {track.instrumentalness && (
                    <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-lg">
                      <div className="text-lg font-bold text-orange-600 dark:text-orange-400">
                        {Math.round(track.instrumentalness * 100)}%
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">Instrumental</div>
                    </div>
                  )}
                  {track.liveness && (
                    <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-lg">
                      <div className="text-lg font-bold text-teal-600 dark:text-teal-400">
                        {Math.round(track.liveness * 100)}%
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">Live</div>
                    </div>
                  )}
                </div>
                
                {/* Analysis Quality */}
                {track.analysis_quality_score && (
                  <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Analysis Quality</span>
                      <span className="text-sm font-bold text-gray-900 dark:text-white">
                        {Math.round(track.analysis_quality_score * 100)}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2 mt-2">
                      <div 
                        className="bg-indigo-600 h-2 rounded-full" 
                        style={{ width: `${track.analysis_quality_score * 100}%` }}
                      />
                    </div>
                  </div>
                )}
                
                {track.analysis_date && (
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    Analyzed: {new Date(track.analysis_date).toLocaleString()}
                  </div>
                )}
              </div>
            )}

                                                  {/* TensorFlow/MusicNN Predictions */}
             {track.analysis?.tensorflow_predictions?.top_predictions && (
               <div className="space-y-4">
                                   {/* Top Dominant Genre and Mood */}
                  {(track.analysis.tensorflow_predictions.dominant_genres || track.analysis.tensorflow_predictions.dominant_moods) && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {track.analysis.tensorflow_predictions.dominant_genres && track.analysis.tensorflow_predictions.dominant_genres.length > 0 && (
                        <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Top Genre</h4>
                          <div className="flex items-center justify-between">
                            <span className="text-lg font-medium text-gray-900 dark:text-white capitalize">
                              {track.analysis.tensorflow_predictions.dominant_genres[0].genre.replace(/_/g, ' ')}
                            </span>
                            <span className="text-lg font-bold text-gray-900 dark:text-white">
                              {(track.analysis.tensorflow_predictions.dominant_genres[0].score * 100).toFixed(0)}%
                            </span>
                          </div>
                        </div>
                      )}
                      
                      {track.analysis.tensorflow_predictions.dominant_moods && track.analysis.tensorflow_predictions.dominant_moods.length > 0 && (
                        <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Top Mood</h4>
                          <div className="flex items-center justify-between">
                            <span className="text-lg font-medium text-gray-900 dark:text-white capitalize">
                              {track.analysis.tensorflow_predictions.dominant_moods[0].mood.replace(/_/g, ' ')}
                            </span>
                            <span className="text-lg font-bold text-gray-900 dark:text-white">
                              {(track.analysis.tensorflow_predictions.dominant_moods[0].score * 100).toFixed(0)}%
                            </span>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                 
                 {/* Emotion Dimensions */}
                 {track.analysis.tensorflow_predictions.emotion_dimensions && (
                   <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                     <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Emotion Dimensions</h4>
                     <div className="grid grid-cols-3 gap-4">
                       <div>
                         <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Valence</div>
                         <div className="text-lg font-bold text-green-600 dark:text-green-400">
                           {(track.analysis.tensorflow_predictions.emotion_dimensions.valence * 100).toFixed(0)}%
                         </div>
                       </div>
                       <div>
                         <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Arousal</div>
                         <div className="text-lg font-bold text-blue-600 dark:text-blue-400">
                           {(track.analysis.tensorflow_predictions.emotion_dimensions.arousal * 100).toFixed(0)}%
                         </div>
                       </div>
                       <div>
                         <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Energy</div>
                         <div className="text-lg font-bold text-orange-600 dark:text-orange-400">
                           {(track.analysis.tensorflow_predictions.emotion_dimensions.energy_level * 100).toFixed(0)}%
                         </div>
                       </div>
                     </div>
                   </div>
                 )}
               </div>
             )}

            {/* Status Information */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Processing Status</h3>
              <div className={`p-4 rounded-lg ${statusInfo.bgColor} dark:bg-gray-700`}>
                <div className="flex items-center space-x-3">
                  <statusInfo.icon className={`w-6 h-6 ${statusInfo.color}`} />
                  <div>
                    <div className="font-medium text-gray-900 dark:text-white">{statusInfo.label}</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">
                      {track.analysis_status || track.status || 'discovered'}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* File Path */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">File Location</h3>
              <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                <code className="text-sm text-gray-800 dark:text-gray-200 break-all">
                  {track.file_path}
                </code>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-2">
            <button className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
              <Play className="w-4 h-4 mr-2" />
              Play
            </button>
            <button className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
              <Download className="w-4 h-4 mr-2" />
              Download
            </button>
          </div>
          <button
            onClick={onClose}
            className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default TrackDetailsModal;
