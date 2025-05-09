<!-- src/components/layout/Navbar.vue -->
<template>
  <nav class="navbar">
    <div class="navbar-left">
      <button type="button" class="sidebar-toggle" @click="toggleSidebar">
        <i class="ri-menu-line text-xl"></i>
      </button>
      <div class="breadcrumb">
        <span class="breadcrumb-item">{{ pageTitle }}</span>
      </div>
    </div>

    <div class="navbar-right">
      <!-- Notifications -->
      <div class="notification-bell">
        <button type="button" class="icon-button">
          <i class="ri-notification-3-line"></i>
          <span class="notification-badge"></span>
        </button>
      </div>

      <!-- Tenant Selector -->
      <div v-if="isSuperAdmin" class="tenant-selector">
        <button @click="toggleTenantDropdown" class="tenant-button">
          <span class="tenant-name">{{ currentTenantName }}</span>
          <i class="ri-arrow-down-s-line"></i>
        </button>

        <div v-if="tenantDropdownOpen" class="dropdown tenant-dropdown">
          <div class="dropdown-header">Switch Tenant</div>
          <div v-for="tenant in tenants" :key="tenant.slug" @click="switchToTenant(tenant.slug)" class="dropdown-item" :class="{ 'active': tenant.slug === selectedTenant }">
            <span>{{ tenant.name }}</span>
            <i v-if="tenant.slug === selectedTenant" class="ri-check-line text-success"></i>
          </div>
        </div>
      </div>

      <!-- User Menu -->
      <div class="user-menu">
        <button type="button" class="user-menu-button" @click="toggleUserMenu">
          <div class="user-avatar" :style="{ 'background-color': avatarColor }">
            <span>{{ userInitials }}</span>
          </div>
          <span class="user-name">{{ username }}</span>
          <i class="ri-arrow-down-s-line"></i>
        </button>

        <div v-if="userMenuOpen" class="dropdown user-dropdown">
          <div class="dropdown-header">
            <div class="user-info">
              <div class="user-avatar large" :style="{ 'background-color': avatarColor }">
                <span>{{ userInitials }}</span>
              </div>
              <div class="user-details">
                <div class="user-fullname">{{ authStore.fullName }}</div>
                <div class="user-email">{{ authStore.user?.email }}</div>
              </div>
            </div>
          </div>

          <div class="dropdown-items">
            <a href="#" class="dropdown-item">
              <i class="ri-user-line"></i> Profile
            </a>
            <a href="#" class="dropdown-item">
              <i class="ri-settings-3-line"></i> Settings
            </a>
            <div class="dropdown-divider"></div>
            <a href="#" class="dropdown-item text-danger" @click.prevent="logout">
              <i class="ri-logout-box-line"></i> Logout
            </a>
          </div>
        </div>
      </div>
    </div>
  </nav>
</template>

<script>
import { useAuthStore } from '@/stores/auth';
import { useTenantStore } from '@/stores/tenant';

export default {
  name: 'Navbar',

  emits: ['toggle-sidebar'],

  data: function () {
    return {
      userMenuOpen: false,
      tenantDropdownOpen: false,
      selectedTenant: null,
      avatarColor: '#0284c7' // Default color
    };
  },

  computed: {
    pageTitle: function () {
      return this.$route.meta.title || '';
    },

    username: function () {
      return this.authStore.fullName || this.authStore.username || 'User';
    },

    userInitials: function () {
      if (!this.authStore.fullName) return 'U';

      return this.authStore.fullName
        .split(' ')
        .map(name => name.charAt(0))
        .join('')
        .toUpperCase()
        .substring(0, 2);
    },

    tenants: function () {
      return this.tenantStore.availableTenants || [];
    },

    currentTenantName: function () {
      return this.tenantStore.currentTenantName || 'Select Tenant';
    },

    isSuperAdmin: function () {
      return this.authStore.isSuperAdmin && this.tenants.length > 0;
    },

    authStore: function () {
      return useAuthStore();
    },

    tenantStore: function () {
      return useTenantStore();
    }
  },

  mounted: function () {
    this.selectedTenant = this.authStore.currentTenant;

    // Generate consistent avatar color based on username
    this.generateAvatarColor();

    // Fetch tenants if user is superadmin
    if (this.authStore.isSuperAdmin) {
      this.tenantStore.fetchTenants();
    }

    // Close dropdowns when clicking outside
    document.addEventListener('click', this.closeDropdownsOnClickOutside);
  },

  beforeUnmount: function () {
    document.removeEventListener('click', this.closeDropdownsOnClickOutside);
  },

  methods: {
    toggleSidebar: function () {
      this.$emit('toggle-sidebar');
    },

    toggleUserMenu: function (event) {
      event.stopPropagation();
      this.userMenuOpen = !this.userMenuOpen;
      this.tenantDropdownOpen = false;
    },

    toggleTenantDropdown: function (event) {
      event.stopPropagation();
      this.tenantDropdownOpen = !this.tenantDropdownOpen;
      this.userMenuOpen = false;
    },

    closeDropdownsOnClickOutside: function (event) {
      if (!this.$el.contains(event.target)) {
        this.userMenuOpen = false;
        this.tenantDropdownOpen = false;
      }
    },

    switchToTenant: function (tenantSlug) {
      if (tenantSlug && tenantSlug !== this.authStore.currentTenant) {
        this.tenantStore.switchTenant(tenantSlug);
      }
      this.tenantDropdownOpen = false;
    },

    generateAvatarColor: function () {
      // Simple hash function to generate consistent color from username
      const hash = this.username.split('').reduce((acc, char) => {
        return char.charCodeAt(0) + ((acc << 5) - acc);
      }, 0);

      // Generate hue between 0 and 360
      const hue = hash % 360;
      this.avatarColor = `hsl(${hue}, 70%, 50%)`;
    },

    logout: function () {
      this.authStore.logout();
    }
  }
};
</script>

<style lang="postcss" scoped>
.navbar-left {
  @apply flex items-center space-x-4;
}

.navbar-right {
  @apply flex items-center space-x-5;
}

.sidebar-toggle {
  @apply p-2 rounded-full text-gray-500 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 transition-colors duration-200;
}

.breadcrumb {
  @apply hidden md:flex text-lg font-semibold text-gray-800;
}

/* Tenant selector */
.tenant-selector {
  @apply relative;
}

.tenant-button {
  @apply flex items-center space-x-1 rounded-md py-1.5 px-3 text-sm font-medium text-gray-600 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 transition-colors duration-200;
}

.tenant-name {
  @apply hidden md:block max-w-[120px] truncate;
}

.tenant-dropdown {
  @apply w-56 right-0;
}

/* User menu */
.user-menu {
  @apply relative;
}

.user-menu-button {
  @apply flex items-center space-x-2 rounded-full py-1 pl-1 pr-2 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 transition-colors duration-200;
}

.user-name {
  @apply hidden md:block text-sm font-medium text-gray-700 max-w-[120px] truncate;
}

.user-dropdown {
  @apply right-0 w-64;
}

.user-info {
  @apply flex items-center space-x-3 p-2;
}

.user-details {
  @apply flex flex-col;
}

.user-fullname {
  @apply text-sm font-medium text-gray-900;
}

.user-email {
  @apply text-xs text-gray-500 truncate max-w-[180px];
}
</style>