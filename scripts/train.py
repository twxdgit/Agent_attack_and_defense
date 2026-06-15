"""
训练脚本
用于批量运行实验并收集结果
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.game_engine import GameEngine
from agents.attack_agent import AttackerAgent
from agents.defense_agent import DefenderAgent
from agents.task_node_agent import create_all_task_nodes
from strategies.random_attack import RandomAttacker
from strategies.degree_attack import DegreeAttacker
from strategies.baseline_defense import BaselineDefender

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Trainer:
    """训练器"""
    
    def __init__(self, output_dir: str = "data/results"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.results = []
    
    def run_experiment(
        self,
        name: str,
        attack_strategy,
        defense_strategy,
        use_llm_attacker: bool = False,
        use_llm_defender: bool = False,
        num_runs: int = 1,
        **kwargs
    ) -> List[Dict]:
        """
        运行实验（可重复多次）
        
        Args:
            name: 实验名称
            attack_strategy: 攻击策略
            defense_strategy: 防御策略
            use_llm_attacker: 是否使用LLM攻击
            use_llm_defender: 是否使用LLM防御
            num_runs: 重复次数
            **kwargs: GameEngine参数
        """
        results = []
        
        for run_id in range(num_runs):
            logger.info(f"Running {name} - Run {run_id + 1}/{num_runs}")
            
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
            
            # 运行实验
            engine = GameEngine(
                attacker=attacker,
                defender=defender,
                task_nodes=task_nodes,
                use_llm_attacker=use_llm_attacker,
                use_llm_defender=use_llm_defender,
                verbose=False,
                save_results=False,
                **kwargs
            )
            
            result = engine.run()
            result_dict = result.to_dict()
            result_dict['experiment_name'] = name
            result_dict['run_id'] = run_id
            result_dict['attack_type'] = type(attack_strategy).__name__ if not use_llm_attacker else "LLM"
            result_dict['defense_type'] = type(defense_strategy).__name__ if not use_llm_defender else "LLM"
            
            results.append(result_dict)
            self.results.append(result_dict)
        
        return results
    
    def run_batch(self, experiments: List[Dict]) -> List[Dict]:
        """批量运行实验"""
        all_results = []
        
        for exp in experiments:
            results = self.run_experiment(
                name=exp["name"],
                attack_strategy=exp["attacker"],
                defense_strategy=exp["defender"],
                use_llm_attacker=exp.get("use_llm_attacker", False),
                use_llm_defender=exp.get("use_llm_defender", False),
                num_runs=exp.get("num_runs", 1),
                **exp.get("kwargs", {})
            )
            all_results.extend(results)
        
        return all_results
    
    def save_results(self, filename: str = None):
        """保存结果"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"training_results_{timestamp}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to {filepath}")
        return filepath
    
    def generate_report(self) -> Dict:
        """生成统计报告"""
        report = {}
        
        # 按实验名称分组
        by_experiment = {}
        for result in self.results:
            name = result.get('experiment_name', 'Unknown')
            if name not in by_experiment:
                by_experiment[name] = []
            by_experiment[name].append(result)
        
        # 计算统计数据
        for name, results in by_experiment.items():
            rounds = [r['total_rounds'] for r in results]
            attackers_wins = sum(1 for r in results if r['winner'] == 'Attacker')
            defenders_wins = sum(1 for r in results if r['winner'] == 'Defender')
            
            report[name] = {
                'num_runs': len(results),
                'avg_rounds': sum(rounds) / len(rounds) if rounds else 0,
                'min_rounds': min(rounds) if rounds else 0,
                'max_rounds': max(rounds) if rounds else 0,
                'attacker_win_rate': attackers_wins / len(results) if results else 0,
                'defender_win_rate': defenders_wins / len(results) if results else 0
            }
        
        return report


def main():
    """主函数"""
    trainer = Trainer()
    
    # 定义实验配置
    experiments = [
        # 随机攻击实验（重复5次）
        {
            "name": "随机攻击 vs 基础防御",
            "attacker": RandomAttacker(max_attacks=2),
            "defender": BaselineDefender(max_repairs=2),
            "use_llm_attacker": False,
            "use_llm_defender": False,
            "num_runs": 5,
            "kwargs": {"num_nodes": 8, "max_rounds": 30}
        },
        # 度数攻击实验（重复5次）
        {
            "name": "度数攻击 vs 基础防御",
            "attacker": DegreeAttacker(max_attacks=2),
            "defender": BaselineDefender(max_repairs=2),
            "use_llm_attacker": False,
            "use_llm_defender": False,
            "num_runs": 5,
            "kwargs": {"num_nodes": 8, "max_rounds": 30}
        },
        # LLM自适应攻击（重复3次）
        {
            "name": "LLM自适应攻击 vs 基础防御",
            "attacker": AttackerAgent(use_llm=True),
            "defender": BaselineDefender(max_repairs=2),
            "use_llm_attacker": True,
            "use_llm_defender": False,
            "num_runs": 3,
            "kwargs": {"num_nodes": 8, "max_rounds": 30}
        }
    ]
    
    print("\n" + "=" * 60)
    print("开始批量训练实验")
    print("=" * 60)
    
    # 运行所有实验
    trainer.run_batch(experiments)
    
    # 保存结果
    trainer.save_results()
    
    # 生成报告
    report = trainer.generate_report()
    
    print("\n" + "=" * 60)
    print("实验统计报告")
    print("=" * 60)
    
    for name, stats in report.items():
        print(f"\n{name}:")
        print(f"  运行次数: {stats['num_runs']}")
        print(f"  平均轮次: {stats['avg_rounds']:.1f}")
        print(f"  攻击方胜率: {stats['attacker_win_rate']:.1%}")
        print(f"  防御方胜率: {stats['defender_win_rate']:.1%}")
    
    print("\n训练完成！")


if __name__ == "__main__":
    main()
