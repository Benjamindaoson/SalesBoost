"""
CLI 入口
命令行接口
"""
import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.sales_simulation.scenarios.loader import ScenarioLoader
from app.sales_simulation.runners.single_agent_runner import SingleAgentRunner
from app.sales_simulation.runners.multi_agent_runner import MultiAgentRunner
from app.sales_simulation.evaluation.metrics_calculator import MetricsCalculator
from app.sales_simulation.evaluation.report_generator import ReportGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_simulation(
    scenario_id: str,
    agent_type: str = "single",
    num_runs: int = 5,
    seed: int = 42,
):
    """
    运行模拟
    
    Args:
        scenario_id: 场景 ID
        agent_type: Agent 类型
        num_runs: 运行次数
        seed: 随机种子
    """
    logger.info(f"Starting simulation: scenario={scenario_id}, agent_type={agent_type}, num_runs={num_runs}")
    
    # 加载场景
    loader = ScenarioLoader()
    scenario = loader.load_scenario(scenario_id)
    
    logger.info(f"Loaded scenario: {scenario.name}")
    
    # 选择运行器
    if agent_type == "single":
        runner = SingleAgentRunner(scenario)
    else:
        runner = MultiAgentRunner(scenario)
    
    # 运行轨迹
    run_id = f"cli_run_{scenario_id}"
    trajectories = []
    
    for i in range(num_runs):
        logger.info(f"Running trajectory {i+1}/{num_runs}")
        trajectory = await runner.run(run_id, i, seed + i)
        trajectories.append(trajectory)
        
        logger.info(
            f"Trajectory {i+1} completed: "
            f"steps={trajectory.total_steps}, score={trajectory.final_score:.2f}, "
            f"goal_achieved={trajectory.goal_achieved}"
        )
    
    # 计算指标
    logger.info("Calculating metrics...")
    metrics = MetricsCalculator.calculate_aggregated_metrics(run_id, trajectories)
    
    # 生成报告
    logger.info("Generating report...")
    json_report = ReportGenerator.generate_json_report(run_id, metrics, trajectories)
    markdown_report = ReportGenerator.generate_markdown_report(run_id, metrics)
    
    # 保存报告
    import json
    with open(f"report_{run_id}.json", 'w', encoding='utf-8') as f:
        json.dump(json_report, f, ensure_ascii=False, indent=2)
    
    with open(f"report_{run_id}.md", 'w', encoding='utf-8') as f:
        f.write(markdown_report)
    
    logger.info(f"Reports saved: report_{run_id}.json, report_{run_id}.md")
    
    # 打印摘要
    print("\n" + "="*50)
    print("模拟运行完成")
    print("="*50)
    print(f"场景: {scenario.name}")
    print(f"轨迹数量: {metrics.num_trajectories}")
    print(f"成功率: {metrics.success_rate:.1%}")
    print(f"平均得分: {metrics.avg_score:.2f}")
    print(f"整体质量: {metrics.overall_quality:.2f}")
    print(f"推荐建议: {metrics.recommendation}")
    print("="*50)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SalesBoost 销售模拟平台 CLI")
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # run 命令
    run_parser = subparsers.add_parser("run", help="运行模拟")
    run_parser.add_argument("--scenario", required=True, help="场景 ID")
    run_parser.add_argument("--agent-type", default="single", choices=["single", "multi"], help="Agent 类型")
    run_parser.add_argument("--num-runs", type=int, default=5, help="运行次数")
    run_parser.add_argument("--seed", type=int, default=42, help="随机种子")
    
    # list 命令
    list_parser = subparsers.add_parser("list", help="列出场景")
    
    args = parser.parse_args()
    
    if args.command == "run":
        asyncio.run(run_simulation(
            scenario_id=args.scenario,
            agent_type=args.agent_type,
            num_runs=args.num_runs,
            seed=args.seed,
        ))
    elif args.command == "list":
        loader = ScenarioLoader()
        scenarios = loader.list_scenario_ids()
        print("\n可用场景:")
        for scenario_id in scenarios:
            print(f"  - {scenario_id}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()




