// src/stores/dashboard.js
import { defineStore } from 'pinia';
import { api } from '@/plugins';
import { useAuthStore } from './auth';
import { websocketService } from '@/services/websocket';

export const useDashboardStore = defineStore('dashboard', {
  state: () => ({
    systemStatus: null,
    predictions: [],
    predictionTrends: [],
    topSymbols: [],
    loading: false,
    error: null,
    lastUpdated: null,
    websocketConnected: false
  }),

  actions: {
    async fetchSystemStatus() {
      try {
        const response = await api.get('/system/status');
        this.systemStatus = response.data;
        return this.systemStatus;
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to fetch system status';
        throw error;
      }
    },

    async fetchRecentPredictions(limit = 5) {
      try {
        const response = await api.get('/predictions', { params: { limit, verified: false } });
        this.predictions = response.data.predictions;
        return this.predictions;
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to fetch predictions';
        throw error;
      }
    },

    async fetchDashboardSummary(timeframe = '1m') {
      this.loading = true;
      this.error = null;

      try {
        const response = await api.get('/analytics/dashboard', { params: { timeframe } });

        const data = response.data;
        this.predictionTrends = data.prediction_trends;
        this.topSymbols = data.top_performing_symbols;
        this.lastUpdated = new Date();

        this.loading = false;
        return data;
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to fetch dashboard data';
        this.loading = false;
        throw error;
      }
    },

    connectToWebsocket() {
      const authStore = useAuthStore();

      if (!authStore.isAuthenticated) {
        return false;
      }

      this.websocketConnected = websocketService.connect('dashboard');

      websocketService.addListener('dashboard', null, 'dashboard_update', (data) => {
        // Handle real-time dashboard updates
        if (data.update_type === 'dashboard_refresh') {
          // Update store data with new values
          if (data.data.prediction_trends) {
            this.predictionTrends = data.data.prediction_trends;
          }

          if (data.data.top_performing_symbols) {
            this.topSymbols = data.data.top_performing_symbols;
          }

          this.lastUpdated = new Date();
        }
      });

      return this.websocketConnected;
    },

    disconnectWebsocket() {
      return websocketService.disconnect('dashboard');
    }
  },

  getters: {
    verificationRate: (state) => {
      if (!state.systemStatus) return 0;
      return state.systemStatus.verification_rate || 0;
    },

    totalPredictions: (state) => {
      if (!state.systemStatus) return 0;
      return state.systemStatus.total_predictions || 0;
    },

    todayPredictions: (state) => {
      if (!state.systemStatus) return 0;
      return state.systemStatus.today_predictions || 0;
    }
  }
});