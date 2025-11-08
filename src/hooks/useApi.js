import { useState, useCallback } from 'react';
import apiClient from '../utils/api';

/**
 * Generic API hook for data fetching with loading/error states
 */
export const useApi = (endpoint, options = {}) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async (params = {}) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiClient.get(endpoint, { params, ...options });
      setData(response.data);
      return response.data;
    } catch (err) {
      setError(err.message || 'An error occurred');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [endpoint]);

  const postData = useCallback(async (body) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiClient.post(endpoint, body, options);
      setData(response.data);
      return response.data;
    } catch (err) {
      setError(err.message || 'An error occurred');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [endpoint]);

  return { data, loading, error, fetchData, postData, setData };
};
