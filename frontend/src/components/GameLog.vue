<template>
  <div class="card game-log">
    <div class="log-header">
      <h2 class="card-title">博弈日志</h2>
      <button class="btn btn-default btn-sm" @click="clearLogs">清空</button>
    </div>
    <div ref="logContainer" class="log-container">
      <div v-if="store.logs.length === 0" class="log-empty">
        暂无日志，等待实验开始...
      </div>
      <div
        v-for="(log, index) in store.logs"
        :key="index"
        class="log-entry"
        :class="log.type"
      >
        <span class="log-time">{{ log.timestamp }}</span>
        <span class="log-round" v-if="log.round > 0">第{{ log.round }}轮</span>
        <span class="log-message">{{ log.message }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useExperimentStore } from '@/stores/experiment'

const store = useExperimentStore()
const logContainer = ref<HTMLElement>()

function clearLogs() {
  store.logs = []
}

function scrollToBottom() {
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  })
}

watch(
  () => store.logs.length,
  () => {
    scrollToBottom()
  }
)
</script>

<style scoped>
.game-log {
  max-height: 500px;
  display: flex;
  flex-direction: column;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.log-header .card-title {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.btn-sm {
  padding: 4px 12px;
  font-size: 12px;
}

.log-container {
  flex: 1;
  overflow-y: auto;
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 4px;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 12px;
  max-height: 400px;
}

.log-empty {
  color: #6a6a6a;
  font-style: italic;
}

.log-entry {
  margin-bottom: 4px;
  line-height: 1.6;
  display: flex;
  gap: 8px;
}

.log-entry.attack {
  color: #f48771;
}

.log-entry.defense {
  color: #89d185;
}

.log-entry.system {
  color: #6796e6;
}

.log-entry.info {
  color: #d4d4d4;
}

.log-time {
  color: #6a6a6a;
  flex-shrink: 0;
}

.log-round {
  color: #ce9178;
  font-weight: 600;
  flex-shrink: 0;
}

.log-message {
  word-break: break-word;
}
</style>
