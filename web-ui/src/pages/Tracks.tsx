import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getTracks } from '../services/api';
import { Search, Music, Filter, Download, Play, Clock, CheckCircle, AlertCircle, FileText, Database, Zap, ChevronUp, ChevronDown, Eye, X } from 'lucide-react';
import LoadingSpinner from '../components/LoadingSpinner';

const Tracks: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'analyzed' | 'unanalyzed'>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [sortField, setSortField] = useState<string>('file_name');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [selectedTrack, setSelectedTrack] = useState<any>(null);
  const [showDetails, setShowDetails] = useState(false);
  const [genreFilter, setGenreFilter] = useState<string>('');
  const tracksPerPage = 20;

  // Get tracks based on filter
  const { data: tracksData, isLoading, error } = useQuery({
    queryKey: ['tracks', statusFilter, searchQuery, sortField, sortDirection, genreFilter],
    queryFn: async () => {
      // For now, get all tracks and filter client-side
      // In a real app, you'd want server-side filtering
      const response = await getTracks(1000, 0, false, false, 'summary');
      
      let filteredTracks = response.tracks || [];
      
      // Apply status filter
      if (statusFilter === 'analyzed') {
        filteredTracks = filteredTracks.filter((track: any) => track && track.is_analyzed);
      } else if (statusFilter === 'unanalyzed') {
        filteredTracks = filteredTracks.filter((track: any) => track && !track.is_analyzed);
      }
      
      // Apply search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        filteredTracks = filteredTracks.filter((track: any) => 
          track && (
            (track.title && track.title.toLowerCase().includes(query)) ||
            (track.artist && track.artist.toLowerCase().includes(query)) ||
            (track.album && track.album.toLowerCase().includes(query)) ||
            (track.file_name && track.file_name.toLowerCase().includes(query)) ||
            (track.genre && track.genre.toLowerCase().includes(query))
          )
        );
      }
      
      // Apply genre filter
      if (genreFilter) {
        filteredTracks = filteredTracks.filter((track: any) => 
          track && track.genre && track.genre.toLowerCase() === genreFilter.toLowerCase()
        );
      }
      
      return filteredTracks;
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Get basic stats for summary
  const { data: statsData } = useQuery({
    queryKey: ['tracks-summary'],
    queryFn: () => getTracks(1000, 0, false, false, 'summary'),
    refetchInterval: 30000,
  });

  // Get unique genres for filter dropdown
  const uniqueGenres = useMemo(() => {
    if (!tracksData) return [];
    const genres = tracksData
      .map((track: any) => track.genre)
      .filter((genre: string) => genre && genre.trim() !== '')
      .filter((genre: string, index: number, arr: string[]) => arr.indexOf(genre) === index)
      .sort();
    return genres;
  }, [tracksData]);

  // Calculate stats
  const stats = statsData && statsData.tracks ? {
    total_files: statsData.total_count,
    analyzed_files: statsData.tracks.filter((t: any) => t.is_analyzed).length,
    unanalyzed_files: statsData.tracks.filter((t: any) => !t.is_analyzed).length
  } : null;

  // Sort tracks
  const sortedTracks = useMemo(() => {
    if (!tracksData) return [];
    
    const sorted = [...tracksData].sort((a: any, b: any) => {
      let aValue = a[sortField];
      let bValue = b[sortField];
      
      // Handle null/undefined values
      if (aValue === null || aValue === undefined) aValue = '';
      if (bValue === null || bValue === undefined) bValue = '';
      
      // Handle numeric values
      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortDirection === 'asc' ? aValue - bValue : bValue - aValue;
      }
      
      // Handle string values
      const aStr = String(aValue).toLowerCase();
      const bStr = String(bValue).toLowerCase();
      
      if (sortDirection === 'asc') {
        return aStr.localeCompare(bStr);
      } else {
        return bStr.localeCompare(aStr);
      }
    });
    
    return sorted;
  }, [tracksData, sortField, sortDirection]);

  // Pagination
  const tracks = sortedTracks;
  const totalTracks = tracks.length;
  const totalPages = Math.ceil(totalTracks / tracksPerPage);
  const startIndex = (currentPage - 1) * tracksPerPage;
  const endIndex = startIndex + tracksPerPage;
  const currentTracks = tracks.slice(startIndex, endIndex);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
  };

  const handleSort = (field: string) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
    setCurrentPage(1);
  };

  const getSortIcon = (field: string) => {
    if (sortField !== field) {
      return <ChevronUp className="w-3 h-3 text-gray-400" />;
    }
    return sortDirection === 'asc' 
      ? <ChevronUp className="w-3 h-3 text-gray-600" />
      : <ChevronDown className="w-3 h-3 text-gray-600" />;
  };

  const handleTrackDetails = (track: any) => {
    setSelectedTrack(track);
    setShowDetails(true);
  };

  const closeDetails = () => {
    setShowDetails(false);
    setSelectedTrack(null);
  };

  const formatDuration = (duration: number | null | undefined) => {
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
    const status = track.status || 'discovered';
    
    switch (status) {
      case 'discovered':
        return {
          label: 'Discovered',
          icon: <FileText className="w-3 h-3" />,
          color: 'bg-blue-100 text-blue-800'
        };
      case 'has_metadata':
        return {
          label: 'Has Metadata',
          icon: <Database className="w-3 h-3" />,
          color: 'bg-purple-100 text-purple-800'
        };
      case 'analyzed':
        return {
          label: 'Analyzed',
          icon: <CheckCircle className="w-3 h-3" />,
          color: 'bg-green-100 text-green-800'
        };
      case 'faiss_analyzed':
        return {
          label: 'FAISS Indexed',
          icon: <Zap className="w-3 h-3" />,
          color: 'bg-indigo-100 text-indigo-800'
        };
      case 'failed':
        return {
          label: 'Failed',
          icon: <AlertCircle className="w-3 h-3" />,
          color: 'bg-red-100 text-red-800'
        };
      default:
        return {
          label: 'Unknown',
          icon: <Clock className="w-3 h-3" />,
          color: 'bg-gray-100 text-gray-800'
        };
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Tracks</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Manage and browse your music library
          </p>
        </div>
        <div className="flex items-center space-x-4 text-sm text-gray-500 dark:text-gray-400">
          <span>Total: {stats?.total_files || 0}</span>
          <span>Analyzed: {stats?.analyzed_files || 0}</span>
          <span>Pending: {stats?.unanalyzed_files || 0}</span>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
        <form onSubmit={handleSearch} className="space-y-4">
          <div className="flex space-x-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                <input
                  type="text"
                  placeholder="Search tracks, artists, albums..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400"
                />
              </div>
            </div>
                         <div className="flex space-x-2">
               <select
                 value={statusFilter}
                 onChange={(e) => {
                   setStatusFilter(e.target.value as 'all' | 'analyzed' | 'unanalyzed');
                   setCurrentPage(1);
                 }}
                 className="px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
               >
                 <option value="all">All Tracks</option>
                 <option value="analyzed">Analyzed</option>
                 <option value="unanalyzed">Unanalyzed</option>
               </select>
               <select
                 value={genreFilter}
                 onChange={(e) => {
                   setGenreFilter(e.target.value);
                   setCurrentPage(1);
                 }}
                 className="px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
               >
                 <option value="">All Genres</option>
                 {uniqueGenres.map((genre: string) => (
                   <option key={genre} value={genre}>{genre}</option>
                 ))}
               </select>
               <button
                 type="submit"
                 className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
               >
                 <Filter className="w-4 h-4 mr-2" />
                 Filter
               </button>
             </div>
          </div>
        </form>
      </div>

      {/* Tracks List */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <LoadingSpinner size="lg" text="Loading tracks..." />
          </div>
                 ) : error ? (
           <div className="p-6 text-center">
             <div className="text-red-600 mb-2">Error loading tracks</div>
             <div className="text-sm text-gray-500 dark:text-gray-400">{error instanceof Error ? error.message : 'Unknown error'}</div>
           </div>
        ) : currentTracks.length === 0 ? (
          <div className="p-6 text-center">
            <Music className="mx-auto h-12 w-12 text-gray-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No tracks found</h3>
            <p className="text-gray-500 dark:text-gray-400">
              {searchQuery || statusFilter !== 'all' 
                ? 'Try adjusting your search or filter criteria.'
                : 'No tracks have been discovered yet. Start by discovering music files.'
              }
            </p>
          </div>
        ) : (
          <>
                         <div className="overflow-x-auto">
                               <table className="min-w-full divide-y divide-gray-200 text-xs">
                  <thead className="bg-gray-50 dark:bg-gray-700">
                    <tr>
                      <th 
                        className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider w-1/4 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600"
                        onClick={() => handleSort('title')}
                      >
                        <div className="flex items-center justify-between">
                          <span>Track</span>
                          {getSortIcon('title')}
                        </div>
                      </th>
                      <th 
                        className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/6 cursor-pointer hover:bg-gray-100"
                        onClick={() => handleSort('artist')}
                      >
                        <div className="flex items-center justify-between">
                          <span>Artist</span>
                          {getSortIcon('artist')}
                        </div>
                      </th>
                      <th 
                        className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/6 cursor-pointer hover:bg-gray-100"
                        onClick={() => handleSort('album')}
                      >
                        <div className="flex items-center justify-between">
                          <span>Album</span>
                          {getSortIcon('album')}
                        </div>
                      </th>
                      <th 
                        className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-16 cursor-pointer hover:bg-gray-100"
                        onClick={() => handleSort('duration')}
                      >
                        <div className="flex items-center justify-between">
                          <span>Duration</span>
                          {getSortIcon('duration')}
                        </div>
                      </th>
                      <th 
                        className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-16 cursor-pointer hover:bg-gray-100"
                        onClick={() => handleSort('file_size')}
                      >
                        <div className="flex items-center justify-between">
                          <span>Size</span>
                          {getSortIcon('file_size')}
                        </div>
                      </th>
                      <th 
                        className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-24 cursor-pointer hover:bg-gray-100"
                        onClick={() => handleSort('status')}
                      >
                        <div className="flex items-center justify-between">
                          <span>Status</span>
                          {getSortIcon('status')}
                        </div>
                      </th>
                                             <th 
                         className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/5 cursor-pointer hover:bg-gray-100"
                         onClick={() => handleSort('tempo')}
                       >
                         <div className="flex items-center justify-between">
                           <span>Analysis</span>
                           {getSortIcon('tempo')}
                         </div>
                       </th>
                       <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-16">
                         Actions
                       </th>
                     </tr>
                   </thead>
                                   <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                    {currentTracks.map((track: any) => (
                      <tr key={track.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                       <td className="px-3 py-2 whitespace-nowrap">
                         <div className="flex items-center">
                           <div className="flex-shrink-0 h-6 w-6">
                             <div className="h-6 w-6 rounded bg-gray-200 flex items-center justify-center">
                               <Music className="h-3 w-3 text-gray-400" />
                             </div>
                           </div>
                           <div className="ml-2">
                                                           <div className="text-xs font-medium text-gray-900 dark:text-white truncate max-w-32">
                                {track.title || track.file_name}
                              </div>
                              <div className="text-xs text-gray-500 dark:text-gray-400">
                                {track.file_extension.toUpperCase()}
                              </div>
                           </div>
                         </div>
                       </td>
                                               <td className="px-3 py-2 whitespace-nowrap text-xs text-gray-900 dark:text-white truncate max-w-24">
                          {track.artist || 'Unknown'}
                        </td>
                        <td className="px-3 py-2 whitespace-nowrap text-xs text-gray-900 dark:text-white truncate max-w-24">
                          {track.album || 'Unknown'}
                        </td>
                        <td className="px-3 py-2 whitespace-nowrap text-xs text-gray-900 dark:text-white">
                          {formatDuration(track.duration)}
                        </td>
                        <td className="px-3 py-2 whitespace-nowrap text-xs text-gray-900 dark:text-white">
                          {formatFileSize(track.file_size)}
                        </td>
                       <td className="px-3 py-2 whitespace-nowrap">
                         {(() => {
                           const statusInfo = getStatusInfo(track);
                           return (
                             <span
                               className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${statusInfo.color}`}
                             >
                               {statusInfo.icon}
                               <span className="ml-1">{statusInfo.label}</span>
                             </span>
                           );
                         })()}
                       </td>
                                               <td className="px-3 py-2 whitespace-nowrap text-xs text-gray-900 dark:text-white">
                          <div className="space-y-0.5">
                           {track.tempo && (
                             <div className="text-xs">
                               <span className="font-medium">T:</span> {Math.round(track.tempo)}
                             </div>
                           )}
                           {track.key && (
                             <div className="text-xs">
                               <span className="font-medium">K:</span> {track.key}
                             </div>
                           )}
                           {track.energy && (
                             <div className="text-xs">
                               <span className="font-medium">E:</span> {Math.round(track.energy * 100)}%
                             </div>
                           )}
                         </div>
                       </td>
                                               <td className="px-3 py-2 whitespace-nowrap text-xs text-gray-900 dark:text-white">
                          <button
                            onClick={() => handleTrackDetails(track)}
                            className="inline-flex items-center px-2 py-1 border border-gray-300 dark:border-gray-600 rounded text-xs font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                         >
                           <Eye className="w-3 h-3 mr-1" />
                           Details
                         </button>
                       </td>
                     </tr>
                   ))}
                 </tbody>
               </table>
             </div>

            {/* Pagination */}
            {totalPages > 1 && (
                             <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
                 <div className="flex items-center justify-between">
                   <div className="text-sm text-gray-700 dark:text-gray-300">
                     Page {currentPage} of {totalPages}
                   </div>
                   <div className="flex space-x-2">
                     <button
                       onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                       disabled={currentPage === 1}
                       className="px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300"
                     >
                       Previous
                     </button>
                     <button
                       onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                       disabled={currentPage === totalPages}
                       className="px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300"
                     >
                       Next
                     </button>
                   </div>
                 </div>
               </div>
            )}
                     </>
         )}
       </div>

       {/* Track Details Modal */}
       {showDetails && selectedTrack && (
         <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
                     <div className="relative top-20 mx-auto p-5 border w-11/12 md:w-3/4 lg:w-1/2 shadow-lg rounded-md bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700">
            <div className="mt-3">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-medium text-gray-900 dark:text-white">Track Details</h3>
                 <button
                   onClick={closeDetails}
                   className="text-gray-400 hover:text-gray-600"
                 >
                   <X className="w-6 h-6" />
                 </button>
               </div>
               
               <div className="space-y-4 max-h-96 overflow-y-auto">
                 {/* Basic Information */}
                 <div>
                   <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Basic Information</h4>
                                       <div className="grid grid-cols-2 gap-2 text-xs text-gray-900 dark:text-white">
                      <div><span className="font-medium">Title:</span> {selectedTrack.title || 'Unknown'}</div>
                      <div><span className="font-medium">Artist:</span> {selectedTrack.artist || 'Unknown'}</div>
                      <div><span className="font-medium">Album:</span> {selectedTrack.album || 'Unknown'}</div>
                      <div><span className="font-medium">Genre:</span> {selectedTrack.genre || 'Unknown'}</div>
                      <div><span className="font-medium">Year:</span> {selectedTrack.year || 'Unknown'}</div>
                      <div><span className="font-medium">Track Number:</span> {selectedTrack.track_number || 'Unknown'}</div>
                      <div><span className="font-medium">Duration:</span> {formatDuration(selectedTrack.duration)}</div>
                      <div><span className="font-medium">File Size:</span> {formatFileSize(selectedTrack.file_size)}</div>
                      <div><span className="font-medium">File Extension:</span> {selectedTrack.file_extension?.toUpperCase()}</div>
                                            <div><span className="font-medium">Bitrate:</span> {selectedTrack.bitrate ? (selectedTrack.bitrate < 1000 ? `${selectedTrack.bitrate} bps` : `${Math.round(selectedTrack.bitrate / 1000)} kbps`) : 'Unknown'}</div>
                      <div><span className="font-medium">Sample Rate:</span> {selectedTrack.sample_rate ? `${selectedTrack.sample_rate} Hz` : 'Unknown'}</div>
                      <div><span className="font-medium">Discovered:</span> {selectedTrack.discovered_at ? new Date(selectedTrack.discovered_at).toLocaleDateString() : 'Unknown'}</div>
                    </div>
                 </div>

                                   {/* Analysis Information */}
                  {selectedTrack.tempo && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Audio Analysis</h4>
                                           <div className="grid grid-cols-2 gap-2 text-xs text-gray-900 dark:text-white">
                        <div><span className="font-medium">Tempo:</span> {Math.round(selectedTrack.tempo)} BPM</div>
                        <div><span className="font-medium">Key:</span> {selectedTrack.key || 'Unknown'}</div>
                        <div><span className="font-medium">Scale:</span> {selectedTrack.scale || 'Unknown'}</div>
                        <div><span className="font-medium">Key Strength:</span> {selectedTrack.key_strength ? Math.round(selectedTrack.key_strength * 100) + '%' : 'Unknown'}</div>
                        <div><span className="font-medium">Energy:</span> {selectedTrack.energy ? Math.round(selectedTrack.energy * 100) + '%' : 'Unknown'}</div>
                        <div><span className="font-medium">Loudness:</span> {selectedTrack.loudness ? `${selectedTrack.loudness.toFixed(1)} dB` : 'Unknown'}</div>
                        {selectedTrack.analysis_timestamp && (
                          <div><span className="font-medium">Analyzed:</span> {new Date(selectedTrack.analysis_timestamp).toLocaleString()}</div>
                        )}
                      </div>
                   </div>
                 )}

                                                     {/* Processing Status */}
                   <div>
                     <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Processing Status</h4>
                                         <div className="grid grid-cols-1 gap-2 text-xs text-gray-900 dark:text-white">
                       <div><span className="font-medium">Current Status:</span> {selectedTrack.status || 'discovered'}</div>
                       <div><span className="font-medium">Processing Complete:</span> {selectedTrack.is_analyzed ? 'Yes' : 'No'}</div>
                     </div>
                  </div>

                                   {/* File Path */}
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">File Path</h4>
                    <div className="text-xs bg-gray-100 dark:bg-gray-700 p-2 rounded break-all text-gray-800 dark:text-gray-200">
                      {selectedTrack.file_path}
                    </div>
                  </div>
               </div>
             </div>
           </div>
         </div>
       )}
     </div>
   );
 };

export default Tracks;
