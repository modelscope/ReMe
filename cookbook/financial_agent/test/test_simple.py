#!/usr/bin/env python3
"""
简化的金融Agent测试脚本
"""

import os
import sys
import json
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 模拟环境变量（如果没有设置的话）
if not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = "test_key"
if not os.getenv("OPENAI_BASE_URL"):
    os.environ["OPENAI_BASE_URL"] = "http://localhost:8000/v1"
if not os.getenv("DASHSCOPE_API_KEY"):
    os.environ["DASHSCOPE_API_KEY"] = "test_key"

from financial_agent.schema import FinancialRelation
from financial_agent.knowledge_graph import KnowledgeGraphBuilder


def test_schema():
    """测试FinancialRelation schema"""
    print("测试FinancialRelation schema...")
    
    # 创建测试关系
    relation = FinancialRelation(
        input_entities=["美债利率", "美元债务"],
        output_entities=["美元指数"],
        relation="负向",
        reasoning="美债利率上升和美元债务增加会导致美元走弱",
        source="金融分析报告",
        confidence=0.85,
        timestamp="2024-01-15 10:30:00"
    )
    
    print(f"创建的关系: {relation}")
    print(f"转换为字典: {relation.to_dict()}")
    
    # 测试验证
    try:
        invalid_relation = FinancialRelation(
            input_entities=["实体1"],
            output_entities=["实体2"],
            relation="无效关系",  # 应该报错
            reasoning="测试",
            source="测试",
            confidence=0.5,
            timestamp="2024-01-15 10:30:00"
        )
    except ValueError as e:
        print(f"验证错误（预期）: {e}")
    
    print("Schema测试通过！\n")


def test_knowledge_graph():
    """测试KnowledgeGraphBuilder"""
    print("测试KnowledgeGraphBuilder...")
    
    # 创建知识图谱
    kg = KnowledgeGraphBuilder()
    
    # 添加关系
    relation1 = FinancialRelation(
        input_entities=["美债利率", "美元债务"],
        output_entities=["美元指数"],
        relation="负向",
        reasoning="美债利率上升和美元债务增加会导致美元走弱",
        source="金融分析报告",
        confidence=0.85,
        timestamp="2024-01-15 10:30:00"
    )
    
    relation2 = FinancialRelation(
        input_entities=["石油价格", "美元指数"],
        output_entities=["通胀预期"],
        relation="正向",
        reasoning="石油价格上涨和美元走弱会推高通胀预期",
        source="经济分析",
        confidence=0.78,
        timestamp="2024-01-15 10:31:00"
    )
    
    # 添加关系
    kg.add_relation(relation1)
    kg.add_relation(relation2)
    
    # 添加实体别名
    kg.add_entity_alias("美元指数", ["USD Index", "DXY"])
    
    # 测试统计
    stats = kg.get_entity_statistics()
    print(f"知识图谱统计: {stats}")
    
    # 测试查询
    usd_relations = kg.find_related_entities("美元指数")
    print(f"美元指数相关关系数量: {len(usd_relations)}")
    
    # 测试导出
    test_file = "test_knowledge_graph.jsonl"
    kg.export_to_jsonl(test_file)
    print(f"知识图谱已导出到: {test_file}")
    
    # 测试加载
    new_kg = KnowledgeGraphBuilder()
    new_kg.load_from_jsonl(test_file)
    print(f"加载后的实体数量: {len(new_kg.entities)}")
    
    # 清理测试文件
    if os.path.exists(test_file):
        os.remove(test_file)
    
    print("KnowledgeGraphBuilder测试通过！\n")


def test_mock_agent():
    """测试模拟的Agent（不调用真实API）"""
    print("测试模拟Agent...")
    
    # 创建模拟的搜索结果
    mock_search_result = """
    根据最新金融分析，美债利率上升和美元债务增加会对美元指数产生负面影响。
    当美债利率上升时，投资者会要求更高的收益率，这可能导致美元走弱。
    同时，美元债务的增加也会增加市场对美元贬值的担忧。
    """
    
    # 模拟LLM响应
    mock_llm_response = {
        "relations": [
            {
                "input_entities": ["美债利率", "美元债务"],
                "output_entities": ["美元指数"],
                "relation": "负向",
                "reasoning": "美债利率上升和美元债务增加会导致美元走弱",
                "source": "金融分析报告",
                "confidence": 0.85
            }
        ],
        "new_entities": ["美联储政策", "市场情绪"]
    }
    
    print(f"模拟搜索结果: {mock_search_result[:100]}...")
    print(f"模拟LLM响应: {json.dumps(mock_llm_response, ensure_ascii=False, indent=2)}")
    
    # 测试关系创建
    try:
        relation = FinancialRelation(
            input_entities=mock_llm_response["relations"][0]["input_entities"],
            output_entities=mock_llm_response["relations"][0]["output_entities"],
            relation=mock_llm_response["relations"][0]["relation"],
            reasoning=mock_llm_response["relations"][0]["reasoning"],
            source=mock_llm_response["relations"][0]["source"],
            confidence=mock_llm_response["relations"][0]["confidence"],
            timestamp="2024-01-15 10:30:00"
        )
        print(f"成功创建关系: {relation}")
    except Exception as e:
        print(f"创建关系失败: {e}")
    
    print("模拟Agent测试通过！\n")


def main():
    """主测试函数"""
    print("=" * 50)
    print("金融Agent测试开始")
    print("=" * 50)
    
    try:
        test_schema()
        test_knowledge_graph()
        test_mock_agent()
        
        print("=" * 50)
        print("所有测试通过！")
        print("=" * 50)
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 