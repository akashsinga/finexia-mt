<!-- src/components/layout/Sidebar.vue -->
<template>
  <aside class="sidebar" :class="{ 'sidebar-expanded': isOpen, 'sidebar-collapsed': !isOpen }">
    <!-- Logo -->
    <div class="sidebar-header">
      <div class="logo-container">
        <img src="@/assets/logo.svg" alt="Finexia" class="logo-image" v-if="isOpen" />
        <img src="@/assets/logo-icon.svg" alt="Finexia" class="logo-icon" v-else />
      </div>
      <button @click="$emit('close')" class="sidebar-close-btn" v-if="isOpen && isMobile">
        <i class="ri-close-line"></i>
      </button>
    </div>

    <!-- Navigation -->
    <div class="sidebar-nav">
      <nav>
        <router-link v-for="item in navigationItems" :key="item.path" :to="item.path" :class="['nav-item', { 'active': isActive(item) }]" v-show="!item.meta?.hideInMenu && canAccessRoute(item)">
          <div class="nav-icon">
            <i :class="`ri-${item.meta.icon}-line`"></i>
          </div>
          <span class="nav-text" v-if="isOpen">{{ item.meta.title }}</span>
        </router-link>
      </nav>
    </div>

    <!-- Bottom section -->
    <div class="sidebar-footer">
      <div class="tenant-info" v-if="isOpen">
        <div class="tenant-details">
          <div class="tenant-name">{{ tenantName }}</div>
          <div class="tenant-plan">{{ tenantPlan }}</div>
        </div>
      </div>
      <div class="collapse-button" @click="$emit('close')">
        <i :class="isOpen ? 'ri-arrow-left-s-line' : 'ri-arrow-right-s-line'"></i>
        <span v-if="isOpen">Collapse</span>
      </div>
    </div>
  </aside>
</template>

<script>
import { useAuthStore } from '@/stores/auth';
import { useTenantStore } from '@/stores/tenant';

export default {
  name: 'Sidebar',

  props: {
    isOpen: {
      type: Boolean,
      default: true
    }
  },

  emits: ['close'],

  data: function () {
    return {
      isMobile: false
    };
  },

  computed: {
    navigationItems: function () {
      return this.$router.options.routes.find(r => r.path === '/').children;
    },

    tenantName: function () {
      return this.tenantStore.currentTenantName || 'No Tenant';
    },

    tenantPlan: function () {
      const plan = this.tenantStore.currentTenantPlan || 'basic';
      return plan.charAt(0).toUpperCase() + plan.slice(1);
    },

    authStore: function () {
      return useAuthStore();
    },

    tenantStore: function () {
      return useTenantStore();
    }
  },

  mounted: function () {
    this.checkMobileView();
    window.addEventListener('resize', this.checkMobileView);
  },

  beforeUnmount: function () {
    window.removeEventListener('resize', this.checkMobileView);
  },

  methods: {
    isActive: function (item) {
      if (this.$route.path === item.path) {
        return true;
      }

      // Handle active state for child routes
      if (item.path !== '/' && this.$route.path.startsWith(item.path)) {
        return true;
      }

      return false;
    },

    canAccessRoute: function (item) {
      if (item.meta?.requiresAdmin) {
        return this.authStore.isAdmin;
      }

      return true;
    },

    checkMobileView: function () {
      this.isMobile = window.innerWidth < 768;

      // Auto close sidebar on mobile
      if (this.isMobile && this.isOpen) {
        this.$emit('close');
      }
    }
  }
};
</script>

<style lang="postcss" scoped>
.sidebar {
  @apply h-screen flex flex-col bg-white z-40 transition-all duration-300 ease-in-out border-r border-gray-100;
}

.sidebar-expanded {
  @apply w-64;
}

.sidebar-collapsed {
  @apply w-16;
}

/* Mobile sidebar */
@media (max-width: 767px) {
  .sidebar {
    @apply fixed top-0 left-0 bottom-0;
  }

  .sidebar-expanded {
    @apply translate-x-0 shadow-xl;
  }

  .sidebar-collapsed {
    @apply -translate-x-full;
  }
}

/* Header */
.sidebar-header {
  @apply flex items-center justify-between h-16 px-4 border-b border-gray-100;
}

.logo-container {
  @apply flex items-center h-full;
}

.logo-image {
  @apply h-8;
}

.logo-icon {
  @apply h-8 w-8;
}

.sidebar-close-btn {
  @apply text-gray-500 hover:text-gray-700 p-1;
}

/* Navigation */
.sidebar-nav {
  @apply flex-1 overflow-y-auto py-4 scrollbar-thin;
}

.nav-item {
  @apply flex items-center px-4 py-2.5 text-gray-700 hover:bg-gray-50 hover:text-primary-600 transition-colors duration-200 mb-1 mx-2 rounded-md;
}

.nav-item.active {
  @apply bg-primary-50 text-primary-600 font-medium;
}

.nav-icon {
  @apply text-xl min-w-[24px] flex justify-center;
}

.nav-text {
  @apply ml-3 text-sm;
}

/* Footer */
.sidebar-footer {
  @apply mt-auto border-t border-gray-100 p-4;
}

.tenant-info {
  @apply flex items-center mb-4 p-3 bg-gray-50 rounded-lg;
}

.tenant-details {
  @apply flex-1 min-w-0;
}

.tenant-name {
  @apply text-sm font-medium text-gray-900 truncate;
}

.tenant-plan {
  @apply text-xs text-gray-500;
}

.collapse-button {
  @apply flex items-center justify-center text-xs text-gray-500 hover:text-primary-600 hover:bg-gray-50 p-2 rounded-md cursor-pointer transition-colors duration-200;
}

.sidebar-collapsed .collapse-button {
  @apply justify-center;
}

/* Custom scrollbar */
.scrollbar-thin {
  scrollbar-width: thin;
  scrollbar-color: rgba(156, 163, 175, 0.5) transparent;
}

.scrollbar-thin::-webkit-scrollbar {
  width: 4px;
}

.scrollbar-thin::-webkit-scrollbar-track {
  background: transparent;
}

.scrollbar-thin::-webkit-scrollbar-thumb {
  background-color: rgba(156, 163, 175, 0.5);
  border-radius: 20px;
}
</style>