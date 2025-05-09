<!-- src/layouts/MainLayout.vue -->
<template>
  <div class="app-container">
    <!-- Sidebar -->
    <Sidebar :is-open="sidebarOpen" @close="closeSidebar" />

    <!-- Main content -->
    <div class="main-content">
      <!-- Top navigation -->
      <Navbar @toggle-sidebar="toggleSidebar" />

      <!-- Page content -->
      <main class="page-content">
        <!-- Page header -->
        <PageHeader v-if="pageTitle" :title="pageTitle" :subtitle="subtitle" />

        <!-- Main content -->
        <div class="content-wrapper">
          <slot></slot>
        </div>
      </main>
    </div>
  </div>
</template>

<script>
import Sidebar from '@/components/layout/Sidebar.vue';
import Navbar from '@/components/layout/Navbar.vue';
import PageHeader from '@/components/layout/PageHeader.vue';

export default {
  name: 'MainLayout',

  components: {
    Sidebar,
    Navbar,
    PageHeader
  },

  props: {
    title: {
      type: String,
      default: ''
    },
    subtitle: {
      type: String,
      default: ''
    }
  },

  data: function () {
    return {
      sidebarOpen: false
    };
  },

  computed: {
    pageTitle: function () {
      return this.title || this.$route.meta.title || '';
    }
  },

  methods: {
    toggleSidebar: function () {
      this.sidebarOpen = !this.sidebarOpen;
    },

    closeSidebar: function () {
      this.sidebarOpen = false;
    }
  }
}
</script>

<style lang="postcss" scoped>
.app-container {
  @apply h-screen flex overflow-hidden;
}

.main-content {
  @apply flex-1 flex flex-col overflow-hidden;
}

.page-content {
  @apply flex-1 overflow-y-auto p-4 sm:p-6;
}

.content-wrapper {
  @apply mt-4;
}
</style>