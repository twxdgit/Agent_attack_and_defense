"""
评估脚本
分析实验结果并生成报告
"""

import os
import sys
import json
import argparse
from typing import List, Dict, Optional
from datetime import datetime
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

from metrics.visualizer import GameVisualizer


class Evaluator:
    """实验结果评估器"""
    
    def __init__(self, results_dir: str = "data/results"):
        self.results_dir = results_dir
        self.results: List[Dict] = []
    
    def load_results(self, filepath: str = None):
        """加载结果文件"""
        if filepath:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.results = json.load(f)
        else:
            # 加载最新的结果文件
            result_files = [
                f for f in os.listdir(self.results_dir) 
                if f.startswith('game_result_') and f.endswith('.json')
            ]
            if result_files:
                latest = sorted(result_files)[-1]
                filepath = os.path.join(self.results_dir, latest)
                with open(filepath, 'r', encoding='utf-8') as f:
                    self.results = json.load(f)
    
    def analyze_robustness(self) -> Dict:
        """分析网络鲁棒性"""
        if not self.results:
            return {}
        
        # 提取指标曲线
        metrics = self.results[0].get('metrics_curves', {})
        
        analysis = {
            'initial_robustness': metrics.get('robustness_index', [0])[0] if metrics.get('robustness_index') else 0,
            'final_robustness': metrics.get('robustness_index', [0])[-1] if metrics.get('robustness_index') else 0,
            'robustness_drop': 0
        }
        
        if analysis['initial_robustness'] > 0:
            analysis['robustness_drop'] = (
                (analysis['initial_robustness'] - analysis['final_robustness']) 
                / analysis['initial_robustness']
            )
        
        return analysis
    
    def compare_strategies(self) -> Dict:
        """对比不同策略的效果"""
        comparison = {}
        
        for result in self.results:
            attack_type = result.get('attack_type', 'Unknown')
            
            if attack_type not in comparison:
                comparison[attack_type] = {
                    'wins': 0,
                    'total_rounds': [],
                    'final_edges': []
                }
            
            comparison[attack_type]['wins'] += 1 if result.get('winner') == 'Attacker' else 0
            comparison[attack_type]['total_rounds'].append(result.get('total_rounds', 0))
            comparison[attack_type]['final_edges'].append(
                result.get('final_network_state', {}).get('num_edges', 0)
            )
        
        # 计算统计
        for attack_type, stats in comparison.items():
            n = len(stats['total_rounds'])
            if n > 0:
                stats['avg_rounds'] = sum(stats['total_rounds']) / n
                stats['win_rate'] = stats['wins'] / n
                stats['avg_final_edges'] = sum(stats['final_edges']) / n
        
        return comparison
    
    def generate_report(self, output_path: str = None) -> str:
        """生成评估报告"""
        report_lines = []
        
        report_lines.append("=" * 70)
        report_lines.append("网络攻防博弈实验评估报告")
        report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("=" * 70)
        
        # 1. 鲁棒性分析
        robustness = self.analyze_robustness()
        if robustness:
            report_lines.append("\n【网络鲁棒性分析】")
            report_lines.append(f"  初始鲁棒性指数: {robustness['initial_robustness']:.4f}")
            report_lines.append(f"  最终鲁棒性指数: {robustness['final_robustness']:.4f}")
            report_lines.append(f"  鲁棒性下降: {robustness['robustness_drop']:.1%}")
        
        # 2. 策略对比
        comparison = self.compare_strategies()
        if comparison:
            report_lines.append("\n【攻击策略效果对比】")
            report_lines.append("-" * 50)
            for attack_type, stats in comparison.items():
                report_lines.append(f"\n  {attack_type}:")
                report_lines.append(f"    攻击方胜率: {stats.get('win_rate', 0):.1%}")
                report_lines.append(f"    平均持续轮次: {stats.get('avg_rounds', 0):.1f}")
                report_lines.append(f"    平均最终链路数: {stats.get('avg_final_edges', 0):.1f}")
        
        # 3. 详细结果
        report_lines.append("\n【详细实验结果】")
        report_lines.append("-" * 50)
        for i, result in enumerate(self.results, 1):
            name = result.get('experiment_name', f'实验{i}')
            winner = result.get('winner', 'Unknown')
            rounds = result.get('total_rounds', 0)
            final_state = result.get('final_network_state', {})
            
            report_lines.append(f"\n  {name}:")
            report_lines.append(f"    胜负: {winner}")
            report_lines.append(f"    轮次: {rounds}")
            report_lines.append(f"    最终链路数: {final_state.get('num_edges', 0)}")
            report_lines.append(f"    最终连通分量: {final_state.get('largest_cc_size', 0)}")
        
        report_lines.append("\n" + "=" * 70)
        
        report_text = "\n".join(report_lines)
        
        # 保存报告
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
        
        return report_text
    
    def plot_robustness_comparison(self, save_path: str = None):
        """绘制鲁棒性对比图"""
        if not self.results:
            print("无可用结果")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # 准备数据
        for i, result in enumerate(self.results):
            name = result.get('experiment_name', f'实验{i+1}')
            metrics = result.get('metrics_curves', {})
            rounds = list(range(len(metrics.get('num_edges', []))))
            
            # 1. 链路数变化
            ax = axes[0, 0]
            if 'num_edges' in metrics:
                ax.plot(rounds, metrics['num_edges'], label=name, linewidth=2)
            
            # 2. 鲁棒性指数变化
            ax = axes[0, 1]
            if 'robustness_index' in metrics:
                ax.plot(rounds, metrics['robustness_index'], label=name, linewidth=2)
            
            # 3. 连通分量比例变化
            ax = axes[1, 0]
            if 'largest_cc_ratio' in metrics:
                ax.plot(rounds, metrics['largest_cc_ratio'], label=name, linewidth=2)
            
            # 4. 聚类系数变化
            ax = axes[1, 1]
            if 'clustering_coeff' in metrics:
                ax.plot(rounds, metrics['clustering_coeff'], label=name, linewidth=2)
        
        # 设置标签
        axes[0, 0].set_title('链路数量随时间变化')
        axes[0, 0].set_xlabel('博弈轮次')
        axes[0, 0].set_ylabel('链路数量')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)

        axes[0, 1].set_title('鲁棒性指数随时间变化')
        axes[0, 1].set_xlabel('博弈轮次')
        axes[0, 1].set_ylabel('鲁棒性指数')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)

        axes[1, 0].set_title('最大连通分量比例随时间变化')
        axes[1, 0].set_xlabel('博弈轮次')
        axes[1, 0].set_ylabel('比例')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)

        axes[1, 1].set_title('聚类系数随时间变化')
        axes[1, 1].set_xlabel('博弈轮次')
        axes[1, 1].set_ylabel('系数')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"对比图已保存: {save_path}")
        else:
            plt.show()


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='评估实验结果')
    
    parser.add_argument('--input', type=str, help='结果文件路径')
    parser.add_argument('--output', type=str, help='报告输出路径')
    parser.add_argument('--plot', action='store_true', help='生成对比图')
    parser.add_argument('--plot-output', type=str, default='data/results/evaluation_plot.png',
                       help='图表输出路径')
    
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()
    
    evaluator = Evaluator()
    
    # 加载结果
    if args.input:
        evaluator.load_results(args.input)
    else:
        evaluator.load_results()
    
    if not evaluator.results:
        print("未找到结果文件，请先运行实验")
        return
    
    # 生成报告
    report = evaluator.generate_report(args.output)
    print(report)
    
    # 生成对比图
    if args.plot:
        evaluator.plot_robustness_comparison(args.plot_output)


if __name__ == "__main__":
    main()
