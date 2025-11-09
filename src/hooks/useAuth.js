import { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../utils/constants';

/**
 * Authentication hook - manages Google OAuth login state
 * Connects to backend /auth/status endpoint
 */
export const useAuth = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [authStatus, setAuthStatus] = useState({ google: false, notion: false });

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/auth/status`);
      const status = response.data;
      setAuthStatus(status);
      
      // User is authenticated if Google is connected
      if (status.google && status.google.connected) {
        setIsAuthenticated(true);
        setUser({ name: 'User', email: 'user@example.com' });
      } else {
        setIsAuthenticated(false);
        setUser(null);
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      setIsAuthenticated(false);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const initiateGoogleLogin = async () => {
    try {
      // Get OAuth authorization URL from backend
      const response = await axios.get(`${API_BASE_URL}/auth/google`);
      const { authorization_url } = response.data;
      
      // Redirect user to Google OAuth
      window.location.href = authorization_url;
    } catch (error) {
      console.error('Failed to initiate Google login:', error);
      throw error;
    }
  };

  const logout = async () => {
    try {
      // Disconnect Google
      if (authStatus.google?.connected) {
        await axios.post(`${API_BASE_URL}/auth/disconnect/google`);
      }
    } catch (error) {
      console.error('Logout failed:', error);
    } finally {
      setIsAuthenticated(false);
      setUser(null);
      setAuthStatus({ google: false, notion: false });
    }
  };

  return { 
    isAuthenticated, 
    user, 
    loading, 
    authStatus,
    initiateGoogleLogin, 
    logout, 
    checkAuthStatus 
  };
};
