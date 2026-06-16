"""
防御智能体
具备自适应修复和加固能力的网络防御者
"""

import random
import re
import json
from typing import List, Tuple, Dict, Any, Optional, Set

from .base_agent import BaseGameAgent


class DefenderAgent(BaseGameAgent):
    """
    防御智能体
    
    行为模式：
    1. 监测网络受损状态
    2. 识别需要修复的关键链路
    3. 优化网络拓扑结构
    4. 执行防御操作并记录效果
    """
    
    def __init__(
        self,
        max_repairs_per_round: int = 2,
        max_new_edges_per_round: int = 1,
        use_llm: bool = True,
        model_provider: Optional[Any] = None
    ):
        """
        初始化防御智能体
        
        Args:
            max_repairs_per_round: 每轮最大修复次数
            max_new_edges_per_round: 每轮最大新增链路数
            use_llm: 是否使用大模型
            model_provider: 模型提供商
        """
        self.max_repairs_per_round = max_repairs_per_round
        self.max_new_edges_per_round = max_new_edges_per_round
        
        super().__init__(
            name="Defender",
            role_description=self._get_role_description(),
            model_provider=model_provider,
            use_llm=use_llm
        )
        
        # 记录修复过的链路
        self.repaired_edges: Set[Tuple[str, str]] = set()
        
        # 新增的链路
        self.new_edges: List[Tuple[str, str]] = []
    
    def _get_role_description(self) -> str:
        """获取角色描述"""
        return f"""你是网络防御智能体，代号"铁壁"。

你的目标是维护网络的连通性和任务执行能力，在有限资源下最大化防御效果。

能力限制：
- 每轮最多修复{self.max_repairs_per_round}条被破坏的链路
- 每轮最多新增{self.max_new_edges_per_round}条防护链路

防御策略：
1. 优先修复被频繁攻击的关键链路
2. 优先保护核心节点，添加旁路连接
3. 优化网络拓扑，提高整体抗毁性
4. 记录每次防御的效果，用于后续优化

决策格式（JSON）：
{{
    "reasoning": "你的思考过程",
    "repairs": [["node1", "node2"], ...],     // 修复目标
    "new_edges": [["node3", "node4"], ...],   // 新增链路
    "confidence": 0.8
}}

请基于当前网络状态和历史记忆，做出最优防御决策。"""
    
    def _build_system_prompt(self) -> str:
        return self._get_role_description()
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """格式化上下文"""
        network_info = context.get("network_info", {})
        attack_history = self.memory.get_recent(10)
        
        prompt = f"""=== 当前网络状态 ===
- 活跃节点数：{network_info.get('num_nodes', 0)}
- 活跃链路数：{network_info.get('num_edges', 0)}
- 网络是否连通：{network_info.get('is_connected', False)}

=== 当前活跃链路 ===
{self._format_edges(network_info.get('edges', []))}

=== 关键节点 ===
{', '.join(context.get('critical_nodes', []))}

=== 初始链路（可修复）===
{self._format_edges(context.get('initial_edges', []))}

=== 最近攻击记录 ===
{self._format_attacks(attack_history)}

=== 已被修复的链路 ===
{self._format_edges([list(e) for e in self.repaired_edges])}

请做出防御决策："""
        return prompt
    
    def _format_edges(self, edges: List) -> str:
        if not edges:
            return "（无）"
        return "\n".join([f"  - {e[0]} <--> {e[1]}" for e in edges[:10]])
    
    def _format_attacks(self, attacks: List[Dict]) -> str:
        if not attacks:
            return "（无）"
        lines = []
        for i, entry in enumerate(attacks[-5:], 1):
            content = entry.get("content", {})
            if isinstance(content, dict):
                targets = content.get("edge", "unknown")
                round_num = content.get("round", "?")
            else:
                targets = str(content)
                round_num = "?"
            lines.append(f"{i}. 第{round_num}轮攻击：{targets}")
        return "\n".join(lines)
    
    def decide_defense_actions(
        self,
        network_state: Dict[str, Any],
        initial_edges: List[Tuple],
        use_llm: Optional[bool] = None
    ) -> Dict[str, List[Tuple[str, str]]]:
        """
        决定防御动作
        
        Returns:
            {"repairs": [...], "new_edges": [...]}
        """
        if use_llm is None:
            use_llm = self.use_llm
        
        active_edges = set(tuple(sorted(e)) for e in network_state.get("edges", []))
        critical_nodes = network_state.get("critical_nodes", [])
        attack_history = self.memory.get_recent(10)

        actions = {"repairs": [], "new_edges": []}

        # 1. 修复被攻击过的初始链路（统一转字符串避免 (0,1) vs ('0','1') 不匹配）
        for edge in initial_edges:
            sorted_edge = tuple(sorted([str(n) for n in edge]))
            if sorted_edge not in active_edges and len(actions["repairs"]) < self.max_repairs_per_round:
                actions["repairs"].append(sorted_edge)
        
        # 2. 如果需要增加新链路
        if len(actions["new_edges"]) < self.max_new_edges_per_round:
            new_edges = self._find_new_edge_candidates(
                active_edges,
                critical_nodes,
                network_state.get("nodes", [])
            )
            actions["new_edges"] = new_edges[:self.max_new_edges_per_round]
        
        # 3. 使用大模型优化决策
        if use_llm and (len(actions["repairs"]) < self.max_repairs_per_round or 
                        len(actions["new_edges"]) < self.max_new_edges_per_round):
            context = {
                "network_info": network_state,
                "attack_history": attack_history,
                "critical_nodes": critical_nodes,
                "initial_edges": initial_edges,
                "planned_repairs": actions["repairs"],
                "planned_new_edges": actions["new_edges"]
            }
            
            llm_actions = self._get_llm_suggestions(context, active_edges)
            actions["repairs"].extend(llm_actions.get("repairs", []))
            actions["new_edges"].extend(llm_actions.get("new_edges", []))
        
        # 去重
        actions["repairs"] = list(set(actions["repairs"]))[:self.max_repairs_per_round]
        actions["new_edges"] = list(set(actions["new_edges"]))[:self.max_new_edges_per_round]
        
        return actions
    
    def _find_new_edge_candidates(
        self,
        active_edges: List,
        critical_nodes: List[str],
        all_nodes: List[str]
    ) -> List[Tuple[str, str]]:
        """寻找可以新增的链路候选"""
        active_set = set(tuple(sorted(e)) for e in active_edges)
        candidates = []
        
        # 策略：为核心节点添加旁路连接
        for node in critical_nodes[:3]:
            for other in all_nodes:
                if other != node:
                    edge = tuple(sorted([node, other]))
                    if edge not in active_set and edge not in candidates:
                        candidates.append(edge)
        
        # 如果还不够，随机选择
        while len(candidates) < self.max_new_edges_per_round and all_nodes:
            u, v = random.sample(all_nodes, 2)
            edge = tuple(sorted([u, v]))
            if edge not in active_set and edge not in candidates:
                candidates.append(edge)
        
        return candidates
    
    def _get_llm_suggestions(
        self,
        context: Dict,
        active_edges: List
    ) -> Dict[str, List[Tuple]]:
        """获取大模型建议"""
        response = self.think(context)
        active_set = set(tuple(sorted(e)) for e in active_edges)
        
        try:
            # 尝试提取JSON
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            json_match = re.search(json_pattern, response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                repairs = []
                for e in data.get("repairs", []):
                    if isinstance(e, list) and len(e) == 2:
                        edge = tuple(sorted(e))
                        repairs.append(edge)
                
                new_edges = []
                for e in data.get("new_edges", []):
                    if isinstance(e, list) and len(e) == 2:
                        new_edges.append(tuple(sorted(e)))
                
                return {"repairs": repairs, "new_edges": new_edges}
        except:
            pass
        
        return {"repairs": [], "new_edges": []}
    
    def execute_defense(
        self,
        actions: Dict[str, List[Tuple[str, str]]],
        network_manager
    ) -> Dict[str, Any]:
        """
        执行防御
        
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
                self.remember(
                    "edge_repaired",
                    {"edge": (u, v), "round": getattr(network_manager, 'round_num', 0)}
                )
            else:
                results["failed_repairs"].append((u, v))
        
        # 执行新增链路
        for u, v in actions.get("new_edges", []):
            if network_manager.add_edge(u, v):
                results["new_edges"].append((u, v))
                self.new_edges.append((u, v))
                self.remember(
                    "edge_added",
                    {"edge": (u, v), "round": getattr(network_manager, 'round_num', 0)}
                )
            else:
                results["failed_new_edges"].append((u, v))
        
        return results
    
    def _rule_based_think(self, context: Dict[str, Any]) -> str:
        """基于规则的思考（不使用LLM时）"""
        # 简单策略：修复尽可能多的链路
        initial_edges = context.get("initial_edges", [])
        active_edges = set(tuple(sorted(e)) for e in context.get("network_info", {}).get("edges", []))
        
        repairs = []
        for edge in initial_edges[:self.max_repairs_per_round]:
            sorted_edge = tuple(sorted(edge))
            if sorted_edge not in active_edges:
                repairs.append(list(sorted_edge))
        
        return json.dumps({
            "reasoning": "基于规则的简单策略：修复初始链路",
            "repairs": repairs,
            "new_edges": [],
            "confidence": 0.6
        })
    
    def reset(self):
        """重置防御智能体"""
        super().reset()
        self.repaired_edges.clear()
        self.new_edges.clear()
