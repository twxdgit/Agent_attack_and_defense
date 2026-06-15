"""
博弈规则配置模块
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class GameConfig:
    """博弈规则配置"""
    
    # === 博弈参数 ===
    max_rounds: int = 30  # 最大博弈轮次
    paralysis_threshold: float = 0.3  # 网络瘫痪阈值（最大连通分量比例）
    paralysis_rounds: int = 3  # 连续瘫痪轮次达到此值则攻击方胜利
    
    # === 攻击限制 ===
    max_attacks_per_round: int = 2  # 每轮最多攻击次数
    
    # === 防御限制 ===
    max_repairs_per_round: int = 2  # 每轮最多修复次数
    max_new_edges_per_round: int = 1  # 每轮最多新增链路数
    
    # === 输出控制 ===
    verbose: bool = True  # 是否输出详细日志
    save_logs: bool = True  # 是否保存日志
    log_dir: str = "data/logs"
    results_dir: str = "data/results"
    
    # === 可视化 ===
    generate_animation: bool = True  # 是否生成动画
    save_plots: bool = True  # 是否保存图表
    
    # === 智能体设置 ===
    use_llm_attacker: bool = True  # 攻击智能体是否使用大模型
    use_llm_defender: bool = True  # 防御智能体是否使用大模型
    
    # === 对照实验 ===
    run_baseline_experiments: bool = True  # 是否运行对照组实验
    
    # === 随机种子 ===
    enable_reproducibility: bool = True  # 是否启用可重现性（固定随机种子）
