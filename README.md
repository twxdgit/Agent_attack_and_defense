# 多智能体任务博弈的动态攻防网络与鲁棒性对抗

基于 AgentScope 的网络攻防博弈实验平台。

## 项目简介

本项目实现了一个多智能体攻防博弈系统，用于研究 AI 驱动的自适应网络攻击与防御策略。系统包含：

- **8 个任务节点智能体**：构成 Facebook 社交网络分析流水线
- **攻击智能体**：自适应学习选择最优攻击目标
- **防御智能体**：实时修复网络并优化拓扑

## 主要特性

- 基于 AgentScope 框架的多智能体系统
- 支持本地 Ollama + 在线 API 混合模型调用
- 多种攻击/防御策略对比
- 完整的网络鲁棒性指标计算
- 可视化与动画生成
- **Web 图形化界面**（Vue.js + Flask）

## Web 界面

项目提供图形化 Web 界面，支持实时可视化博弈过程。

### 界面功能

- **参数配置**：设置博弈轮次、节点数量、网络类型、大模型开关等
- **网络拓扑可视化**：实时展示网络结构变化
- **智能体状态监控**：显示攻击/防御智能体任务进度和统计
- **指标图表**：实时绘制鲁棒性指标变化曲线
- **博弈日志**：记录完整攻防过程

### 启动 Web 界面

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动后端 API 服务（终端1）
python backend/app.py

# 3. 启动前端（终端2）
cd frontend
npm install
npm run dev

# 4. 打开浏览器访问 http://localhost:3000
```

## 数据集

使用 Stanford SNAP 提供的 Facebook 社交网络数据集：
- 4,039 个用户节点
- 88,234 条好友关系边

## 项目结构

```
network_attack_defense/
├── config/          # 配置模块
├── core/            # 核心模块（网络、模型、引擎）
├── agents/         # 智能体模块
├── strategies/     # 对照实验策略
├── metrics/        # 指标与可视化
├── scripts/        # 工具脚本
├── data/           # 数据目录
├── main.py         # 主程序
└── run_experiments.py  # 对照实验
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 安装 Ollama（可选）

```bash
# 安装 Ollama
# https://ollama.com/download

# 拉取 Qwen 模型
ollama pull qwen2.5:7b
```

### 3. 配置 API（可选）

复制 `.env.example` 为 `.env`，填写 API Key：

```bash
cp .env.example .env
```

### 4. 运行实验

```bash
# 使用合成网络运行
python main.py --rounds 30 --nodes 8

# 使用 Facebook 数据集运行
python main.py --use-facebook --subgraph-size 100

# 运行对照实验
python run_experiments.py --experiments all
```

## 使用方法

### 命令行参数

```bash
python main.py [选项]

选项：
  --rounds R        最大博弈轮次（默认30）
  --nodes N         节点数量（默认8）
  --network-type T  网络类型（watts_strogatz/barabasi_albert/facebook）
  --use-llm        使用大模型
  --use-facebook   使用Facebook数据集
  --save-plot      保存可视化图表
```

### Python API

```python
from core.game_engine import GameEngine
from agents.task_node_agent import create_all_task_nodes

# 创建博弈引擎
engine = GameEngine(
    num_nodes=8,
    max_rounds=30,
    use_llm_attacker=True,
    use_llm_defender=True
)

# 运行实验
result = engine.run()

# 查看结果
print(f"Winner: {result.winner}")
print(f"Rounds: {result.total_rounds}")
```

## 对照实验

| 实验组 | 攻击策略 | 防御策略 |
|-------|---------|---------|
| 对照组1 | 随机攻击 | 基础防御 |
| 对照组2 | 度数攻击 | 基础防御 |
| 实验组 | LLM自适应攻击 | LLM自适应防御 |

## 指标体系

- 最大连通分量比例
- 平均最短路径
- 聚类系数
- 网络效率
- 综合鲁棒性指数

## 8个任务节点

| 节点 | 角色 | 任务 |
|------|------|------|
| Node-1 | 数据采集节点 | 获取Facebook用户基础信息 |
| Node-2 | 关系解析节点 | 分析好友关系强度 |
| Node-3 | 社区发现节点 | Louvain社区划分 |
| Node-4 | 中心性分析节点 | PageRank、介数中心性 |
| Node-5 | 传播模型节点 | SI/SIR传播模拟 |
| Node-6 | 异常检测节点 | 识别风险用户 |
| Node-7 | 聚类分析节点 | K-means用户分群 |
| Node-8 | 结果汇总节点 | 生成分析报告 |

## License

MIT License
