"""
攻击智能体
具备自适应学习能力的网络攻击者
"""

import random
import re
import json
from typing import List, Tuple, Dict, Any, Optional

from .base_agent import BaseGameAgent


class AttackerAgent(BaseGameAgent):
    """
    攻击智能体
    
    行为模式：
    1. 分析当前网络状态
    2. 基于历史经验评估攻击目标价值
    3. 选择最优攻击策略
    4. 执行攻击并记录效果
    """
    
    def __init__(
        self,
        max_attacks_per_round: int = 2,
        use_llm: bool = True,
        model_provider: Optional[Any] = None
    ):
        """
        初始化攻击智能体
        
        Args:
            max_attacks_per_round: 每轮最大攻击次数
            use_llm: 是否使用大模型
            model_provider: 模型提供商
        """
        self.max_attacks_per_round = max_attacks_per_round
        
        super().__init__(
            name="Attacker",
            role_description=self._get_role_description(),
            model_provider=model_provider,
            use_llm=use_llm
        )
        
        # 攻击历史记录
        self.attack_history: List[Dict] = []
        
        # 攻击效果评估
        self.edge_effectiveness: Dict[Tuple[str, str], float] = {}
    
    def _get_role_description(self) -> str:
        """获取角色描述"""
        return f"""你是网络攻击智能体。

你的目标是在有限的攻击次数内，最大化破坏网络的连通性和任务执行能力。

能力限制：
- 每轮最多攻击{self.max_attacks_per_round}条链路
- 每次攻击必须选择当前网络中存在的链路

攻击策略：
1. 分析网络结构，识别关键节点和链路
2. 优先攻击那些被修复过的链路（防御方的弱点）
3. 优先攻击核心节点之间的连接
4. 记录每次攻击的效果，用于后续策略优化

决策格式（JSON）：
{{
    "reasoning": "你的思考过程",
    "targets": [["node1", "node2"], ...],  // 攻击目标列表
    "confidence": 0.8  // 决策置信度
}}

请基于当前网络状态和历史记忆，做出最优攻击决策。"""
    
    def _build_system_prompt(self) -> str:
        return self._get_role_description()
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """格式化上下文"""
        network_info = context.get("network_info", {})
        recent_history = self.memory.get_recent(5)
        
        prompt = f"""=== 当前网络状态 ===
- 活跃节点数：{network_info.get('num_nodes', 0)}
- 活跃链路数：{network_info.get('num_edges', 0)}
- 网络是否连通：{network_info.get('is_connected', False)}
- 连通分量数：{network_info.get('num_components', 0)}

=== 当前活跃链路 ===
{self._format_edges(network_info.get('edges', []))}

=== 关键链路分析 ===
{self._format_edges(context.get('critical_edges', []))}

=== 关键节点 ===
{', '.join(context.get('critical_nodes', []))}

=== 最近攻击历史 ===
{self._format_history(recent_history)}

请做出攻击决策："""
        return prompt
    
    def _format_edges(self, edges: List) -> str:
        """格式化链路列表"""
        if not edges:
            return "（无）"
        return "\n".join([f"  - {e[0]} <--> {e[1]}" for e in edges[:10]])
    
    def _format_history(self, history: List[Dict]) -> str:
        """格式化历史记录"""
        if not history:
            return "（无历史记录）"
        
        lines = []
        for i, entry in enumerate(history[-5:], 1):
            action = entry.get("type", "")
            content = entry.get("content", "")
            lines.append(f"{i}. {action}: {content}")
        return "\n".join(lines)
    
    def decide_attack_targets(
        self,
        network_state: Dict[str, Any],
        use_llm: Optional[bool] = None
    ) -> List[Tuple[str, str]]:
        """
        决定攻击目标
        
        Args:
            network_state: 当前网络状态
            use_llm: 是否使用大模型决策
            
        Returns:
            攻击目标列表 [(u, v), ...]
        """
        if use_llm is None:
            use_llm = self.use_llm
        
        active_edges = network_state.get("edges", [])
        critical_edges = network_state.get("critical_edges", [])
        recent_history = self.memory.get_recent(5)
        
        if not active_edges:
            return []
        
        # 优先攻击关键链路
        priority_targets = []
        for edge in critical_edges:
            if edge in active_edges:
                priority_targets.append(edge)
        
        # 如果关键链路被修复过，增加优先级
        repaired_edges = self._get_recently_repaired_edges()
        for edge in repaired_edges:
            if edge in active_edges and edge not in priority_targets:
                priority_targets.insert(0, edge)
        
        # 限制攻击数量
        num_to_attack = min(self.max_attacks_per_round, len(active_edges))
        
        if use_llm and len(priority_targets) < num_to_attack:
            # 使用大模型补充选择
            context = {
                "network_info": network_state,
                "recent_history": recent_history,
                "critical_edges": critical_edges,
                "priority_targets": priority_targets
            }
            
            response = self.think(context)
            additional_targets = self._parse_llm_response(response, active_edges)
            priority_targets.extend(additional_targets)
        
        # 去重并限制数量
        final_targets = []
        for t in priority_targets:
            if t not in final_targets and len(final_targets) < num_to_attack:
                final_targets.append(t)
        
        # 如果还不够，随机选择
        while len(final_targets) < num_to_attack:
            remaining = [e for e in active_edges if e not in final_targets]
            if not remaining:
                break
            final_targets.append(random.choice(remaining))
        
        return final_targets[:num_to_attack]
    
    def _parse_llm_response(self, response: str, available_edges: List[Tuple]) -> List[Tuple]:
        """解析大模型回复，提取攻击目标"""
        try:
            # 尝试提取JSON
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*"targets"[^{}]*(?:\[[^\]]*\])?[^{}]*\}', 
                                   response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                targets = data.get("targets", [])
                result = []
                for t in targets:
                    if isinstance(t, list) and len(t) == 2:
                        edge = tuple(sorted(t))
                        if edge in available_edges:
                            result.append(edge)
                return result
        except:
            pass
        
        return []
    
    def _get_recently_repaired_edges(self) -> List[Tuple[str, str]]:
        """获取最近被修复过的链路"""
        repaired = []
        for entry in self.memory.get_by_type("edge_repaired"):
            content = entry.get("content", {})
            if isinstance(content, dict):
                edge = content.get("edge")
                if edge:
                    repaired.append(tuple(edge))
            elif isinstance(content, tuple):
                repaired.append(content)
        return repaired
    
    def execute_attack(
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
            "failed_edges": [],
            "effects": {}
        }
        
        for u, v in targets:
            success = network_manager.remove_edge(u, v)
            if success:
                results["attacked_edges"].append((u, v))
                self.remember(
                    "edge_attacked",
                    {"edge": (u, v), "round": getattr(network_manager, 'round_num', 0)},
                    metadata={"timestamp": "now"}
                )
                self.attack_history.append({
                    "edge": (u, v),
                    "round": getattr(network_manager, 'round_num', 0)
                })
            else:
                results["failed_edges"].append((u, v))
        
        # 计算攻击效果
        results["effects"] = self._calculate_effects(
            results["attacked_edges"],
            network_manager
        )
        
        return results
    
    def _calculate_effects(
        self,
        attacked_edges: List[Tuple],
        network_manager
    ) -> Dict[str, float]:
        """计算攻击效果"""
        info = network_manager.get_network_info()
        
        return {
            "edges_removed": len(attacked_edges),
            "components_before": info.get("num_components", 1),
            "largest_cc_size": info.get("largest_cc_size", 0)
        }
    
    def _rule_based_think(self, context: Dict[str, Any]) -> str:
        """基于规则的思考（不使用LLM时）"""
        network_info = context.get("network_info", {})
        critical_edges = context.get("critical_edges", [])
        
        # 简单策略：选择关键链路
        if critical_edges:
            targets = critical_edges[:self.max_attacks_per_round]
            return json.dumps({
                "reasoning": "基于规则的简单策略：攻击关键链路",
                "targets": [list(t) for t in targets],
                "confidence": 0.7
            })
        
        return json.dumps({
            "reasoning": "无可用关键链路，选择随机链路",
            "targets": [],
            "confidence": 0.5
        })
    
    def reset(self):
        """重置攻击智能体"""
        super().reset()
        self.attack_history.clear()
        self.edge_effectiveness.clear()
