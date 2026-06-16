<template>
  <div class="metrics-chart">
    <div ref="chartContainer" class="chart-container"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { useExperimentStore } from '@/stores/experiment'

const store = useExperimentStore()
const chartContainer = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

function initChart() {
  if (!chartContainer.value) return

  chart = echarts.init(chartContainer.value)

  const option = {
    title: {
      text: '网络鲁棒性指标变化',
      left: 'center',
      textStyle: { fontSize: 16, fontWeight: 'normal' }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    legend: {
      data: ['链路数量', '最大连通分量', '鲁棒性指数', '聚类系数'],
      top: 30,
      left: 'center'
    },
    grid: {
      left: '10%',
      right: '10%',
      bottom: '15%',
      top: '80px'
    },
    xAxis: {
      type: 'category',
      data: [],
      name: '博弈轮次',
      nameLocation: 'middle',
      nameGap: 30
    },
    yAxis: [
      {
        type: 'value',
        name: '链路数量',
        position: 'left',
        min: 0
      },
      {
        type: 'value',
        name: '比例/指数',
        position: 'right',
        min: 0,
        max: 1
      }
    ],
    series: [
      {
        name: '链路数量',
        type: 'line',
        data: [],
        smooth: true,
        yAxisIndex: 0,
        itemStyle: { color: '#1890ff' }
      },
      {
        name: '最大连通分量',
        type: 'line',
        data: [],
        smooth: true,
        yAxisIndex: 1,
        itemStyle: { color: '#52c41a' }
      },
      {
        name: '鲁棒性指数',
        type: 'line',
        data: [],
        smooth: true,
        yAxisIndex: 1,
        itemStyle: { color: '#faad14' }
      },
      {
        name: '聚类系数',
        type: 'line',
        data: [],
        smooth: true,
        yAxisIndex: 1,
        itemStyle: { color: '#722ed1' }
      }
    ],
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100
      }
    ]
  }

  chart.setOption(option)
}

function updateChart() {
  if (!chart) return

  const history = store.metricsHistory

  chart.setOption({
    xAxis: {
      data: history.rounds
    },
    series: [
      {
        name: '链路数量',
        data: history.num_edges
      },
      {
        name: '最大连通分量',
        data: history.largest_cc_ratio
      },
      {
        name: '鲁棒性指数',
        data: history.robustness_index
      },
      {
        name: '聚类系数',
        data: history.clustering_coeff
      }
    ]
  })
}

onMounted(() => {
  initChart()

  window.addEventListener('resize', () => {
    chart?.resize()
  })
})

watch(
  () => store.metricsHistory,
  () => {
    updateChart()
  },
  { deep: true }
)

onUnmounted(() => {
  if (chart) {
    chart.dispose()
    chart = null
  }
})
</script>

<style scoped>
.metrics-chart {
  width: 100%;
}

.chart-container {
  width: 100%;
  height: 300px;
}
</style>
