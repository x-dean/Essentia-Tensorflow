import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Tracks from './pages/Tracks';
import ApiDocs from './pages/ApiDocs';
import ErrorBoundary from './components/ErrorBoundary';

// Placeholder components for other pages
const Analysis = () => (
  <div className="text-center py-12">
    <h2 className="text-2xl font-bold text-gray-900">Analysis</h2>
    <p className="mt-2 text-gray-600">Analysis management coming soon...</p>
  </div>
);

const Search = () => (
  <div className="text-center py-12">
    <h2 className="text-2xl font-bold text-gray-900">Search</h2>
    <p className="mt-2 text-gray-600">Similarity search coming soon...</p>
  </div>
);

const Settings = () => (
  <div className="text-center py-12">
    <h2 className="text-2xl font-bold text-gray-900">Settings</h2>
    <p className="mt-2 text-gray-600">Configuration coming soon...</p>
  </div>
);

const App: React.FC = () => {
  return (
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
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </Layout>
  );
};

export default App;
