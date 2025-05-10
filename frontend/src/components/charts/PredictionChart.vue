<!-- src/components/dashboard/PredictionChart.vue -->
<template>
  <div>
    <Line :data="chartData" :options="chartOptions" />
  </div>
</template>

<script>
import { defineComponent, computed } from 'vue'
import { Line } from 'vue-chartjs'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend)

export default defineComponent({
  name: 'PredictionChart',
  components: {
    Line
  },
  props: {
    trends: {
      type: Array,
      required: true
    }
  },
  setup(props) {
    const chartData = computed(() => ({
      labels: props.trends.map(item => item.date),
      datasets: [
        {
          label: 'Accuracy',
          data: props.trends.map(item => (item.accuracy * 100).toFixed(1)),
          borderColor: '#0ea5e9',
          backgroundColor: 'rgba(14, 165, 233, 0.1)',
          tension: 0.3,
          fill: true
        }
      ]
    }))

    const chartOptions = {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          ticks: {
            callback: function (value) {
              return value + '%'
            }
          }
        }
      },
      plugins: {
        legend: {
          display: false
        }
      }
    }

    return {
      chartData,
      chartOptions
    }
  }
})
</script>