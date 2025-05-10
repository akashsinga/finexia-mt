<template>
  <div class="dashboard">
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      <StatCard label="Total Predictions" :value="stats.totalPredictions" icon="ph-chart-line" icon-background="bg-primary-light" :change-text="`${Math.abs(stats.predictionChange)}% from last week`" :change-type="stats.predictionChange >= 0 ? 'positive' : 'negative'" />

      <StatCard label="Prediction Accuracy" :value="`${(stats.accuracy * 100).toFixed(1)}%`" icon="ph-check-circle" icon-background="bg-success-light" :change-text="`${Math.abs(stats.accuracyChange)}% from last week`" :change-type="stats.accuracyChange >= 0 ? 'positive' : 'negative'" />

      <StatCard label="Today's Predictions" :value="stats.todayPredictions" icon="ph-calendar-check" icon-background="bg-info-light" :change-text="`Updated ${formatTime(stats.lastUpdate)}`" change-type="neutral" />

      <StatCard label="Active Models" :value="stats.activeModels" icon="ph-brain" icon-background="bg-warning-light" :change-text="`${stats.newModels} new this week`" change-type="positive" />
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
      <div class="bg-white p-4 rounded-lg ring-1 ring-slate-300">
        <h2 class="text-lg font-semibold mb-4">Recent Predictions</h2>
        <div v-if="loading" class="flex justify-center py-8">
          <div class="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
        </div>
        <div v-else-if="predictions.length === 0" class="text-center py-8 text-gray-500">
          No recent predictions available
        </div>
        <div v-else class="overflow-x-auto">
          <!-- Predictions table -->
          <table class="min-w-full">
            <thead>
              <tr>
                <th class="text-left px-4 py-2">Symbol</th>
                <th class="text-left px-4 py-2">Date</th>
                <th class="text-left px-4 py-2">Direction</th>
                <th class="text-left px-4 py-2">Confidence</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="pred in predictions" :key="pred.id" class="border-t">
                <td class="px-4 py-2">{{ pred.symbol_name }}</td>
                <td class="px-4 py-2">{{ formatDate(pred.date) }}</td>
                <td class="px-4 py-2">
                  <span :class="getDirectionClass(pred.direction_prediction)">
                    {{ pred.direction_prediction }}
                  </span>
                </td>
                <td class="px-4 py-2">{{ (pred.direction_confidence * 100).toFixed(1) }}%</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="bg-white p-4 rounded-lg ring-1 ring-slate-300">
        <h2 class="text-lg font-semibold mb-4">Prediction Accuracy</h2>
        <div v-if="loading" class="flex justify-center py-8">
          <div class="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
        </div>
        <div v-else-if="!predictionTrends || predictionTrends.length === 0" class="text-center py-8 text-gray-500">
          No trend data available
        </div>
        <div v-else class="h-64">
          <PredictionChart :trends="predictionTrends" />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'
import { format } from 'date-fns'
import StatCard from '@/components/dashboard/statCardComponent.vue'
import PredictionChart from '@/components/charts/PredictionChart.vue'
import { useDashboardStore } from '@/stores/dashboard'

export default {
  components: {
    StatCard,
    PredictionChart
  },
  setup() {
    const dashboardStore = useDashboardStore()
    const stats = ref({
      totalPredictions: 0,
      predictionChange: 0,
      accuracy: 0,
      accuracyChange: 0.5,
      todayPredictions: 0,
      lastUpdate: new Date(),
      activeModels: 0,
      newModels: 0
    })

    const loading = ref(true)

    const fetchDashboardData = async () => {
      loading.value = true
      try {
        await Promise.all([
          dashboardStore.fetchSystemStatus(),
          dashboardStore.fetchRecentPredictions(),
          dashboardStore.fetchDashboardSummary()
        ])

        // Update local stats from store
        stats.value.totalPredictions = dashboardStore.totalPredictions
        stats.value.todayPredictions = dashboardStore.todayPredictions
        stats.value.accuracy = dashboardStore.verificationRate
        stats.value.lastUpdate = dashboardStore.lastUpdated || new Date()

        // Connect to WebSocket for real-time updates
        dashboardStore.connectToWebsocket()
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error)
      } finally {
        loading.value = false
      }
    }

    const formatDate = (dateString) => {
      return format(new Date(dateString), 'MMM d, yyyy')
    }

    const formatTime = (date) => {
      return format(date, 'h:mm a')
    }

    const getDirectionClass = (direction) => {
      if (direction === 'UP') return 'text-green-600 font-medium'
      if (direction === 'DOWN') return 'text-red-600 font-medium'
      return 'text-gray-600'
    }

    onMounted(() => {
      fetchDashboardData()
    })

    onUnmounted(() => {
      // Disconnect WebSocket when component is destroyed
      dashboardStore.disconnectWebsocket()
    })

    return {
      stats,
      predictions: dashboardStore.predictions,
      predictionTrends: dashboardStore.predictionTrends,
      loading,
      formatDate,
      formatTime,
      getDirectionClass
    }
  }
}
</script>

<style lang="postcss" scoped>
.dashboard {
  @apply max-w-full;
}
</style>