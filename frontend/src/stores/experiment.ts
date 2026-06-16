import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  ExperimentConfig,
  GameState,
  MetricsHistory,
  GameLog,
  ExperimentResult
} from '@/types'
import * as api from '@/api/experiment'

export const useExperimentStore = defineStore('experiment', () => {
  // 状态
  const experimentId = ref<string | null>(null)
  const status = ref<'idle' | 'running' | 'paused' | 'finished'>('idle')
  const config = ref<ExperimentConfig | null>(null)
  const currentRound = ref(0)
  const maxRounds = ref(30)
  const winner = ref<'attacker' | 'defender' | 'draw' | null>(null)

  // 网络状态
  const networkNodes = ref<any[]>([])
  const networkEdges = ref<any[]>([])

  // 智能体状态
  const attackerState = ref<any>(null)
  const defenderState = ref<any>(null)
  const taskNodesState = ref<any>(null)

  // 指标数据
  const metricsHistory = ref<MetricsHistory>({
    rounds: [],
    num_edges: [],
    largest_cc_ratio: [],
    robustness_index: [],
    clustering_coeff: []
  })
  const currentMetrics = ref<any>(null)

  // 日志
  const logs = ref<GameLog[]>([])
  const maxLogs = ref(100)

  // SSE连接
  let eventSource: EventSource | null = null
  let pollTimer: ReturnType<typeof setInterval> | null = null

  // 计算属性
  const isRunning = computed(() => status.value === 'running')
  const isPaused = computed(() => status.value === 'paused')
  const isFinished = computed(() => status.value === 'finished')
  const isIdle = computed(() => status.value === 'idle')

  const progress = computed(() => {
    if (maxRounds.value === 0) return 0
    return (currentRound.value / maxRounds.value) * 100
  })

  // Actions
  async function createExperiment(newConfig: ExperimentConfig): Promise<string> {
    const result = await api.createExperiment(newConfig)
    experimentId.value = result.id
    config.value = newConfig
    maxRounds.value = newConfig.rounds
    status.value = 'idle'
    return result.id
  }

  async function startExperiment() {
    if (!experimentId.value) {
      throw new Error('No experiment ID')
    }
    await api.startExperiment(experimentId.value)
    status.value = 'running'
    connectStream()
    // 轮询兜底：每2秒强制拉取一次状态，防止 SSE 漏接
    if (pollTimer) clearInterval(pollTimer)
    pollTimer = setInterval(() => {
      if (status.value === 'running' || status.value === 'paused') {
        fetchCurrentState()
      }
    }, 2000)
  }

  async function pauseExperiment() {
    if (!experimentId.value) return
    await api.pauseExperiment(experimentId.value)
    status.value = 'paused'
  }

  async function resumeExperiment() {
    if (!experimentId.value) return
    await api.resumeExperiment(experimentId.value)
    status.value = 'running'
  }

  async function stopExperiment() {
    if (!experimentId.value) return
    await api.stopExperiment(experimentId.value)
    status.value = 'finished'
    disconnectStream()
  }

  async function loadExperimentHistory(): Promise<ExperimentResult[]> {
    return await api.getExperimentHistory()
  }

  async function loadExperiment(id: string) {
    const result = await api.getExperiment(id)
    experimentId.value = result.id
    config.value = result.config
    status.value = result.status
    maxRounds.value = result.config.rounds

    if (result.status === 'finished') {
      metricsHistory.value = result.metrics_history
      winner.value = result.winner || null
    }
  }

  async function fetchCurrentState() {
    if (!experimentId.value) return
    try {
      const state = await api.getGameState(experimentId.value)
      updateState(state)
    } catch (e) {
      console.error('Failed to fetch state:', e)
    }
  }

  async function fetchMetrics() {
    if (!experimentId.value) return
    try {
      const history = await api.getMetricsHistory(experimentId.value)
      metricsHistory.value = history
    } catch (e) {
      console.error('Failed to fetch metrics:', e)
    }
  }

  async function fetchLogs() {
    if (!experimentId.value) return
    try {
      const newLogs = await api.getLogs(experimentId.value)
      logs.value = newLogs.slice(-maxLogs.value)
    } catch (e) {
      console.error('Failed to fetch logs:', e)
    }
  }

  function connectStream() {
    if (!experimentId.value || eventSource) return

    // 防止重复连接
    disconnectStream()

    eventSource = api.createSSEConnection(
      experimentId.value,
      (state) => {
        // 更新状态（由 SSE 数据驱动）
        updateState(state)
      },
      (error) => {
        console.error('SSE error:', error)
        // SSE 连接关闭时，不主动改变状态
        // 状态由 fetchCurrentState 轮询来同步
        fetchCurrentState()
      }
    )
  }

  function disconnectStream() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  function updateState(state: GameState) {
    currentRound.value = state.round
    maxRounds.value = state.max_rounds
    status.value = state.status as any
    winner.value = state.winner || null

    if (state.network) {
      networkNodes.value = state.network.nodes
      networkEdges.value = state.network.edges
    }

    if (state.agents) {
      attackerState.value = state.agents.attacker
      defenderState.value = state.agents.defender
      taskNodesState.value = state.agents.task_nodes
    }

    if (state.metrics) {
      currentMetrics.value = state.metrics

      // 防止 SSE 和轮询对同一轮次重复推送数据
      const lastRound = metricsHistory.value.rounds[metricsHistory.value.rounds.length - 1]
      if (lastRound !== state.round) {
        metricsHistory.value.rounds.push(state.round)
        metricsHistory.value.num_edges.push(state.metrics.num_edges)
        metricsHistory.value.largest_cc_ratio.push(state.metrics.largest_cc_ratio)
        metricsHistory.value.robustness_index.push(state.metrics.robustness_index)
        metricsHistory.value.clustering_coeff.push(state.metrics.clustering_coeff)
      }
    }

    // 增量追加日志（增量追加而非全量覆盖，防止 SSE 重推时日志重复）
    if (state.logs && state.logs.length > 0) {
      const existingTimestamps = new Set(logs.value.map((l: GameLog) => l.timestamp + l.message))
      for (const log of state.logs) {
        const key = log.timestamp + log.message
        if (!existingTimestamps.has(key)) {
          logs.value.push(log)
        }
      }
      if (logs.value.length > maxLogs.value) {
        logs.value = logs.value.slice(-maxLogs.value)
      }
    }
  }

  function addLog(log: GameLog) {
    logs.value.push(log)
    if (logs.value.length > maxLogs.value) {
      logs.value = logs.value.slice(-maxLogs.value)
    }
  }

  function reset() {
    experimentId.value = null
    status.value = 'idle'
    config.value = null
    currentRound.value = 0
    maxRounds.value = 30
    winner.value = null
    networkNodes.value = []
    networkEdges.value = []
    attackerState.value = null
    defenderState.value = null
    taskNodesState.value = null
    metricsHistory.value = {
      rounds: [],
      num_edges: [],
      largest_cc_ratio: [],
      robustness_index: [],
      clustering_coeff: []
    }
    currentMetrics.value = null
    logs.value = []
    disconnectStream()
  }

  return {
    // State
    experimentId,
    status,
    config,
    currentRound,
    maxRounds,
    winner,
    networkNodes,
    networkEdges,
    attackerState,
    defenderState,
    taskNodesState,
    metricsHistory,
    currentMetrics,
    logs,

    // Computed
    isRunning,
    isPaused,
    isFinished,
    isIdle,
    progress,

    // Actions
    createExperiment,
    startExperiment,
    pauseExperiment,
    resumeExperiment,
    stopExperiment,
    loadExperimentHistory,
    loadExperiment,
    fetchCurrentState,
    fetchMetrics,
    fetchLogs,
    connectStream,
    disconnectStream,
    updateState,
    addLog,
    reset
  }
})
