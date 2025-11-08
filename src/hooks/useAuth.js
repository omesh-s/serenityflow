import { useState, useEffect } from 'react';
import apiClient from '../utils/api';

/**
 * Authentication hook - manages Google OAuth login state
 * TODO: Connect to backend /auth/google endpoint
 */
export const useAuth = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const token = localStorage.getItem('auth_token');
      if (!token) {
        setLoading(false);
        return;
      }

      // TODO: API Call - Verify token with backend
      // const response = await apiClient.get('/auth/verify');
      // setUser(response.data.user);
      
      // Mock data for development
      setUser({ name: 'User', email: 'user@example.com' });
      setIsAuthenticated(true);
    } catch (error) {
      console.error('Auth check failed:', error);
      localStorage.removeItem('auth_token');
      setIsAuthenticated(false);
    } finally {
      setLoading(false);
    }
  };

  const login = async (googleToken) => {
    try {
      // TODO: API Call - Exchange Google token for backend JWT
      // const response = await apiClient.post('/auth/google', { token: googleToken });
      // localStorage.setItem('auth_token', response.data.token);
      // setUser(response.data.user);
      
      // Mock implementation
      localStorage.setItem('auth_token', 'mock_token_' + googleToken);
      setIsAuthenticated(true);
      return true;
    } catch (error) {
      console.error('Login failed:', error);
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem('auth_token');
    setIsAuthenticated(false);
    setUser(null);
  };

  return { isAuthenticated, user, loading, login, logout };
};
