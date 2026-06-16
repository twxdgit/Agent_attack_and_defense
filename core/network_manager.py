"""
网络管理器
负责网络的构建、修改、状态维护
"""

import networkx as nx
import random
from typing import List, Tuple, Dict, Optional, Set
from dataclasses import dataclass, field
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class NetworkState:
    """网络状态快照"""
    round_num: int
    nodes: Dict[str, bool]  # 节点存活状态
    edges: List[Tuple[str, str]]  # 当前活跃链路
    largest_cc_size: int  # 最大连通分量大小
    avg_shortest_path: float  # 平均最短路径
    clustering_coeff: float  # 聚类系数
    attack_history: List[Dict] = field(default_factory=list)
    defense_history: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "round_num": self.round_num,
            "num_nodes": len(self.nodes),
            "num_edges": len(self.edges),
            "largest_cc_size": self.largest_cc_size,
            "avg_shortest_path": self.avg_shortest_path,
            "clustering_coeff": self.clustering_coeff,
            "is_connected": len(self.edges) > 0 and self.largest_cc_size == len(self.nodes),
            "attack_history": self.attack_history,
            "defense_history": self.defense_history
        }


class NetworkManager:
    """网络管理器"""
    
    def __init__(
        self,
        num_nodes: int = 8,
        avg_degree: float = 3.0,
        seed: int = 42,
        network_type: str = "watts_strogatz",
        graph: Optional[nx.Graph] = None
    ):
        """
        初始化网络管理器
        
        Args:
            num_nodes: 节点数量（默认8个任务节点）
            avg_degree: 平均度数
            seed: 随机种子
            network_type: 网络类型
            graph: 外部传入的图（优先使用）
        """
        self.num_nodes = num_nodes
        self.avg_degree = avg_degree
        self.seed = seed
        self.network_type = network_type
        self.round_num = 0
        
        # 如果提供了图，优先使用
        if graph is not None:
            self.graph = graph.copy()
            self.num_nodes = graph.number_of_nodes()
        else:
            self.graph = self._build_initial_network()
        
        # 保存初始状态（统一转为字符串元组，避免 (0,1) vs ('0','1') 不匹配）
        self.initial_edges = [(str(u), str(v)) for u, v in self.graph.edges()]
        
        # 历史记录
        self.state_history: List[NetworkState] = []
        
        # 节点属性
        self.node_capabilities = {
            str(n): random.randint(1, 5) for n in self.graph.nodes()
        }
        
        logger.info(f"网络初始化完成：{self.num_nodes}个节点，{self.graph.number_of_edges()}条边")
    
    def _build_initial_network(self) -> nx.Graph:
        """构建初始网络"""
        random.seed(self.seed)
        
        if self.network_type == "watts_strogatz":
            # Watts-Strogatz小世界网络
            G = nx.watts_strogatz_graph(
                n=self.num_nodes,
                k=int(self.avg_degree),
                p=0.1,
                seed=self.seed
            )
        elif self.network_type == "barabasi_albert":
            # Barabasi-Albert无标度网络
            m = int(self.avg_degree / 2)
            G = nx.barabasi_albert_graph(n=self.num_nodes, m=m, seed=self.seed)
        elif self.network_type == "complete":
            # 完全图
            G = nx.complete_graph(self.num_nodes)
        elif self.network_type == "cycle":
            # 环形网络
            G = nx.cycle_graph(self.num_nodes)
        else:
            # 默认使用小世界网络
            G = nx.watts_strogatz_graph(
                n=self.num_nodes,
                k=int(self.avg_degree),
                p=0.1,
                seed=self.seed
            )
        
        # 确保网络连通
        if not nx.is_connected(G):
            components = list(nx.connected_components(G))
            for i in range(len(components) - 1):
                G.add_edge(
                    random.choice(list(components[i])),
                    random.choice(list(components[i + 1]))
                )
        
        return G
    
    def get_active_nodes(self) -> List[str]:
        """获取活跃节点列表"""
        return [str(n) for n in self.graph.nodes()]
    
    def get_active_edges(self) -> List[Tuple[str, str]]:
        """获取活跃链路列表"""
        return [(str(u), str(v)) for u, v in self.graph.edges()]
    
    def get_network_info(self) -> Dict:
        """获取网络基本信息"""
        info = {
            "num_nodes": self.graph.number_of_nodes(),
            "num_edges": self.graph.number_of_edges(),
            "edges": self.get_active_edges(),
            "nodes": self.get_active_nodes(),
        }
        
        if self.graph.number_of_nodes() > 0:
            info["is_connected"] = nx.is_connected(self.graph)
            info["num_components"] = nx.number_connected_components(self.graph)
            
            if nx.is_connected(self.graph):
                info["largest_cc_size"] = self.graph.number_of_nodes()
            else:
                largest_cc = max(nx.connected_components(self.graph), key=len)
                info["largest_cc_size"] = len(largest_cc)
        else:
            info["is_connected"] = False
            info["num_components"] = 0
            info["largest_cc_size"] = 0
        
        return info
    
    def remove_edge(self, u: str, v: str) -> bool:
        """
        移除链路

        Args:
            u, v: 链路两端节点（字符串或整数）

        Returns:
            是否成功移除
        """
        try:
            # NetworkX 使用整数节点ID，需转换；外部接口统一用字符串
            u_int = int(u)
            v_int = int(v)
            if self.graph.has_edge(u_int, v_int):
                self.graph.remove_edge(u_int, v_int)
                logger.debug(f"移除链路: {u_int} <--> {v_int}")
                return True
        except (ValueError, nx.NetworkXError):
            pass
        return False

    def add_edge(self, u: str, v: str) -> bool:
        """
        添加链路

        Args:
            u, v: 链路两端节点（字符串或整数）

        Returns:
            是否成功添加
        """
        try:
            # NetworkX 使用整数节点ID，需转换；外部接口统一用字符串
            u_int = int(u)
            v_int = int(v)
            if not self.graph.has_edge(u_int, v_int) and u_int != v_int:
                self.graph.add_edge(u_int, v_int)
                logger.debug(f"添加链路: {u_int} <--> {v_int}")
                return True
        except (ValueError, nx.NetworkXError):
            pass
        return False
    
    def is_network_paralyzed(self, threshold: float = 0.3) -> bool:
        """
        判断网络是否瘫痪
        
        Args:
            threshold: 瘫痪阈值（最大连通分量占比）
            
        Returns:
            网络是否瘫痪
        """
        if self.graph.number_of_nodes() == 0:
            return True
        
        largest_cc = max(nx.connected_components(self.graph), key=len)
        ratio = len(largest_cc) / self.num_nodes
        
        return ratio < threshold
    
    def get_critical_edges(self, top_k: int = 5) -> List[Tuple[str, str]]:
        """
        获取关键链路（基于介数中心性）
        
        Returns:
            关键链路列表，按重要性排序
        """
        if self.graph.number_of_edges() == 0:
            return []
        
        try:
            betweenness = nx.edge_betweenness_centrality(self.graph)
            sorted_edges = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)
            return [(str(u), str(v)) for (u, v), _ in sorted_edges[:top_k]]
        except:
            return []
    
    def get_critical_nodes(self, top_k: int = 3) -> List[str]:
        """
        获取关键节点（基于度中心性和介数中心性）
        """
        if self.graph.number_of_nodes() == 0:
            return []
        
        degree_cent = nx.degree_centrality(self.graph)
        betweenness = nx.betweenness_centrality(self.graph)
        
        max_degree = max(degree_cent.values()) if degree_cent else 1
        max_between = max(betweenness.values()) if betweenness else 1
        
        scores = {
            str(node): degree_cent[node] / max_degree + betweenness[node] / max_between
            for node in self.graph.nodes()
        }
        
        sorted_nodes = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [node for node, _ in sorted_nodes[:top_k]]
    
    def save_state(self) -> NetworkState:
        """保存当前网络状态"""
        state = NetworkState(
            round_num=self.round_num,
            nodes={str(n): True for n in self.graph.nodes()},
            edges=[(str(u), str(v)) for u, v in self.graph.edges()],
            largest_cc_size=self._calc_largest_cc_size(),
            avg_shortest_path=self._calc_avg_shortest_path(),
            clustering_coeff=nx.average_clustering(self.graph)
        )
        self.state_history.append(state)
        return state
    
    def _calc_largest_cc_size(self) -> int:
        """计算最大连通分量大小"""
        if self.graph.number_of_nodes() == 0:
            return 0
        if not nx.is_connected(self.graph):
            largest_cc = max(nx.connected_components(self.graph), key=len)
            return len(largest_cc)
        return self.graph.number_of_nodes()
    
    def _calc_avg_shortest_path(self) -> float:
        """计算平均最短路径"""
        if self.graph.number_of_nodes() < 2:
            return float('inf')
        
        try:
            if nx.is_connected(self.graph):
                return nx.average_shortest_path_length(self.graph)
            else:
                largest_cc = max(nx.connected_components(self.graph), key=len)
                subg = self.graph.subgraph(largest_cc)
                if subg.number_of_nodes() > 1:
                    return nx.average_shortest_path_length(subg)
                return float('inf')
        except:
            return float('inf')
    
    def reset(self):
        """重置网络到初始状态"""
        self.graph = self._build_initial_network()
        self.round_num = 0
        self.state_history.clear()
    
    def to_json(self) -> str:
        """导出网络为JSON格式"""
        data = {
            "num_nodes": self.num_nodes,
            "num_edges": self.graph.number_of_edges(),
            "edges": [[u, v] for u, v in self.graph.edges()],
            "initial_edges": [[u, v] for u, v in self.initial_edges],
            "state_history": [s.to_dict() for s in self.state_history]
        }
        return json.dumps(data, indent=2)
    
    def __repr__(self):
        return f"NetworkManager(nodes={self.num_nodes}, edges={self.graph.number_of_edges()})"
