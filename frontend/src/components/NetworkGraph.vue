<template>
  <div class="card network-graph">
    <h2 class="card-title">网络拓扑可视化</h2>

    <div ref="container" class="network-container"></div>

    <!-- 图例 -->
    <div class="legend">
      <div class="legend-item">
        <span class="legend-line" style="background: #8c8c8c;"></span>
        <span>正常</span>
      </div>
      <div class="legend-item">
        <span class="legend-line" style="background: #f5222d;"></span>
        <span>被攻击</span>
      </div>
      <div class="legend-item">
        <span class="legend-line" style="background: #1890ff;"></span>
        <span>已修复</span>
      </div>
      <div class="legend-item">
        <span class="legend-line" style="background: #722ed1;"></span>
        <span>新增链路</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted } from 'vue'
import { Network, DataSet } from 'vis-network/standalone'
import { useExperimentStore } from '@/stores/experiment'

const store = useExperimentStore()
const container = ref<HTMLElement>()
let network: Network | null = null

const nodeColors = {
  active: '#52c41a',
  attacked: '#f5222d',
  repaired: '#1890ff'
}

const edgeColors = {
  normal: '#8c8c8c',
  attacked: '#f5222d',
  repaired: '#1890ff',
  new: '#722ed1',
  failed: '#faad14'
}

function getNodeColor(status: string): string {
  return nodeColors[status as keyof typeof nodeColors] || nodeColors.active
}

function getEdgeColor(status: string): string {
  return edgeColors[status as keyof typeof edgeColors] || edgeColors.normal
}

function initNetwork() {
  if (!container.value) return

  // 创建空的 DataSet，初始不预填数据
  // 所有节点/边由 updateNetwork() 负责渲染
  const nodes = new DataSet()
  const edges = new DataSet()

  const options = {
    nodes: {
      shape: 'dot',
      size: 20,
      font: { size: 14, color: '#000000' },
      color: {
        background: nodeColors.active,
        border: '#2b7a0b',
        highlight: { background: '#73d13d', border: '#2b7a0b' }
      }
    },
    edges: {
      width: 2,
      color: { color: edgeColors.normal, highlight: '#1890ff' },
      smooth: { type: 'continuous' }
    },
    physics: {
      enabled: true,
      solver: 'forceAtlas2Based',
      forceAtlas2Based: {
        gravitationalConstant: -50,
        centralGravity: 0.01,
        springLength: 100,
        springConstant: 0.08
      },
      stabilization: { iterations: 100 }
    },
    interaction: {
      hover: true,
      tooltipDelay: 200
    }
  }

  network = new Network(container.value, { nodes, edges }, options)
}

// 每帧都全量同步，确保 vis-network 的节点/边集合与后端完全一致
function updateNetwork() {
  if (!network) return

  const nodes = store.networkNodes.map((n: any) => ({
    id: n.id,
    label: String(n.id),
    color: {
      background: getNodeColor(n.status),
      border: '#2b7a0b'
    }
  }))

  const edges = store.networkEdges.map((e: any) => ({
    id: `${e.source}-${e.target}`,
    from: e.source,
    to: e.target,
    color: {
      color: getEdgeColor(e.status),
      highlight: getEdgeColor(e.status)
    },
    // 未修复的幽灵边用虚线，表示它已被永久删除
    dashes: e.status === 'failed',
    width: e.status === 'attacked' || e.status === 'repaired' ? 3 : 2
  }))

  // 全量同步：先清空再重新添加，保证节点/边完全对齐后端状态
  network.body.data.nodes.clear()
  network.body.data.nodes.add(nodes)
  network.body.data.edges.clear()
  network.body.data.edges.add(edges)

  network.fit()
}

onMounted(() => {
  initNetwork()
})

watch(
  () => [store.networkNodes, store.networkEdges, store.status],
  () => {
    updateNetwork()
  },
  { deep: true }
)

onUnmounted(() => {
  if (network) {
    network.destroy()
    network = null
  }
})
</script>

<style scoped>
.network-graph {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.network-container {
  flex: 1;
  height: 100%;
  background: #fafafa;
  border-radius: 4px;
  border: 1px solid var(--border-color);
  overflow: hidden;
}

.legend {
  display: flex;
  gap: 16px;
  padding: 12px 0;
  flex-wrap: wrap;
  border-top: 1px solid var(--border-color);
  margin-top: 12px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.legend-color {
  width: 16px;
  height: 16px;
  border-radius: 3px;
}

.legend-line {
  width: 24px;
  height: 3px;
  border-radius: 2px;
  display: inline-block;
  flex-shrink: 0;
}
</style>
