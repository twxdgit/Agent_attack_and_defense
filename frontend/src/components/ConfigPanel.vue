<template>
  <div class="card config-panel">
    <h2 class="card-title">参数配置</h2>

    <form @submit.prevent="handleSubmit">
      <!-- 博弈参数 -->
      <div class="form-section">
        <h3 class="section-title">博弈参数</h3>

        <div class="form-group">
          <label class="form-label">博弈轮次</label>
          <input
            v-model.number="config.rounds"
            type="number"
            class="form-input"
            min="1"
            max="100"
            :disabled="!isIdle"
          />
        </div>

        <div class="form-group">
          <label class="form-label">节点数量</label>
          <input
            v-model.number="config.nodes"
            type="number"
            class="form-input"
            min="3"
            max="50"
            :disabled="!isIdle"
          />
        </div>

        <div class="form-group">
          <label class="form-label">网络类型</label>
          <select v-model="config.network_type" class="form-select" :disabled="!isIdle">
            <option value="watts_strogatz">小世界网络 (WS)</option>
            <option value="barabasi_albert">无标度网络 (BA)</option>
            <option value="complete">完全图</option>
            <option value="cycle">环形网络</option>
          </select>
        </div>
      </div>

      <!-- 能力限制 -->
      <div class="form-section">
        <h3 class="section-title">能力限制</h3>

        <div class="form-group">
          <label class="form-label">每轮最大攻击链路数</label>
          <input
            v-model.number="config.max_attacks"
            type="number"
            class="form-input"
            min="1"
            max="10"
            :disabled="!isIdle"
          />
        </div>

        <div class="form-group">
          <label class="form-label">每轮最大修复链路数</label>
          <input
            v-model.number="config.max_repairs"
            type="number"
            class="form-input"
            min="1"
            max="10"
            :disabled="!isIdle"
          />
        </div>

        <div class="form-group">
          <label class="form-label">每轮最大新增链路数</label>
          <input
            v-model.number="config.max_new_edges"
            type="number"
            class="form-input"
            min="0"
            max="5"
            :disabled="!isIdle"
          />
        </div>
      </div>

      <!-- 大模型设置 -->
      <div class="form-section">
        <h3 class="section-title">大模型设置</h3>

        <div class="form-group">
          <label class="checkbox-label">
            <input v-model="config.use_llm" type="checkbox" :disabled="!isIdle" />
            <span>启用大模型智能体</span>
          </label>
        </div>

        <div class="form-group" v-if="config.use_llm">
          <label class="form-label">模型选择</label>
          <select v-model="config.model" class="form-select" :disabled="!isIdle">
            <option value="ollama">Qwen (本地 Ollama)</option>
            <option value="dashscope">通义千问</option>
            <option value="deepseek">DeepSeek</option>
          </select>
        </div>
      </div>

      <!-- 控制按钮 -->
      <div class="btn-group">
        <button
          v-if="isIdle"
          type="submit"
          class="btn btn-primary btn-full"
        >
          开始实验
        </button>

        <button
          v-if="isRunning"
          type="button"
          class="btn btn-warning btn-full"
          @click="handlePause"
        >
          暂停
        </button>

        <button
          v-if="isPaused"
          type="button"
          class="btn btn-success btn-full"
          @click="handleResume"
        >
          继续
        </button>

        <button
          v-if="!isIdle"
          type="button"
          class="btn btn-danger btn-full"
          @click="handleStop"
        >
          停止
        </button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { reactive, computed } from 'vue'
import { useExperimentStore } from '@/stores/experiment'
import type { ExperimentConfig } from '@/types'

const store = useExperimentStore()

const config = reactive<ExperimentConfig>({
  rounds: 30,
  nodes: 8,
  network_type: 'watts_strogatz',
  use_llm: false,
  model: 'ollama',
  max_attacks: 2,
  max_repairs: 2,
  max_new_edges: 1,
  paralysis_threshold: 0.3,
  paralysis_rounds: 3
})

const isIdle = computed(() => store.status === 'idle')
const isRunning = computed(() => store.status === 'running')
const isPaused = computed(() => store.status === 'paused')

async function handleSubmit() {
  try {
    await store.createExperiment(config)
    await store.startExperiment()
  } catch (error) {
    console.error('Failed to start experiment:', error)
  }
}

async function handlePause() {
  await store.pauseExperiment()
}

async function handleResume() {
  await store.resumeExperiment()
}

async function handleStop() {
  await store.stopExperiment()
}
</script>

<style scoped>
.config-panel {
  height: fit-content;
}

.form-section {
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-color);
}

.form-section:last-of-type {
  border-bottom: none;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--text-color);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.checkbox-label input {
  width: 16px;
  height: 16px;
}

.btn-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 16px;
}
</style>
