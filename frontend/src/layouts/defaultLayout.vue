<template>
  <div class="flex min-h-screen w-full">
    <!-- Sidebar -->
    <div class="fixed z-10 h-full transition-all duration-300 bg-white border-r border-gray-300 flex flex-col" :class="{ 'w-64': !collapsed, 'w-16': collapsed }">
      <!-- Header -->
      <div class="py-5 px-4 border-b border-gray-200" :class="{ 'justify-center px-0': collapsed }">
        <div class="flex items-center gap-3" :class="{ 'justify-center': collapsed }">
          <div class="w-10 h-10 bg-blue-800 rounded-lg flex items-center justify-center p-1">
            <img src="@/assets/images/favicon.svg" class="w-full h-full" alt="Finexia logo" />
          </div>
          <div v-if="!collapsed" class="flex flex-col">
            <div class="text-lg font-bold text-gray-800">Finexia</div>
            <div class="text-xs text-gray-500">Predictive Stock Analytics</div>
          </div>
        </div>
      </div>

      <!-- Collapse Button -->
      <button class="absolute top-1/2 -right-3.5 w-7 h-7 bg-white rounded-full flex items-center justify-center ring-1 ring-gray-300 text-gray-600 hover:text-blue-600 transition-colors duration-200" @click="toggleSidebar" aria-label="Toggle sidebar">
        <i class="ph" :class="collapsed ? 'ph-caret-right' : 'ph-caret-left'"></i>
      </button>

      <!-- Sidebar Content -->
      <div class="flex flex-col justify-between flex-grow px-3 py-4" :class="{ 'px-2': collapsed }">
        <!-- Navigation -->
        <div class="mb-auto">
          <div class="flex flex-col space-y-1">
            <div v-for="(item, i) in navItems" :key="i" class="nav-item flex relative cursor-pointer rounded-lg transition-all duration-200" :class="{ 'active': $route.name === item.pathName }" @click="navigateTo(item.pathName)">
              <div v-if="!collapsed" class="w-1 absolute bg-transparent h-6 -left-3 top-1/2 -translate-y-1/2 rounded-r-full transition-all duration-200" :class="{ 'bg-blue-600': $route.name === item.pathName }"></div>
              <div class="nav-link flex items-center w-full py-2.5 px-3 space-x-3 rounded-lg transition-all duration-200" :class="{ 'bg-blue-50': $route.name === item.pathName, 'justify-center': collapsed }">
                <i class="ph text-lg transition-colors duration-200" :class="[item.icon, $route.name === item.pathName ? 'text-blue-600' : 'text-gray-500']"></i>
                <span v-if="!collapsed" class="text-sm font-medium transition-colors duration-200" :class="$route.name === item.pathName ? 'text-blue-600 font-semibold' : 'text-gray-600'">
                  {{ item.title }}
                </span>
                <i v-if="!collapsed && $route.name === item.pathName" class="ph ph-caret-right text-sm absolute right-2 text-blue-600"></i>
              </div>
            </div>
          </div>
        </div>

        <!-- Tenant Selector -->
        <div v-if="tenantStore.availableTenants.length && !collapsed" class="mt-4 pt-4 border-t border-gray-200">
          <div class="form-input-icon-wrapper">
            <i class="ph ph-buildings input-icon"></i>
            <select id="tenant-select" class="form-select" v-model="tenantStore.currentTenantSlug" @change="switchTenant(tenantStore.currentTenantSlug)">
              <option v-for="tenant in tenantStore.availableTenants" :key="tenant.id" :value="tenant.slug">
                {{ tenant.name }}
              </option>
            </select>
          </div>
        </div>


        <!-- User Info with Logout Icon -->
        <div v-if="authStore.isAuthenticated" class="mt-4 pt-4 border-t border-gray-200 flex justify-between items-center" :class="{ 'justify-center': collapsed }">
          <div class="flex items-center gap-3" :class="{ 'justify-center': collapsed }">
            <div class="w-9 h-9 rounded-full bg-blue-600 text-white flex items-center justify-center font-semibold text-sm">
              {{ userInitials }}
            </div>
            <div v-if="!collapsed" class="flex flex-col">
              <div class="text-sm font-medium text-gray-800">{{ authStore.fullName }}</div>
              <div class="text-xs text-gray-500 truncate max-w-[10rem]">{{ userEmail }}</div>
            </div>
          </div>
          <button v-if="!collapsed" @click="logout" class="text-gray-500 hover:text-red-600 transition-colors duration-200 cursor-pointer">
            <i class="ph ph-sign-out text-lg"></i>
          </button>
        </div>

        <!-- Separate logout button when collapsed -->
        <div v-if="collapsed && authStore.isAuthenticated" class="mt-2 flex justify-center border-t border-gray-200 pt-2">
          <button @click="logout" class="p-2 rounded-full text-gray-500 hover:text-red-600 hover:bg-gray-100 transition-colors duration-200">
            <i class="ph ph-sign-out"></i>
          </button>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="flex flex-col min-h-screen transition-all duration-300 w-full" :class="{ 'pl-64': !collapsed, 'pl-16': collapsed }">
      <div class="sticky top-0 z-40 px-6 py-3 flex items-center justify-between bg-white/90 border-b border-gray-300 backdrop-blur">
        <div class="flex flex-col">
          <h1 class="text-lg font-semibold text-blue-600">{{ pageTitle }}</h1>
          <div v-if="breadcrumbs.length > 1" class="flex items-center text-xs text-gray-500 mt-1">
            <div v-for="(crumb, index) in breadcrumbs" :key="index" class="flex items-center">
              <span v-if="index < breadcrumbs.length - 1" class="text-blue-600 hover:text-blue-800 cursor-pointer" @click="navigateTo(crumb.name)">
                {{ crumb.title }}
              </span>
              <span v-else class="font-medium text-gray-600">{{ crumb.title }}</span>
              <i v-if="index < breadcrumbs.length - 1" class="ph ph-caret-right mx-1 text-gray-400 text-xs"></i>
            </div>
          </div>
        </div>
        <div class="flex items-center gap-4">
          <div class="flex items-center gap-2 px-3 py-1 rounded-full text-sm bg-gray-100 border border-gray-300">
            <span class="w-2.5 h-2.5 rounded-full shadow-md" :class="marketStatus === 'LIVE' ? 'bg-green-500' : 'bg-red-500'"></span>
            <span class="text-gray-700">{{ marketStatus }}</span>
            <span class="text-gray-500 text-xs">• {{ formattedTime }} IST</span>
          </div>
          <div class="flex items-center gap-1">
            <!-- Notification button -->
            <button class="p-2 text-gray-500 hover:text-blue-600 hover:bg-gray-100 rounded-full transition-colors duration-200 relative">
              <i class="ph ph-bell"></i>
              <span v-if="notificationCount > 0" class="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-red-500 text-white text-[10px] flex items-center justify-center">
                {{ notificationCount }}
              </span>
            </button>
            <!-- Help button -->
            <button class="p-2 text-gray-500 hover:text-blue-600 hover:bg-gray-100 rounded-full transition-colors duration-200">
              <i class="ph ph-question"></i>
            </button>
          </div>
        </div>
      </div>

      <div class="flex-1 p-6 overflow-auto relative bg-gray-50 content-area">
        <!-- Add transition wrapper around router-view -->
        <transition name="fade-slide" mode="out-in">
          <router-view />
        </transition>
      </div>

      <div class="py-3 px-6 text-xs text-gray-500 bg-white/90 border-t border-gray-300 backdrop-blur">
        <div class="flex justify-between items-center">
          <div>© {{ currentYear }} Finexia - All rights reserved</div>
          <div>Version 1.0.0</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { useAuthStore } from '@/stores/auth'
import { useTenantStore } from '@/stores/tenant'

export default {
  name: 'DefaultLayout',
  data() {
    return {
      collapsed: false,
      marketOpenTime: '09:15',
      marketCloseTime: '15:30',
      currentTime: null,
      notificationCount: 3,
      showTenantDropdown: false,
      navItems: [
        { title: 'Dashboard', icon: 'ph-chart-line', pathName: 'dashboard' },
        { title: 'Pipeline', icon: 'ph-flow-arrow', pathName: 'pipeline' },
        { title: 'Symbols', icon: 'ph-trend-up', pathName: 'symbols' },
        { title: 'Predictions', icon: 'ph-chart-bar', pathName: 'predictions' },
        { title: 'Models', icon: 'ph-brain', pathName: 'models' },
        { title: 'Settings', icon: 'ph-gear', pathName: 'settings' }
      ]
    }
  },
  computed: {
    authStore() {
      return useAuthStore()
    },
    tenantStore() {
      return useTenantStore()
    },
    userInitials() {
      const username = this.authStore.username || '';
      return username.substring(0, 2).toUpperCase();
    },
    userEmail() {
      return this.authStore.user?.email || 'user@example.com';
    },
    currentTenantName() {
      return this.tenantStore.currentTenantName || 'Select Tenant';
    },
    marketStatus() {
      const now = this.currentTime;
      const open = new Date(now);
      const close = new Date(now);

      const [openH, openM] = this.marketOpenTime.split(':');
      const [closeH, closeM] = this.marketCloseTime.split(':');

      open.setHours(parseInt(openH), parseInt(openM), 0);
      close.setHours(parseInt(closeH), parseInt(closeM), 0);

      return now >= open && now <= close ? 'LIVE' : 'CLOSED';
    },
    formattedTime() {
      return this.currentTime.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    },
    currentYear() {
      return new Date().getFullYear();
    },
    pageTitle() {
      return this.$route.meta?.title || 'Dashboard';
    },
    breadcrumbs() {
      const crumbs = [];

      // Always include home
      crumbs.push({ title: 'Home', name: 'dashboard' });

      // Add current page
      if (this.$route.name && this.$route.name !== 'dashboard') {
        // Find the nav item with the matching pathName
        const navItem = this.navItems.find(item => item.pathName === this.$route.name);

        if (navItem) {
          crumbs.push({ title: navItem.title, name: navItem.pathName });
        }

        // If we have a route param like symbol, add it as the final crumb
        if (this.$route.params.symbol) {
          crumbs.push({ title: this.$route.params.symbol, name: null });
        }
      }

      return crumbs;
    }
  },
  methods: {
    toggleSidebar: function () {
      this.collapsed = !this.collapsed;
    },
    toggleTenantDropdown: function () {
      if (!this.collapsed) {
        this.showTenantDropdown = !this.showTenantDropdown;
      }
    },
    switchTenant: async function (tenantSlug) {
      try {
        await this.tenantStore.switchTenant(tenantSlug);
        this.showTenantDropdown = false;
      } catch (error) {
        console.error('Failed to switch tenant:', error);
      }
    },
    logout: function () {
      this.authStore.logout();
      this.$router.push('/login');
    },
    navigateTo: function (routeName) {
      if (routeName) {
        this.$router.push({ name: routeName });
      }
    },
    closeDropdowns: function (event) {
      // Close tenant dropdown when clicking outside
      if (this.showTenantDropdown && !event.target.closest('.tenant-dropdown')) {
        this.showTenantDropdown = false;
      }
    }
  },
  created() {
    this.currentTime = new Date();
    this._clock = setInterval(() => {
      this.currentTime = new Date();
    }, 1000);

    // Fetch tenants if user is authenticated
    if (this.authStore.isAuthenticated) {
      this.tenantStore.fetchTenants();
      this.tenantStore.fetchCurrentTenant();
    }

    // Add event listener to close dropdowns when clicking outside
    document.addEventListener('click', this.closeDropdowns);
  },
  beforeUnmount() {
    clearInterval(this._clock);
    document.removeEventListener('click', this.closeDropdowns);
  }
}
</script>

<style lang="postcss" scoped>
/* Page transition animations */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* Content area background pattern */
.content-area::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle, rgba(191, 219, 254, 0.4) 1px, transparent 1px),
    radial-gradient(circle, rgba(186, 230, 253, 0.3) 1px, transparent 1px);
  opacity: 0.5;
  pointer-events: none;
  z-index: 0;
}

/* Navigation hover styles */
.nav-item .nav-link:hover {
  @apply bg-gray-100;
}

.nav-item:hover .ph {
  @apply text-gray-700;
}

.nav-item:hover .nav-link span {
  @apply text-gray-800;
}

/* Active nav-item already has styles */
.nav-item.active .nav-link:hover {
  @apply bg-blue-50;
}
</style>