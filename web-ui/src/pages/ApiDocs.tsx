import React from 'react';
import { ExternalLink, Copy, Check } from 'lucide-react';

interface ApiEndpoint {
  method: string;
  path: string;
  description: string;
  category: string;
  example?: string;
}

const ApiDocs: React.FC = () => {
  const [copiedEndpoint, setCopiedEndpoint] = React.useState<string | null>(null);

  const apiEndpoints: ApiEndpoint[] = [
    // Health & System
    {
      method: 'GET',
      path: '/health',
      description: 'System health check and status information',
      category: 'System',
      example: 'curl http://localhost:8000/health'
    },
    {
      method: 'GET',
      path: '/api',
      description: 'API information and available endpoints',
      category: 'System',
      example: 'curl http://localhost:8000/api'
    },
    {
      method: 'GET',
      path: '/config',
      description: 'Get current application configuration',
      category: 'System',
      example: 'curl http://localhost:8000/config'
    },

    // Tracks
    {
      method: 'GET',
      path: '/api/tracks/',
      description: 'Get all tracks with filtering and pagination',
      category: 'Tracks',
      example: 'curl "http://localhost:8000/api/tracks/?limit=10&offset=0&analyzed_only=false"'
    },
    {
      method: 'GET',
      path: '/api/tracks/database-status',
      description: 'Get database status and statistics',
      category: 'Tracks',
      example: 'curl http://localhost:8000/api/tracks/database-status'
    },
    {
      method: 'POST',
      path: '/api/tracks/reset-database',
      description: 'Reset and recreate the database (requires confirmation)',
      category: 'Tracks',
      example: 'curl -X POST "http://localhost:8000/api/tracks/reset-database?confirm=true"'
    },

    // Discovery
    {
      method: 'POST',
      path: '/discovery/trigger',
      description: 'Trigger file discovery manually',
      category: 'Discovery',
      example: 'curl -X POST http://localhost:8000/discovery/trigger'
    },
    {
      method: 'GET',
      path: '/api/discovery/stats',
      description: 'Get discovery statistics',
      category: 'Discovery',
      example: 'curl http://localhost:8000/api/discovery/stats'
    },
    {
      method: 'POST',
      path: '/discovery/background/toggle',
      description: 'Toggle background discovery on/off',
      category: 'Discovery',
      example: 'curl -X POST http://localhost:8000/discovery/background/toggle'
    },

    // Analyzer
    {
      method: 'GET',
      path: '/api/analyzer/categorize',
      description: 'Categorize files by length',
      category: 'Analysis',
      example: 'curl http://localhost:8000/api/analyzer/categorize'
    },
    {
      method: 'POST',
      path: '/api/analyzer/analyze-batches',
      description: 'Process all batches automatically',
      category: 'Analysis',
      example: 'curl -X POST "http://localhost:8000/api/analyzer/analyze-batches?include_tensorflow=false"'
    },
    {
      method: 'GET',
      path: '/api/analyzer/statistics',
      description: 'Get analysis statistics',
      category: 'Analysis',
      example: 'curl http://localhost:8000/api/analyzer/statistics'
    },
    {
      method: 'POST',
      path: '/api/analyzer/analyze-file',
      description: 'Analyze a single file',
      category: 'Analysis',
      example: 'curl -X POST "http://localhost:8000/api/analyzer/analyze-file" -H "Content-Type: application/json" -d \'{"file_path": "music/track.mp3", "include_tensorflow": true}\''
    },
    {
      method: 'POST',
      path: '/api/analyzer/analyze-files',
      description: 'Analyze multiple files in batch',
      category: 'Analysis',
      example: 'curl -X POST "http://localhost:8000/api/analyzer/analyze-files" -H "Content-Type: application/json" -d \'{"file_paths": ["music/track1.mp3", "music/track2.mp3"], "include_tensorflow": true}\''
    },
    {
      method: 'GET',
      path: '/api/analyzer/analysis/{file_path}',
      description: 'Get analysis results for a specific file',
      category: 'Analysis',
      example: 'curl "http://localhost:8000/api/analyzer/analysis/music/track.mp3"'
    },
    {
      method: 'GET',
      path: '/api/analyzer/analysis-summary/{file_path}',
      description: 'Get analysis summary for a specific file',
      category: 'Analysis',
      example: 'curl "http://localhost:8000/api/analyzer/analysis-summary/music/track.mp3"'
    },
    {
      method: 'GET',
      path: '/api/analyzer/unanalyzed-files',
      description: 'Get list of unanalyzed files',
      category: 'Analysis',
      example: 'curl "http://localhost:8000/api/analyzer/unanalyzed-files?limit=10"'
    },

    // FAISS
    {
      method: 'POST',
      path: '/api/faiss/build-index',
      description: 'Build FAISS index from analyzed tracks',
      category: 'FAISS',
      example: 'curl -X POST "http://localhost:8000/api/faiss/build-index?include_tensorflow=true&force_rebuild=false"'
    },
    {
      method: 'GET',
      path: '/api/faiss/statistics',
      description: 'Get FAISS index statistics',
      category: 'FAISS',
      example: 'curl http://localhost:8000/api/faiss/statistics'
    },
    {
      method: 'POST',
      path: '/api/faiss/add-track',
      description: 'Add a single track to the FAISS index',
      category: 'FAISS',
      example: 'curl -X POST "http://localhost:8000/api/faiss/add-track?file_path=music/track.mp3&include_tensorflow=true"'
    },
    {
      method: 'POST',
      path: '/api/faiss/search',
      description: 'Search for similar tracks',
      category: 'FAISS',
      example: 'curl -X POST "http://localhost:8000/api/faiss/search" -H "Content-Type: application/json" -d \'{"query_file": "music/track.mp3", "top_n": 5}\''
    },

    // Metadata
    {
      method: 'GET',
      path: '/api/metadata/{file_path}',
      description: 'Get metadata for a specific file',
      category: 'Metadata',
      example: 'curl "http://localhost:8000/api/metadata/music/track.mp3"'
    },
    {
      method: 'POST',
      path: '/api/metadata/enrich-genres',
      description: 'Enrich genres using external APIs',
      category: 'Metadata',
      example: 'curl -X POST "http://localhost:8000/api/metadata/enrich-genres" -H "Content-Type: application/json" -d \'{"file_paths": ["music/track1.mp3", "music/track2.mp3"]}\''
    },

    // Database
    {
      method: 'POST',
      path: '/database/reset',
      description: 'Reset and recreate the database (requires confirmation)',
      category: 'Database',
      example: 'curl -X POST "http://localhost:8000/database/reset?confirm=true"'
    }
  ];

  const copyToClipboard = async (text: string, endpoint: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedEndpoint(endpoint);
      setTimeout(() => setCopiedEndpoint(null), 2000);
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
    }
  };

  const getMethodColor = (method: string) => {
    switch (method) {
      case 'GET': return 'bg-green-100 text-green-800';
      case 'POST': return 'bg-blue-100 text-blue-800';
      case 'PUT': return 'bg-yellow-100 text-yellow-800';
      case 'DELETE': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const categories = [...new Set(apiEndpoints.map(ep => ep.category))];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">API Documentation</h1>
        <p className="mt-1 text-sm text-gray-500">
          Complete list of available API endpoints with examples
        </p>
      </div>

      {/* Quick Links */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Quick Links</h2>
        <div className="flex flex-wrap gap-2">
          {categories.map(category => (
            <a
              key={category}
              href={`#${category.toLowerCase()}`}
              className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-indigo-100 text-indigo-800 hover:bg-indigo-200"
            >
              {category}
            </a>
          ))}
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-purple-100 text-purple-800 hover:bg-purple-200"
          >
            <ExternalLink className="w-4 h-4 mr-1" />
            Interactive Docs
          </a>
        </div>
      </div>

      {/* API Endpoints by Category */}
      {categories.map(category => (
        <div key={category} id={category.toLowerCase()} className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">{category}</h2>
          </div>
          <div className="divide-y divide-gray-200">
            {apiEndpoints
              .filter(ep => ep.category === category)
              .map((endpoint, index) => (
                <div key={`${endpoint.method}-${endpoint.path}-${index}`} className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getMethodColor(endpoint.method)}`}>
                          {endpoint.method}
                        </span>
                        <code className="text-sm font-mono bg-gray-100 px-2 py-1 rounded">
                          {endpoint.path}
                        </code>
                      </div>
                      <p className="text-sm text-gray-600 mb-3">{endpoint.description}</p>
                      {endpoint.example && (
                        <div className="relative">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-xs font-medium text-gray-500">Example:</span>
                            <button
                              onClick={() => copyToClipboard(endpoint.example!, `${endpoint.method}-${endpoint.path}`)}
                              className="inline-flex items-center text-xs text-gray-500 hover:text-gray-700"
                            >
                              {copiedEndpoint === `${endpoint.method}-${endpoint.path}` ? (
                                <Check className="w-4 h-4 mr-1" />
                              ) : (
                                <Copy className="w-4 h-4 mr-1" />
                              )}
                              {copiedEndpoint === `${endpoint.method}-${endpoint.path}` ? 'Copied!' : 'Copy'}
                            </button>
                          </div>
                          <pre className="bg-gray-50 p-3 rounded text-xs font-mono text-gray-800 overflow-x-auto">
                            {endpoint.example}
                          </pre>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
          </div>
        </div>
      ))}

      {/* Additional Resources */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Additional Resources</h2>
        <div className="space-y-3">
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center text-indigo-600 hover:text-indigo-800"
          >
            <ExternalLink className="w-4 h-4 mr-2" />
            Interactive API Documentation (Swagger UI)
          </a>
          <a
            href="http://localhost:8000/openapi.json"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center text-indigo-600 hover:text-indigo-800"
          >
            <ExternalLink className="w-4 h-4 mr-2" />
            OpenAPI Specification (JSON)
          </a>
        </div>
      </div>
    </div>
  );
};

export default ApiDocs;
