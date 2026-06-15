"""
随机攻击策略（对照组1）
模拟传统随机攻击，作为LLM自适应攻击的对照
"""

import random
from typing import List, Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)


class RandomAttacker:
    """
    随机攻击策略
    
    特点：
    - 完全随机选择攻击目标
    - 无学习、无自适应
    - 作为baseline对照
    """
    
    def __init__(self, max_attacks: int = 2, seed: int = None):
        """
        初始化随机攻击器
        
        Args:
            max_attacks: 每轮最大攻击次数
            seed: 随机种子
        """
        self.max_attacks = max_attacks
        if seed is not None:
            random.seed(seed)
        
        self.name = "RandomAttacker"
    
    def select_targets(
        self,
        network_state: Dict[str, Any],
        **kwargs
    ) -> List[Tuple[str, str]]:
        """
        随机选择攻击目标
        
        Args:
            network_state: 当前网络状态
            
        Returns:
            攻击目标列表
        """
        edges = network_state.get("edges", [])
        
        if not edges:
            return []
        
        num_to_attack = min(self.max_attacks, len(edges))
        targets = random.sample(edges, num_to_attack)
        
        logger.debug(f"随机攻击选择: {targets}")
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
        
        logger.info(f"随机攻击完成: {len(results['attacked_edges'])}条链路")
        return results
