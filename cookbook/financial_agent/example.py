#!/usr/bin/env python3
"""
金融分析师Agent使用示例
"""

import sys
from experiencemaker.utils.util_function import load_env_keys

load_env_keys("../../.env")
# 添加项目根目录到Python路径
# project_root = Path(__file__).parent.parent
# sys.path.insert(0, str(project_root))
sys.path.append(".")
from financial_agent import FinancialAgent




def main():
    """主函数"""
    # 加载环境变量
    load_env_keys()

    # 初始实体列表
    init_entity_list = [
        "美元债务",
        "美债利率",
        "美元指数",
        "工业金属银、铜、铝",
        "黄金",
        "稳定币",
        "石油",
        "能源",
        "军工",
        "海运",
    ]

    # 创建金融分析师Agent
    agent = FinancialAgent(
        model_name="qwen-max-2025-01-25",
        verbose=True
    )

    # 执行知识图谱构建
    output_file = "金融知识图谱.jsonl"
    stats = agent.execute(
        init_entity_list=init_entity_list,
        dump_file_path=output_file,
        max_iter=5,  # 减少迭代次数用于演示
        search_strategy="mixed"
    )

    print("\n" + "=" * 50)
    print("执行结果统计:")
    print(f"总实体数: {stats['total_entities']}")
    print(f"总关系数: {stats['total_relations']}")
    print(f"新增关系数: {stats['new_relations']}")
    print(f"迭代次数: {stats['iterations']}")
    print("=" * 50)

    # 查询示例
    print("\n查询示例:")
    query_results = agent.query_knowledge_graph("美元")
    print(f"包含'美元'的关系数量: {len(query_results)}")

    # 获取特定实体的关系
    print("\n美元指数的关系:")
    usd_relations = agent.get_entity_relations("美元指数")
    for i, relation in enumerate(usd_relations[:3]):  # 只显示前3个
        print(f"{i + 1}. {relation}")

    # 生成可视化图表
    print("\n生成可视化图表...")
    agent.visualize("financial_knowledge_graph.html")

    print(f"\n知识图谱已保存到: {output_file}")
    print("可视化图表已保存到: financial_knowledge_graph.html")


if __name__ == "__main__":
    main()
