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
      console.log('Auth status response:', status); // Debug log
      setAuthStatus(status);
      
      // User is authenticated if Google is connected
      if (status.google && status.google.connected) {
        setIsAuthenticated(true);
        // Use user info from Google if available
        if (status.google.user && status.google.user.given_name) {
          const userInfo = status.google.user;
          console.log('✅ User info from backend:', userInfo); // Debug log
          const firstName = userInfo.given_name || userInfo.name || 'User';
          console.log('✅ Setting user name to:', firstName); // Debug log
          setUser({
            name: firstName, // Use first name (given_name) - this is what displays
            email: userInfo.email || '',
            picture: userInfo.picture || ''
          });
        } else if (status.google.user && status.google.user.name) {
          // Fallback to full name if given_name is not available
          const userInfo = status.google.user;
          console.log('⚠️ Using full name (given_name not available):', userInfo.name);
          setUser({
            name: userInfo.name.split(' ')[0] || 'User', // Extract first word as first name
            email: userInfo.email || '',
            picture: userInfo.picture || ''
          });
        } else {
          // Fallback if user info not available yet
          console.warn('⚠️ User info not available in status response. User may need to re-authenticate.');
          console.warn('Status response:', JSON.stringify(status, null, 2));
          setUser({ name: 'User', email: '' });
        }
      } else {
        setIsAuthenticated(false);
        setUser(null);
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      console.error('Error details:', error.response?.data || error.message);
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
