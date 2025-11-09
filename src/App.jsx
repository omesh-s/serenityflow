import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './components/Dashboard';
import Settings from './components/Settings';
import AuthGate from './components/AuthGate';
import { useAuth } from './hooks/useAuth';
import { ThemeProvider } from './hooks/useTheme.jsx';
import { TimezoneProvider } from './hooks/useTimezone.jsx';

function App() {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-ocean-50 to-serenity-light">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-ocean-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-ocean-600 font-medium">Loading SerenityFlow...</p>
        </div>
      </div>
    );
  }

  return (
    <ThemeProvider>
      <TimezoneProvider>
        <Router>
          <Routes>
            <Route path="/auth" element={<AuthGate />} />
            <Route path="/auth/callback" element={<AuthGate />} />
            <Route
              path="/*"
              element={
                isAuthenticated ? (
                  <Layout>
                    <Routes>
                      <Route path="/" element={<Dashboard />} />
                      <Route path="/settings" element={<Settings />} />
                      <Route path="*" element={<Navigate to="/" replace />} />
                    </Routes>
                  </Layout>
                ) : (
                  <Navigate to="/auth" replace />
                )
              }
            />
          </Routes>
        </Router>
      </TimezoneProvider>
    </ThemeProvider>
  );
}

export default App;
