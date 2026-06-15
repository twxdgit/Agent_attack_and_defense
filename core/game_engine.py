"""
博弈引擎
控制攻防博弈的轮次循环
"""

import logging
import random
import sys
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.network_manager import NetworkManager, NetworkState
from agents.attack_agent import AttackerAgent
from agents.defense_agent import DefenderAgent
from agents.task_node_agent import TaskNodeAgent, create_all_task_nodes
from metrics.robustness import RobustnessMetrics
from metrics.visualizer import GameVisualizer
from config.game_config import GameConfig

logger = logging.getLogger(__name__)


@dataclass
class GameRecord:
    """单轮博弈记录"""
    round_num: int
    timestamp: str
    attack_targets: List[Tuple[str, str]]
    attack_success: bool
    repair_targets: List[Tuple[str, str]]
    new_edges: List[Tuple[str, str]]
    network_state: Dict[str, Any]
    metrics: Dict[str, float]
    game_over: bool
    winner: Optional[str] = None


@dataclass
class GameResult:
    """博弈结果"""
    winner: Optional[str]
    total_rounds: int
    final_network_state: Dict[str, Any]
    metrics_curves: Dict[str, List]
    rounds_data: List[Dict]
    attack_history: List[Dict]
    defense_history: List[Dict]
    
    def to_dict(self) -> Dict:
        return {
            "winner": self.winner,
            "total_rounds": self.total_rounds,
            "final_network_state": self.final_network_state,
            "metrics_curves": self.metrics_curves,
            "rounds_data": self.rounds_data,
            "attack_history": self.attack_history,
            "defense_history": self.defense_history
        }


class GameEngine:
    """
    博弈引擎
    
    控制攻防博弈的主循环
    """
    
    def __init__(
        self,
        num_nodes: int = 8,
        max_rounds: int = 30,
        paralysis_threshold: float = 0.3,
        paralysis_rounds: int = 3,
        max_attacks_per_round: int = 2,
        max_repairs_per_round: int = 2,
        max_new_edges_per_round: int = 1,
        use_llm_attacker: bool = True,
        use_llm_defender: bool = True,
        network_type: str = "watts_strogatz",
        graph: Optional[Any] = None,
        task_nodes: Optional[List[TaskNodeAgent]] = None,
        attacker: Optional[AttackerAgent] = None,
        defender: Optional[DefenderAgent] = None,
        seed: int = 42,
        verbose: bool = True,
        save_results: bool = True
    ):
        """
        初始化博弈引擎
        """
        self.num_nodes = num_nodes
        self.max_rounds = max_rounds
        self.paralysis_threshold = paralysis_threshold
        self.paralysis_rounds = paralysis_rounds
        self.max_attacks_per_round = max_attacks_per_round
        self.max_repairs_per_round = max_repairs_per_round
        self.max_new_edges_per_round = max_new_edges_per_round
        self.use_llm_attacker = use_llm_attacker
        self.use_llm_defender = use_llm_defender
        self.verbose = verbose
        self.save_results = save_results
        
        # 设置随机种子
        if seed is not None:
            random.seed(seed)
        
        # 初始化组件
        self.network = NetworkManager(
            num_nodes=num_nodes,
            network_type=network_type,
            graph=graph,
            seed=seed
        )
        self.metrics_calculator = RobustnessMetrics()
        self.visualizer = GameVisualizer()
        
        # 初始化智能体
        if attacker:
            self.attacker = attacker
        else:
            self.attacker = AttackerAgent(
                max_attacks_per_round=max_attacks_per_round,
                use_llm=use_llm_attacker
            )
        
        if defender:
            self.defender = defender
        else:
            self.defender = DefenderAgent(
                max_repairs_per_round=max_repairs_per_round,
                max_new_edges_per_round=max_new_edges_per_round,
                use_llm=use_llm_defender
            )
        
        # 任务节点
        self.task_nodes = task_nodes or create_all_task_nodes()
        
        # 博弈记录
        self.game_records: List[GameRecord] = []
        self.current_round = 0
        self.paralysis_count = 0
        self.game_over = False
        self.winner: Optional[str] = None
        
        # 初始链路备份
        self.initial_edges = self.network.initial_edges.copy()
        
        logger.info(f"博弈引擎初始化完成: {num_nodes}节点, {max_rounds}轮")
    
    def log(self, message: str):
        """日志输出"""
        if self.verbose:
            print(f"[Round {self.current_round}] {message}")
        logger.info(message)
    
    def run(self) -> GameResult:
        """
        运行完整博弈
        
        Returns:
            博弈结果摘要
        """
        self.log("=" * 50)
        self.log("开始攻防博弈实验")
        self.log("=" * 50)
        
        # 记录初始状态
        self._record_round(is_initial=True)
        
        # 博弈主循环
        while not self.game_over and self.current_round < self.max_rounds:
            self.current_round += 1
            self._run_single_round()
            
            # 检查终止条件
            self._check_termination()
        
        # 生成最终报告
        return self._generate_summary()
    
    def _run_single_round(self):
        """执行单轮博弈"""
        self.log("-" * 40)
        self.log(f"第 {self.current_round} 轮开始")
        
        # === 阶段1：攻击阶段 ===
        self.log(">>> 攻击阶段")
        network_state = self.network.get_network_info()
        attack_targets = self.attacker.decide_attack_targets(
            network_state,
            use_llm=self.use_llm_attacker
        )
        attack_result = self.attacker.execute_attack(attack_targets, self.network)
        self.log(f"    攻击目标: {attack_result['attacked_edges']}")
        
        # === 阶段2：状态检测 ===
        network_state = self.network.get_network_info()
        is_paralyzed = self.network.is_network_paralyzed(self.paralysis_threshold)
        
        if is_paralyzed:
            self.paralysis_count += 1
            self.log(f"    ⚠ 网络瘫痪（连续第{self.paralysis_count}轮）")
        else:
            self.paralysis_count = 0
        
        # === 阶段3：防御阶段 ===
        self.log(">>> 防御阶段")
        defense_actions = self.defender.decide_defense_actions(
            network_state,
            self.initial_edges,
            use_llm=self.use_llm_defender
        )
        defense_result = self.defender.execute_defense(defense_actions, self.network)
        self.log(f"    修复链路: {defense_result['repairs']}")
        self.log(f"    新增链路: {defense_result['new_edges']}")
        
        # === 阶段4：记录状态 ===
        self._record_round(
            attack_targets=attack_result['attacked_edges'],
            attack_success=len(attack_result['attacked_edges']) > 0,
            repair_targets=defense_result['repairs'],
            new_edges=defense_result['new_edges']
        )
        
        # === 阶段5：可视化更新 ===
        self.visualizer.update(
            self.network,
            self.current_round,
            attack_result['attacked_edges'],
            defense_result['repairs'],
            defense_result['new_edges']
        )
        
        # === 输出状态 ===
        final_network_state = self.network.get_network_info()
        self.log(f"    当前链路数: {final_network_state['num_edges']}")
        self.log(f"    最大连通分量: {final_network_state['largest_cc_size']} 节点")
    
    def _record_round(
        self,
        is_initial: bool = False,
        attack_targets: List = None,
        attack_success: bool = False,
        repair_targets: List = None,
        new_edges: List = None
    ):
        """记录当前轮次"""
        metrics = self.metrics_calculator.calculate(self.network)
        network_state = self.network.get_network_info()
        
        record = GameRecord(
            round_num=self.current_round,
            timestamp=datetime.now().isoformat(),
            attack_targets=attack_targets or [],
            attack_success=attack_success,
            repair_targets=repair_targets or [],
            new_edges=new_edges or [],
            network_state=network_state,
            metrics=metrics,
            game_over=self.game_over,
            winner=self.winner
        )
        
        self.game_records.append(record)
    
    def _check_termination(self):
        """检查终止条件"""
        # 攻击方胜利：连续N轮网络瘫痪
        if self.paralysis_count >= self.paralysis_rounds:
            self.game_over = True
            self.winner = "Attacker"
            self.log("=" * 50)
            self.log(">>> 攻击方胜利！网络已彻底瘫痪")
            self.log("=" * 50)
        
        # 防御方胜利：达到最大轮次且网络未瘫
        elif self.current_round >= self.max_rounds:
            self.game_over = True
            self.winner = "Defender"
            self.log("=" * 50)
            self.log(">>> 防御方胜利！网络成功维持运行")
            self.log("=" * 50)
    
    def _generate_summary(self) -> GameResult:
        """生成博弈结果摘要"""
        # 计算汇总指标
        rounds_data = [
            {
                "round": r.round_num,
                "metrics": r.metrics,
                "network_state": r.network_state
            }
            for r in self.game_records
        ]
        
        # 提取关键指标曲线
        metrics_curves = {
            "num_edges": [r.metrics.get("num_edges", 0) for r in self.game_records],
            "largest_cc_ratio": [r.metrics.get("largest_cc_ratio", 0) for r in self.game_records],
            "avg_path_length": [r.metrics.get("avg_path_length", float('inf')) for r in self.game_records],
            "clustering_coeff": [r.metrics.get("clustering_coeff", 0) for r in self.game_records],
            "robustness_index": [r.metrics.get("robustness_index", 0) for r in self.game_records]
        }
        
        result = GameResult(
            winner=self.winner,
            total_rounds=self.current_round,
            final_network_state=self.game_records[-1].network_state if self.game_records else {},
            metrics_curves=metrics_curves,
            rounds_data=rounds_data,
            attack_history=[
                {"round": r.round_num, "targets": r.attack_targets}
                for r in self.game_records if r.attack_targets
            ],
            defense_history=[
                {"round": r.round_num, "repairs": r.repair_targets, "new_edges": r.new_edges}
                for r in self.game_records if r.repair_targets or r.new_edges
            ]
        )
        
        # 保存结果
        if self.save_results:
            self._save_results(result)
        
        return result
    
    def _save_results(self, result: GameResult):
        """保存实验结果"""
        os.makedirs("data/results", exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/results/game_result_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
        
        logger.info(f"结果已保存: {filename}")
    
    def get_metrics_over_time(self) -> Dict[str, List]:
        """获取指标随时间变化的数据"""
        return {
            "rounds": [r.round_num for r in self.game_records],
            "num_edges": [r.metrics.get("num_edges", 0) for r in self.game_records],
            "largest_cc_ratio": [r.metrics.get("largest_cc_ratio", 0) for r in self.game_records],
            "avg_path_length": [r.metrics.get("avg_path_length", 0) for r in self.game_records],
            "clustering_coeff": [r.metrics.get("clustering_coeff", 0) for r in self.game_records],
            "robustness_index": [r.metrics.get("robustness_index", 0) for r in self.game_records]
        }
    
    def reset(self):
        """重置博弈引擎"""
        self.network.reset()
        self.current_round = 0
        self.paralysis_count = 0
        self.game_over = False
        self.winner = None
        self.game_records.clear()
        self.attacker.reset()
        self.defender.reset()
        self.visualizer.reset()
