"""
网络鲁棒性指标计算
"""

import networkx as nx
import numpy as np
from typing import Dict, Any, List
import sys
import os
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'WenQuanYi Micro Hei', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False
try:
    for font_path in ['C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf']:
        if os.path.exists(font_path):
            fm.fontManager.addfont(font_path)
            plt.rcParams['font.family'] = fm.FontProperties(fname=font_path).get_name()
            break
except:
    pass

from core.network_manager import NetworkManager


class RobustnessMetrics:
    """网络鲁棒性指标计算器"""
    
    def __init__(self):
        self.history: List[Dict[str, float]] = []
    
    def calculate(self, network: NetworkManager) -> Dict[str, float]:
        """
        计算当前网络的所有指标
        
        Args:
            network: 网络管理器
            
        Returns:
            指标字典
        """
        G = network.graph
        
        if G.number_of_nodes() == 0:
            return self._empty_metrics()
        
        metrics = {
            "num_nodes": float(G.number_of_nodes()),
            "num_edges": float(G.number_of_edges()),
            "largest_cc_size": float(self._largest_connected_component_size(G)),
            "largest_cc_ratio": self._largest_connected_component_ratio(G, network.num_nodes),
            "avg_degree": self._average_degree(G),
            "degree_variance": self._degree_variance(G),
            "clustering_coeff": self._clustering_coefficient(G),
            "avg_path_length": self._average_shortest_path(G),
            "diameter": self._network_diameter(G),
            "degree_centralization": self._degree_centralization(G),
            "betweenness_centralization": self._betweenness_centralization(G),
            "efficiency": self._network_efficiency(G),
            "robustness_index": self._robustness_index(G, network.num_nodes)
        }
        
        self.history.append(metrics)
        return metrics
    
    def _empty_metrics(self) -> Dict[str, float]:
        """空网络指标"""
        return {
            "num_nodes": 0.0,
            "num_edges": 0.0,
            "largest_cc_size": 0.0,
            "largest_cc_ratio": 0.0,
            "avg_degree": 0.0,
            "degree_variance": 0.0,
            "clustering_coeff": 0.0,
            "avg_path_length": float('inf'),
            "diameter": 0.0,
            "degree_centralization": 0.0,
            "betweenness_centralization": 0.0,
            "efficiency": 0.0,
            "robustness_index": 0.0
        }
    
    def _largest_connected_component_size(self, G: nx.Graph) -> int:
        """最大连通分量大小"""
        if G.number_of_nodes() == 0:
            return 0
        if not nx.is_connected(G):
            return len(max(nx.connected_components(G), key=len))
        return G.number_of_nodes()
    
    def _largest_connected_component_ratio(self, G: nx.Graph, total_nodes: int) -> float:
        """最大连通分量占比"""
        if total_nodes == 0:
            return 0.0
        return self._largest_connected_component_size(G) / total_nodes
    
    def _average_degree(self, G: nx.Graph) -> float:
        """平均度数"""
        if G.number_of_nodes() == 0:
            return 0.0
        return sum(dict(G.degree()).values()) / G.number_of_nodes()
    
    def _degree_variance(self, G: nx.Graph) -> float:
        """度数方差"""
        degrees = [d for n, d in G.degree()]
        if len(degrees) == 0:
            return 0.0
        return float(np.var(degrees))
    
    def _clustering_coefficient(self, G: nx.Graph) -> float:
        """聚类系数"""
        if G.number_of_nodes() < 3:
            return 0.0
        return float(nx.average_clustering(G))
    
    def _average_shortest_path(self, G: nx.Graph) -> float:
        """平均最短路径"""
        if G.number_of_nodes() < 2:
            return float('inf')
        
        try:
            if nx.is_connected(G):
                return float(nx.average_shortest_path_length(G))
            else:
                largest_cc = max(nx.connected_components(G), key=len)
                subg = G.subgraph(largest_cc)
                if subg.number_of_nodes() > 1:
                    return float(nx.average_shortest_path_length(subg))
                return float('inf')
        except:
            return float('inf')
    
    def _network_diameter(self, G: nx.Graph) -> float:
        """网络直径"""
        if G.number_of_nodes() < 2:
            return 0.0
        
        try:
            if nx.is_connected(G):
                return float(nx.diameter(G))
            else:
                largest_cc = max(nx.connected_components(G), key=len)
                subg = G.subgraph(largest_cc)
                return float(nx.diameter(subg))
        except:
            return float('inf')
    
    def _degree_centralization(self, G: nx.Graph) -> float:
        """度中心化"""
        if G.number_of_nodes() <= 2:
            return 0.0
        
        try:
            degree_cent = nx.degree_centrality(G)
            max_degree = max(degree_cent.values())
            n = G.number_of_nodes()
            theoretical_max = (n - 1) * (n - 2) / (n - 1)
            if theoretical_max == 0:
                return 0.0
            return sum(max_degree - d for d in degree_cent.values()) / theoretical_max
        except:
            return 0.0
    
    def _betweenness_centralization(self, G: nx.Graph) -> float:
        """介数中心化"""
        if G.number_of_nodes() <= 2:
            return 0.0
        
        try:
            betweenness = nx.betweenness_centrality(G)
            max_between = max(betweenness.values())
            n = G.number_of_nodes()
            theoretical_max = (n - 1) * (n - 2) / 2
            if theoretical_max == 0:
                return 0.0
            return sum(max_between - b for b in betweenness.values()) / theoretical_max
        except:
            return 0.0
    
    def _network_efficiency(self, G: nx.Graph) -> float:
        """网络效率"""
        if G.number_of_nodes() < 2:
            return 0.0
        return float(nx.global_efficiency(G))
    
    def _robustness_index(self, G: nx.Graph, original_size: int) -> float:
        """
        综合鲁棒性指数
        综合考虑连通性、效率和结构完整性
        """
        if original_size == 0:
            return 0.0
        
        cc_ratio = self._largest_connected_component_ratio(G, original_size)
        efficiency = self._network_efficiency(G)
        clustering = self._clustering_coefficient(G)
        
        # 加权综合
        robustness = 0.5 * cc_ratio + 0.3 * efficiency + 0.2 * clustering
        return float(robustness)
    
    def get_history(self) -> List[Dict[str, float]]:
        """获取历史指标"""
        return self.history.copy()
    
    def clear_history(self):
        """清空历史"""
        self.history.clear()
    
    def plot_metrics(self, save_path: str = None):
        """绘制指标变化图"""
        import matplotlib.pyplot as plt
        
        if not self.history:
            print("无历史数据")
            return
        
        rounds = list(range(len(self.history)))
        
        # 选择要绘制的指标
        metrics_to_plot = [
            'largest_cc_ratio',
            'clustering_coeff',
            'robustness_index'
        ]
        
        # 指标中文名称映射
        metric_names = {
            'largest_cc_ratio': '最大连通分量比例',
            'clustering_coeff': '聚类系数',
            'robustness_index': '鲁棒性指数'
        }

        fig, axes = plt.subplots(len(metrics_to_plot), 1, figsize=(10, 8))

        for i, metric in enumerate(metrics_to_plot):
            values = [h.get(metric, 0) for h in self.history]
            axes[i].plot(rounds, values, marker='o')
            axes[i].set_title(metric_names.get(metric, metric))
            axes[i].set_xlabel('博弈轮次')
            axes[i].set_ylabel('数值')
            axes[i].grid(True)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path)
            print(f"图表已保存: {save_path}")
        else:
            plt.show()
