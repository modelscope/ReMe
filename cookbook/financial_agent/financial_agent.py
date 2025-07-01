"""
金融分析师Agent主类
"""

import datetime
import json
import re
from typing import List, Dict

from loguru import logger

from experiencemaker.enumeration.role import Role
from experiencemaker.model import OpenAICompatibleBaseLLM
from experiencemaker.schema.trajectory import Message
from experiencemaker.tool import CodeTool, DashscopeSearchTool
from knowledge_graph import KnowledgeGraphBuilder
from schema import FinancialRelation


class FinancialAgent:
    """金融分析师Agent"""

    def __init__(self, model_name: str = "qwen-max-2025-01-25", verbose: bool = True):
        """初始化金融分析师Agent"""
        self.llm = OpenAICompatibleBaseLLM(model_name=model_name)
        self.search_tool = DashscopeSearchTool()
        self.code_tool = CodeTool()
        self.tools = [self.search_tool, self.code_tool]
        self.verbose = verbose

        # 知识图谱构建器
        self.knowledge_graph = KnowledgeGraphBuilder()

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
- 多跳关系要拆分成多个单跳关系
"""

    def _search_entity_relations(self, entity_list: List[str]) -> List[FinancialRelation]:
        """搜索实体间的关系"""
        if self.verbose:
            logger.info(f"Searching relations for entities: {entity_list[:5]}...")

        # 构建搜索查询
        entities_str = "、".join(entity_list[:5])  # 限制实体数量
        query = f"请分析以下金融实体之间的关系：{entities_str}。请详细说明它们之间的逻辑关系，包括正向、负向或中性的影响关系。"

        # 使用搜索工具
        try:
            search_result = self.search_tool.execute(query=query)
            if self.verbose:
                logger.info(f"Search completed, result length: {len(str(search_result))}")
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

        # 使用LLM分析搜索结果并提取关系
        analysis_prompt = f"""
基于以下搜索结果，请分析金融实体之间的关系：

搜索结果：
{search_result[:10000]}

当前实体列表：
{entity_list[:100]}

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
5. 多跳关系要拆分成多个单跳关系
"""

        messages = [
            Message(role=Role.SYSTEM, content=self.system_prompt),
            Message(role=Role.USER, content=analysis_prompt)
        ]

        try:
            response = self.llm.chat(messages, self.tools)

            # 尝试解析JSON响应
            content = str(response.content)
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())

                relations = []
                for rel_data in data.get("relations", []):
                    try:
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
                    except Exception as e:
                        logger.exception(f"Failed to create relation: {e}, data: {rel_data}")

                # 添加新实体
                for new_entity in data.get("new_entities", []):
                    self.knowledge_graph.entities.add(new_entity)

                if self.verbose:
                    logger.info(
                        f"Extracted {len(relations)} relations and {len(data.get('new_entities', []))} new entities")

                return relations
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            if self.verbose:
                logger.error(f"Response content: {response.content if 'response' in locals() else 'No response'}")

        return []

    def _search_specific_entity_pairs(self, entity_pairs: List[List[str]]) -> List[FinancialRelation]:
        """搜索特定实体对之间的关系"""
        all_relations = []

        for pair in entity_pairs:
            if len(pair) < 2:
                continue

            query = f"请分析{pair[0]}和{pair[1]}之间的金融关系，包括它们如何相互影响，以及对其他金融实体的影响。"

            try:
                search_result = self.search_tool.execute(query=query)

                analysis_prompt = f"""
基于搜索结果，分析{pair[0]}和{pair[1]}之间的关系：

搜索结果：
{search_result[:800] if isinstance(search_result, str) else str(search_result)[:800]}

请提取关系，格式如下（JSON格式）：
{{
    "relations": [
        {{
            "input_entities": ["{pair[0]}", "{pair[1]}"],
            "output_entities": ["影响实体1", "影响实体2"],
            "relation": "正向/负向/中性",
            "reasoning": "详细分析",
            "source": "来源",
            "confidence": 0.8
        }}
    ]
}}

只返回JSON格式。
"""

                messages = [
                    Message(role=Role.SYSTEM, content=self.system_prompt),
                    Message(role=Role.USER, content=analysis_prompt)
                ]

                response = self.llm.chat(messages, self.tools)

                content = str(response.content)
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())

                    for rel_data in data.get("relations", []):
                        try:
                            relation = FinancialRelation(
                                input_entities=rel_data["input_entities"],
                                output_entities=rel_data["output_entities"],
                                relation=rel_data["relation"],
                                reasoning=rel_data["reasoning"],
                                source=rel_data["source"],
                                confidence=rel_data["confidence"],
                                timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            )
                            all_relations.append(relation)
                        except Exception as e:
                            logger.warning(f"Failed to create relation: {e}")

            except Exception as e:
                logger.error(f"Error searching pair {pair}: {e}")

        return all_relations

    def _generate_entity_pairs(self, entity_list: List[str], max_pairs: int = 10) -> List[List[str]]:
        """生成实体对用于搜索"""
        pairs = []
        entities = list(entity_list)

        # 生成所有可能的二元组合
        for i in range(len(entities)):
            for j in range(i + 1, len(entities)):
                pairs.append([entities[i], entities[j]])
                if len(pairs) >= max_pairs:
                    break
            if len(pairs) >= max_pairs:
                break

        return pairs

    def execute(self, init_entity_list: List[str], dump_file_path: str, max_iter: int = 10,
                search_strategy: str = "mixed") -> Dict:
        """
        执行金融知识图谱构建
        
        Args:
            init_entity_list: 初始实体列表
            dump_file_path: 输出文件路径
            max_iter: 最大迭代次数
            search_strategy: 搜索策略 ("general", "pairs", "mixed")
        
        Returns:
            执行结果统计
        """
        logger.info(f"Starting financial knowledge graph construction with {len(init_entity_list)} initial entities")

        # 1. 初始化实体列表
        self.knowledge_graph.entities = set(init_entity_list)

        # 2. 加载历史数据
        self.knowledge_graph.load_from_jsonl(dump_file_path)

        # 3. 迭代搜索
        iteration = 0
        total_new_relations = 0

        while iteration < max_iter:
            iteration += 1
            logger.info(f"Iteration {iteration}/{max_iter}")

            new_relations_count = 0

            if search_strategy in ["general", "mixed"]:
                # 通用搜索
                entity_list = list(self.knowledge_graph.entities)
                relations = self._search_entity_relations(entity_list)

                for relation in relations:
                    if self.knowledge_graph.add_relation(relation):
                        new_relations_count += 1

            if search_strategy in ["pairs", "mixed"] and iteration % 2 == 0:
                # 实体对搜索
                entity_list = list(self.knowledge_graph.entities)
                entity_pairs = self._generate_entity_pairs(entity_list, max_pairs=5)
                relations = self._search_specific_entity_pairs(entity_pairs)

                for relation in relations:
                    if self.knowledge_graph.add_relation(relation):
                        new_relations_count += 1

            total_new_relations += new_relations_count
            logger.info(f"Added {new_relations_count} new relations in iteration {iteration}")

            # 检查是否还有新的关系可以添加
            if new_relations_count == 0:
                logger.info("No new relations found, stopping iteration")
                break

            # 保存中间结果
            self.knowledge_graph.export_to_jsonl(dump_file_path)

        # 4. 保存最终结果
        self.knowledge_graph.export_to_jsonl(dump_file_path)

        # 5. 生成统计信息
        stats = self.knowledge_graph.get_entity_statistics()
        stats["new_relations"] = total_new_relations
        stats["iterations"] = iteration

        logger.info(f"Financial knowledge graph construction completed!")
        logger.info(f"Total entities: {stats['total_entities']}")
        logger.info(f"Total relations: {stats['total_relations']}")
        logger.info(f"New relations added: {total_new_relations}")

        return stats

    def query_knowledge_graph(self, query: str) -> List[FinancialRelation]:
        """查询知识图谱"""
        # 简单的关键词匹配查询
        query_lower = query.lower()
        results = []

        for relation in self.knowledge_graph.relations:
            # 检查输入实体、输出实体、推理过程是否包含查询关键词
            all_text = " ".join([
                " ".join(relation.input_entities),
                " ".join(relation.output_entities),
                relation.reasoning,
                relation.source
            ]).lower()

            if query_lower in all_text:
                results.append(relation)

        return results

    def get_entity_relations(self, entity: str) -> List[FinancialRelation]:
        """获取特定实体的所有关系"""
        return self.knowledge_graph.find_related_entities(entity)

    def visualize(self, output_path: str = "financial_knowledge_graph.html"):
        """生成可视化图表"""
        self.knowledge_graph.visualize_graph(output_path)
