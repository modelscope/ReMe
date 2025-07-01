#!/usr/bin/env python3
"""
金融分析师Agent测试脚本
"""

import json
import os
import datetime
from typing import List, Dict, Set
from dataclasses import dataclass
import hashlib
import re

from experiencemaker.model import OpenAICompatibleBaseLLM
from experiencemaker.tool import CodeTool, DashscopeSearchTool
from experiencemaker.schema.trajectory import Message
from experiencemaker.enumeration.role import Role


@dataclass
class FinancialRelation:
    """金融实体关系的数据结构"""
    input_entities: List[str]
    output_entities: List[str]
    relation: str  # "正向", "负向", "中性"
    reasoning: str
    source: str
    confidence: float
    timestamp: str


class FinancialAgent:
    """金融分析师Agent"""
    
    def __init__(self, model_name: str = "qwen-max-2025-01-25"):
        """初始化金融分析师Agent"""
        self.llm = OpenAICompatibleBaseLLM(model_name=model_name)
        self.search_tool = DashscopeSearchTool()
        self.code_tool = CodeTool()
        self.tools = [self.search_tool, self.code_tool]
        
        # 存储实体和关系
        self.entities: Set[str] = set()
        self.relations: List[FinancialRelation] = []
        self.relation_hashes: Set[str] = set()  # 用于去重
        
        # 系统提示词
        self.system_prompt = """你是一个专业的金融分析师，专门负责分析金融市场中各种实体之间的逻辑关系。

你的任务：
1. 通过搜索发现多个实体之间的逻辑关系
2. 不断补充新的实体到实体列表中
3. 将多跳的实体关系拆分成多个单跳的实体关系

实体关系格式：
{
    "input_entities": ["实体1", "实体2"],
    "output_entities": ["实体3", "实体4"],
    "relation": "正向、负向、中性", 
    "reasoning": "实体1和实体2是通过什么样的逻辑影响到实体3和实体4",
    "source": "来源",
    "confidence": "置信度(0-1)",
    "timestamp": "时间戳",
}

请确保：
- 关系描述准确、具体
- 置信度合理评估
- 来源信息完整
- 时间戳格式：YYYY-MM-DD HH:MM:SS
"""

    def _generate_relation_hash(self, relation: FinancialRelation) -> str:
        """生成关系的哈希值用于去重"""
        content = f"{sorted(relation.input_entities)}_{sorted(relation.output_entities)}_{relation.relation}_{relation.reasoning}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _add_relation(self, relation: FinancialRelation) -> bool:
        """添加关系，如果重复则返回False"""
        relation_hash = self._generate_relation_hash(relation)
        if relation_hash in self.relation_hashes:
            return False
        
        self.relation_hashes.add(relation_hash)
        self.relations.append(relation)
        
        # 添加新实体到实体列表
        for entity in relation.input_entities + relation.output_entities:
            self.entities.add(entity)
        
        return True
    
    def _load_existing_relations(self, file_path: str):
        """加载已存在的关系数据"""
        if not os.path.exists(file_path):
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        relation = FinancialRelation(**data)
                        self._add_relation(relation)
            print(f"Loaded {len(self.relations)} existing relations from {file_path}")
        except Exception as e:
            print(f"Error loading existing relations: {e}")
    
    def _save_relations(self, file_path: str):
        """保存关系到文件"""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            for relation in self.relations:
                f.write(json.dumps(relation.__dict__, ensure_ascii=False) + '\n')
        print(f"Saved {len(self.relations)} relations to {file_path}")
    
    def _search_entity_relations(self, entity_list: List[str]) -> List[FinancialRelation]:
        """搜索实体间的关系"""
        # 构建搜索查询
        entities_str = "、".join(entity_list[:5])  # 限制实体数量
        query = f"请分析以下金融实体之间的关系：{entities_str}。请详细说明它们之间的逻辑关系，包括正向、负向或中性的影响关系。"
        
        # 使用搜索工具
        search_result = self.search_tool.execute(query=query)
        
        # 使用LLM分析搜索结果并提取关系
        analysis_prompt = f"""
基于以下搜索结果，请分析金融实体之间的关系：

搜索结果：
{search_result[:1000] if isinstance(search_result, str) else str(search_result)[:1000]}  # 限制长度

当前实体列表：
{entity_list[:10]}  # 限制显示数量

请提取出实体间的关系，格式如下（JSON格式）：
{{
    "relations": [
        {{
            "input_entities": ["实体1", "实体2"],
            "output_entities": ["实体3", "实体4"],
            "relation": "正向/负向/中性",
            "reasoning": "详细的分析逻辑",
            "source": "信息来源",
            "confidence": 0.8
        }}
    ],
    "new_entities": ["新实体1", "新实体2"]
}}

请确保：
1. 关系描述准确具体
2. 置信度在0-1之间
3. 如果发现新的相关实体，请添加到new_entities中
4. 只返回JSON格式，不要其他内容
"""

        messages = [
            Message(role=Role.SYSTEM, content=self.system_prompt),
            Message(role=Role.USER, content=analysis_prompt)
        ]
        
        response = self.llm._chat(messages, self.tools)
        
        try:
            # 尝试解析JSON响应
            content = str(response.content)
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                relations = []
                for rel_data in data.get("relations", []):
                    relation = FinancialRelation(
                        input_entities=rel_data["input_entities"],
                        output_entities=rel_data["output_entities"],
                        relation=rel_data["relation"],
                        reasoning=rel_data["reasoning"],
                        source=rel_data["source"],
                        confidence=rel_data["confidence"],
                        timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
                    relations.append(relation)
                
                # 添加新实体
                for new_entity in data.get("new_entities", []):
                    self.entities.add(new_entity)
                
                return relations
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            print(f"Response content: {response.content}")
        
        return []
    
    def execute(self, init_entity_list: List[str], dump_file_path: str, max_iter: int = 5):
        """
        执行金融知识图谱构建
        
        Args:
            init_entity_list: 初始实体列表
            dump_file_path: 输出文件路径
            max_iter: 最大迭代次数
        """
        print(f"Starting financial knowledge graph construction with {len(init_entity_list)} initial entities")
        
        # 1. 初始化实体列表
        self.entities = set(init_entity_list)
        
        # 2. 加载历史数据
        self._load_existing_relations(dump_file_path)
        
        # 3. 迭代搜索
        iteration = 0
        new_relations_count = 0
        
        while iteration < max_iter:
            iteration += 1
            print(f"Iteration {iteration}/{max_iter}")
            
            # 搜索实体间关系
            entity_list = list(self.entities)
            relations = self._search_entity_relations(entity_list)
            
            # 添加新关系
            added_count = 0
            for relation in relations:
                if self._add_relation(relation):
                    added_count += 1
            
            new_relations_count += added_count
            print(f"Added {added_count} new relations in iteration {iteration}")
            
            # 检查是否还有新的关系可以添加
            if added_count == 0:
                print("No new relations found, stopping iteration")
                break
            
            # 保存中间结果
            if iteration % 2 == 0:
                self._save_relations(dump_file_path)
        
        # 4. 保存最终结果
        self._save_relations(dump_file_path)
        
        print(f"Financial knowledge graph construction completed!")
        print(f"Total entities: {len(self.entities)}")
        print(f"Total relations: {len(self.relations)}")
        print(f"New relations added: {new_relations_count}")
        
        return {
            "entities": list(self.entities),
            "relations": [rel.__dict__ for rel in self.relations],
            "total_entities": len(self.entities),
            "total_relations": len(self.relations),
            "new_relations": new_relations_count
        }


def main():
    """主函数"""
    from experiencemaker.utils.util_function import load_env_keys
    
    # 加载环境变量
    load_env_keys()
    
    # 初始实体列表
    init_entities = [
        "美元债务",
        "美债利率", 
        "美元指数",
        "黄金",
        "石油",
    ]
    
    # 创建Agent并执行
    agent = FinancialAgent()
    result = agent.execute(
        init_entity_list=init_entities,
        dump_file_path="test/金融知识图谱.jsonl",
        max_iter=3  # 减少迭代次数用于测试
    )
    
    print("=" * 50)
    print("构建完成！")
    print(f"总实体数: {result['total_entities']}")
    print(f"总关系数: {result['total_relations']}")
    print(f"新增关系数: {result['new_relations']}")
    print("=" * 50)


if __name__ == "__main__":
    main() 