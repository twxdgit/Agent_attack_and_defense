"""
网络参数配置模块
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class NetworkConfig:
    """网络参数配置"""
    
    # === 基本参数 ===
    num_nodes: int = 8  # 任务节点数量（固定8个）
    avg_degree: float = 3.0  # 平均度数
    seed: int = 42  # 随机种子
    
    # === Facebook数据集参数 ===
    facebook_data_path: str = "data/raw/facebook_combined.txt"
    subgraph_size: int = 100  # 子图节点数
    subgraph_radius: int = 2  # 扩展半径
    
    # === 网络类型 ===
    network_type: str = "watts_strogatz"  # watts_strogatz / barabasi_albert / facebook
    rewiring_prob: float = 0.1  # WS模型的随机重连概率
    
    # === 数据集URL ===
    SNAP_DATA_URL: str = "https://snap.stanford.edu/data/facebook_combined.txt.gz"
    
    # === 节点角色配置 ===
    NODE_ROLES: List[dict] = field(default_factory=lambda: [
        {"id": "Node-1", "name": "数据采集节点", "role": "DATA_COLLECTOR",
         "input_from": [], "output_to": ["Node-2", "Node-4"]},
        {"id": "Node-2", "name": "关系解析节点", "role": "RELATION_PARSER",
         "input_from": ["Node-1"], "output_to": ["Node-3"]},
        {"id": "Node-3", "name": "社区发现节点", "role": "COMMUNITY_DETECTOR",
         "input_from": ["Node-2"], "output_to": ["Node-4", "Node-6", "Node-7"]},
        {"id": "Node-4", "name": "中心性分析节点", "role": "CENTRALITY_ANALYZER",
         "input_from": ["Node-1", "Node-3"], "output_to": ["Node-5", "Node-8"]},
        {"id": "Node-5", "name": "传播模型节点", "role": "PROPAGATION_MODELER",
         "input_from": ["Node-4"], "output_to": ["Node-8"]},
        {"id": "Node-6", "name": "异常检测节点", "role": "ANOMALY_DETECTOR",
         "input_from": ["Node-3"], "output_to": ["Node-7", "Node-8"]},
        {"id": "Node-7", "name": "聚类分析节点", "role": "CLUSTER_ANALYZER",
         "input_from": ["Node-3", "Node-6"], "output_to": ["Node-8"]},
        {"id": "Node-8", "name": "结果汇总节点", "role": "RESULT_AGGREGATOR",
         "input_from": ["Node-4", "Node-5", "Node-6", "Node-7"], "output_to": []},
    ])
    
    # === 节点能力配置 ===
    NODE_CAPABILITIES: dict = field(default_factory=lambda: {
        "Node-1": 1000,  # 数据采集
        "Node-2": 800,   # 关系解析
        "Node-3": 600,   # 社区发现
        "Node-4": 700,   # 中心性分析
        "Node-5": 500,   # 传播模型
        "Node-6": 400,   # 异常检测
        "Node-7": 500,   # 聚类分析
        "Node-8": 1000,  # 结果汇总
    })
    
    def get_node_config(self, node_id: str) -> Optional[dict]:
        """获取指定节点配置"""
        for node in self.NODE_ROLES:
            if node["id"] == node_id:
                return node
        return None
    
    def get_node_ids(self) -> List[str]:
        """获取所有节点ID"""
        return [node["id"] for node in self.NODE_ROLES]
    
    def get_input_chain(self, node_id: str) -> List[str]:
        """获取节点的上游链路"""
        config = self.get_node_config(node_id)
        return config["input_from"] if config else []
    
    def get_output_chain(self, node_id: str) -> List[str]:
        """获取节点的下游链路"""
        config = self.get_node_config(node_id)
        return config["output_to"] if config else []
