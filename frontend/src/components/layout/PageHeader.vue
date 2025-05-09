<!-- src/components/layout/PageHeader.vue -->
<template>
  <div class="page-header">
    <!-- Title section -->
    <div class="header-content">
      <div class="header-titles">
        <h1 class="header-title">{{ title }}</h1>
        <p v-if="subtitle" class="header-subtitle">{{ subtitle }}</p>
      </div>

      <!-- Actions -->
      <div class="header-actions" v-if="$slots.actions">
        <slot name="actions"></slot>
      </div>
      <div class="header-actions" v-else-if="defaultActions">
        <button v-if="refreshAction" @click="$emit('refresh')" class="btn btn-secondary btn-sm">
          <i class="ph ph-arrow-clockwise mr-1"></i> Refresh
        </button>
        <button v-if="addAction" @click="$emit('add')" class="btn btn-primary btn-sm">
          <i class="ph ph-plus mr-1"></i> {{ addLabel }}
        </button>
      </div>
    </div>

    <!-- Tabs - Optional -->
    <div class="header-tabs" v-if="tabs && tabs.length">
      <nav class="tabs-nav">
        <router-link v-for="tab in tabs" :key="tab.route" :to="tab.route" class="tab-item" :class="{ 'active': isActiveTab(tab.route) }">
          <i v-if="tab.icon" :class="`ph ph-${tab.icon} mr-1.5`"></i>
          {{ tab.label }}
          <span v-if="tab.count" class="tab-badge">{{ formatCount(tab.count) }}</span>
        </router-link>
      </nav>
    </div>

    <!-- Filters - Optional -->
    <div class="header-filters" v-if="$slots.filters">
      <slot name="filters"></slot>
    </div>
  </div>
</template>

<script>
export default {
  name: 'PageHeader',

  props: {
    title: {
      type: String,
      required: true
    },
    subtitle: {
      type: String,
      default: ''
    },
    defaultActions: {
      type: Boolean,
      default: true
    },
    refreshAction: {
      type: Boolean,
      default: true
    },
    addAction: {
      type: Boolean,
      default: false
    },
    addLabel: {
      type: String,
      default: 'Add New'
    },
    tabs: {
      type: Array,
      default: function () { return []; }
    }
  },

  emits: ['refresh', 'add'],

  methods: {
    isActiveTab: function (route) {
      return this.$route.path === route || this.$route.fullPath === route;
    },

    formatCount: function (count) {
      if (count > 999) {
        return (count / 1000).toFixed(1) + 'k';
      }
      return count;
    }
  }
};
</script>

<style lang="postcss" scoped>
.page-header {
  @apply mb-6 space-y-4;
}

.header-content {
  @apply flex flex-col sm:flex-row sm:items-center justify-between gap-4;
}

.header-titles {
  @apply min-w-0;
}

.header-title {
  @apply text-2xl font-bold text-gray-900 m-0 truncate;
}

.header-subtitle {
  @apply text-sm text-gray-500 mt-1 mb-0;
}

.header-actions {
  @apply flex flex-wrap items-center gap-2 sm:justify-end;
}

.header-tabs {
  @apply border-b border-gray-200 mt-6;
}

.tabs-nav {
  @apply -mb-px flex space-x-6 overflow-x-auto scrollbar-none;
}

.tab-item {
  @apply py-3 px-1 inline-flex items-center border-b-2 border-transparent text-sm font-medium text-gray-500 whitespace-nowrap hover:text-gray-700 hover:border-gray-300 transition-colors duration-200;
}

.tab-item.active {
  @apply border-indigo-600 text-indigo-600;
}

.tab-badge {
  @apply ml-2 px-2 py-0.5 rounded-full text-xs bg-gray-100 text-gray-600;
}

.header-filters {
  @apply flex flex-wrap items-center gap-3 mt-4 bg-gray-50 p-3 rounded-lg;
}
</style>