"""
Facebook社交网络数据加载器
数据来源：SNAP Stanford
下载地址：https://snap.stanford.edu/data/ego-Facebook.html
"""

import os
import random
from typing import Tuple, Optional, Dict, Any
import logging

import networkx as nx

logger = logging.getLogger(__name__)


class FacebookDataLoader:
    """Facebook社交网络数据加载器"""
    
    DATA_URL = "https://snap.stanford.edu/data/facebook_combined.txt.gz"
    
    def __init__(self, data_dir: str = "data/raw"):
        self.data_dir = data_dir
        self.data_file = os.path.join(data_dir, "facebook_combined.txt")
        self.gz_file = self.data_file + ".gz"
    
    def load_full_network(self) -> nx.Graph:
        """
        加载完整Facebook网络
        
        Returns:
            NetworkX Graph对象
            - 节点：Facebook用户ID
            - 边：双向好友关系
        """
        if not os.path.exists(self.data_file):
            logger.info("数据文件不存在，开始下载...")
            self._download_data()
        
        # 读取边列表，构建无向图
        G = nx.read_edgelist(
            self.data_file,
            comments='#',
            delimiter=' ',
            create_using=nx.Graph(),
            nodetype=int
        )
        
        logger.info(f"加载完成：{G.number_of_nodes()} 个节点，{G.number_of_edges()} 条边")
        return G
    
    def load_subgraph(
        self,
        G: nx.Graph,
        center_node: Optional[int] = None,
        num_nodes: int = 100,
        radius: int = 2
    ) -> nx.Graph:
        """
        提取核心子图用于博弈实验
        
        Args:
            G: 完整网络
            center_node: 中心节点（默认选择度数最高的节点）
            num_nodes: 目标节点数
            radius: 扩展半径（从中心节点出发）
            
        Returns:
            子图
        """
        if center_node is None:
            # 自动选择度数最高的节点作为中心
            degrees = dict(G.degree())
            center_node = max(degrees, key=degrees.get)
        
        # 收集半径内的节点
        nodes_in_radius = {center_node}
        current_frontier = {center_node}
        
        for _ in range(radius):
            next_frontier = set()
            for node in current_frontier:
                if node in G:
                    next_frontier.update(G.neighbors(node))
            nodes_in_radius.update(next_frontier)
            current_frontier = next_frontier - nodes_in_radius
            
            if len(nodes_in_radius) >= num_nodes:
                break
        
        # 如果还不够，随机补充
        if len(nodes_in_radius) < num_nodes:
            remaining = set(G.nodes()) - nodes_in_radius
            if remaining:
                additional = set(random.sample(
                    list(remaining), 
                    min(num_nodes - len(nodes_in_radius), len(remaining))
                ))
                nodes_in_radius.update(additional)
        
        # 构建子图
        nodes_list = list(nodes_in_radius)[:num_nodes]
        subgraph = G.subgraph(nodes_list).copy()
        
        # 如果子图不连通，提取最大连通分量
        if not nx.is_connected(subgraph):
            largest_cc = max(nx.connected_components(subgraph), key=len)
            subgraph = subgraph.subgraph(largest_cc).copy()
            logger.info(f"提取最大连通分量：{subgraph.number_of_nodes()} 个节点")
        
        logger.info(f"子图提取：{subgraph.number_of_nodes()} 个节点，{subgraph.number_of_edges()} 条边")
        return subgraph
    
    def _download_data(self):
        """下载数据集"""
        try:
            import urllib.request
            
            os.makedirs(self.data_dir, exist_ok=True)
            
            logger.info(f"正在下载数据集...")
            logger.info(f"URL: {self.DATA_URL}")
            
            urllib.request.urlretrieve(self.DATA_URL, self.gz_file)
            
            # 解压
            import gzip
            with gzip.open(self.gz_file, 'rb') as f_in:
                with open(self.data_file, 'wb') as f_out:
                    f_out.write(f_in.read())
            
            # 删除压缩包
            if os.path.exists(self.gz_file):
                os.remove(self.gz_file)
            
            logger.info("下载完成")
            
        except Exception as e:
            logger.error(f"下载失败: {e}")
            raise
    
    def get_statistics(self, G: nx.Graph) -> Dict[str, Any]:
        """计算网络统计指标"""
        stats = {
            "节点数": G.number_of_nodes(),
            "边数": G.number_of_edges(),
            "平均度": sum(dict(G.degree()).values()) / G.number_of_nodes() if G.number_of_nodes() > 0 else 0,
            "网络密度": nx.density(G),
            "聚类系数": nx.average_clustering(G),
            "是否连通": nx.is_connected(G),
            "连通分量数": nx.number_connected_components(G),
        }
        
        if nx.is_connected(G):
            stats["平均路径长度"] = nx.average_shortest_path_length(G)
            stats["直径"] = nx.diameter(G)
        else:
            largest_cc = max(nx.connected_components(G), key=len)
            stats["最大连通分量大小"] = len(largest_cc)
            subg = G.subgraph(largest_cc)
            stats["最大连通分量平均路径长度"] = nx.average_shortest_path_length(subg)
        
        return stats


def get_network_statistics(G: nx.Graph) -> dict:
    """计算网络统计指标的便捷函数"""
    return FacebookDataLoader().get_statistics(G)


def print_statistics(G: nx.Graph):
    """打印网络统计信息"""
    stats = get_network_statistics(G)
    print("\n" + "=" * 50)
    print("Facebook社交网络统计信息")
    print("=" * 50)
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"{key}: {value:.4f}")
        else:
            print(f"{key}: {value}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    # 测试数据加载
    logging.basicConfig(level=logging.INFO)
    
    loader = FacebookDataLoader()
    
    print("正在加载Facebook数据集...")
    G = loader.load_full_network()
    
    print_statistics(G)
    
    # 提取子图
    print("正在提取子图...")
    subgraph = loader.load_subgraph(G, num_nodes=100, radius=2)
    
    print("\n子图统计：")
    print_statistics(subgraph)
