"""
运行多组对照实验
对比随机攻击、度数攻击、LLM自适应攻击的效果
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from typing import List, Dict

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.game_engine import GameEngine
from agents.attack_agent import AttackerAgent
from agents.defense_agent import DefenderAgent
from agents.task_node_agent import create_all_task_nodes
from strategies.random_attack import RandomAttacker
from strategies.degree_attack import DegreeAttacker
from strategies.baseline_defense import BaselineDefender
from metrics.visualizer import GameVisualizer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ExperimentRunner:
    """实验运行器"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.results = []
        self.visualizer = GameVisualizer()
        
    def run_single_experiment(
        self,
        name: str,
        attack_strategy,
        defense_strategy,
        use_llm_attacker: bool = False,
        use_llm_defender: bool = False,
        **kwargs
    ) -> Dict:
        """
        运行单组实验
        
        Args:
            name: 实验名称
            attack_strategy: 攻击策略
            defense_strategy: 防御策略
            use_llm_attacker: 攻击方是否使用LLM
            use_llm_defender: 防御方是否使用LLM
            **kwargs: GameEngine其他参数
        """
        print(f"\n{'='*60}")
        print(f"开始实验: {name}")
        print(f"{'='*60}\n")
        
        # 创建智能体
        if use_llm_attacker:
            attacker = AttackerAgent(use_llm=True)
        else:
            attacker = attack_strategy
        
        if use_llm_defender:
            defender = DefenderAgent(use_llm=True)
        else:
            defender = defense_strategy
        
        # 创建任务节点
        task_nodes = create_all_task_nodes()
        
        # 创建博弈引擎
        engine = GameEngine(
            attacker=attacker,
            defender=defender,
            task_nodes=task_nodes,
            use_llm_attacker=use_llm_attacker,
            use_llm_defender=use_llm_defender,
            verbose=True,
            save_results=True,
            **kwargs
        )
        
        # 运行实验
        result = engine.run()
        
        # 保存结果
        result_dict = result.to_dict()
        result_dict['experiment_name'] = name
        result_dict['attack_type'] = type(attack_strategy).__name__ if not use_llm_attacker else "LLM"
        result_dict['defense_type'] = type(defense_strategy).__name__ if not use_llm_defender else "LLM"
        
        self.results.append(result_dict)
        
        print(f"\n实验结果: {name}")
        print(f"  胜负: {result.winner}")
        print(f"  轮次: {result.total_rounds}")
        
        return result_dict
    
    def run_baseline_comparison(self, num_nodes: int = 8, max_rounds: int = 30) -> List[Dict]:
        """
        运行基线对照实验
        
        实验组：
        1. 随机攻击 vs 基础防御
        2. 度数攻击 vs 基础防御
        3. LLM自适应攻击 vs LLM自适应防御
        """
        print("\n" + "=" * 70)
        print("开始对照实验")
        print("=" * 70)
        
        # 实验配置
        experiments = [
            {
                "name": "随机攻击 vs 基础防御",
                "attacker": RandomAttacker(max_attacks=2),
                "defender": BaselineDefender(max_repairs=2, max_new_edges=1),
                "use_llm_attacker": False,
                "use_llm_defender": False
            },
            {
                "name": "度数攻击 vs 基础防御",
                "attacker": DegreeAttacker(max_attacks=2),
                "defender": BaselineDefender(max_repairs=2, max_new_edges=1),
                "use_llm_attacker": False,
                "use_llm_defender": False
            },
            {
                "name": "LLM自适应攻击 vs LLM自适应防御",
                "attacker": AttackerAgent(use_llm=True),
                "defender": DefenderAgent(use_llm=True),
                "use_llm_attacker": True,
                "use_llm_defender": True
            }
        ]
        
        for exp in experiments:
            self.run_single_experiment(
                name=exp["name"],
                attack_strategy=exp["attacker"],
                defense_strategy=exp["defender"],
                use_llm_attacker=exp["use_llm_attacker"],
                use_llm_defender=exp["use_llm_defender"],
                num_nodes=num_nodes,
                max_rounds=max_rounds
            )
        
        return self.results
    
    def run_custom_experiments(self, experiments: List[Dict]) -> List[Dict]:
        """运行自定义实验"""
        for exp in experiments:
            self.run_single_experiment(
                name=exp["name"],
                attack_strategy=exp["attacker"],
                defense_strategy=exp["defender"],
                use_llm_attacker=exp.get("use_llm_attacker", False),
                use_llm_defender=exp.get("use_llm_defender", False),
                **exp.get("kwargs", {})
            )
        
        return self.results
    
    def generate_comparison_plot(self, save_path: str = None):
        """生成对比图"""
        if not self.results:
            print("无可用结果")
            return
        
        if save_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = f"data/results/comparison_{timestamp}.png"
        
        self.visualizer.plot_comparison(
            results_list=self.results,
            labels=[r.get('experiment_name', r.get('name', 'Unknown')) for r in self.results],
            save_path=save_path
        )
    
    def save_results(self, save_path: str = None):
        """保存所有结果"""
        if save_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = f"data/results/all_experiments_{timestamp}.json"
        
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\n结果已保存: {save_path}")
    
    def print_summary(self):
        """打印结果摘要"""
        print("\n" + "=" * 70)
        print("实验结果摘要")
        print("=" * 70)
        
        for result in self.results:
            name = result.get('experiment_name', 'Unknown')
            winner = result.get('winner', 'Unknown')
            rounds = result.get('total_rounds', 0)
            final_edges = result.get('final_network_state', {}).get('num_edges', 0)
            
            print(f"\n{name}:")
            print(f"  胜负: {winner}")
            print(f"  轮次: {rounds}")
            print(f"  最终链路数: {final_edges}")
        
        print("\n" + "=" * 70)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='运行攻防博弈对照实验')
    
    parser.add_argument('--rounds', type=int, default=30, help='最大博弈轮次')
    parser.add_argument('--nodes', type=int, default=8, help='节点数量')
    parser.add_argument('--experiments', type=str, default='all',
                       choices=['all', 'random', 'degree', 'llm', 'custom'],
                       help='运行的实验类型')
    parser.add_argument('--save-plot', action='store_true', help='保存对比图')
    parser.add_argument('--output', type=str, help='结果输出文件')
    
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()
    
    runner = ExperimentRunner()
    
    if args.experiments == 'all':
        # 运行所有对照实验
        results = runner.run_baseline_comparison(
            num_nodes=args.nodes,
            max_rounds=args.rounds
        )
    elif args.experiments == 'random':
        results = [runner.run_single_experiment(
            "随机攻击 vs 基础防御",
            RandomAttacker(max_attacks=2),
            BaselineDefender(max_repairs=2),
            num_nodes=args.nodes,
            max_rounds=args.rounds
        )]
    elif args.experiments == 'degree':
        results = [runner.run_single_experiment(
            "度数攻击 vs 基础防御",
            DegreeAttacker(max_attacks=2),
            BaselineDefender(max_repairs=2),
            num_nodes=args.nodes,
            max_rounds=args.rounds
        )]
    elif args.experiments == 'llm':
        results = [runner.run_single_experiment(
            "LLM自适应攻防",
            AttackerAgent(use_llm=True),
            DefenderAgent(use_llm=True),
            use_llm_attacker=True,
            use_llm_defender=True,
            num_nodes=args.nodes,
            max_rounds=args.rounds
        )]
    else:
        print("请指定实验类型")
        return
    
    # 打印摘要
    runner.print_summary()
    
    # 保存结果
    runner.save_results(args.output)
    
    # 生成对比图
    if args.save_plot:
        runner.generate_comparison_plot()
    
    print("\n所有实验完成！")


if __name__ == "__main__":
    main()
