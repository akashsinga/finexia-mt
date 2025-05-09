// src/stores/tenant.js
import { defineStore } from 'pinia';
import { api } from '@/plugins';
import { useAuthStore } from './auth';

export const useTenantStore = defineStore('tenant', {
  state: () => ({
    tenants: [],
    currentTenant: null,
    loading: false,
    error: null
  }),

  getters: {
    availableTenants: (state) => state.tenants,
    currentTenantName: (state) => state.currentTenant?.name || 'No Tenant',
    currentTenantSlug: (state) => state.currentTenant?.slug || null,
    currentTenantId: (state) => state.currentTenant?.id || null,
    currentTenantPlan: (state) => state.currentTenant?.plan || 'basic',
  },

  actions: {
    async fetchTenants() {
      const authStore = useAuthStore();

      // Only superadmins can list all tenants
      if (!authStore.isSuperAdmin) {
        return;
      }

      this.loading = true;
      this.error = null;

      try {
        const response = await api.get('/tenants');
        this.tenants = response.data;
        return this.tenants;
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to fetch tenants';
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async fetchCurrentTenant() {
      const authStore = useAuthStore();
      const tenantSlug = authStore.tenant;

      if (!tenantSlug) {
        this.currentTenant = null;
        return null;
      }

      this.loading = true;
      this.error = null;

      try {
        // For a regular user, we need to get tenant info from the system endpoint
        const response = await api.get('/system/status');
        this.currentTenant = {
          id: response.data.tenant_id,
          name: response.data.tenant_name,
          slug: tenantSlug,
          plan: response.data.tenant_plan || 'basic',
        };
        return this.currentTenant;
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to fetch tenant info';
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async switchTenant(tenantSlug) {
      const authStore = useAuthStore();

      if (!tenantSlug) {
        return false;
      }

      // Update in localStorage and auth store
      localStorage.setItem('tenant', tenantSlug);
      authStore.tenant = tenantSlug;

      // Fetch the current tenant info
      await this.fetchCurrentTenant();

      // Reload the page to reset application state
      window.location.reload();

      return true;
    },

    clearError() {
      this.error = null;
    }
  }
});