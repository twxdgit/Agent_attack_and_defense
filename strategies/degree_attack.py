"""
度数攻击策略（对照组2）
模拟传统蓄意攻击，优先攻击高度数节点相连的链路
"""

from typing import List, Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)


class DegreeAttacker:
    """
    度数攻击策略
    
    特点：
    - 优先攻击度数最高的节点
    - 策略固定，无学习能力
    - 模拟传统蓄意攻击
    """
    
    def __init__(self, max_attacks: int = 2):
        """
        初始化度数攻击器
        
        Args:
            max_attacks: 每轮最大攻击次数
        """
        self.max_attacks = max_attacks
        self.name = "DegreeAttacker"
    
    def select_targets(
        self,
        network_state: Dict[str, Any],
        **kwargs
    ) -> List[Tuple[str, str]]:
        """
        选择度数最高的链路进行攻击
        
        Args:
            network_state: 当前网络状态
            
        Returns:
            攻击目标列表
        """
        import networkx as nx
        
        # 获取图对象（如果提供）
        graph = kwargs.get("graph")
        
        if graph is None:
            # 如果没有图对象，从edges构建
            edges = network_state.get("edges", [])
            if not edges:
                return []
            
            # 创建临时图
            G = nx.Graph()
            for u, v in edges:
                G.add_edge(u, v)
        else:
            G = graph
        
        # 获取度数最高的节点
        degree_dict = dict(G.degree())
        sorted_nodes = sorted(degree_dict.keys(), key=lambda x: degree_dict[x], reverse=True)
        
        # 选择度数最高节点相连的边
        targets = []
        for node in sorted_nodes:
            for neighbor in G.neighbors(node):
                edge = tuple(sorted([node, neighbor]))
                if edge not in targets:
                    targets.append(edge)
                    if len(targets) >= self.max_attacks:
                        break
            if len(targets) >= self.max_attacks:
                break
        
        logger.debug(f"度数攻击选择: {targets}")
        return targets
    
    def execute(
        self,
        targets: List[Tuple[str, str]],
        network_manager
    ) -> Dict[str, Any]:
        """
        执行攻击
        
        Args:
            targets: 攻击目标
            network_manager: 网络管理器
            
        Returns:
            攻击结果
        """
        results = {
            "attacked_edges": [],
            "failed_edges": []
        }
        
        for u, v in targets:
            success = network_manager.remove_edge(u, v)
            if success:
                results["attacked_edges"].append((u, v))
            else:
                results["failed_edges"].append((u, v))
        
        logger.info(f"度数攻击完成: {len(results['attacked_edges'])}条链路")
        return results

    # --- 适配 GameEngine 接口 ---
    def decide_attack_targets(
        self,
        network_state: Dict[str, Any],
        **kwargs
    ) -> List[Tuple[str, str]]:
        return self.select_targets(network_state, **kwargs)

    def execute_attack(
        self,
        targets: List[Tuple[str, str]],
        network_manager
    ) -> Dict[str, Any]:
        return self.execute(targets, network_manager)
