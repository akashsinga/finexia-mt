<!-- src/views/symbols/SymbolsList.vue -->
<template>
  <div class="symbols-list">
    <div class="mb-6 flex justify-between items-center">
      <h1 class="text-xl font-semibold text-gray-800">Symbols</h1>

      <div class="flex items-center space-x-3">
        <!-- Search -->
        <div class="form-input-icon-wrapper w-64">
          <i class="ph ph-magnifying-glass input-icon"></i>
          <input type="text" v-model="searchQuery" @input="debounceSearch" placeholder="Search symbols..." class="form-input" />
          <i v-if="searching" class="ph ph-spinner animate-spin input-icon-right"></i>
          <i v-else-if="searchQuery" @click="clearSearch" class="ph ph-x input-icon-right cursor-pointer"></i>
        </div>

        <!-- Filters -->
        <div class="flex items-center space-x-2">
          <label class="flex items-center text-sm text-gray-600">
            <input type="checkbox" v-model="activeOnly" class="form-checkbox mr-1" />
            Active only
          </label>

          <label class="flex items-center text-sm text-gray-600">
            <input type="checkbox" v-model="foEligible" class="form-checkbox mr-1" />
            F&O eligible
          </label>
        </div>

        <!-- Refresh button -->
        <button @click="fetchSymbols" class="p-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100 transition-colors" :class="{ 'animate-spin': loading }">
          <i class="ph ph-arrows-clockwise"></i>
        </button>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="flex justify-center py-10">
      <div class="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-blue-600"></div>
    </div>

    <!-- Empty state -->
    <div v-else-if="symbols.length === 0" class="bg-white rounded-lg p-10 text-center">
      <i class="ph ph-chart-line text-6xl text-gray-400"></i>
      <h3 class="text-lg font-medium text-gray-700 mt-4">No symbols found</h3>
      <p class="text-gray-500 mt-2">Try changing your filters or search query</p>
    </div>

    <!-- Symbols table -->
    <div v-else class="bg-white rounded-lg shadow overflow-hidden">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Symbol
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Name
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Exchange
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Type
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Status
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-for="symbol in symbols" :key="symbol.id" class="hover:bg-gray-50">
            <td class="px-6 py-4 whitespace-nowrap">
              <div class="font-medium text-gray-900">{{ symbol.trading_symbol }}</div>
            </td>
            <td class="px-6 py-4">
              <div class="text-sm text-gray-900">{{ symbol.name }}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <div class="text-sm text-gray-900">{{ symbol.exchange }}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <div class="text-sm text-gray-900">{{ symbol.instrument_type }}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full" :class="symbol.active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'">
                {{ symbol.active ? 'Active' : 'Inactive' }}
              </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              <div class="flex items-center space-x-2">
                <button @click="viewSymbol(symbol.id)" class="text-blue-600 hover:text-blue-800">
                  <i class="ph ph-eye"></i>
                </button>
                <button @click="addToWatchlist(symbol.id)" class="text-green-600 hover:text-green-800">
                  <i class="ph ph-plus"></i>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Pagination -->
      <div class="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6">
        <div class="flex-1 flex justify-between sm:hidden">
          <button @click="prevPage" :disabled="currentPage === 1" class="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50" :class="{ 'opacity-50 cursor-not-allowed': currentPage === 1 }">
            Previous
          </button>
          <button @click="nextPage" :disabled="symbols.length < limit" class="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50" :class="{ 'opacity-50 cursor-not-allowed': symbols.length < limit }">
            Next
          </button>
        </div>
        <div class="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
          <div>
            <p class="text-sm text-gray-700">
              Showing <span class="font-medium">{{ symbols.length }}</span> results
            </p>
          </div>
          <div>
            <nav class="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
              <button @click="prevPage" :disabled="currentPage === 1" class="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50" :class="{ 'opacity-50 cursor-not-allowed': currentPage === 1 }">
                <i class="ph ph-caret-left"></i>
              </button>
              <span class="relative inline-flex items-center px-4 py-2 border border-gray-300 bg-white text-sm font-medium">
                Page {{ currentPage }}
              </span>
              <button @click="nextPage" :disabled="symbols.length < limit" class="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50" :class="{ 'opacity-50 cursor-not-allowed': symbols.length < limit }">
                <i class="ph ph-caret-right"></i>
              </button>
            </nav>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/plugins'

export default {
  name: 'SymbolsList',
  setup() {
    const router = useRouter()

    // Data
    const symbols = ref([])
    const loading = ref(false)
    const searchQuery = ref('')
    const searching = ref(false)
    const activeOnly = ref(true)
    const foEligible = ref(false)
    const currentPage = ref(1)
    const limit = 20
    const searchTimeoutId = ref(null)

    // Methods
    const fetchSymbols = async () => {
      loading.value = true

      try {
        const response = await api.get('/symbols', {
          params: {
            active_only: activeOnly.value,
            fo_eligible: foEligible.value,
            skip: (currentPage.value - 1) * limit,
            limit
          }
        })

        symbols.value = response.data.symbols
      } catch (error) {
        console.error('Error fetching symbols:', error)
      } finally {
        loading.value = false
      }
    }

    const searchSymbols = async () => {
      if (!searchQuery.value.trim()) {
        return fetchSymbols()
      }

      searching.value = true

      try {
        const response = await api.get('/symbols/search', {
          params: {
            query: searchQuery.value,
            active_only: activeOnly.value
          }
        })

        symbols.value = response.data.symbols
      } catch (error) {
        console.error('Error searching symbols:', error)
      } finally {
        searching.value = false
      }
    }

    const debounceSearch = () => {
      if (searchTimeoutId.value) {
        clearTimeout(searchTimeoutId.value)
      }

      searchTimeoutId.value = setTimeout(() => {
        searchSymbols()
      }, 300)
    }

    const clearSearch = () => {
      searchQuery.value = ''
      fetchSymbols()
    }

    const viewSymbol = (symbolId) => {
      router.push({ name: 'symbol-detail', params: { id: symbolId } })
    }

    const addToWatchlist = async (symbolId) => {
      try {
        await api.post(`/watchlist/${symbolId}`)
        // Show success notification
      } catch (error) {
        console.error('Error adding to watchlist:', error)
        // Show error notification
      }
    }

    const prevPage = () => {
      if (currentPage.value > 1) {
        currentPage.value--
        fetchSymbols()
      }
    }

    const nextPage = () => {
      if (symbols.value.length === limit) {
        currentPage.value++
        fetchSymbols()
      }
    }

    // Lifecycle hooks
    onMounted(() => {
      fetchSymbols()
    })

    return {
      symbols,
      loading,
      searchQuery,
      searching,
      activeOnly,
      foEligible,
      currentPage,
      limit,
      fetchSymbols,
      searchSymbols,
      debounceSearch,
      clearSearch,
      viewSymbol,
      addToWatchlist,
      prevPage,
      nextPage
    }
  }
}
</script>