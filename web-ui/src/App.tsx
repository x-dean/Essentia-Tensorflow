import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Tracks from './pages/Tracks';
import ApiDocs from './pages/ApiDocs';
import Settings from './pages/Settings';
import SettingsNew from './pages/SettingsNew';
import ErrorBoundary from './components/ErrorBoundary';
import { ThemeProvider } from './contexts/ThemeContext';
import { ConfigProvider } from './contexts/ConfigContext';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      retryDelay: 1000,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

// Placeholder components for other pages
const Analysis = () => (
  <div className="text-center py-12">
    <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Analysis</h2>
    <p className="mt-2 text-gray-600 dark:text-gray-400">Analysis management coming soon...</p>
  </div>
);

const Search = () => (
  <div className="text-center py-12">
    <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Search</h2>
    <p className="mt-2 text-gray-600 dark:text-gray-400">Similarity search coming soon...</p>
  </div>
);

const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider>
        <ThemeProvider>
          <Layout>
            <Routes>
              <Route path="/" element={
                <ErrorBoundary>
                  <Dashboard />
                </ErrorBoundary>
              } />
              <Route path="/tracks" element={
                <ErrorBoundary>
                  <Tracks />
                </ErrorBoundary>
              } />
              <Route path="/analysis" element={<Analysis />} />
              <Route path="/search" element={<Search />} />
              <Route path="/api-docs" element={<ApiDocs />} />
              <Route path="/settings" element={
                <ErrorBoundary>
                  <SettingsNew />
                </ErrorBoundary>
              } />
            </Routes>
          </Layout>
        </ThemeProvider>
      </ConfigProvider>
    </QueryClientProvider>
  );
};

export default App;
