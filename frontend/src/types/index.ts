// 实验配置
export interface ExperimentConfig {
  rounds: number
  nodes: number
  network_type: 'watts_strogatz' | 'barabasi_albert' | 'complete' | 'cycle' | 'facebook'
  use_llm: boolean
  model: 'ollama' | 'dashscope' | 'deepseek' | 'wenxin'
  max_attacks: number
  max_repairs: number
  max_new_edges: number
  paralysis_threshold: number
  paralysis_rounds: number
}

// 网络节点
export interface NetworkNode {
  id: number
  status: 'active' | 'attacked' | 'repaired'
  degree: number
  betweenness?: number
  label?: string
}

// 网络边
export interface NetworkEdge {
  source: number
  target: number
  status: 'normal' | 'attacked' | 'repaired' | 'new'
}

// 网络状态
export interface NetworkState {
  nodes: NetworkNode[]
  edges: NetworkEdge[]
}

// 智能体任务
export interface AgentTask {
  id: string
  description: string
  progress: number
  status: 'pending' | 'running' | 'completed'
}

// 攻击智能体状态
export interface AttackerState {
  current_task: string
  progress: number
  stats: {
    attacked: number
    hit_rate: number
    learned_strategies: string[]
  }
}

// 防御智能体状态
export interface DefenderState {
  current_task: string
  progress: number
  stats: {
    repaired: number
    repair_rate: number
    added_edges: number
  }
}

// 任务节点状态
export interface TaskNodesState {
  total: number
  active: number
  normal_edges: number
  tasks_in_progress: number
}

// 智能体状态
export interface AgentsState {
  attacker: AttackerState
  defender: DefenderState
  task_nodes: TaskNodesState
}

// 指标数据
export interface MetricsData {
  num_edges: number
  largest_cc_ratio: number
  robustness_index: number
  clustering_coeff: number
  avg_path_length: number
  avg_degree: number
  diameter: number
  degree_centralization: number
}

// 博弈状态
export interface GameState {
  round: number
  max_rounds: number
  status: 'idle' | 'running' | 'paused' | 'finished'
  winner?: 'attacker' | 'defender' | 'draw'
  network: NetworkState
  agents: AgentsState
  metrics: MetricsData
  logs?: GameLog[]
}

// 指标历史
export interface MetricsHistory {
  rounds: number[]
  num_edges: number[]
  largest_cc_ratio: number[]
  robustness_index: number[]
  clustering_coeff: number[]
  avg_degree: number[]
  avg_path_length: number[]
  diameter: number[]
  degree_centralization: number[]
}

// 游戏日志
export interface GameLog {
  timestamp: string
  round: number
  type: 'attack' | 'defense' | 'system' | 'info'
  message: string
  details?: Record<string, unknown>
}

// 实验结果
export interface ExperimentResult {
  id: string
  config: ExperimentConfig
  status: 'running' | 'finished' | 'stopped'
  winner?: 'attacker' | 'defender' | 'draw'
  total_rounds: number
  final_metrics: MetricsData
  metrics_history: MetricsHistory
  logs: GameLog[]
}

// 智能体学习分析
export interface AgentLearningAnalysis {
  agent_type: 'attacker' | 'defender'
  learning_effectiveness: number
  strategy_evolution: {
    round: number
    strategy: string
    effectiveness: number
  }[]
  recommendations: string[]
}
