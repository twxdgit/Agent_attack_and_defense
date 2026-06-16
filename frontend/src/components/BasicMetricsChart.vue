<template>
  <div class="basic-metrics-chart">
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
      text: '基本指标变化',
      left: 'center',
      textStyle: { fontSize: 16, fontWeight: 'normal' }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    legend: {
      data: ['平均度数', '平均最短路径', '网络直径', '度中心化'],
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
        name: '度数/路径',
        position: 'left',
        min: 0
      },
      {
        type: 'value',
        name: '比例',
        position: 'right',
        min: 0,
        max: 1
      }
    ],
    series: [
      {
        name: '平均度数',
        type: 'line',
        data: [],
        smooth: true,
        yAxisIndex: 0,
        itemStyle: { color: '#13c2c2' }
      },
      {
        name: '平均最短路径',
        type: 'line',
        data: [],
        smooth: true,
        yAxisIndex: 0,
        itemStyle: { color: '#fa541c' }
      },
      {
        name: '网络直径',
        type: 'line',
        data: [],
        smooth: true,
        yAxisIndex: 0,
        itemStyle: { color: '#eb2f96' }
      },
      {
        name: '度中心化',
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

  // 处理 avg_path_length 和 diameter 的无穷大值
  const avgPathData = (history.avg_path_length || []).map(v =>
    v === Infinity || v === null || v === undefined ? null : v
  )
  const diameterData = (history.diameter || []).map(v =>
    v === Infinity || v === null || v === undefined ? null : v
  )

  chart.setOption({
    xAxis: {
      data: history.rounds
    },
    series: [
      {
        name: '平均度数',
        data: history.avg_degree || []
      },
      {
        name: '平均最短路径',
        data: avgPathData
      },
      {
        name: '网络直径',
        data: diameterData
      },
      {
        name: '度中心化',
        data: history.degree_centralization || []
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
.basic-metrics-chart {
  width: 100%;
}

.chart-container {
  width: 100%;
  height: 300px;
}
</style>
