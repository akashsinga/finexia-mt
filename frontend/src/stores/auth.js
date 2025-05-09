// src/stores/auth.js
import { defineStore } from 'pinia';
import { api } from '@/plugins';
import router from '@/router';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || null,
    user: JSON.parse(localStorage.getItem('user')) || null,
    tenant: localStorage.getItem('tenant') || null,
    loading: false,
    error: null
  }),

  getters: {
    isAuthenticated: (state) => !!state.token,
    isAdmin: (state) => state.user?.is_admin || false,
    isSuperAdmin: (state) => state.user?.is_superadmin || false,
    username: (state) => state.user?.username || '',
    fullName: (state) => state.user?.full_name || '',
    currentTenant: (state) => state.tenant,
  },

  actions: {
    async login(username, password) {
      this.loading = true;
      this.error = null;

      try {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const response = await api.post('/auth/token', formData, {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
          }
        });

        this.setAuthData(response.data);
        return response.data;
      } catch (error) {
        this.error = error.response?.data?.detail || 'Login failed';
        throw error;
      } finally {
        this.loading = false;
      }
    },

    setAuthData(data) {
      this.token = data.access_token;
      localStorage.setItem('token', data.access_token);

      // Store tenant if available
      if (data.tenant_slug) {
        this.tenant = data.tenant_slug;
        localStorage.setItem('tenant', data.tenant_slug);
      }

      // Fetch user info
      this.fetchUserInfo();
    },

    async fetchUserInfo() {
      try {
        const response = await api.get('/users/me');
        this.user = response.data;
        localStorage.setItem('user', JSON.stringify(response.data));
      } catch (error) {
        console.error('Failed to fetch user info:', error);
      }
    },

    logout() {
      this.token = null;
      this.user = null;
      this.tenant = null;
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      localStorage.removeItem('tenant');
      router.push('/login');
    },

    clearError() {
      this.error = null;
    }
  }
});