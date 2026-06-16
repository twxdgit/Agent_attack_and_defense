"""
主程序入口
运行攻防博弈实验
"""

import argparse
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.game_engine import GameEngine
from agents.task_node_agent import create_all_task_nodes
from scripts.load_facebook_data import FacebookDataLoader, print_statistics
from config.model_config import ModelProvider
from metrics.visualizer import GameVisualizer

# 创建日志目录
LOG_DIR = Path("data/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 生成唯一运行ID
RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")

# 配置日志 - 同时输出到终端和文件
log_file = LOG_DIR / f"experiment_{RUN_ID}.log"
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[console_handler, file_handler]
)
logger = logging.getLogger(__name__)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='网络攻防博弈实验')
    
    # 博弈参数
    parser.add_argument('--rounds', type=int, default=30, help='最大博弈轮次')
    parser.add_argument('--nodes', type=int, default=8, help='节点数量')
    parser.add_argument('--network-type', type=str, default='watts_strogatz',
                       choices=['watts_strogatz', 'barabasi_albert', 'complete', 'cycle', 'facebook'],
                       help='网络类型')
    
    # 能力限制
    parser.add_argument('--max-attacks', type=int, default=2, help='每轮最大攻击次数')
    parser.add_argument('--max-repairs', type=int, default=2, help='每轮最大修复次数')
    parser.add_argument('--max-new-edges', type=int, default=1, help='每轮最大新增链路数')
    
    # 模型设置
    parser.add_argument('--use-llm', action='store_true', help='使用大模型')
    parser.add_argument('--model', type=str, default='ollama',
                       choices=['ollama', 'dashscope', 'deepseek', 'wenxin'],
                       help='使用的模型')
    
    # 博弈规则
    parser.add_argument('--paralysis-threshold', type=float, default=0.3, help='网络瘫痪阈值')
    parser.add_argument('--paralysis-rounds', type=int, default=3, help='连续瘫痪轮次判定')
    
    # 输出设置
    parser.add_argument('--verbose', action='store_true', default=True, help='输出详细信息')
    parser.add_argument('--save-results', action='store_true', default=True, help='保存结果')
    parser.add_argument('--save-plot', action='store_true', help='保存可视化图表')
    
    # Facebook数据集
    parser.add_argument('--use-facebook', action='store_true', help='使用Facebook数据集')
    parser.add_argument('--subgraph-size', type=int, default=100, help='Facebook子图大小')
    
    return parser.parse_args()


def run_with_facebook(args):
    """使用Facebook数据集运行实验"""
    print("\n" + "=" * 60)
    print("Facebook社交网络攻防博弈实验")
    print("=" * 60 + "\n")
    
    # 加载数据
    loader = FacebookDataLoader()
    print("正在加载Facebook数据集...")
    G = loader.load_full_network()
    
    print_statistics(G)
    
    # 提取子图
    print(f"正在提取{args.subgraph_size}个节点的子图...")
    subgraph = loader.load_subgraph(G, num_nodes=args.subgraph_size, radius=2)
    
    print(f"\n子图统计：")
    print_statistics(subgraph)
    
    # 创建任务节点
    task_nodes = create_all_task_nodes()
    
    # 创建博弈引擎
    engine = GameEngine(
        num_nodes=subgraph.number_of_nodes(),
        max_rounds=args.rounds,
        paralysis_threshold=args.paralysis_threshold,
        paralysis_rounds=args.paralysis_rounds,
        max_attacks_per_round=args.max_attacks,
        max_repairs_per_round=args.max_repairs,
        max_new_edges_per_round=args.max_new_edges,
        use_llm_attacker=args.use_llm,
        use_llm_defender=args.use_llm,
        graph=subgraph,
        task_nodes=task_nodes,
        verbose=args.verbose,
        save_results=args.save_results
    )
    
    return engine.run()


def run_with_synthetic_network(args):
    """使用合成网络运行实验"""
    print("\n" + "=" * 60)
    print("合成网络攻防博弈实验")
    print("=" * 60 + "\n")

    # 创建任务节点
    task_nodes = create_all_task_nodes()

    # 创建博弈引擎
    engine = GameEngine(
        num_nodes=args.nodes,
        max_rounds=args.rounds,
        paralysis_threshold=args.paralysis_threshold,
        paralysis_rounds=args.paralysis_rounds,
        max_attacks_per_round=args.max_attacks,
        max_repairs_per_round=args.max_repairs,
        max_new_edges_per_round=args.max_new_edges,
        use_llm_attacker=args.use_llm,
        use_llm_defender=args.use_llm,
        network_type=args.network_type,
        task_nodes=task_nodes,
        verbose=args.verbose,
        save_results=args.save_results,
        run_id=RUN_ID  # 传递运行ID
    )

    return engine.run()


def main():
    """主函数"""
    args = parse_args()
    
    print(f"\n[运行ID: {RUN_ID}]")
    print("\n实验配置：")
    print(f"  博弈轮次: {args.rounds}")
    print(f"  节点数量: {args.nodes}")
    print(f"  网络类型: {args.network_type}")
    print(f"  使用LLM: {args.use_llm}")
    print(f"  攻击限制: 每轮{args.max_attacks}条链路")
    print(f"  防御限制: 每轮修复{args.max_repairs}条+新增{args.max_new_edges}条")
    
    logger.info(f"实验开始 - 运行ID: {RUN_ID}")
    logger.info(f"配置: rounds={args.rounds}, nodes={args.nodes}, network={args.network_type}")
    
    # 运行实验
    try:
        if args.use_facebook:
            result = run_with_facebook(args)
        else:
            result = run_with_synthetic_network(args)
        
        # 打印结果
        print("\n" + "=" * 60)
        print("实验结果")
        print("=" * 60)
        print(f"  胜负方: {result.winner}")
        print(f"  总轮次: {result.total_rounds}")
        print(f"  最终链路数: {result.final_network_state.get('num_edges', 0)}")
        print(f"  最终连通分量: {result.final_network_state.get('largest_cc_size', 0)}")
        
        # 保存可视化 - 使用唯一文件名
        if args.save_plot:
            visualizer = GameVisualizer()
            plot_path = f"data/results/metrics_{RUN_ID}.png"
            visualizer.plot_metrics_overview(
                result.metrics_curves,
                save_path=plot_path
            )
        
        print("\n实验完成！")
        logger.info(f"实验完成 - 胜负: {result.winner}, 轮次: {result.total_rounds}")
        
        # 打印日志保存位置
        print(f"\n日志已保存至: {log_file}")
        
    except KeyboardInterrupt:
        print("\n\n实验被用户中断")
        logger.warning("实验被用户中断")
        sys.exit(0)
    except Exception as e:
        logger.error(f"实验运行出错: {e}")
        import traceback
        traceback.print_exc()
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
