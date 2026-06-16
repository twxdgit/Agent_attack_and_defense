import axios from 'axios'
import type {
  ExperimentConfig,
  GameState,
  ExperimentResult,
  MetricsHistory,
  GameLog
} from '@/types'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// 创建新实验
export async function createExperiment(config: ExperimentConfig): Promise<{ id: string }> {
  const response = await api.post('/experiments', config)
  return response.data
}

// 获取实验配置
export async function getExperiment(id: string): Promise<ExperimentResult> {
  const response = await api.get(`/experiments/${id}`)
  return response.data
}

// 启动实验
export async function startExperiment(id: string): Promise<void> {
  await api.post(`/experiments/${id}/start`)
}

// 暂停实验
export async function pauseExperiment(id: string): Promise<void> {
  await api.post(`/experiments/${id}/pause`)
}

// 继续实验
export async function resumeExperiment(id: string): Promise<void> {
  await api.post(`/experiments/${id}/resume`)
}

// 停止实验
export async function stopExperiment(id: string): Promise<void> {
  await api.post(`/experiments/${id}/stop`)
}

// 获取当前状态
export async function getGameState(id: string): Promise<GameState> {
  const response = await api.get(`/experiments/${id}/state`)
  return response.data
}

// 获取网络拓扑
export async function getNetworkTopology(id: string): Promise<{ nodes: any[], edges: any[] }> {
  const response = await api.get(`/experiments/${id}/network`)
  return response.data
}

// 获取指标数据
export async function getMetricsHistory(id: string): Promise<MetricsHistory> {
  const response = await api.get(`/experiments/${id}/metrics`)
  return response.data
}

// 获取分析报告
export async function getAnalysis(id: string): Promise<{
  attacker_analysis: any
  defender_analysis: any
  summary: string
}> {
  const response = await api.get(`/experiments/${id}/analysis`)
  return response.data
}

// 获取日志
export async function getLogs(id: string): Promise<GameLog[]> {
  const response = await api.get(`/experiments/${id}/logs`)
  return response.data
}

// 获取所有实验历史
export async function getExperimentHistory(): Promise<ExperimentResult[]> {
  const response = await api.get('/experiments')
  return response.data
}

// SSE直连后端Flask（不走Vite代理，EventSource不走XMLHttpRequest）
const SSE_BASE = 'http://localhost:5000/api'

// SSE流连接
export function createSSEConnection(
  id: string,
  onMessage: (data: GameState) => void,
  onError?: (error: Event) => void
): EventSource {
  const eventSource = new EventSource(`${SSE_BASE}/experiments/${id}/stream`)

  eventSource.onmessage = (event) => {
    try {
      // 后端实验结束时发送空行作为关闭信号，跳过解析
      if (!event.data || event.data.trim() === '') return
      const data = JSON.parse(event.data)
      onMessage(data)
    } catch (e) {
      console.warn('SSE parse error (ignored):', e)
    }
  }

  eventSource.onerror = (error) => {
    if (eventSource.readyState === EventSource.CLOSED) {
      console.debug('SSE connection closed (experiment finished)')
    } else {
      // CONNECTING(0) 或 OPEN(1) 状态下触发 onerror 表示连接异常
      // EventSource 会自动重试，前端由轮询兜底，不主动干预
      console.warn('SSE connection error, state:', eventSource.readyState)
      if (onError) onError(error)
    }
  }

  return eventSource
}

export default api
