<template>
  <div class="dashboard">
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      <!-- <StatCard label="Total Predictions" :value="systemStats.totalPredictions || 0" icon="mdi-chart-timeline-variant" icon-color="primary" icon-background="bg-primary-light" :change-text="`${Math.abs(systemStats.predictionChange)}% from last week`" :change-type="systemStats.predictionChange >= 0 ? 'positive' : 'negative'" />

      <StatCard label="Prediction Accuracy" :value="`${(predictionStats.accuracy * 100).toFixed(1)}%`" icon="mdi-check-circle" icon-color="success" icon-background="bg-success-light" :change-text="`${Math.abs(predictionStats.accuracyChange)}% from last week`" :change-type="predictionStats.accuracyChange >= 0 ? 'positive' : 'negative'" />

      <StatCard label="Today's Predictions" :value="systemStats.todayPredictions || 0" icon="mdi-calendar-check" icon-color="info" icon-background="bg-info-light" :change-text="`Updated ${lastUpdateTime}`" change-type="neutral" />

      <StatCard label="Active Models" :value="systemStats.activeModels || 0" icon="mdi-brain" icon-color="warning" icon-background="bg-warning-light" :change-text="`${systemStats.newModels || 0} new this week`" change-type="positive" /> -->
    </div>
  </div>
</template>
<script>
import StatCard from '@/components/dashboard/statCardComponent.vue'
export default {
  components: {
    StatCard
  },
  data() {
    return {

    }
  }
}
</script>
<style lang="postcss" scoped>
.dashboard {
  @apply max-w-full;
}
</style>