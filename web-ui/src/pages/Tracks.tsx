import React, { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getTracks } from '../services/api';
import { 
  Search, Music, Filter, Download, Play, Clock, CheckCircle, AlertCircle, 
  FileText, Database, Zap, ChevronUp, ChevronDown, Eye, X, Grid, List,
  Sliders, BarChart3, RefreshCw, MoreHorizontal, Heart, Share2, Pause, Square
} from 'lucide-react';
import LoadingSpinner from '../components/LoadingSpinner';
import TrackDetailsModal from '../components/TrackDetailsModal';

// Types
interface TrackFilters {
  search: string;
  status: 'all' | 'analyzed' | 'unanalyzed' | 'failed';
  genre: string;
  // Audio Analysis Filters
  tempoRange: [number, number];
  energyRange: [number, number];
  danceabilityRange: [number, number];
  valenceRange: [number, number];
  acousticnessRange: [number, number];
  instrumentalnessRange: [number, number];
  livenessRange: [number, number];
  loudnessRange: [number, number];
  // Key and Scale Filters
  key: string;
  scale: 'all' | 'major' | 'minor';
  // TensorFlow Predictions Filters
  aiGenre: string;
  aiMood: string;
  // Duration and File Filters
  durationRange: [number, number];
  fileSizeRange: [number, number];
  // Sorting
  sortBy: string;
  sortDirection: 'asc' | 'desc';
}

interface ViewMode {
  type: 'table' | 'cards';
  compact: boolean;
}

const Tracks: React.FC = () => {
  // State
  const [filters, setFilters] = useState<TrackFilters>({
    search: '',
    status: 'all', // Show all tracks by default
    genre: '',
    // Audio Analysis Filters
    tempoRange: [0, 200],
    energyRange: [0, 1],
    danceabilityRange: [0, 1],
    valenceRange: [0, 1],
    acousticnessRange: [0, 1],
    instrumentalnessRange: [0, 1],
    livenessRange: [0, 1],
    loudnessRange: [0, 1],
    // Key and Scale Filters
    key: '',
    scale: 'all',
    // TensorFlow Predictions Filters
    aiGenre: '',
    aiMood: '',
    // Duration and File Filters
    durationRange: [0, 7200], // 0-120 minutes (2 hours)
    fileSizeRange: [0, 1024 * 1024 * 1024], // 0-1GB
    // Sorting
    sortBy: 'title',
    sortDirection: 'asc'
  });
  
  const [viewMode, setViewMode] = useState<ViewMode>({
    type: 'table',
    compact: false
  });
  
  const [selectedTracks, setSelectedTracks] = useState<Set<number>>(new Set());
  const [showFilters, setShowFilters] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [tracksPerPage, setTracksPerPage] = useState(50);
  const [selectedTrack, setSelectedTrack] = useState<any>(null);
  const [showDetails, setShowDetails] = useState(false);
  
  // Audio player state
  const [currentPlayingTrack, setCurrentPlayingTrack] = useState<number | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Data fetching with better caching
  const { data: tracksData, isLoading, error, refetch } = useQuery({
    queryKey: ['tracks', 'detailed'],
    queryFn: async () => {
      const response = await getTracks(2000, 0, false, false, 'detailed');
      return response.tracks || [];
    },
    staleTime: 30000, // 30 seconds
    refetchInterval: 60000, // 1 minute
  });

  // Filtered and sorted tracks
  const filteredTracks = useMemo(() => {
    if (!tracksData) return [];
    
    let filtered = [...tracksData];
    
    // Search filter
    if (filters.search) {
      const query = filters.search.toLowerCase();
      filtered = filtered.filter(track => 
        (track.metadata?.title?.toLowerCase().includes(query)) ||
        (track.metadata?.artist?.toLowerCase().includes(query)) ||
        (track.metadata?.album?.toLowerCase().includes(query)) ||
        (track.metadata?.genre?.toLowerCase().includes(query))
      );
    }
    
    // Status filter
    if (filters.status !== 'all') {
      filtered = filtered.filter(track => {
        const status = track.analysis_status;
        switch (filters.status) {
          case 'analyzed': return status === 'complete';
          case 'unanalyzed': return status !== 'complete';
          case 'failed': return status === 'failed';
          default: return true;
        }
      });
    }
    
    // Genre filter
    if (filters.genre) {
      filtered = filtered.filter(track => 
        track.metadata?.genre?.toLowerCase() === filters.genre.toLowerCase()
      );
    }
    
    // Comprehensive Analysis Filters
    filtered = filtered.filter(track => {
      // Audio Analysis Filters
      if (track.analysis?.tempo && (track.analysis.tempo < filters.tempoRange[0] || track.analysis.tempo > filters.tempoRange[1])) {
        return false;
      }
      if (track.analysis?.energy && (track.analysis.energy < filters.energyRange[0] || track.analysis.energy > filters.energyRange[1])) {
        return false;
      }
      if (track.analysis?.danceability && (track.analysis.danceability < filters.danceabilityRange[0] || track.analysis.danceability > filters.danceabilityRange[1])) {
        return false;
      }
      if (track.analysis?.valence && (track.analysis.valence < filters.valenceRange[0] || track.analysis.valence > filters.valenceRange[1])) {
        return false;
      }
      if (track.analysis?.acousticness && (track.analysis.acousticness < filters.acousticnessRange[0] || track.analysis.acousticness > filters.acousticnessRange[1])) {
        return false;
      }
      if (track.analysis?.instrumentalness && (track.analysis.instrumentalness < filters.instrumentalnessRange[0] || track.analysis.instrumentalness > filters.instrumentalnessRange[1])) {
        return false;
      }
      if (track.analysis?.liveness && (track.analysis.liveness < filters.livenessRange[0] || track.analysis.liveness > filters.livenessRange[1])) {
        return false;
      }
      if (track.analysis?.loudness && (track.analysis.loudness < filters.loudnessRange[0] || track.analysis.loudness > filters.loudnessRange[1])) {
        return false;
      }

      // Key and Scale Filters
      if (filters.key && track.analysis?.key && track.analysis.key !== filters.key) {
        return false;
      }
      if (filters.scale !== 'all' && track.analysis?.scale && track.analysis.scale !== filters.scale) {
        return false;
      }

      // TensorFlow Predictions Filters
      if (filters.aiGenre && track.analysis?.tensorflow_predictions?.dominant_genres) {
        const hasGenre = track.analysis.tensorflow_predictions.dominant_genres.some(
          (g: any) => g.genre.toLowerCase().includes(filters.aiGenre.toLowerCase())
        );
        if (!hasGenre) return false;
      }
      if (filters.aiMood && track.analysis?.tensorflow_predictions?.dominant_moods) {
        const hasMood = track.analysis.tensorflow_predictions.dominant_moods.some(
          (m: any) => m.mood.toLowerCase().includes(filters.aiMood.toLowerCase())
        );
        if (!hasMood) return false;
      }

      // Duration and File Filters
      if (track.metadata?.duration && (track.metadata.duration < filters.durationRange[0] || track.metadata.duration > filters.durationRange[1])) {
        return false;
      }
      if (track.file_size && (track.file_size < filters.fileSizeRange[0] || track.file_size > filters.fileSizeRange[1])) {
        return false;
      }

      return true;
    });
    
    // Sorting
    filtered.sort((a, b) => {
      let aValue: any;
      let bValue: any;
      
      // Handle nested data structure
      switch (filters.sortBy) {
        case 'title':
          aValue = a.metadata?.title || a.file_name;
          bValue = b.metadata?.title || b.file_name;
          break;
        case 'artist':
          aValue = a.metadata?.artist;
          bValue = b.metadata?.artist;
          break;
        case 'album':
          aValue = a.metadata?.album;
          bValue = b.metadata?.album;
          break;
        case 'genre':
          aValue = a.metadata?.genre;
          bValue = b.metadata?.genre;
          break;
        case 'duration':
          aValue = a.metadata?.duration;
          bValue = b.metadata?.duration;
          break;
        case 'tempo':
          aValue = a.analysis?.tempo || a.metadata?.bpm;
          bValue = b.analysis?.tempo || b.metadata?.bpm;
          break;
        case 'key_analysis':
          aValue = a.analysis?.key;
          bValue = b.analysis?.key;
          break;
        case 'energy':
          aValue = a.analysis?.energy;
          bValue = b.analysis?.energy;
          break;
        case 'danceability':
          aValue = a.analysis?.danceability;
          bValue = b.analysis?.danceability;
          break;
        case 'valence':
          aValue = a.analysis?.valence;
          bValue = b.analysis?.valence;
          break;
        case 'acousticness':
          aValue = a.analysis?.acousticness;
          bValue = b.analysis?.acousticness;
          break;
        default:
          aValue = a[filters.sortBy as keyof typeof a];
          bValue = b[filters.sortBy as keyof typeof b];
      }
      
      if (aValue === null || aValue === undefined) aValue = '';
      if (bValue === null || bValue === undefined) bValue = '';
      
      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return filters.sortDirection === 'asc' ? aValue - bValue : bValue - aValue;
      }
      
      const aStr = String(aValue).toLowerCase();
      const bStr = String(bValue).toLowerCase();
      
      return filters.sortDirection === 'asc' 
        ? aStr.localeCompare(bStr) 
        : bStr.localeCompare(aStr);
    });
    
    return filtered;
  }, [tracksData, filters]);

  // Pagination
  const totalTracks = filteredTracks.length;
  const totalPages = Math.ceil(totalTracks / tracksPerPage);
  const startIndex = (currentPage - 1) * tracksPerPage;
  const currentTracks = filteredTracks.slice(startIndex, startIndex + tracksPerPage);

  // Stats
  const stats = useMemo(() => {
    if (!tracksData) return null;
    return {
      total: tracksData.length,
      analyzed: tracksData.filter((t: any) => t.analysis_status === 'complete').length,
      unanalyzed: tracksData.filter((t: any) => t.analysis_status !== 'complete').length,
      failed: tracksData.filter((t: any) => t.analysis_status === 'failed').length,
      genres: [...new Set(tracksData.map((t: any) => t.metadata?.genre).filter(Boolean))].length
    };
  }, [tracksData]);

  // Unique values for filters
  const uniqueGenres = useMemo(() => {
    if (!tracksData) return [];
    return [...new Set(tracksData.map((t: any) => t.metadata?.genre).filter(Boolean))].sort();
  }, [tracksData]);

  const uniqueKeys = useMemo(() => {
    if (!tracksData) return [];
    return [...new Set(tracksData.map((t: any) => t.analysis?.key).filter(Boolean))].sort();
  }, [tracksData]);

  const uniqueAiGenres = useMemo(() => {
    if (!tracksData) return [];
    const genres = new Set<string>();
    tracksData.forEach((t: any) => {
      if (t.analysis?.tensorflow_predictions?.dominant_genres) {
        t.analysis.tensorflow_predictions.dominant_genres.forEach((g: any) => {
          genres.add(g.genre.replace(/_/g, ' '));
        });
      }
    });
    return Array.from(genres).sort();
  }, [tracksData]);

  const uniqueAiMoods = useMemo(() => {
    if (!tracksData) return [];
    const moods = new Set<string>();
    tracksData.forEach((t: any) => {
      if (t.analysis?.tensorflow_predictions?.dominant_moods) {
        t.analysis.tensorflow_predictions.dominant_moods.forEach((m: any) => {
          moods.add(m.mood.replace(/_/g, ' '));
        });
      }
    });
    return Array.from(moods).sort();
  }, [tracksData]);

  // Handlers
  const handleFilterChange = useCallback((key: keyof TrackFilters, value: any) => {
    setFilters((prev: TrackFilters) => ({ ...prev, [key]: value }));
    setCurrentPage(1);
  }, []);

  const handleSort = useCallback((field: string) => {
    setFilters((prev: TrackFilters) => ({
      ...prev,
      sortBy: field,
      sortDirection: prev.sortBy === field && prev.sortDirection === 'asc' ? 'desc' : 'asc'
    }));
    setCurrentPage(1);
  }, []);

  const toggleTrackSelection = useCallback((trackId: number) => {
    setSelectedTracks((prev: Set<number>) => {
      const newSet = new Set(prev);
      if (newSet.has(trackId)) {
        newSet.delete(trackId);
      } else {
        newSet.add(trackId);
      }
      return newSet;
    });
  }, []);

  const selectAllTracks = useCallback(() => {
    if (selectedTracks.size === currentTracks.length) {
      setSelectedTracks(new Set());
    } else {
      setSelectedTracks(new Set(currentTracks.map((t: any) => t.id)));
    }
  }, [currentTracks.length, selectedTracks.size]);

  const handleTrackDetails = useCallback((track: any) => {
    setSelectedTrack(track);
    setShowDetails(true);
  }, []);

  const closeDetails = useCallback(() => {
    setShowDetails(false);
    setSelectedTrack(null);
  }, []);

  // Audio player effects
  useEffect(() => {
    // Create a single audio element that will be reused
    const audio = new Audio();
    audioRef.current = audio;
    
    // Set up event listeners once
    const handlePlay = () => {
      setIsPlaying(true);
    };
    
    const handlePause = () => {
      setIsPlaying(false);
    };
    
    const handleEnded = () => {
      setIsPlaying(false);
      setCurrentPlayingTrack(null);
    };
    
    const handleError = (error: any) => {
      console.error('Error playing track:', error);
      setIsPlaying(false);
      setCurrentPlayingTrack(null);
      alert('Unable to play track. Please try again.');
    };

    audio.addEventListener('play', handlePlay);
    audio.addEventListener('pause', handlePause);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('error', handleError);

    // Cleanup audio when component unmounts
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = '';
        audioRef.current.removeEventListener('play', handlePlay);
        audioRef.current.removeEventListener('pause', handlePause);
        audioRef.current.removeEventListener('ended', handleEnded);
        audioRef.current.removeEventListener('error', handleError);
      }
    };
  }, []);

  const handlePlayTrack = useCallback((track: any) => {
    if (!audioRef.current) {
      console.error('Audio element not initialized');
      return;
    }

    // If the same track is already playing, just resume it
    if (currentPlayingTrack === track.id) {
      audioRef.current.play().catch(error => {
        console.error('Error resuming track:', error);
        alert('Unable to resume track. Please try again.');
      });
      return;
    }

    // If a different track is playing, stop it first
    audioRef.current.pause();
    
    // Set the new source
    audioRef.current.src = `/api/tracks/stream/${track.id}`;
    setCurrentPlayingTrack(track.id);

    // Play the track
    audioRef.current.play().catch(error => {
      console.error('Error playing track:', error);
      setIsPlaying(false);
      setCurrentPlayingTrack(null);
      alert('Unable to play track. Please try again.');
    });
  }, [currentPlayingTrack]);

  const handlePauseTrack = useCallback(() => {
    if (audioRef.current && isPlaying) {
      audioRef.current.pause();
    }
  }, [isPlaying]);

  const handleStopTrack = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current.src = '';
      setIsPlaying(false);
      setCurrentPlayingTrack(null);
    }
  }, []);

  // Utility functions
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

  const getStatusBadge = (track: any) => {
    const status = track.analysis_status || track.status;
    const configs = {
      complete: { label: 'Analyzed', icon: CheckCircle, color: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' },
      failed: { label: 'Failed', icon: AlertCircle, color: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300' },
      has_metadata: { label: 'Has Metadata', icon: Database, color: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300' },
      discovered: { label: 'Discovered', icon: FileText, color: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300' }
    };
    
    const config = configs[status as keyof typeof configs] || configs.discovered;
    const Icon = config.icon;
    
    return (
      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${config.color}`}>
        <Icon className="w-3 h-3 mr-1" />
        {config.label}
      </span>
    );
  };

  if (error) {
    return (
      <div className="space-y-6">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
          <div className="flex items-center">
            <AlertCircle className="w-5 h-5 text-red-400 mr-3" />
            <div>
              <h3 className="text-sm font-medium text-red-800 dark:text-red-200">Error loading tracks</h3>
              <p className="text-sm text-red-700 dark:text-red-300 mt-1">
                {error instanceof Error ? error.message : 'Unknown error occurred'}
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Music Library</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {stats ? `${stats.total} tracks • ${stats.analyzed} analyzed • ${stats.genres} genres` : 'Loading...'}
          </p>
        </div>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={() => refetch()}
            disabled={isLoading}
            className="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          
          <div className="flex border border-gray-300 dark:border-gray-600 rounded-md">
            <button
              onClick={() => setViewMode(prev => ({ ...prev, type: 'table' }))}
              className={`px-3 py-2 text-sm font-medium ${
                viewMode.type === 'table' 
                  ? 'bg-indigo-600 text-white' 
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
              }`}
            >
              <List className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode(prev => ({ ...prev, type: 'cards' }))}
              className={`px-3 py-2 text-sm font-medium ${
                viewMode.type === 'cards' 
                  ? 'bg-indigo-600 text-white' 
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
              }`}
            >
              <Grid className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium text-gray-900 dark:text-white">Filters</h2>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              <Sliders className="w-4 h-4 mr-2" />
              {showFilters ? 'Hide' : 'Show'} Advanced
            </button>
          </div>
          
          {/* Basic filters */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <input
                type="text"
                placeholder="Search tracks..."
                value={filters.search}
                onChange={(e) => handleFilterChange('search', e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>
            
            <select
              value={filters.status}
              onChange={(e) => handleFilterChange('status', e.target.value)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              <option value="all">All Status</option>
              <option value="analyzed">Analyzed</option>
              <option value="unanalyzed">Unanalyzed</option>
              <option value="failed">Failed</option>
            </select>
            
            <select
              value={filters.genre}
              onChange={(e) => handleFilterChange('genre', e.target.value)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              <option value="">All Genres</option>
              {uniqueGenres.map(genre => (
                <option key={genre} value={genre}>{genre}</option>
              ))}
            </select>
            
            <select
              value={`${filters.sortBy}-${filters.sortDirection}`}
              onChange={(e) => {
                const [field, direction] = e.target.value.split('-');
                handleFilterChange('sortBy', field);
                handleFilterChange('sortDirection', direction);
              }}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              <option value="title-asc">Title A-Z</option>
              <option value="title-desc">Title Z-A</option>
              <option value="artist-asc">Artist A-Z</option>
              <option value="artist-desc">Artist Z-A</option>
              <option value="tempo-asc">Tempo Low-High</option>
              <option value="tempo-desc">Tempo High-Low</option>
              <option value="duration-asc">Duration Short-Long</option>
              <option value="duration-desc">Duration Long-Short</option>
            </select>
          </div>
          
          {/* Advanced filters */}
          {showFilters && (
            <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <div className="space-y-6">
                {/* Audio Analysis Filters */}
                <div>
                  <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Audio Analysis</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Tempo: {filters.tempoRange[0]} - {filters.tempoRange[1]} BPM
                      </label>
                      <div className="flex space-x-2">
                        <input
                          type="range"
                          min="0"
                          max="200"
                          value={filters.tempoRange[0]}
                          onChange={(e) => handleFilterChange('tempoRange', [parseInt(e.target.value), filters.tempoRange[1]])}
                          className="flex-1"
                        />
                        <input
                          type="range"
                          min="0"
                          max="200"
                          value={filters.tempoRange[1]}
                          onChange={(e) => handleFilterChange('tempoRange', [filters.tempoRange[0], parseInt(e.target.value)])}
                          className="flex-1"
                        />
                      </div>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Energy: {(filters.energyRange[0] * 100).toFixed(0)}% - {(filters.energyRange[1] * 100).toFixed(0)}%
                      </label>
                      <div className="flex space-x-2">
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.1"
                          value={filters.energyRange[0]}
                          onChange={(e) => handleFilterChange('energyRange', [parseFloat(e.target.value), filters.energyRange[1]])}
                          className="flex-1"
                        />
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.1"
                          value={filters.energyRange[1]}
                          onChange={(e) => handleFilterChange('energyRange', [filters.energyRange[0], parseFloat(e.target.value)])}
                          className="flex-1"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Danceability: {(filters.danceabilityRange[0] * 100).toFixed(0)}% - {(filters.danceabilityRange[1] * 100).toFixed(0)}%
                      </label>
                      <div className="flex space-x-2">
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.1"
                          value={filters.danceabilityRange[0]}
                          onChange={(e) => handleFilterChange('danceabilityRange', [parseFloat(e.target.value), filters.danceabilityRange[1]])}
                          className="flex-1"
                        />
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.1"
                          value={filters.danceabilityRange[1]}
                          onChange={(e) => handleFilterChange('danceabilityRange', [filters.danceabilityRange[0], parseFloat(e.target.value)])}
                          className="flex-1"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Valence: {(filters.valenceRange[0] * 100).toFixed(0)}% - {(filters.valenceRange[1] * 100).toFixed(0)}%
                      </label>
                      <div className="flex space-x-2">
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.1"
                          value={filters.valenceRange[0]}
                          onChange={(e) => handleFilterChange('valenceRange', [parseFloat(e.target.value), filters.valenceRange[1]])}
                          className="flex-1"
                        />
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.1"
                          value={filters.valenceRange[1]}
                          onChange={(e) => handleFilterChange('valenceRange', [filters.valenceRange[0], parseFloat(e.target.value)])}
                          className="flex-1"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Acousticness: {(filters.acousticnessRange[0] * 100).toFixed(0)}% - {(filters.acousticnessRange[1] * 100).toFixed(0)}%
                      </label>
                      <div className="flex space-x-2">
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.1"
                          value={filters.acousticnessRange[0]}
                          onChange={(e) => handleFilterChange('acousticnessRange', [parseFloat(e.target.value), filters.acousticnessRange[1]])}
                          className="flex-1"
                        />
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.1"
                          value={filters.acousticnessRange[1]}
                          onChange={(e) => handleFilterChange('acousticnessRange', [filters.acousticnessRange[0], parseFloat(e.target.value)])}
                          className="flex-1"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Instrumentalness: {(filters.instrumentalnessRange[0] * 100).toFixed(0)}% - {(filters.instrumentalnessRange[1] * 100).toFixed(0)}%
                      </label>
                      <div className="flex space-x-2">
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.1"
                          value={filters.instrumentalnessRange[0]}
                          onChange={(e) => handleFilterChange('instrumentalnessRange', [parseFloat(e.target.value), filters.instrumentalnessRange[1]])}
                          className="flex-1"
                        />
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.1"
                          value={filters.instrumentalnessRange[1]}
                          onChange={(e) => handleFilterChange('instrumentalnessRange', [filters.instrumentalnessRange[0], parseFloat(e.target.value)])}
                          className="flex-1"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Liveness: {(filters.livenessRange[0] * 100).toFixed(0)}% - {(filters.livenessRange[1] * 100).toFixed(0)}%
                      </label>
                      <div className="flex space-x-2">
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.1"
                          value={filters.livenessRange[0]}
                          onChange={(e) => handleFilterChange('livenessRange', [parseFloat(e.target.value), filters.livenessRange[1]])}
                          className="flex-1"
                        />
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.1"
                          value={filters.livenessRange[1]}
                          onChange={(e) => handleFilterChange('livenessRange', [filters.livenessRange[0], parseFloat(e.target.value)])}
                          className="flex-1"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Loudness: {(filters.loudnessRange[0] * 100).toFixed(0)}% - {(filters.loudnessRange[1] * 100).toFixed(0)}%
                      </label>
                      <div className="flex space-x-2">
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.1"
                          value={filters.loudnessRange[0]}
                          onChange={(e) => handleFilterChange('loudnessRange', [parseFloat(e.target.value), filters.loudnessRange[1]])}
                          className="flex-1"
                        />
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.1"
                          value={filters.loudnessRange[1]}
                          onChange={(e) => handleFilterChange('loudnessRange', [filters.loudnessRange[0], parseFloat(e.target.value)])}
                          className="flex-1"
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Key and Scale Filters */}
                <div>
                  <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Musical Key</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Key</label>
                      <select
                        value={filters.key}
                        onChange={(e) => handleFilterChange('key', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                      >
                        <option value="">All Keys</option>
                        {uniqueKeys.map(key => (
                          <option key={key} value={key}>{key}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Scale</label>
                      <select
                        value={filters.scale}
                        onChange={(e) => handleFilterChange('scale', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                      >
                        <option value="all">All Scales</option>
                        <option value="major">Major</option>
                        <option value="minor">Minor</option>
                      </select>
                    </div>
                  </div>
                </div>

                {/* AI Predictions Filters */}
                <div>
                  <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">AI Predictions (MusicNN)</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">AI Genre</label>
                      <select
                        value={filters.aiGenre}
                        onChange={(e) => handleFilterChange('aiGenre', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                      >
                        <option value="">All AI Genres</option>
                        {uniqueAiGenres.map(genre => (
                          <option key={genre} value={genre}>{genre}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">AI Mood</label>
                      <select
                        value={filters.aiMood}
                        onChange={(e) => handleFilterChange('aiMood', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                      >
                        <option value="">All AI Moods</option>
                        {uniqueAiMoods.map(mood => (
                          <option key={mood} value={mood}>{mood}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>

                {/* Duration and File Filters */}
                <div>
                  <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">File Properties</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Duration: {Math.floor(filters.durationRange[0] / 60)}:{String(Math.floor(filters.durationRange[0] % 60)).padStart(2, '0')} - {Math.floor(filters.durationRange[1] / 60)}:{String(Math.floor(filters.durationRange[1] % 60)).padStart(2, '0')}
                      </label>
                      <div className="flex space-x-2">
                        <input
                          type="range"
                          min="0"
                          max="7200"
                          step="60"
                          value={filters.durationRange[0]}
                          onChange={(e) => handleFilterChange('durationRange', [parseInt(e.target.value), filters.durationRange[1]])}
                          className="flex-1"
                        />
                        <input
                          type="range"
                          min="0"
                          max="7200"
                          step="60"
                          value={filters.durationRange[1]}
                          onChange={(e) => handleFilterChange('durationRange', [filters.durationRange[0], parseInt(e.target.value)])}
                          className="flex-1"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        File Size: {(filters.fileSizeRange[0] / (1024 * 1024)).toFixed(1)} - {(filters.fileSizeRange[1] / (1024 * 1024)).toFixed(1)} MB
                      </label>
                      <div className="flex space-x-2">
                        <input
                          type="range"
                          min="0"
                          max={1024 * 1024 * 1024}
                          step={10 * 1024 * 1024}
                          value={filters.fileSizeRange[0]}
                          onChange={(e) => handleFilterChange('fileSizeRange', [parseInt(e.target.value), filters.fileSizeRange[1]])}
                          className="flex-1"
                        />
                        <input
                          type="range"
                          min="0"
                          max={1024 * 1024 * 1024}
                          step={10 * 1024 * 1024}
                          value={filters.fileSizeRange[1]}
                          onChange={(e) => handleFilterChange('fileSizeRange', [filters.fileSizeRange[0], parseInt(e.target.value)])}
                          className="flex-1"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Results summary */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-gray-700 dark:text-gray-300">
          Showing {startIndex + 1}-{Math.min(startIndex + tracksPerPage, totalTracks)} of {totalTracks} tracks
        </div>
        
        {selectedTracks.size > 0 && (
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-700 dark:text-gray-300">
              {selectedTracks.size} selected
            </span>
            <button className="text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-500">
              Batch Actions
            </button>
          </div>
        )}
      </div>

      {/* Tracks Display */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner size="lg" text="Loading tracks..." />
        </div>
      ) : currentTracks.length === 0 ? (
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-12 text-center">
          <Music className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No tracks found</h3>
          <p className="text-gray-500 dark:text-gray-400">
            {filters.search || filters.status !== 'all' 
              ? 'Try adjusting your search or filter criteria.'
              : 'No tracks have been discovered yet.'
            }
          </p>
        </div>
      ) : viewMode.type === 'table' ? (
        <TracksTable 
          tracks={currentTracks}
          selectedTracks={selectedTracks}
          onTrackSelect={toggleTrackSelection}
          onSelectAll={selectAllTracks}
          onSort={handleSort}
          sortBy={filters.sortBy}
          sortDirection={filters.sortDirection}
          getStatusBadge={getStatusBadge}
          formatDuration={formatDuration}
          formatFileSize={formatFileSize}
          onTrackDetails={handleTrackDetails}
          onPlayTrack={handlePlayTrack}
          onPauseTrack={handlePauseTrack}
          onStopTrack={handleStopTrack}
          currentPlayingTrack={currentPlayingTrack}
          isPlaying={isPlaying}
        />
      ) : (
        <TracksGrid 
          tracks={currentTracks}
          selectedTracks={selectedTracks}
          onTrackSelect={toggleTrackSelection}
          getStatusBadge={getStatusBadge}
          formatDuration={formatDuration}
          onTrackDetails={handleTrackDetails}
          onPlayTrack={handlePlayTrack}
          onPauseTrack={handlePauseTrack}
          onStopTrack={handleStopTrack}
          currentPlayingTrack={currentPlayingTrack}
          isPlaying={isPlaying}
        />
      )}

      {/* Pagination and Page Size Controls */}
      <div className="flex items-center justify-between">
        {/* Page Size Selector */}
        <div className="flex items-center space-x-3">
          <label className="text-sm text-gray-700 dark:text-gray-300">
            Show:
          </label>
          <select
            value={tracksPerPage}
            onChange={(e) => {
              setTracksPerPage(Number(e.target.value));
              setCurrentPage(1); // Reset to first page when changing page size
            }}
            className="px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded-md focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value={25}>25 per page</option>
            <option value={50}>50 per page</option>
            <option value={100}>100 per page</option>
            <option value={200}>200 per page</option>
            <option value={500}>500 per page</option>
            <option value={1000}>1000 per page</option>
            <option value={2000}>All tracks</option>
          </select>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {filteredTracks.length} tracks total
          </span>
        </div>

        {/* Pagination Controls */}
        {totalPages > 1 && (
          <div className="flex items-center space-x-2">
            <div className="text-sm text-gray-700 dark:text-gray-300">
              Page {currentPage} of {totalPages}
            </div>
            <button
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
            >
              Previous
            </button>
            <button
              onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
              disabled={currentPage === totalPages}
              className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
            >
              Next
            </button>
          </div>
        )}
      </div>

       {/* Track Details Modal */}
       <TrackDetailsModal
         track={selectedTrack}
         isOpen={showDetails}
         onClose={closeDetails}
       />
     </div>
   );
 };

// Table Component
const TracksTable: React.FC<{
  tracks: any[];
  selectedTracks: Set<number>;
  onTrackSelect: (id: number) => void;
  onSelectAll: () => void;
  onSort: (field: string) => void;
  sortBy: string;
  sortDirection: 'asc' | 'desc';
  getStatusBadge: (track: any) => JSX.Element;
  formatDuration: (duration?: number) => string;
  formatFileSize: (bytes: number) => string;
  onTrackDetails: (track: any) => void;
  onPlayTrack: (track: any) => void;
  onPauseTrack: () => void;
  onStopTrack: () => void;
  currentPlayingTrack: number | null;
  isPlaying: boolean;
}> = ({ tracks, selectedTracks, onTrackSelect, onSelectAll, onSort, sortBy, sortDirection, getStatusBadge, formatDuration, formatFileSize, onTrackDetails, onPlayTrack, onPauseTrack, onStopTrack, currentPlayingTrack, isPlaying }) => {
  const getSortIcon = (field: string) => {
    if (sortBy !== field) {
      return <ChevronUp className="w-4 h-4 text-gray-400" />;
    }
    return sortDirection === 'asc' 
      ? <ChevronUp className="w-4 h-4 text-gray-600" />
      : <ChevronDown className="w-4 h-4 text-gray-600" />;
  };

  return (
    <div className="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 text-xs">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="px-2 py-2 text-left">
                <input
                  type="checkbox"
                  checked={selectedTracks.size === tracks.length && tracks.length > 0}
                  onChange={onSelectAll}
                  className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                />
              </th>
              <th 
                className="px-2 py-2 text-left font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600 w-48"
                onClick={() => onSort('title')}
              >
                <div className="flex items-center space-x-1">
                  <span>Track</span>
                  {getSortIcon('title')}
                </div>
              </th>

              <th 
                className="px-2 py-2 text-left font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600 w-16"
                onClick={() => onSort('duration')}
              >
                <div className="flex items-center space-x-1">
                  <span>Time</span>
                  {getSortIcon('duration')}
                </div>
              </th>
              <th 
                className="px-2 py-2 text-left font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600 w-16"
                onClick={() => onSort('tempo')}
              >
                <div className="flex items-center space-x-1">
                  <span>BPM</span>
                  {getSortIcon('tempo')}
                </div>
              </th>
              <th 
                className="px-2 py-2 text-left font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600 w-16"
                onClick={() => onSort('key_analysis')}
              >
                <div className="flex items-center space-x-1">
                  <span>Key</span>
                  {getSortIcon('key_analysis')}
                </div>
              </th>
              <th 
                className="px-2 py-2 text-left font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600 w-16"
                onClick={() => onSort('energy')}
              >
                <div className="flex items-center space-x-1">
                  <span>Energy</span>
                  {getSortIcon('energy')}
                </div>
              </th>
              <th 
                className="px-2 py-2 text-left font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600 w-20"
                onClick={() => onSort('danceability')}
              >
                <div className="flex items-center space-x-1">
                  <span>Dance</span>
                  {getSortIcon('danceability')}
                </div>
              </th>
              <th 
                className="px-2 py-2 text-left font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600 w-20"
                onClick={() => onSort('valence')}
              >
                <div className="flex items-center space-x-1">
                  <span>Mood</span>
                  {getSortIcon('valence')}
                </div>
              </th>
              <th 
                className="px-2 py-2 text-left font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600 w-20"
                onClick={() => onSort('acousticness')}
              >
                <div className="flex items-center space-x-1">
                  <span>Acoustic</span>
                  {getSortIcon('acousticness')}
                </div>
              </th>
              <th className="px-2 py-2 text-left font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider w-20">
                Status
              </th>
              <th className="px-2 py-2 text-left font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider w-16">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            {tracks.map((track) => (
              <tr key={track.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                <td className="px-2 py-2 whitespace-nowrap">
                  <input
                    type="checkbox"
                    checked={selectedTracks.has(track.id)}
                    onChange={() => onTrackSelect(track.id)}
                    className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                  />
                </td>
                <td className="px-2 py-2 whitespace-nowrap">
                  <div className="min-w-0 flex-1">
                    <div className="text-xs font-medium text-gray-900 dark:text-white truncate">
                      {track.metadata?.title || track.file_name}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
                      {track.metadata?.artist || 'Unknown'} • {track.metadata?.album || 'Unknown'} • {track.metadata?.genre || 'Unknown'}
                    </div>
                  </div>
                </td>
                <td className="px-2 py-2 whitespace-nowrap text-xs text-gray-900 dark:text-white">
                  {formatDuration(track.metadata?.duration)}
                </td>
                <td className="px-2 py-2 whitespace-nowrap text-xs text-gray-900 dark:text-white">
                  {track.analysis?.tempo ? Math.round(track.analysis.tempo) : (track.metadata?.bpm && track.metadata.bpm > 0 ? Math.round(track.metadata.bpm) : '--')}
                </td>
                <td className="px-2 py-2 whitespace-nowrap text-xs text-gray-900 dark:text-white">
                  {track.analysis?.key ? `${track.analysis.key}${track.analysis?.scale === 'minor' ? 'm' : ''}` : '--'}
                </td>
                <td className="px-2 py-2 whitespace-nowrap text-xs text-gray-900 dark:text-white">
                  {track.analysis?.energy ? Math.round(track.analysis.energy * 100) : '--'}
                </td>
                <td className="px-2 py-2 whitespace-nowrap text-xs text-gray-900 dark:text-white">
                  {track.analysis?.danceability ? Math.round(track.analysis.danceability * 100) : '--'}
                </td>
                <td className="px-2 py-2 whitespace-nowrap text-xs text-gray-900 dark:text-white">
                  {track.analysis?.valence ? Math.round(track.analysis.valence * 100) : '--'}
                </td>
                <td className="px-2 py-2 whitespace-nowrap text-xs text-gray-900 dark:text-white">
                  {track.analysis?.acousticness ? Math.round(track.analysis.acousticness * 100) : '--'}
                </td>
                <td className="px-2 py-2 whitespace-nowrap">
                  {getStatusBadge(track)}
                </td>
                <td className="px-2 py-2 whitespace-nowrap text-xs font-medium">
                  <div className="flex items-center space-x-1">
                    <button 
                      onClick={() => onTrackDetails(track)}
                      className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-500"
                      title="View Details"
                    >
                      <Eye className="w-3 h-3" />
                    </button>
                    {currentPlayingTrack === track.id && isPlaying ? (
                      <div className="flex items-center space-x-1">
                        <button 
                          onClick={onPauseTrack}
                          className="text-yellow-600 dark:text-yellow-400 hover:text-yellow-500"
                          title="Pause Track"
                        >
                          <Pause className="w-3 h-3" />
                        </button>
                        <button 
                          onClick={onStopTrack}
                          className="text-red-600 dark:text-red-400 hover:text-red-500"
                          title="Stop Track"
                        >
                          <Square className="w-3 h-3" />
                        </button>
                      </div>
                    ) : (
                      <button 
                        onClick={() => onPlayTrack(track)}
                        className="text-green-600 dark:text-green-400 hover:text-green-500"
                        title="Play Track"
                      >
                        <Play className="w-3 h-3" />
                      </button>
                    )}
                    <button className="text-gray-600 dark:text-gray-400 hover:text-gray-500" title="More Options">
                      <MoreHorizontal className="w-3 h-3" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// Grid Component
const TracksGrid: React.FC<{
  tracks: any[];
  selectedTracks: Set<number>;
  onTrackSelect: (id: number) => void;
  getStatusBadge: (track: any) => JSX.Element;
  formatDuration: (duration?: number) => string;
  onTrackDetails: (track: any) => void;
  onPlayTrack: (track: any) => void;
  onPauseTrack: () => void;
  onStopTrack: () => void;
  currentPlayingTrack: number | null;
  isPlaying: boolean;
}> = ({ tracks, selectedTracks, onTrackSelect, getStatusBadge, formatDuration, onTrackDetails, onPlayTrack, onPauseTrack, onStopTrack, currentPlayingTrack, isPlaying }) => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {tracks.map((track) => (
        <div
          key={track.id}
          className={`bg-white dark:bg-gray-800 rounded-lg shadow-sm border-2 transition-all duration-200 hover:shadow-md ${
            selectedTracks.has(track.id) 
              ? 'border-indigo-500 ring-2 ring-indigo-200 dark:ring-indigo-800' 
              : 'border-gray-200 dark:border-gray-700'
          }`}
        >
          <div className="p-4">
            <div className="flex items-start justify-between mb-3">
              <div className="flex-shrink-0 h-12 w-12">
                <div className="h-12 w-12 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                  <Music className="h-6 w-6 text-white" />
                </div>
              </div>
              <input
                type="checkbox"
                checked={selectedTracks.has(track.id)}
                onChange={() => onTrackSelect(track.id)}
                className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              />
            </div>
            
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-gray-900 dark:text-white truncate">
                {track.title || track.file_name}
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                {track.artist || 'Unknown Artist'}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                {track.album || 'Unknown Album'}
              </p>
              
              <div className="flex items-center justify-between pt-2">
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {formatDuration(track.duration)}
                </span>
                {track.tempo && (
                  <span className="text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 px-2 py-1 rounded">
                    {Math.round(track.tempo)} BPM
                  </span>
                )}
              </div>
              
              <div className="pt-2">
                {getStatusBadge(track)}
              </div>
              
                             <div className="flex items-center justify-between pt-2">
                 <button 
                   onClick={() => onTrackDetails(track)}
                   className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-500"
                   title="View Details"
                 >
                   <Eye className="w-4 h-4" />
                 </button>
                 <div className="flex items-center space-x-1">
                   {currentPlayingTrack === track.id && isPlaying ? (
                     <>
                       <button 
                         onClick={onPauseTrack}
                         className="text-yellow-600 dark:text-yellow-400 hover:text-yellow-500"
                         title="Pause Track"
                       >
                         <Pause className="w-4 h-4" />
                       </button>
                       <button 
                         onClick={onStopTrack}
                         className="text-red-600 dark:text-red-400 hover:text-red-500"
                         title="Stop Track"
                       >
                         <Square className="w-4 h-4" />
                       </button>
                     </>
                   ) : (
                     <button 
                       onClick={() => onPlayTrack(track)}
                       className="text-green-600 dark:text-green-400 hover:text-green-500"
                       title="Play Track"
                     >
                       <Play className="w-4 h-4" />
                     </button>
                   )}
                   <button className="text-gray-600 dark:text-gray-400 hover:text-gray-500">
                     <Heart className="w-4 h-4" />
                   </button>
                   <button className="text-gray-600 dark:text-gray-400 hover:text-gray-500">
                     <Share2 className="w-4 h-4" />
                   </button>
                 </div>
               </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default Tracks;
