"""
可视化模块
用于绘制网络结构和指标变化
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.font_manager as fm
import networkx as nx
from typing import List, Tuple, Dict, Any, Optional
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.network_manager import NetworkManager

# 配置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'WenQuanYi Micro Hei', 'Songti SC', 'Heiti SC', 'Arial Unicode MS', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

# 尝试加载系统字体
try:
    # Windows 常见中文字体
    font_paths = [
        'C:/Windows/Fonts/msyh.ttc',      # 微软雅黑
        'C:/Windows/Fonts/simhei.ttf',    # 黑体
        'C:/Windows/Fonts/simsun.ttc',    # 宋体
    ]
    for font_path in font_paths:
        if os.path.exists(font_path):
            fm.fontManager.addfont(font_path)
            font_prop = fm.FontProperties(fname=font_path)
            plt.rcParams['font.family'] = font_prop.get_name()
            break
except:
    pass


class GameVisualizer:
    """游戏可视化器"""
    
    def __init__(
        self,
        figsize: tuple = (12, 10),
        save_dir: str = "data/results/frames"
    ):
        """
        初始化可视化器
        
        Args:
            figsize: 图形大小
            save_dir: 帧保存目录
        """
        self.figsize = figsize
        self.save_dir = save_dir
        self.frames: List[Dict] = []
        
        # 创建保存目录
        os.makedirs(save_dir, exist_ok=True)
    
    def update(
        self,
        network: NetworkManager,
        round_num: int,
        attack_targets: List[Tuple],
        repair_targets: List[Tuple],
        new_edges: List[Tuple],
        save_frame: bool = True
    ):
        """
        更新可视化状态
        
        Args:
            network: 网络管理器
            round_num: 当前轮次
            attack_targets: 攻击目标
            repair_targets: 修复目标
            new_edges: 新增链路
            save_frame: 是否保存帧
        """
        frame = {
            "round": round_num,
            "network": network,
            "attack_targets": attack_targets,
            "repair_targets": repair_targets,
            "new_edges": new_edges
        }
        self.frames.append(frame)
        
        if save_frame:
            self._save_frame(frame)
    
    def _save_frame(self, frame: Dict):
        """保存单帧图像"""
        plt.figure(figsize=self.figsize)
        self._draw_network(frame)
        plt.tight_layout()
        
        filename = os.path.join(self.save_dir, f"frame_{frame['round']:03d}.png")
        plt.savefig(filename, dpi=100, bbox_inches='tight')
        plt.close()
    
    def _draw_network(self, frame: Dict):
        """绘制网络"""
        network = frame["network"]
        attack_targets = set(tuple(sorted(e)) for e in frame["attack_targets"])
        repair_targets = set(tuple(sorted(e)) for e in frame["repair_targets"])
        new_edges = set(tuple(sorted(e)) for e in frame["new_edges"])
        
        G = network.graph
        
        if G.number_of_nodes() == 0:
            plt.text(0.5, 0.5, "网络为空", ha='center', va='center', fontsize=20)
            return
        
        # 使用spring布局
        pos = nx.spring_layout(G, seed=42, k=2)
        
        # 分类边
        normal_edges = []
        attack_edges = []
        repair_edges = []
        new_edge_list = []
        
        for u, v in G.edges():
            edge = tuple(sorted([str(u), str(v)]))
            if edge in attack_targets:
                attack_edges.append((u, v))
            elif edge in repair_targets:
                repair_edges.append((u, v))
            elif edge in new_edges:
                new_edge_list.append((u, v))
            else:
                normal_edges.append((u, v))
        
        # 绘制节点
        node_colors = []
        for node in G.nodes():
            degree = G.degree(node)
            node_colors.append(plt.cm.Blues(0.3 + 0.5 * degree / max(dict(G.degree()).values())))
        
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, 
                              node_size=500, alpha=0.8)
        nx.draw_networkx_labels(G, pos, font_size=8, font_weight='bold')
        
        # 绘制各类边
        if normal_edges:
            nx.draw_networkx_edges(G, pos, edgelist=normal_edges,
                                 edge_color='gray', width=1.5, alpha=0.6)
        if attack_edges:
            nx.draw_networkx_edges(G, pos, edgelist=attack_edges,
                                 edge_color='red', width=3, alpha=0.9)
        if repair_edges:
            nx.draw_networkx_edges(G, pos, edgelist=repair_edges,
                                 edge_color='green', width=3, alpha=0.9)
        if new_edge_list:
            nx.draw_networkx_edges(G, pos, edgelist=new_edge_list,
                                 edge_color='blue', width=2.5, style='dashed', alpha=0.9)
        
        # 添加图例
        legend_elements = [
            mpatches.Patch(color='gray', alpha=0.6, label='正常链路'),
            mpatches.Patch(color='red', label='被攻击'),
            mpatches.Patch(color='green', label='已修复'),
            mpatches.Patch(color='blue', label='新增链路')
        ]
        plt.legend(handles=legend_elements, loc='upper right')
        
        # 标题
        info = network.get_network_info()
        title = f"第 {frame['round']} 轮 - 节点:{info['num_nodes']} 链路:{info['num_edges']} 连通分量:{info.get('largest_cc_size', 0)}"
        plt.title(title, fontsize=14, fontweight='bold')
        plt.axis('off')
    
    def plot_metrics_overview(self, metrics_curves: Dict[str, List], save_path: str = None):
        """
        绘制指标变化概览图
        
        Args:
            metrics_curves: 指标曲线数据
            save_path: 保存路径
        """
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        rounds = list(range(len(metrics_curves.get('num_edges', []))))
        
        # 1. 链路数变化
        ax = axes[0, 0]
        if 'num_edges' in metrics_curves:
            ax.plot(rounds, metrics_curves['num_edges'], 'b-o', linewidth=2)
            ax.set_xlabel('博弈轮次')
            ax.set_ylabel('链路数量')
            ax.set_title('链路数量随时间变化')
            ax.grid(True, alpha=0.3)
        
        # 2. 最大连通分量比例
        ax = axes[0, 1]
        if 'largest_cc_ratio' in metrics_curves:
            ax.plot(rounds, metrics_curves['largest_cc_ratio'], 'g-o', linewidth=2)
            ax.set_xlabel('博弈轮次')
            ax.set_ylabel('比例')
            ax.set_title('最大连通分量比例变化')
            ax.grid(True, alpha=0.3)
            ax.axhline(y=0.3, color='r', linestyle='--', label='网络瘫痪阈值')
            ax.legend()
        
        # 3. 聚类系数
        ax = axes[1, 0]
        if 'clustering_coeff' in metrics_curves:
            ax.plot(rounds, metrics_curves['clustering_coeff'], 'm-o', linewidth=2)
            ax.set_xlabel('博弈轮次')
            ax.set_ylabel('系数')
            ax.set_title('聚类系数变化')
            ax.grid(True, alpha=0.3)
        
        # 4. 鲁棒性指数
        ax = axes[1, 1]
        if 'robustness_index' in metrics_curves:
            ax.plot(rounds, metrics_curves['robustness_index'], 'c-o', linewidth=2)
            ax.set_xlabel('博弈轮次')
            ax.set_ylabel('指数')
            ax.set_title('网络鲁棒性指数变化')
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"指标图已保存: {save_path}")
        else:
            plt.show()
    
    def plot_comparison(
        self,
        results_list: List[Dict],
        labels: List[str],
        save_path: str = None
    ):
        """
        绘制多组实验对比图
        
        Args:
            results_list: 实验结果列表
            labels: 实验标签
            save_path: 保存路径
        """
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        # 左图：链路数对比
        ax = axes[0]
        for result, label in zip(results_list, labels):
            metrics = result.get('metrics_curves', {})
            if 'num_edges' in metrics:
                rounds = list(range(len(metrics['num_edges'])))
                ax.plot(rounds, metrics['num_edges'], label=label, linewidth=2)
        
        ax.set_xlabel('博弈轮次')
        ax.set_ylabel('链路数量')
        ax.set_title('链路数量对比')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 右图：鲁棒性指数对比
        ax = axes[1]
        for result, label in zip(results_list, labels):
            metrics = result.get('metrics_curves', {})
            if 'robustness_index' in metrics:
                rounds = list(range(len(metrics['robustness_index'])))
                ax.plot(rounds, metrics['robustness_index'], label=label, linewidth=2)
        
        ax.set_xlabel('博弈轮次')
        ax.set_ylabel('鲁棒性指数')
        ax.set_title('鲁棒性指数对比')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"对比图已保存: {save_path}")
        else:
            plt.show()
    
    def save_animation_summary(self):
        """保存动画摘要信息"""
        summary = {
            "total_frames": len(self.frames),
            "rounds": [f["round"] for f in self.frames]
        }
        
        import json
        summary_path = os.path.join(self.save_dir, "summary.json")
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"动画摘要已保存: {summary_path}")
    
    def reset(self):
        """重置可视化器"""
        self.frames.clear()
    
    def show_frame(self, frame_num: int):
        """显示指定帧"""
        if 0 <= frame_num < len(self.frames):
            plt.figure(figsize=self.figsize)
            self._draw_network(self.frames[frame_num])
            plt.tight_layout()
            plt.show()
