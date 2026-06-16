"""
基础防御策略（对照组）
基于规则的简单防御策略，作为LLM自适应防御的对照
"""

from typing import List, Tuple, Dict, Any, Set
import logging

logger = logging.getLogger(__name__)


class BaselineDefender:
    """
    基础防御策略
    
    特点：
    - 优先修复初始链路
    - 简单规则，无学习能力
    - 作为baseline对照
    """
    
    def __init__(
        self,
        max_repairs: int = 2,
        max_new_edges: int = 1
    ):
        """
        初始化基础防御器
        
        Args:
            max_repairs: 每轮最大修复次数
            max_new_edges: 每轮最大新增链路数
        """
        self.max_repairs = max_repairs
        self.max_new_edges = max_new_edges
        self.repaired_edges: Set[Tuple[str, str]] = set()
        self.name = "BaselineDefender"
    
    def select_actions(
        self,
        network_state: Dict[str, Any],
        initial_edges: List[Tuple[str, str]],
        **kwargs
    ) -> Dict[str, List[Tuple[str, str]]]:
        """
        选择防御动作
        
        Args:
            network_state: 当前网络状态
            initial_edges: 初始链路（可修复）
            
        Returns:
            {"repairs": [...], "new_edges": [...]}
        """
        active_edges = set(tuple(sorted(e)) for e in network_state.get("edges", []))
        
        actions = {"repairs": [], "new_edges": []}
        
        # 1. 修复初始链路（优先）
        for edge in initial_edges:
            sorted_edge = tuple(sorted([str(u) for u in edge]))
            if sorted_edge not in active_edges and len(actions["repairs"]) < self.max_repairs:
                actions["repairs"].append(sorted_edge)
        
        # 2. 添加新链路（如果还有余量）
        if len(actions["repairs"]) < self.max_repairs:
            # 计算应该新增多少链路
            remaining_slots = self.max_repairs - len(actions["repairs"])
            new_edge_slots = min(remaining_slots, self.max_new_edges)
            
            # 简单策略：为度数低的节点添加连接
            nodes = network_state.get("nodes", [])
            if len(nodes) >= 2:
                import random
                for _ in range(new_edge_slots):
                    u, v = random.sample(nodes, 2)
                    edge = tuple(sorted([str(u), str(v)]))
                    if edge not in active_edges and edge not in actions["new_edges"]:
                        actions["new_edges"].append(edge)
        
        logger.debug(f"基础防御选择: {actions}")
        return actions
    
    def execute(
        self,
        actions: Dict[str, List[Tuple[str, str]]],
        network_manager
    ) -> Dict[str, Any]:
        """
        执行防御
        
        Args:
            actions: 防御动作
            network_manager: 网络管理器
            
        Returns:
            防御结果
        """
        results = {
            "repairs": [],
            "new_edges": [],
            "failed_repairs": [],
            "failed_new_edges": []
        }
        
        # 执行修复
        for u, v in actions.get("repairs", []):
            if network_manager.add_edge(u, v):
                results["repairs"].append((u, v))
                self.repaired_edges.add((u, v))
            else:
                results["failed_repairs"].append((u, v))
        
        # 执行新增
        for u, v in actions.get("new_edges", []):
            if network_manager.add_edge(u, v):
                results["new_edges"].append((u, v))
            else:
                results["failed_new_edges"].append((u, v))
        
        logger.info(f"基础防御完成: 修复{len(results['repairs'])}条, 新增{len(results['new_edges'])}条")
        return results
    
    def reset(self):
        """重置"""
        self.repaired_edges.clear()
