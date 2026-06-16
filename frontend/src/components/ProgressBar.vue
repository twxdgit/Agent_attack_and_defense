<template>
  <div class="progress-bar-container">
    <div class="progress-info">
      <span class="round-label">当前轮次</span>
      <span class="round-value">{{ store.currentRound }} / {{ store.maxRounds }}</span>
    </div>
    <div class="progress-track">
      <div class="progress-fill" :style="{ width: `${store.progress}%` }"></div>
    </div>
    <div class="winner-banner" v-if="store.winner">
      <span :class="winnerClass">🏆 {{ winnerText }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useExperimentStore } from '@/stores/experiment'

const store = useExperimentStore()



const winnerClass = computed(() => {
  if (!store.winner) return ''
  return store.winner === 'attacker' ? 'winner-attacker' : 'winner-defender'
})
</script>

<style scoped>
.progress-bar-container {
  background: var(--card-bg);
  border-radius: 8px;
  padding: 16px;
  box-shadow: var(--shadow);
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.round-label {
  font-size: 14px;
  color: var(--text-secondary);
}

.round-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--primary-color);
}

.progress-track {
  height: 12px;
  background: #f0f0f0;
  border-radius: 6px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-color), #40a9ff);
  border-radius: 6px;
  transition: width 0.5s ease;
}

.winner-banner {
  margin-top: 12px;
  text-align: center;
  padding: 8px;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
}

.winner-attacker {
  background: #fff1f0;
  color: var(--error-color);
}

.winner-defender {
  background: #f6ffed;
  color: var(--success-color);
}
</style>
