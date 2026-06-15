"""
任务节点智能体
8个专门的数据分析节点，构成Facebook网络分析流水线
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from .base_agent import BaseGameAgent


class NodeRole(Enum):
    """节点角色枚举"""
    DATA_COLLECTOR = "数据采集节点"      # Node-1
    RELATION_PARSER = "关系解析节点"     # Node-2
    COMMUNITY_DETECTOR = "社区发现节点"  # Node-3
    CENTRALITY_ANALYZER = "中心性分析节点" # Node-4
    PROPAGATION_MODELER = "传播模型节点"  # Node-5
    ANOMALY_DETECTOR = "异常检测节点"     # Node-6
    CLUSTER_ANALYZER = "聚类分析节点"    # Node-7
    RESULT_AGGREGATOR = "结果汇总节点"   # Node-8


# 节点角色配置表
NODE_ROLE_CONFIG = {
    "Node-1": {
        "role": NodeRole.DATA_COLLECTOR,
        "name": "数据采集节点",
        "description": "从Facebook网络获取用户基础信息",
        "input_from": [],  # 无上游节点，数据入口
        "output_to": ["Node-2", "Node-4"],
        "capability": 1000
    },
    "Node-2": {
        "role": NodeRole.RELATION_PARSER,
        "name": "关系解析节点",
        "description": "分析好友关系的双向性、亲密度",
        "input_from": ["Node-1"],
        "output_to": ["Node-3"],
        "capability": 800
    },
    "Node-3": {
        "role": NodeRole.COMMUNITY_DETECTOR,
        "name": "社区发现节点",
        "description": "识别社交圈/社区结构（Louvain算法）",
        "input_from": ["Node-2"],
        "output_to": ["Node-4", "Node-6", "Node-7"],
        "capability": 600
    },
    "Node-4": {
        "role": NodeRole.CENTRALITY_ANALYZER,
        "name": "中心性分析节点",
        "description": "计算各用户的度中心性、介数中心性、PageRank",
        "input_from": ["Node-1", "Node-3"],
        "output_to": ["Node-5", "Node-8"],
        "capability": 700
    },
    "Node-5": {
        "role": NodeRole.PROPAGATION_MODELER,
        "name": "传播模型节点",
        "description": "模拟信息在社交网络中的传播过程",
        "input_from": ["Node-4"],
        "output_to": ["Node-8"],
        "capability": 500
    },
    "Node-6": {
        "role": NodeRole.ANOMALY_DETECTOR,
        "name": "异常检测节点",
        "description": "识别异常用户/可疑关系",
        "input_from": ["Node-3"],
        "output_to": ["Node-7", "Node-8"],
        "capability": 400
    },
    "Node-7": {
        "role": NodeRole.CLUSTER_ANALYZER,
        "name": "聚类分析节点",
        "description": "对用户进行K-means聚类",
        "input_from": ["Node-3", "Node-6"],
        "output_to": ["Node-8"],
        "capability": 500
    },
    "Node-8": {
        "role": NodeRole.RESULT_AGGREGATOR,
        "name": "结果汇总节点",
        "description": "汇总各节点分析结果",
        "input_from": ["Node-4", "Node-5", "Node-6", "Node-7"],
        "output_to": [],  # 最终输出，无下游节点
        "capability": 1000
    }
}


@dataclass
class TaskData:
    """任务数据"""
    task_id: str
    data: Any
    source_node: str
    timestamp: int  # 轮次
    processed: bool = False


class TaskNodeAgent(BaseGameAgent):
    """
    任务节点智能体基类
    
    每个节点智能体负责特定的数据分析任务
    """
    
    def __init__(
        self,
        node_id: str,
        role: NodeRole,
        input_from: List[str],
        output_to: List[str],
        capability: int = 500,
        use_llm: bool = False  # 任务节点默认不使用LLM
    ):
        """
        初始化任务节点
        
        Args:
            node_id: 节点ID（如"Node-1"）
            role: 节点角色
            input_from: 依赖的上游节点列表
            output_to: 输出到哪些下游节点
            capability: 处理能力
            use_llm: 是否使用大模型
        """
        self.node_id = node_id
        self.role = role
        self.input_from = input_from
        self.output_to = output_to
        self.capability = capability
        
        # 获取配置信息
        config = NODE_ROLE_CONFIG.get(node_id, {})
        
        # 任务队列
        self.task_queue: List[TaskData] = []
        self.completed_tasks: List[TaskData] = []
        
        # 节点状态
        self.is_active = True
        
        # 角色描述
        role_description = self._build_role_description(config)
        
        super().__init__(
            name=node_id,
            role_description=role_description,
            use_llm=use_llm
        )
    
    def _build_role_description(self, config: Dict) -> str:
        """构建角色描述"""
        return f"""你是{config.get('name', '任务节点')}，代号{self.node_id}。

你的职责：{config.get('description', '')}

数据来源：{', '.join(self.input_from) if self.input_from else '数据入口（从Facebook网络直接获取）'}
数据输出：{', '.join(self.output_to) if self.output_to else '最终结果输出'}

在攻防博弈中：
- 你的节点可能遭受攻击而被切断
- 如果上游节点被攻击，你将收不到数据
- 如果你被攻击，你的数据将无法传递到下游
- 如果所有输入/输出链路都被切断，任务将失败

请正常处理任务数据，并将结果传递给下游节点。"""
    
    def _build_system_prompt(self) -> str:
        return self.role_description
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """格式化上下文"""
        return f"""=== 当前状态 ===
节点ID：{self.node_id}
节点角色：{self.role.value}
是否活跃：{"是" if self.is_active else "否"}
待处理任务：{len(self.task_queue)}个
已完成任务：{len(self.completed_tasks)}个

=== 任务数据 ===
{self._format_task_data()}
"""
    
    def _format_task_data(self) -> str:
        if not self.task_queue:
            return "（无待处理任务）"
        return "\n".join([f"  - Task {t.task_id}: {t.source_node} → {self.node_id}" 
                         for t in self.task_queue[:3]])
    
    def receive_data(self, task: TaskData) -> bool:
        """
        接收上游数据
        
        Args:
            task: 任务数据
            
        Returns:
            是否成功接收
        """
        if not self.is_active:
            return False
        
        self.task_queue.append(task)
        self.remember(
            "data_received",
            {"task_id": task.task_id, "source": task.source_node}
        )
        return True
    
    def process_task(self, round_num: int) -> Optional[TaskData]:
        """
        处理当前任务
        
        Args:
            round_num: 当前轮次
            
        Returns:
            处理后的任务数据
        """
        if not self.is_active or not self.task_queue:
            return None
        
        task = self.task_queue.pop(0)
        task.processed = True
        task.timestamp = round_num
        self.completed_tasks.append(task)
        
        # 执行数据分析
        processed_data = self._execute_analysis(task.data)
        
        result = TaskData(
            task_id=f"{task.task_id}_processed",
            data=processed_data,
            source_node=self.node_id,
            timestamp=round_num
        )
        
        self.remember(
            "task_processed",
            {"task_id": task.task_id, "output_to": self.output_to}
        )
        
        return result
    
    def _execute_analysis(self, data: Any) -> Dict[str, Any]:
        """
        执行数据分析（子类实现具体逻辑）
        """
        return {
            "node_id": self.node_id,
            "role": self.role.value,
            "input_data_shape": str(type(data)),
            "analysis_result": f"{self.role.value}分析完成",
            "status": "success"
        }
    
    def _rule_based_think(self, context: Dict[str, Any]) -> str:
        """基于规则的思考（任务节点简单处理）"""
        if self.can_execute_task():
            return f"正常处理任务：{self.role.value}"
        return f"等待上游数据：{self.input_from}"
    
    def can_execute_task(self) -> bool:
        """判断是否可以执行任务"""
        if not self.is_active:
            return False
        
        # 检查是否有上游数据可用（或者本身就是数据入口）
        if self.input_from and not self.task_queue:
            return False
        
        return True
    
    def get_output_targets(self) -> List[str]:
        """获取可以输出的下游节点"""
        return self.output_to.copy()
    
    def set_inactive(self):
        """设置节点为失效状态"""
        self.is_active = False
        self.task_queue.clear()
    
    def set_active(self):
        """恢复节点活跃状态"""
        self.is_active = True
    
    def reset(self):
        """重置节点状态"""
        super().reset()
        self.task_queue.clear()
        self.completed_tasks.clear()
        self.is_active = True


# ==================== 8个具体节点实现 ====================

class DataCollectorNode(TaskNodeAgent):
    """数据采集节点（Node-1）"""
    
    def __init__(self):
        config = NODE_ROLE_CONFIG["Node-1"]
        super().__init__(
            node_id="Node-1",
            role=config["role"],
            input_from=config["input_from"],
            output_to=config["output_to"],
            capability=config["capability"]
        )
    
    def _execute_analysis(self, data) -> Dict[str, Any]:
        """采集Facebook网络用户数据"""
        # 实际实现中会调用FacebookDataLoader
        return {
            "node_id": self.node_id,
            "role": "数据采集",
            "collected_users": 4039,
            "collected_edges": 88234,
            "sample_users": [str(i) for i in range(10)],
            "user_profiles": [{"id": i, "friends_count": 0} for i in range(10)],
            "status": "success"
        }


class RelationParserNode(TaskNodeAgent):
    """关系解析节点（Node-2）"""
    
    def __init__(self):
        config = NODE_ROLE_CONFIG["Node-2"]
        super().__init__(
            node_id="Node-2",
            role=config["role"],
            input_from=config["input_from"],
            output_to=config["output_to"],
            capability=config["capability"]
        )
    
    def _execute_analysis(self, data) -> Dict[str, Any]:
        """解析好友关系"""
        return {
            "node_id": self.node_id,
            "role": "关系解析",
            "total_edges": 88234,
            "bidirectional_count": 82000,
            "relation_strength_matrix": {},
            "status": "success"
        }


class CommunityDetectorNode(TaskNodeAgent):
    """社区发现节点（Node-3）"""
    
    def __init__(self):
        config = NODE_ROLE_CONFIG["Node-3"]
        super().__init__(
            node_id="Node-3",
            role=config["role"],
            input_from=config["input_from"],
            output_to=config["output_to"],
            capability=config["capability"]
        )
    
    def _execute_analysis(self, data) -> Dict[str, Any]:
        """社区发现（Louvain算法）"""
        return {
            "node_id": self.node_id,
            "role": "社区发现",
            "num_communities": 16,
            "community_sizes": [450, 320, 280, 250, 200, 180, 150, 140, 
                              120, 100, 90, 80, 70, 60, 50, 40],
            "modularity": 0.62,
            "status": "success"
        }


class CentralityAnalyzerNode(TaskNodeAgent):
    """中心性分析节点（Node-4）"""
    
    def __init__(self):
        config = NODE_ROLE_CONFIG["Node-4"]
        super().__init__(
            node_id="Node-4",
            role=config["role"],
            input_from=config["input_from"],
            output_to=config["output_to"],
            capability=config["capability"]
        )
    
    def _execute_analysis(self, data) -> Dict[str, Any]:
        """计算中心性指标"""
        return {
            "node_id": self.node_id,
            "role": "中心性分析",
            "top_degree_centrality": [{"node": "107", "score": 0.85}],
            "top_betweenness_centrality": [{"node": "1684", "score": 0.48}],
            "top_pagerank": [{"node": "1912", "score": 0.0078}],
            "status": "success"
        }


class PropagationModelerNode(TaskNodeAgent):
    """传播模型节点（Node-5）"""
    
    def __init__(self):
        config = NODE_ROLE_CONFIG["Node-5"]
        super().__init__(
            node_id="Node-5",
            role=config["role"],
            input_from=config["input_from"],
            output_to=config["output_to"],
            capability=config["capability"]
        )
    
    def _execute_analysis(self, data) -> Dict[str, Any]:
        """模拟信息传播（SI/SIR模型）"""
        return {
            "node_id": self.node_id,
            "role": "传播模型",
            "model_type": "SIR",
            "infection_rate": 0.03,
            "recovery_rate": 0.01,
            "final_infected_ratio": 0.72,
            "spread_time_steps": 45,
            "status": "success"
        }


class AnomalyDetectorNode(TaskNodeAgent):
    """异常检测节点（Node-6）"""
    
    def __init__(self):
        config = NODE_ROLE_CONFIG["Node-6"]
        super().__init__(
            node_id="Node-6",
            role=config["role"],
            input_from=config["input_from"],
            output_to=config["output_to"],
            capability=config["capability"]
        )
    
    def _execute_analysis(self, data) -> Dict[str, Any]:
        """检测异常用户"""
        return {
            "node_id": self.node_id,
            "role": "异常检测",
            "total_anomalies_detected": 23,
            "suspicious_users": ["U123", "U456", "U789"],
            "anomaly_types": {"fake_accounts": 8, "bots": 10, "suspicious_links": 5},
            "status": "success"
        }


class ClusterAnalyzerNode(TaskNodeAgent):
    """聚类分析节点（Node-7）"""
    
    def __init__(self):
        config = NODE_ROLE_CONFIG["Node-7"]
        super().__init__(
            node_id="Node-7",
            role=config["role"],
            input_from=config["input_from"],
            output_to=config["output_to"],
            capability=config["capability"]
        )
    
    def _execute_analysis(self, data) -> Dict[str, Any]:
        """用户聚类分析"""
        return {
            "node_id": self.node_id,
            "role": "聚类分析",
            "num_clusters": 5,
            "cluster_profiles": [
                {"cluster_id": 0, "size": 1200, "avg_degree": 45},
                {"cluster_id": 1, "size": 980, "avg_degree": 32},
                {"cluster_id": 2, "size": 750, "avg_degree": 28},
                {"cluster_id": 3, "size": 620, "avg_degree": 18},
                {"cluster_id": 4, "size": 489, "avg_degree": 12}
            ],
            "status": "success"
        }


class ResultAggregatorNode(TaskNodeAgent):
    """结果汇总节点（Node-8）"""
    
    def __init__(self):
        config = NODE_ROLE_CONFIG["Node-8"]
        super().__init__(
            node_id="Node-8",
            role=config["role"],
            input_from=config["input_from"],
            output_to=config["output_to"],
            capability=config["capability"]
        )
    
    def _execute_analysis(self, data) -> Dict[str, Any]:
        """汇总所有分析结果"""
        return {
            "node_id": self.node_id,
            "role": "结果汇总",
            "report_title": "Facebook社交网络分析报告",
            "sections": [
                "数据概览", "社区结构", "用户影响力", 
                "传播特性", "异常分析", "用户分群"
            ],
            "overall_quality_score": 0.85,
            "status": "success"
        }
    
    def is_task_complete(self) -> bool:
        """判断分析任务是否完成（Node-8收到所有输入）"""
        required_inputs = {"Node-4", "Node-5", "Node-6", "Node-7"}
        received_from = {task.source_node for task in self.completed_tasks}
        return required_inputs.issubset(received_from)


# ==================== 工厂函数 ====================

def create_task_nodes() -> Dict[str, TaskNodeAgent]:
    """创建所有8个任务节点（字典形式）"""
    node_classes = [
        DataCollectorNode,
        RelationParserNode,
        CommunityDetectorNode,
        CentralityAnalyzerNode,
        PropagationModelerNode,
        AnomalyDetectorNode,
        ClusterAnalyzerNode,
        ResultAggregatorNode
    ]
    
    return {node_class.__name__: node_class() for node_class in node_classes}


def create_all_task_nodes() -> List[TaskNodeAgent]:
    """创建所有任务节点列表"""
    return [
        DataCollectorNode(),
        RelationParserNode(),
        CommunityDetectorNode(),
        CentralityAnalyzerNode(),
        PropagationModelerNode(),
        AnomalyDetectorNode(),
        ClusterAnalyzerNode(),
        ResultAggregatorNode()
    ]


def get_node_by_id(node_id: str) -> Optional[TaskNodeAgent]:
    """根据ID获取节点"""
    config = NODE_ROLE_CONFIG.get(node_id)
    if not config:
        return None
    
    node_map = {
        "Node-1": DataCollectorNode,
        "Node-2": RelationParserNode,
        "Node-3": CommunityDetectorNode,
        "Node-4": CentralityAnalyzerNode,
        "Node-5": PropagationModelerNode,
        "Node-6": AnomalyDetectorNode,
        "Node-7": ClusterAnalyzerNode,
        "Node-8": ResultAggregatorNode
    }
    
    node_class = node_map.get(node_id)
    return node_class() if node_class else None
