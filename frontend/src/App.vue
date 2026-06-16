<template>
  <div class="app-container">
    <!-- 头部 -->
    <header class="app-header">
      <h1>🛡️ 智能体网络攻防博弈平台</h1>
      <div class="header-actions">
        <span class="status-indicator" :class="statusClass">
          {{ statusText }}
        </span>
      </div>
    </header>

    <!-- 主内容 -->
    <main class="app-main">
      <!-- 左侧：参数配置 -->
      <ConfigPanel class="config-section" />

      <!-- 中央：网络拓扑 -->
      <div class="center-section">
        <NetworkGraph class="network-section" />
        <ProgressBar class="progress-section" />
      </div>

      <!-- 右侧：智能体状态 -->
      <AgentStatus class="status-section" />
    </main>

    <!-- 底部：指标图表 -->
    <div class="bottom-section">
      <div class="metrics-row">
        <MetricsChart class="metrics-section" />
        <BasicMetricsChart class="metrics-section" />
      </div>
    </div>

    <!-- 日志面板 -->
    <GameLog class="log-section" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useExperimentStore } from '@/stores/experiment'
import ConfigPanel from '@/components/ConfigPanel.vue'
import NetworkGraph from '@/components/NetworkGraph.vue'
import ProgressBar from '@/components/ProgressBar.vue'
import AgentStatus from '@/components/AgentStatus.vue'
import MetricsChart from '@/components/MetricsChart.vue'
import BasicMetricsChart from '@/components/BasicMetricsChart.vue'
import GameLog from '@/components/GameLog.vue'

const store = useExperimentStore()

const statusText = computed(() => {
  const statusMap = {
    idle: '等待开始',
    running: '运行中',
    paused: '已暂停',
    finished: '已完成'
  }
  return statusMap[store.status]
})

const statusClass = computed(() => {
  return `status-${store.status}`
})
</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.app-header {
  background: var(--card-bg);
  padding: 16px 24px;
  box-shadow: var(--shadow);
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  top: 0;
  z-index: 100;
}

.app-header h1 {
  font-size: 20px;
  font-weight: 600;
}

.app-main {
  flex: 1;
  padding: 16px;
  display: grid;
  grid-template-columns: 300px 1fr 300px;
  gap: 16px;
  max-height: calc(100vh - 180px);
}

.center-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.config-section,
.status-section {
  max-height: calc(100vh - 200px);
  overflow-y: auto;
}

.network-section {
  flex: 0 0 600px;
  min-height: unset;
  max-height: 600px;
}

.progress-section {
  flex-shrink: 0;
}

.bottom-section {
  padding: 0 16px 16px;
}

.metrics-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.metrics-section {
  background: var(--card-bg);
  border-radius: 8px;
  box-shadow: var(--shadow);
  padding: 16px;
}

.log-section {
  margin: 0 16px 16px;
}

@media (max-width: 1200px) {
  .app-main {
    grid-template-columns: 1fr;
    max-height: none;
  }

  .config-section,
  .status-section {
    max-height: none;
  }
}
</style>
