// src/plugins/index.js
import axios from 'axios';

// API Configuration
const setupApiClient = () => {
  const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

  // Create a base axios instance
  const api = axios.create({
    baseURL: API_URL,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Add a request interceptor to inject the auth token
  api.interceptors.request.use(
    (config) => {
      const token = localStorage.getItem('token');
      if (token) {
        config.headers['Authorization'] = `Bearer ${token}`;
      }

      // Add tenant header if available
      const tenant = localStorage.getItem('tenant');
      if (tenant) {
        config.headers['X-Tenant'] = tenant;
      }

      return config;
    },
    (error) => Promise.reject(error)
  );

  // Add a response interceptor for error handling
  api.interceptors.response.use(
    (response) => response,
    (error) => {
      // Handle session expiration - redirect to login
      if (error.response && error.response.status === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('tenant');
        window.location.href = '/login';
      }
      return Promise.reject(error);
    }
  );

  return api;
};

// Date formatting
const setupDateFormatters = () => {
  // You can add date formatting utilities here
  const formatDate = (date) => {
    if (!date) return '';
    return new Date(date).toLocaleDateString();
  };

  const formatDateTime = (date) => {
    if (!date) return '';
    return new Date(date).toLocaleString();
  };

  return { formatDate, formatDateTime };
};

// Export configured plugins
export const api = setupApiClient();
export const dateUtils = setupDateFormatters();

// Plugin installation
export default {
  install: (app) => {
    app.config.globalProperties.$api = api;
    app.config.globalProperties.$dateUtils = dateUtils;

    // Make available in Options API
    app.provide('api', api);
    app.provide('dateUtils', dateUtils);
  }
};