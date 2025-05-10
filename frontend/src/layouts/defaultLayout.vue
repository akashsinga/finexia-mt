<template>
  <div class="flex min-h-screen w-full bg-gray-50">
    <!-- Sidebar -->
    <aside class="fixed z-10 h-full transition-all duration-300 bg-white border-r border-slate-300 flex flex-col shadow-sm" :class="[sidebarClass, { 'w-64': !collapsed, 'w-16': collapsed }]">
      <!-- Logo section -->
      <div class="p-4 border-b border-slate-300" :class="{ 'justify-center !px-0': collapsed }">
        <div class="flex items-center gap-3" :class="{ 'justify-center': collapsed }">
          <div class="w-10 h-10 bg-blue-800 rounded-lg flex items-center justify-center p-1 shadow-md">
            <img src="@/assets/images/favicon.svg" class="w-full h-full" alt="Finexia logo" />
          </div>
          <div v-if="!collapsed" class="flex flex-col">
            <div class="text-lg font-bold text-gray-800">Finexia</div>
            <div class="text-xs text-gray-500 mt-0.5">Predictive Market Analytics</div>
          </div>
        </div>
      </div>

      <!-- Navigation -->
      <nav class="flex flex-col flex-grow py-4" :class="{ 'px-2': collapsed, 'px-3': !collapsed }">
        <div class="flex flex-col space-y-1">
          <div v-for="(item, i) in navItems" :key="i" class="nav-item flex relative cursor-pointer rounded-lg transition-all duration-200" :class="{ 'active': $route.name === item.pathName }" @click="navigateTo(item.pathName)">
            <div v-if="!collapsed" class="w-1 absolute bg-transparent h-6 -left-3 top-1/2 -translate-y-1/2 rounded-r-full transition-all duration-200" :class="{ 'bg-blue-600': $route.name === item.pathName }"></div>
            <div class="nav-link flex items-center w-full py-2.5 px-3 space-x-3 rounded-lg transition-all duration-200" :class="{ 'bg-blue-50': $route.name === item.pathName, 'justify-center': collapsed }">
              <i class="ph text-lg transition-colors duration-200" :class="[item.icon, $route.name === item.pathName ? 'text-blue-600' : 'text-gray-500']"></i>
              <span v-if="!collapsed" class="text-sm font-medium transition-colors duration-200" :class="$route.name === item.pathName ? 'text-blue-600 font-semibold' : 'text-gray-600'">
                {{ item.title }}
              </span>
            </div>
          </div>
        </div>
      </nav>

      <!-- Tenant Selector -->
      <div v-if="tenantStore.availableTenants.length && !collapsed" class="mt-auto px-4 pb-4 pt-3 border-t border-slate-300">
        <label for="tenant-select" class="block text-sm font-medium text-gray-700 mb-1.5">Current Organization</label>
        <div class="form-input-icon-wrapper">
          <i class="ph ph-buildings input-icon"></i>
          <select id="tenant-select" class="form-select" v-model="tenantStore.currentTenantSlug" @change="switchTenant(tenantStore.currentTenantSlug)">
            <option v-for="tenant in tenantStore.availableTenants" :key="tenant.id" :value="tenant.slug">
              {{ tenant.name }}
            </option>
          </select>
        </div>
      </div>
    </aside>

    <!-- Collapse Button - Centered and Fully Rounded -->
    <button class="fixed left-0 z-20 transform translate-x-[46px] top-1/2 -translate-y-1/2 w-5 h-5 bg-white rounded-full flex items-center justify-center ring-1 ring-gray-300 text-gray-600 hover:text-blue-600 hover:ring-blue-300 transition-all duration-200 shadow-md" :class="{ '!translate-x-[215px]': !collapsed }" @click="toggleSidebar" aria-label="Toggle sidebar">
      <i class="ph" :class="collapsed ? 'ph-caret-right' : 'ph-caret-left'"></i>
    </button>

    <!-- Main Content -->
    <main class="flex flex-col min-h-screen transition-all duration-300 w-full" :class="[contentClass, { 'pl-64': !collapsed, 'pl-16': collapsed }]">
      <!-- Top header bar -->
      <header class="sticky top-0 z-40 px-4 md:px-6 py-3 flex items-center justify-between bg-white border-b border-slate-300 backdrop-blur-sm">
        <div class="flex flex-col">
          <h1 class="text-base font-semibold text-gray-800">{{ pageTitle }}</h1>
          <div v-if="breadcrumbs.length > 1" class="flex items-center text-xs text-gray-500 mt-0.5">
            <div v-for="(crumb, index) in breadcrumbs" :key="index" class="flex items-center">
              <span v-if="index < breadcrumbs.length - 1" class="text-blue-600 hover:text-blue-800 cursor-pointer" @click="navigateTo(crumb.name)">
                {{ crumb.title }}
              </span>
              <span v-else class="font-medium text-gray-600">{{ crumb.title }}</span>
              <i v-if="index < breadcrumbs.length - 1" class="ph ph-caret-right mx-1 text-gray-400 text-xs"></i>
            </div>
          </div>
        </div>

        <div class="flex items-center gap-2 md:gap-4">
          <!-- Market status pill -->
          <div class="market-status-pill flex items-center gap-2 px-3 py-1 rounded-full text-xs bg-gray-100 border border-slate-300">
            <span class="w-2.5 h-2.5 rounded-full shadow-sm animate-pulse" :class="marketStatus === 'LIVE' ? 'bg-green-500' : 'bg-red-500'"></span>
            <span class="text-gray-700 hidden xs:inline">{{ marketStatus }}</span>
            <span class="text-gray-500 text-xs hidden sm:inline">• {{ formattedTime }} IST</span>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-2">
            <!-- Search button -->
            <button @click="openGlobalSearch" class="p-2 text-gray-500 hover:text-blue-600 hover:bg-gray-100 rounded-full transition-colors duration-200 relative" aria-label="Search">
              <i class="ph ph-magnifying-glass"></i>
              <span class="sr-only">Search</span>
            </button>

            <!-- Notification button -->
            <button @click="toggleNotifications" class="p-2 text-gray-500 hover:text-blue-600 hover:bg-gray-100 rounded-full transition-colors duration-200 relative" aria-label="Notifications">
              <i class="ph ph-bell"></i>
              <span v-if="notificationCount > 0" class="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-red-500 text-white text-[10px] flex items-center justify-center">
                {{ notificationCount > 9 ? '9+' : notificationCount }}
              </span>
              <span class="sr-only">Notifications</span>
            </button>

            <!-- Notification dropdown -->
            <div v-if="notificationsOpen" class="absolute right-16 top-12 w-80 bg-white rounded-lg shadow-lg z-50 border border-slate-300 animate-fade-in">
              <div class="flex justify-between items-center p-3 border-b border-slate-300">
                <h3 class="font-medium">Notifications</h3>
                <button class="text-xs text-blue-600 hover:text-blue-800">Mark all as read</button>
              </div>
              <div class="max-h-96 overflow-y-auto">
                <div v-if="notifications.length === 0" class="p-4 text-center text-gray-500">
                  <i class="ph ph-bell-slash text-2xl mb-2"></i>
                  <p>No notifications</p>
                </div>
                <div v-else>
                  <!-- Notification items would go here -->
                </div>
              </div>
              <div class="p-2 border-t border-slate-300">
                <button class="w-full py-1.5 text-sm text-center text-blue-600 hover:bg-blue-50 rounded">
                  View all notifications
                </button>
              </div>
            </div>

            <!-- Help button -->
            <button class="p-2 text-gray-500 hover:text-blue-600 hover:bg-gray-100 rounded-full transition-colors duration-200" aria-label="Help">
              <i class="ph ph-question"></i>
              <span class="sr-only">Help</span>
            </button>

            <!-- User menu -->
            <div class="relative user-menu">
              <button @click="toggleUserMenu" class="flex items-center gap-2 text-gray-700 hover:text-blue-600 p-1 rounded-full hover:bg-gray-50" aria-label="User menu" aria-expanded="userMenuOpen">
                <div class="w-8 h-8 rounded-full bg-gradient-to-br from-blue-600 to-blue-800 text-white flex items-center justify-center font-medium text-sm">
                  {{ userInitials }}
                </div>
              </button>

              <!-- Dropdown menu -->
              <div v-if="userMenuOpen" class="absolute right-0 mt-2 w-64 bg-white rounded-lg shadow-lg py-1 z-50 border border-slate-300 animate-fade-in">
                <div class="px-4 py-3 border-b border-slate-300">
                  <div class="font-medium text-gray-900">{{ authStore.fullName }}</div>
                  <div class="text-sm text-gray-500 truncate">{{ userEmail }}</div>
                </div>
                <div class="py-1">
                  <a href="#" class="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                    <i class="ph ph-user-circle mr-3 text-gray-400"></i>
                    <span>Your Profile</span>
                  </a>
                  <a href="#" class="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                    <i class="ph ph-gear mr-3 text-gray-400"></i>
                    <span>Settings</span>
                  </a>
                  <a href="#" class="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                    <i class="ph ph-chart-line-up mr-3 text-gray-400"></i>
                    <span>Activity Log</span>
                  </a>
                </div>
                <div class="py-1 border-t border-slate-300">
                  <a href="#" @click.prevent="logout" class="flex items-center px-4 py-2 text-sm text-red-600 hover:bg-gray-100">
                    <i class="ph ph-sign-out mr-3 text-red-500"></i>
                    <span>Sign out</span>
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      <!-- Global search modal -->
      <div v-if="showSearch" class="fixed inset-0 bg-black/30 backdrop-blur-sm z-50 flex items-start justify-center pt-20" @click="showSearch = false">
        <div class="bg-white w-full max-w-2xl rounded-lg shadow-xl overflow-hidden" @click.stop>
          <div class="p-4 border-b border-slate-300">
            <div class="relative">
              <i class="ph ph-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"></i>
              <input type="text" class="w-full py-2 pl-10 pr-4 border-none ring-1 ring-gray-300 rounded-lg focus:ring-blue-500 outline-none" placeholder="Search anything..." v-model="searchQuery" @keydown.esc="showSearch = false" ref="searchInput">
            </div>
          </div>

          <div class="max-h-96 overflow-y-auto p-2">
            <div v-if="searchQuery" class="p-2 text-xs text-gray-500">
              Searching for "{{ searchQuery }}"...
            </div>
            <div v-else class="p-4 text-center text-gray-500">
              <i class="ph ph-magnifying-glass-plus text-4xl mb-2"></i>
              <p>Start typing to search</p>
              <p class="text-xs mt-2">Press <kbd class="px-1.5 py-0.5 bg-gray-100 rounded border border-gray-300 text-gray-500">/</kbd> to search anywhere</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Page content -->
      <div class="flex-1 p-4 md:p-6 overflow-auto relative">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>

      <!-- Footer -->
      <footer class="py-3 px-4 md:px-6 text-xs text-gray-500 bg-white border-t border-slate-300">
        <div class="flex justify-between items-center">
          <div>© {{ currentYear }} Finexia - All rights reserved</div>
          <div>Version 1.0.0</div>
        </div>
      </footer>
    </main>
  </div>
</template>
<script>
import { ref, onMounted, onUnmounted, computed, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useTenantStore } from '@/stores/tenant'

export default {
  name: 'DefaultLayout',
  setup() {
    const router = useRouter()
    const authStore = useAuthStore()
    const tenantStore = useTenantStore()

    // State
    const collapsed = ref(localStorage.getItem('sidebarCollapsed') === 'true')
    const marketOpenTime = '09:15'
    const marketCloseTime = '15:30'
    const currentTime = ref(new Date())
    const notificationCount = ref(3)
    const userMenuOpen = ref(false)
    const notificationsOpen = ref(false)
    const showSearch = ref(false)
    const searchQuery = ref('')
    const searchInput = ref(null)
    const notifications = ref([])
    const isMobile = ref(window.innerWidth < 768)

    // Watch sidebar state changes
    watch(collapsed, (newValue) => {
      localStorage.setItem('sidebarCollapsed', newValue)
    })

    // Responsive classes
    const sidebarClass = computed(() => {
      return isMobile.value ? 'transform transition-transform duration-300 ease-in-out' : ''
    })

    const contentClass = computed(() => {
      return isMobile.value ? 'pl-0' : ''
    })

    // Navigation items
    const navItems = [
      { title: 'Dashboard', icon: 'ph-chart-line', pathName: 'dashboard' },
      { title: 'Pipeline', icon: 'ph-flow-arrow', pathName: 'pipeline' },
      { title: 'Symbols', icon: 'ph-trend-up', pathName: 'symbols' },
      { title: 'Predictions', icon: 'ph-chart-bar', pathName: 'predictions' },
      { title: 'Models', icon: 'ph-brain', pathName: 'models' },
      { title: 'Analytics', icon: 'ph-chart-pie-slice', pathName: 'analytics' },
      { title: 'Settings', icon: 'ph-gear', pathName: 'settings' }
    ]

    // Computed properties
    const userInitials = computed(() => {
      const username = authStore.username || ''
      return username.substring(0, 2).toUpperCase()
    })

    const userEmail = computed(() => {
      return authStore.user?.email || 'user@example.com'
    })

    const marketStatus = computed(() => {
      const now = currentTime.value
      const open = new Date(now)
      const close = new Date(now)

      const [openH, openM] = marketOpenTime.split(':')
      const [closeH, closeM] = marketCloseTime.split(':')

      open.setHours(parseInt(openH), parseInt(openM), 0)
      close.setHours(parseInt(closeH), parseInt(closeM), 0)

      return now >= open && now <= close ? 'LIVE' : 'CLOSED'
    })

    const formattedTime = computed(() => {
      return currentTime.value.toLocaleTimeString('en-IN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })
    })

    const currentYear = computed(() => {
      return new Date().getFullYear()
    })

    const pageTitle = computed(() => {
      return router.currentRoute.value.meta?.title || 'Dashboard'
    })

    const breadcrumbs = computed(() => {
      const crumbs = []
      const route = router.currentRoute.value

      // Always include home
      crumbs.push({ title: 'Home', name: 'dashboard' })

      // Add current page
      if (route.name && route.name !== 'dashboard') {
        // Find the nav item with the matching pathName
        const navItem = navItems.find(item => item.pathName === route.name)

        if (navItem) {
          crumbs.push({ title: navItem.title, name: navItem.pathName })
        }

        // If we have a route param like symbol, add it as the final crumb
        if (route.params.symbol) {
          crumbs.push({ title: route.params.symbol, name: null })
        }
      }

      return crumbs
    })

    // Methods
    const toggleSidebar = () => {
      collapsed.value = !collapsed.value
    }

    const toggleUserMenu = () => {
      userMenuOpen.value = !userMenuOpen.value
      if (userMenuOpen.value) {
        notificationsOpen.value = false
      }
    }

    const toggleNotifications = () => {
      notificationsOpen.value = !notificationsOpen.value
      if (notificationsOpen.value) {
        userMenuOpen.value = false
      }
    }

    const openGlobalSearch = () => {
      showSearch.value = true
      nextTick(() => {
        searchInput.value?.focus()
      })
    }

    const switchTenant = async (tenantSlug) => {
      try {
        await tenantStore.switchTenant(tenantSlug)
      } catch (error) {
        console.error('Failed to switch tenant:', error)
      }
    }

    const logout = () => {
      authStore.logout()
      router.push('/login')
    }

    const navigateTo = (routeName) => {
      if (routeName) {
        router.push({ name: routeName })

        // Close sidebar on mobile after navigation
        if (isMobile.value) {
          collapsed.value = true
        }
      }
    }

    const handleClickOutside = (event) => {
      // Close menus when clicking outside
      if (userMenuOpen.value && !event.target.closest('.user-menu')) {
        userMenuOpen.value = false
      }

      if (notificationsOpen.value && !event.target.closest('.notifications-menu')) {
        notificationsOpen.value = false
      }
    }

    // Handle window resize for responsive layout
    const handleResize = () => {
      isMobile.value = window.innerWidth < 768
      if (isMobile.value && !collapsed.value) {
        collapsed.value = true
      }
    }

    // Keyboard shortcuts
    const handleKeydown = (event) => {
      // Press / to open search
      if (event.key === '/' && !showSearch.value) {
        event.preventDefault()
        openGlobalSearch()
      }

      // Press Escape to close search
      if (event.key === 'Escape' && showSearch.value) {
        showSearch.value = false
      }
    }

    // Lifecycle hooks
    onMounted(() => {
      // Set up clock
      currentTime.value = new Date()
      const clockInterval = setInterval(() => {
        currentTime.value = new Date()
      }, 1000)

      // Fetch tenants if user is authenticated
      if (authStore.isAuthenticated) {
        tenantStore.fetchTenants()
        tenantStore.fetchCurrentTenant()
      }

      // Add event listeners
      document.addEventListener('click', handleClickOutside)
      document.addEventListener('keydown', handleKeydown)
      window.addEventListener('resize', handleResize)

      // Initial check for mobile
      handleResize()

      // Cleanup
      onUnmounted(() => {
        clearInterval(clockInterval)
        document.removeEventListener('click', handleClickOutside)
        document.removeEventListener('keydown', handleKeydown)
        window.removeEventListener('resize', handleResize)
      })
    })

    return {
      // State
      collapsed,
      currentTime,
      notificationCount,
      navItems,
      userMenuOpen,
      notificationsOpen,
      showSearch,
      searchQuery,
      searchInput,
      notifications,
      isMobile,
      sidebarClass,
      contentClass,

      // Store access
      authStore,
      tenantStore,

      // Computed
      userInitials,
      userEmail,
      marketStatus,
      formattedTime,
      currentYear,
      pageTitle,
      breadcrumbs,

      // Methods
      toggleSidebar,
      toggleUserMenu,
      toggleNotifications,
      openGlobalSearch,
      switchTenant,
      logout,
      navigateTo
    }
  }
}
</script>

<style lang="postcss" scoped>
/* Page transition animations */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Fade-in animation for dropdowns */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fade-in {
  animation: fadeIn 0.2s ease forwards;
}

/* Navigation hover styles */
.nav-item .nav-link:hover {
  @apply bg-gray-50;
}

.nav-item:hover .ph {
  @apply text-gray-700;
}

.nav-item:hover .nav-link span {
  @apply text-gray-800;
}

/* Pulse animation for market status indicator */
@keyframes pulse {
  0% {
    transform: scale(0.95);
    opacity: 0.7;
  }

  50% {
    transform: scale(1);
    opacity: 1;
  }

  100% {
    transform: scale(0.95);
    opacity: 0.7;
  }
}

.animate-pulse {
  animation: pulse 2s infinite ease-in-out;
}

/* Responsive utility classes */
@media (max-width: 639px) {
  .xs\:inline {
    display: inline;
  }
}

@media (min-width: 640px) {
  .sm\:inline {
    display: inline;
  }
}
</style>