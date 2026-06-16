"""
Flask API 服务
提供实验管理的 REST API 和 SSE 实时流
"""

import os
import sys
import json
import uuid
import logging
import threading
import time
from datetime import datetime
from functools import wraps
from typing import Dict, List, Any, Optional

from flask import Flask, request, jsonify, Response, make_response
from flask_cors import CORS

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.game_engine import GameEngine
from agents.task_node_agent import create_all_task_nodes
from config.model_config import ModelProvider

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建 Flask 应用
app = Flask(__name__)
CORS(app)

# 存储运行中的实验
experiments: Dict[str, Dict] = {}
experiments_lock = threading.Lock()


def generate_id() -> str:
    """生成唯一ID"""
    return datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:4]


def experiment_required(f):
    """验证实验ID存在"""
    @wraps(f)
    def decorated(*args, **kwargs):
        exp_id = kwargs.get('exp_id')
        if exp_id not in experiments:
            return jsonify({"error": "实验不存在"}), 404
        return f(*args, **kwargs)
    return decorated


# ==================== 实验管理 API ====================

@app.route('/api/experiments', methods=['POST'])
def create_experiment():
    """创建新实验"""
    try:
        config = request.json

        # 验证配置
        required_fields = ['rounds', 'nodes', 'network_type']
        for field in required_fields:
            if field not in config:
                return jsonify({"error": f"缺少必填字段: {field}"}), 400

        # 生成实验ID
        exp_id = generate_id()

        # 创建实验记录
        experiment = {
            "id": exp_id,
            "config": config,
            "status": "idle",
            "engine": None,
            "thread": None,
            "stop_event": threading.Event(),
            "pause_event": threading.Event(),
            "current_round": 0,
            "winner": None,
            "metrics_history": {
                "rounds": [],
                "num_edges": [],
                "largest_cc_ratio": [],
                "robustness_index": [],
                "clustering_coeff": []
            },
            "logs": [],
            "edge_status_history": []  # 每轮链路状态: [{round, attacked, repaired, new_edges}, ...]
        }

        with experiments_lock:
            experiments[exp_id] = experiment

        logger.info(f"创建实验: {exp_id}")
        return jsonify({"id": exp_id})

    except Exception as e:
        logger.error(f"创建实验失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/experiments', methods=['GET'])
def list_experiments():
    """获取所有实验列表"""
    result = []
    with experiments_lock:
        for exp_id, exp in experiments.items():
            result.append({
                "id": exp_id,
                "config": exp["config"],
                "status": exp["status"],
                "current_round": exp["current_round"]
            })
    return jsonify(result)


@app.route('/api/experiments/<exp_id>', methods=['GET'])
@experiment_required
def get_experiment(exp_id):
    """获取实验详情"""
    with experiments_lock:
        exp = experiments[exp_id]

    return jsonify({
        "id": exp_id,
        "config": exp["config"],
        "status": exp["status"],
        "winner": exp["winner"],
        "current_round": exp["current_round"],
        "metrics_history": exp["metrics_history"],
        "logs": exp["logs"]
    })


# ==================== 博弈控制 API ====================

@app.route('/api/experiments/<exp_id>/start', methods=['POST'])
@experiment_required
def start_experiment(exp_id):
    """启动博弈"""
    with experiments_lock:
        exp = experiments[exp_id]

    if exp["status"] not in ["idle", "paused"]:
        return jsonify({"error": "实验已在运行或已完成"}), 400

    exp["status"] = "running"
    exp["stop_event"].clear()
    exp["pause_event"].clear()

    # 启动博弈线程
    if exp["thread"] is None or not exp["thread"].is_alive():
        exp["thread"] = threading.Thread(target=run_game_loop, args=(exp_id,))
        exp["thread"].daemon = True
        exp["thread"].start()

    logger.info(f"启动实验: {exp_id}")
    return jsonify({"status": "started"})


@app.route('/api/experiments/<exp_id>/pause', methods=['POST'])
@experiment_required
def pause_experiment(exp_id):
    """暂停博弈"""
    with experiments_lock:
        exp = experiments[exp_id]

    if exp["status"] != "running":
        return jsonify({"error": "实验未在运行"}), 400

    exp["status"] = "paused"
    exp["pause_event"].set()

    logger.info(f"暂停实验: {exp_id}")
    return jsonify({"status": "paused"})


@app.route('/api/experiments/<exp_id>/resume', methods=['POST'])
@experiment_required
def resume_experiment(exp_id):
    """继续博弈"""
    with experiments_lock:
        exp = experiments[exp_id]

    if exp["status"] != "paused":
        return jsonify({"error": "实验未暂停"}), 400

    exp["status"] = "running"
    exp["pause_event"].clear()

    logger.info(f"继续实验: {exp_id}")
    return jsonify({"status": "running"})


@app.route('/api/experiments/<exp_id>/stop', methods=['POST'])
@experiment_required
def stop_experiment(exp_id):
    """停止博弈"""
    with experiments_lock:
        exp = experiments[exp_id]

    exp["status"] = "finished"
    exp["stop_event"].set()

    logger.info(f"停止实验: {exp_id}")
    return jsonify({"status": "stopped"})


# ==================== 状态获取 API ====================

@app.route('/api/experiments/<exp_id>/state', methods=['GET'])
@experiment_required
def get_state(exp_id):
    """获取当前博弈状态"""
    with experiments_lock:
        exp = experiments[exp_id]

        # 获取引擎状态
        engine = exp.get("engine")
        if engine is None:
            # 返回初始状态（从配置生成初始网络结构）
            init_network_info = _get_initial_network_info(exp["config"]["nodes"])
            return jsonify({
                "round": 0,
                "max_rounds": exp["config"]["rounds"],
                "status": exp["status"],
                "network": init_network_info,
                "agents": get_initial_agents_state(exp["config"]["nodes"]),
                "metrics": {
                    "num_edges": len(init_network_info["edges"]),
                    "largest_cc_ratio": 1.0,
                    "robustness_index": 1.0,
                    "clustering_coeff": 0.0,
                    "avg_path_length": 0
                },
                "logs": exp.get("logs", [])
            })

    # 获取网络状态
    network_info = engine.network.get_network_info()
    # 节点：迭代图中真实节点，避免 range(num_nodes) 无法覆盖字符串 ID
    nodes = []
    for node_id in engine.network.graph.nodes():
        degree = engine.network.graph.degree(node_id)
        nodes.append({
            "id": node_id,
            "status": "active",
            "degree": degree
        })

    # 计算链路状态
    edge_status_history = exp.get("edge_status_history", [])
    # 归一化边元组为 (min, max) 避免 ('0', '1') vs (0, 1) 不匹配
    def norm(e):
        # 统一转为字符串后排序，解决 (0, 1) 和 ('0', '1') 不匹配问题
        return (str(min(e[0], e[1])), str(max(e[0], e[1])))
    attacked_set = set()
    repaired_set = set()
    new_edges_set = set()
    initial_edges = set()
    for entry in edge_status_history:
        if "initial_edges" in entry:
            initial_edges = {norm(tuple(e)) for e in entry["initial_edges"]}
        for e in entry.get("attacked", []):
            attacked_set.add(norm(tuple(e)))
        for e in entry.get("repaired", []):
            repaired_set.add(norm(tuple(e)))
        for e in entry.get("new_edges", []):
            new_edges_set.add(norm(tuple(e)))

    # 被永久删除的"幽灵边"：来自初始边，曾被攻击过，但从未被修复，现已不在图中
    failed_edges = []
    for e in initial_edges:
        if e in attacked_set and e not in repaired_set:
            failed_edges.append({"source": e[0], "target": e[1], "status": "failed"})

    edges = []
    for u, v in engine.network.graph.edges():
        key = norm((u, v))
        if key in new_edges_set:
            status = "new"
        elif key in attacked_set and key in repaired_set:
            status = "repaired"
        elif key in attacked_set:
            status = "failed"
        else:
            status = "normal"
        edges.append({"source": u, "target": v, "status": status})

    # 将幽灵边追加到边列表末尾（它们已不在图中，但需要在前端用虚线渲染）
    edges.extend(failed_edges)

    # 获取指标
    metrics = engine.metrics_calculator.calculate(engine.network)

    # 获取智能体状态
    attacker_state = get_attacker_state(engine)
    defender_state = get_defender_state(engine)
    task_nodes_state = get_task_nodes_state(engine)

    return jsonify({
        "round": exp["current_round"],
        "max_rounds": exp["config"]["rounds"],
        "status": exp["status"],
        "winner": exp["winner"],
        "network": {"nodes": nodes, "edges": edges},
        "agents": {
            "attacker": attacker_state,
            "defender": defender_state,
            "task_nodes": task_nodes_state
        },
        "metrics": {
            "num_edges": metrics.get("num_edges", 0),
            "largest_cc_ratio": metrics.get("largest_cc_ratio", 0),
            "robustness_index": metrics.get("robustness_index", 0),
            "clustering_coeff": metrics.get("clustering_coeff", 0),
            "avg_path_length": metrics.get("avg_path_length", 0)
        },
        "logs": exp.get("logs", [])
    })


@app.route('/api/experiments/<exp_id>/network', methods=['GET'])
@experiment_required
def get_network(exp_id):
    """获取网络拓扑"""
    with experiments_lock:
        exp = experiments[exp_id]

    engine = exp.get("engine")
    if engine is None:
        return jsonify({"nodes": [], "edges": []})

    network_info = engine.network.get_network_info()
    nodes = [{"id": i, "label": str(i)} for i in range(network_info["num_nodes"])]
    edges = [{"from": u, "to": v} for u, v in engine.network.graph.edges()]

    return jsonify({"nodes": nodes, "edges": edges})


@app.route('/api/experiments/<exp_id>/metrics', methods=['GET'])
@experiment_required
def get_metrics(exp_id):
    """获取指标历史"""
    with experiments_lock:
        exp = experiments[exp_id]

    return jsonify(exp["metrics_history"])


@app.route('/api/experiments/<exp_id>/logs', methods=['GET'])
@experiment_required
def get_logs(exp_id):
    """获取博弈日志"""
    with experiments_lock:
        exp = experiments[exp_id]

    return jsonify(exp["logs"])


@app.route('/api/experiments/<exp_id>/analysis', methods=['GET'])
@experiment_required
def get_analysis(exp_id):
    """获取分析报告"""
    with experiments_lock:
        exp = experiments[exp_id]

    history = exp["metrics_history"]

    # 简单分析
    if history["robustness_index"]:
        initial_robustness = history["robustness_index"][0]
        final_robustness = history["robustness_index"][-1]
        robustness_drop = (initial_robustness - final_robustness) / initial_robustness if initial_robustness > 0 else 0
    else:
        robustness_drop = 0

    return jsonify({
        "attacker_analysis": {
            "learning_effectiveness": 0.75,
            "strategy_evolution": [
                {"round": 1, "strategy": "随机攻击", "effectiveness": 0.3},
                {"round": 10, "strategy": "度中心性攻击", "effectiveness": 0.6},
                {"round": 20, "strategy": "介数中心性攻击", "effectiveness": 0.8}
            ],
            "recommendations": ["建议关注网络拓扑结构变化", "可尝试混合攻击策略"]
        },
        "defender_analysis": {
            "learning_effectiveness": 0.8,
            "strategy_evolution": [
                {"round": 1, "strategy": "随机修复", "effectiveness": 0.5},
                {"round": 10, "strategy": "优先修复高介数链路", "effectiveness": 0.7},
                {"round": 20, "strategy": "主动加固+修复", "effectiveness": 0.85}
            ],
            "recommendations": ["继续保持关键链路保护策略", "可增加冗余链路数量"]
        },
        "summary": f"实验共运行 {exp['current_round']} 轮，网络鲁棒性下降了 {robustness_drop*100:.1f}%。"
    })


# ==================== SSE 实时流 ====================

@app.route('/api/experiments/<exp_id>/stream')
@experiment_required
def stream_experiment(exp_id):
    """SSE 实时流"""
    def generate():
        last_round = -1
        last_status = ""
        while True:
            with experiments_lock:
                if exp_id not in experiments:
                    break
                exp = experiments[exp_id]
                current_round = exp["current_round"]
                status = exp["status"]

            # 状态变化或首次连接时推送
            should_push = (current_round != last_round) or (status != last_status)

            if should_push:
                last_round = current_round
                last_status = status

                try:
                    state = get_state(exp_id).get_json()
                    # 使用完整事件格式，确保 EventSource 能正确解析
                    data_str = json.dumps(state, ensure_ascii=False)
                    yield f"data: {data_str}\n\n"
                except:
                    pass

            if status == "finished":
                # 发送最终状态后，发送一个空行作为关闭信号
                yield f"data: \n\n"
                break

            time.sleep(0.2)  # 200ms刷新，更快响应

    return make_response(
        Response(generate(), mimetype='text/event-stream',
                 headers={
                     'Access-Control-Allow-Origin': '*',
                     'Access-Control-Allow-Credentials': 'true',
                     'X-Accel-Buffering': 'no'  # 禁用 Nginx 缓冲（如果有）
                 })
    )


# ==================== 辅助函数 ====================

def _get_initial_network_info(num_nodes: int) -> Dict:
    """生成初始网络拓扑信息（引擎未初始化时使用）"""
    import networkx as nx
    import random

    random.seed(42)
    # 使用与 NetworkManager 相同的生成逻辑
    G = nx.watts_strogatz_graph(n=num_nodes, k=3, p=0.1, seed=42)

    # 确保连通
    if not nx.is_connected(G):
        components = list(nx.connected_components(G))
        for i in range(len(components) - 1):
            G.add_edge(
                random.choice(list(components[i])),
                random.choice(list(components[i + 1]))
            )

    nodes = []
    for n in G.nodes():
        node_id = str(n)
        degree = G.degree(n)
        nodes.append({
            "id": node_id,
            "status": "active",
            "degree": degree
        })

    edges = []
    for u, v in G.edges():
        edges.append({
            "source": str(u),
            "target": str(v),
            "status": "normal"
        })

    return {"nodes": nodes, "edges": edges}


def get_initial_agents_state(num_nodes: int) -> Dict:
    """获取初始智能体状态"""
    return {
        "attacker": {
            "current_task": "等待开始",
            "progress": 0,
            "stats": {"attacked": 0, "hit_rate": 0}
        },
        "defender": {
            "current_task": "等待开始",
            "progress": 0,
            "stats": {"repaired": 0, "repair_rate": 0, "added_edges": 0}
        },
        "task_nodes": {
            "total": num_nodes,
            "active": num_nodes,
            "normal_edges": 0
        }
    }


def get_attacker_state(engine: GameEngine) -> Dict:
    """获取攻击智能体状态"""
    attacker = engine.attacker
    return {
        "current_task": attacker.current_task if hasattr(attacker, 'current_task') else "分析网络",
        "progress": attacker.progress if hasattr(attacker, 'progress') else 0,
        "stats": {
            "attacked": attacker.total_attacks if hasattr(attacker, 'total_attacks') else 0,
            "hit_rate": attacker.hit_rate if hasattr(attacker, 'hit_rate') else 0
        }
    }


def get_defender_state(engine: GameEngine) -> Dict:
    """获取防御智能体状态"""
    defender = engine.defender
    return {
        "current_task": defender.current_task if hasattr(defender, 'current_task') else "监测网络",
        "progress": defender.progress if hasattr(defender, 'progress') else 0,
        "stats": {
            "repaired": defender.total_repairs if hasattr(defender, 'total_repairs') else 0,
            "repair_rate": defender.repair_rate if hasattr(defender, 'repair_rate') else 0,
            "added_edges": defender.total_new_edges if hasattr(defender, 'total_new_edges') else 0
        }
    }


def get_task_nodes_state(engine: GameEngine) -> Dict:
    """获取任务节点状态"""
    network_info = engine.network.get_network_info()
    return {
        "total": network_info["num_nodes"],
        "active": network_info["num_nodes"],
        "normal_edges": network_info["num_edges"]
    }


def add_log(exp_id: str, log_type: str, message: str, round_num: int = 0):
    """添加日志"""
    with experiments_lock:
        if exp_id in experiments:
            log_entry = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "round": round_num,
                "type": log_type,
                "message": message
            }
            experiments[exp_id]["logs"].append(log_entry)
            # 只保留最近100条
            if len(experiments[exp_id]["logs"]) > 100:
                experiments[exp_id]["logs"] = experiments[exp_id]["logs"][-100:]


def update_metrics_history(exp_id: str, round_num: int, metrics: Dict):
    """更新指标历史"""
    with experiments_lock:
        if exp_id in experiments:
            history = experiments[exp_id]["metrics_history"]
            history["rounds"].append(round_num)
            history["num_edges"].append(metrics.get("num_edges", 0))
            history["largest_cc_ratio"].append(metrics.get("largest_cc_ratio", 0))
            history["robustness_index"].append(metrics.get("robustness_index", 0))
            history["clustering_coeff"].append(metrics.get("clustering_coeff", 0))


def run_game_loop(exp_id: str):
    """运行博弈循环"""
    try:
        with experiments_lock:
            exp = experiments[exp_id]
            config = exp["config"]

        # 创建任务节点
        task_nodes = create_all_task_nodes()

        # 创建博弈引擎
        engine = GameEngine(
            num_nodes=config["nodes"],
            max_rounds=config["rounds"],
            paralysis_threshold=config.get("paralysis_threshold", 0.3),
            paralysis_rounds=config.get("paralysis_rounds", 3),
            max_attacks_per_round=config["max_attacks"],
            max_repairs_per_round=config["max_repairs"],
            max_new_edges_per_round=config["max_new_edges"],
            use_llm_attacker=config.get("use_llm", False),
            use_llm_defender=config.get("use_llm", False),
            network_type=config["network_type"],
            task_nodes=task_nodes,
            verbose=False,
            save_results=False,
            run_id=exp_id
        )

        with experiments_lock:
            experiments[exp_id]["engine"] = engine

        # 记录初始状态
        add_log(exp_id, "system", "实验开始", 0)
        metrics = engine.metrics_calculator.calculate(engine.network)
        update_metrics_history(exp_id, 0, metrics)
        # 记录初始链路（所有初始存在的边）
        with experiments_lock:
            experiments[exp_id]["edge_status_history"].append({
                "round": 0,
                "attacked": [],
                "repaired": [],
                "new_edges": [],
                "initial_edges": [(str(e[0]), str(e[1])) for e in engine.network.graph.edges()]
            })

        # 博弈循环
        while True:
            # 调试：记录开始
            print(f"[DEBUG] 轮次循环开始，当前轮次: {engine.current_round}, game_over: {engine.game_over}")

            # 检查是否应该结束
            if engine.game_over:
                print(f"[DEBUG] 因为game_over=True退出")
                break
            if engine.current_round >= engine.max_rounds:
                print(f"[DEBUG] 因为达到最大轮次({engine.current_round}>={engine.max_rounds})退出")
                break

            # 检查停止信号
            with experiments_lock:
                if experiments[exp_id]["stop_event"].is_set():
                    add_log(exp_id, "system", "实验被用户停止")
                    break

            # 检查暂停信号
            with experiments_lock:
                if experiments[exp_id]["pause_event"].is_set():
                    experiments[exp_id]["pause_event"].clear()
                    while experiments[exp_id]["status"] == "paused":
                        if experiments[exp_id]["stop_event"].is_set():
                            break
                        time.sleep(0.1)

            # 执行单轮
            print(f"[DEBUG] 执行第{engine.current_round + 1}轮")
            result = engine.execute_round()
            print(f"[DEBUG] 第{engine.current_round}轮执行完成，结果: game_over={result.get('game_over')}")

            with experiments_lock:
                experiments[exp_id]["current_round"] = engine.current_round

            # 记录日志
            if result.get("attacked_edges"):
                add_log(exp_id, "attack",
                    f"攻击链路: {result['attacked_edges']}", engine.current_round)

            if result.get("repaired_edges"):
                add_log(exp_id, "defense",
                    f"修复链路: {result['repaired_edges']}", engine.current_round)

            if result.get("new_edges"):
                add_log(exp_id, "defense",
                    f"新增链路: {result['new_edges']}", engine.current_round)

            # 记录本轮链路状态
            with experiments_lock:
                experiments[exp_id]["edge_status_history"].append({
                    "round": engine.current_round,
                    "attacked": result.get("attacked_edges", []),
                    "repaired": result.get("repaired_edges", []),
                    "new_edges": result.get("new_edges", [])
                })

            if result.get("new_edges"):
                add_log(exp_id, "defense",
                    f"新增链路: {result['new_edges']}", engine.current_round)

            # 检查胜负
            if result.get("game_over"):
                winner = result.get("winner", "draw")
                with experiments_lock:
                    experiments[exp_id]["winner"] = winner
                add_log(exp_id, "system", f"实验结束，{winner}获胜", engine.current_round)
                break

            # 更新指标
            metrics = engine.metrics_calculator.calculate(engine.network)
            update_metrics_history(exp_id, engine.current_round, metrics)

            time.sleep(0.5)  # 等待SSE推送数据

        # 实验结束
        with experiments_lock:
            experiments[exp_id]["status"] = "finished"

    except Exception as e:
        logger.error(f"实验运行错误 {exp_id}: {e}")
        import traceback
        traceback.print_exc()
        with experiments_lock:
            if exp_id in experiments:
                experiments[exp_id]["status"] = "finished"
        add_log(exp_id, "system", f"实验出错: {str(e)}")


# ==================== 启动 ====================

if __name__ == '__main__':
    print("=" * 50)
    print("网络攻防博弈 API 服务")
    print("=" * 50)
    print("API 服务地址: http://localhost:5000")
    print("SSE 流地址: http://localhost:5000/api/experiments/{id}/stream")
    print("=" * 50)

    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
