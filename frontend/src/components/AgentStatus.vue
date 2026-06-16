<template>
  <div class="card agent-status">
    <h2 class="card-title">智能体状态</h2>

    <!-- 攻击智能体 -->
    <div class="agent-card">
      <div class="agent-header">
        <span class="agent-icon">🤖</span>
        <span class="agent-name">攻击智能体</span>
      </div>
      <div class="agent-task">
        {{ attackerTask }}
      </div>
      <div class="agent-stats">
        <div class="stat-item">
          <span class="stat-label">已攻击链路</span>
          <span class="stat-value">{{ attackerStats.attacked }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">命中率</span>
          <span class="stat-value">{{ (attackerStats.hit_rate * 100).toFixed(0) }}%</span>
        </div>
      </div>

      <!-- 攻击记录 -->
      <div class="record-section">
        <button class="record-toggle" @click="attackExpanded = !attackExpanded">
          <span class="toggle-icon">{{ attackExpanded ? '▼' : '▶' }}</span>
          攻击记录 ({{ attackLogs.length }})
        </button>
        <div v-if="attackExpanded" class="record-list">
          <div v-if="attackLogs.length === 0" class="record-empty">暂无攻击记录</div>
          <div v-for="(log, i) in attackLogs" :key="i" class="record-item attack">
            <span class="record-round">第{{ log.round }}轮</span>
            <span class="record-msg">{{ log.message }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 防御智能体 -->
    <div class="agent-card">
      <div class="agent-header">
        <span class="agent-icon">🛡️</span>
        <span class="agent-name">防御智能体</span>
      </div>
      <div class="agent-task">
        {{ defenderTask }}
      </div>
      <div class="agent-stats">
        <div class="stat-item">
          <span class="stat-label">已修复链路</span>
          <span class="stat-value">{{ defenderStats.repaired }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">修复率</span>
          <span class="stat-value">{{ (defenderStats.repair_rate * 100).toFixed(0) }}%</span>
        </div>
      </div>

      <!-- 防御记录 -->
      <div class="record-section">
        <button class="record-toggle" @click="defenseExpanded = !defenseExpanded">
          <span class="toggle-icon">{{ defenseExpanded ? '▼' : '▶' }}</span>
          防御记录 ({{ defenseLogs.length }})
        </button>
        <div v-if="defenseExpanded" class="record-list">
          <div v-if="defenseLogs.length === 0" class="record-empty">暂无防御记录</div>
          <div v-for="(log, i) in defenseLogs" :key="i" class="record-item defense">
            <span class="record-round">第{{ log.round }}轮</span>
            <span class="record-msg">{{ log.message }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 任务节点智能体 -->
    <div class="agent-card">
      <div class="agent-header">
        <span class="agent-icon">📋</span>
        <span class="agent-name">任务节点 ({{ taskNodes.total }}个)</span>
      </div>
      <div class="task-nodes-stats">
        <div class="node-stat">
          <span class="node-label">存活节点</span>
          <span class="node-value">{{ taskNodes.active }} / {{ taskNodes.total }}</span>
        </div>
        <div class="node-stat">
          <span class="node-label">正常链路</span>
          <span class="node-value">{{ taskNodes.normal_edges }}</span>
        </div>
      </div>
    </div>

    <!-- 当前指标 -->
    <div class="current-metrics" v-if="currentMetrics">
      <h3 class="metrics-title">当前网络指标</h3>
      <div class="metrics-grid">
        <div class="metric-item">
          <span class="metric-label">链路数</span>
          <span class="metric-value">{{ currentMetrics.num_edges }}</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">连通分量</span>
          <span class="metric-value">{{ (currentMetrics.largest_cc_ratio * 100).toFixed(1) }}%</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">鲁棒性</span>
          <span class="metric-value">{{ (currentMetrics.robustness_index * 100).toFixed(1) }}%</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">聚类系数</span>
          <span class="metric-value">{{ currentMetrics.clustering_coeff.toFixed(3) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useExperimentStore } from '@/stores/experiment'

const store = useExperimentStore()

// 归一化边格式：('0', '1') -> (0,1)，(0, 1) -> (0,1)
function normalizeEdge(raw: string): string {
  const m = raw.match(/\(?['"]?(\d+)['"]?\s*,\s*['"]?(\d+)['"]?\)?/)
  if (!m) return raw
  return `(${m[1]},${m[2]})`
}

// 从日志中收集唯一边集合
function extractUniqueEdges(logs: any[], _field: string, pattern: RegExp): Set<string> {
  const edges = new Set<string>()
  for (const log of logs) {
    const m = log.message.match(pattern)
    if (m && m[1]) {
      const rawEdges = m[1].trim()
      if (rawEdges) {
        const parts = rawEdges.split('),')
        for (let i = 0; i < parts.length; i++) {
          let part = parts[i].trim()
          if (!part.endsWith(')')) part += ')'
          const norm = normalizeEdge(part)
          if (norm !== '()') edges.add(norm)
        }
      }
    }
  }
  return edges
}

const attackerTask = computed(() => store.attackerState?.current_task || '等待开始...')
const attackerStats = computed(() => {
  const atkLogs = store.logs.filter(l => l.type === 'attack')
  const defLogs = store.logs.filter(l => l.type === 'defense')

  const allAttacked = extractUniqueEdges(atkLogs, 'attacked', /攻击链路:\s*\[(.*?)\]/)
  const allRepaired = extractUniqueEdges(defLogs, 'repaired', /修复链路:\s*\[(.*?)\]/)

  let notRepaired = 0
  for (const edge of allAttacked) {
    if (!allRepaired.has(edge)) notRepaired++
  }

  const hitRate = allAttacked.size > 0 ? notRepaired / allAttacked.size : 0
  return { attacked: allAttacked.size, hit_rate: hitRate }
})

const defenderTask = computed(() => store.defenderState?.current_task || '等待开始...')
const defenderStats = computed(() => {
  const atkLogs = store.logs.filter(l => l.type === 'attack')
  const defLogs = store.logs.filter(l => l.type === 'defense')

  const allAttacked = extractUniqueEdges(atkLogs, 'attacked', /攻击链路:\s*\[(.*?)\]/)
  const allRepaired = extractUniqueEdges(defLogs, 'repaired', /修复链路:\s*\[(.*?)\]/)
  const allAdded = extractUniqueEdges(defLogs, 'added', /新增链路:\s*\[(.*?)\]/)

  const repairRate = allAttacked.size > 0 ? allRepaired.size / allAttacked.size : 0
  return { repaired: allRepaired.size, repair_rate: repairRate, added_edges: allAdded.size }
})

const taskNodes = computed(() => store.taskNodesState || { total: 0, active: 0, normal_edges: 0 })

const currentMetrics = computed(() => store.currentMetrics)

const attackLogs = computed(() => store.logs.filter(l => l.type === 'attack'))
const defenseLogs = computed(() => store.logs.filter(l => l.type === 'defense'))

const attackExpanded = ref(true)
const defenseExpanded = ref(true)
</script>

<style scoped>
.agent-status {
  height: fit-content;
}

.agent-card {
  background: #fafafa;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

.agent-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.agent-icon {
  font-size: 20px;
}

.agent-name {
  font-weight: 600;
  font-size: 14px;
}

.agent-task {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 12px;
  padding: 8px;
  background: white;
  border-radius: 4px;
  border: 1px solid var(--border-color);
}

.agent-stats {
  display: flex;
  gap: 16px;
}

.stat-item {
  display: flex;
  flex-direction: column;
}

.stat-label {
  font-size: 11px;
  color: var(--text-secondary);
}

.stat-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--primary-color);
}

/* 记录区 */
.record-section {
  margin-top: 12px;
  border-top: 1px solid var(--border-color);
  padding-top: 10px;
}

.record-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  color: var(--primary-color);
  padding: 4px 0;
  width: 100%;
  text-align: left;
}

.record-toggle:hover {
  color: var(--info-color);
}

.toggle-icon {
  font-size: 10px;
  width: 10px;
  flex-shrink: 0;
}

.record-list {
  margin-top: 8px;
  max-height: 160px;
  overflow-y: auto;
  background: #1e1e1e;
  border-radius: 4px;
  padding: 8px;
}

.record-empty {
  color: #6a6a6a;
  font-size: 12px;
  font-style: italic;
  text-align: center;
  padding: 8px;
}

.record-item {
  display: flex;
  gap: 8px;
  font-size: 12px;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  margin-bottom: 4px;
  line-height: 1.5;
}

.record-item.attack {
  color: #f48771;
}

.record-item.defense {
  color: #89d185;
}

.record-round {
  flex-shrink: 0;
  color: #ce9178;
  font-weight: 600;
}

.record-msg {
  word-break: break-word;
}

.task-nodes-stats {
  display: flex;
  gap: 24px;
}

.node-stat {
  display: flex;
  flex-direction: column;
}

.node-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.node-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--info-color);
}

.current-metrics {
  background: #f0f5ff;
  border-radius: 8px;
  padding: 16px;
}

.metrics-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.metric-item {
  display: flex;
  flex-direction: column;
  background: white;
  padding: 8px;
  border-radius: 4px;
}

.metric-label {
  font-size: 11px;
  color: var(--text-secondary);
}

.metric-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--primary-color);
}
</style>
