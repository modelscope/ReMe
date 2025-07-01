"""
金融知识图谱构建器
"""

import hashlib
import json
import os
from typing import List, Set, Dict

from schema import FinancialRelation


class KnowledgeGraphBuilder:
    """金融知识图谱构建器"""

    def __init__(self):
        """初始化知识图谱构建器"""
        self.entities: Set[str] = set()
        self.relations: List[FinancialRelation] = []
        self.relation_hashes: Set[str] = set()  # 用于去重
        self.entity_aliases: Dict[str, Set[str]] = {}  # 实体别名映射

    def _generate_relation_hash(self, relation: FinancialRelation) -> str:
        """生成关系的哈希值用于去重"""
        content = f"{sorted(relation.input_entities)}_{sorted(relation.output_entities)}_{relation.relation}_{relation.reasoning}"
        return hashlib.md5(content.encode()).hexdigest()

    def add_relation(self, relation: FinancialRelation) -> bool:
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

    def add_entity_alias(self, main_entity: str, aliases: List[str]):
        """添加实体别名"""
        if main_entity not in self.entity_aliases:
            self.entity_aliases[main_entity] = set()

        for alias in aliases:
            self.entity_aliases[main_entity].add(alias)
            self.entities.add(alias)

    def get_entity_aliases(self, entity: str) -> Set[str]:
        """获取实体的所有别名"""
        for main_entity, aliases in self.entity_aliases.items():
            if entity in aliases or entity == main_entity:
                return aliases | {main_entity}
        return {entity}

    def find_related_entities(self, entity: str, max_depth: int = 2) -> List[FinancialRelation]:
        """查找与指定实体相关的所有关系"""
        related_relations = []
        visited_entities = set()
        entities_to_check = {entity}

        for depth in range(max_depth):
            current_entities = entities_to_check.copy()
            entities_to_check.clear()

            for relation in self.relations:
                # 检查关系是否涉及当前实体
                relation_entities = set(relation.input_entities + relation.output_entities)
                if relation_entities & current_entities:
                    related_relations.append(relation)
                    # 添加新的实体到下一轮检查
                    entities_to_check.update(relation_entities - visited_entities)

            visited_entities.update(current_entities)

            if not entities_to_check:
                break

        return related_relations

    def get_entity_statistics(self) -> Dict:
        """获取实体统计信息"""
        return {
            "total_entities": len(self.entities),
            "total_relations": len(self.relations),
            "unique_relations": len(self.relation_hashes),
            "entity_aliases": len(self.entity_aliases)
        }

    def export_to_jsonl(self, file_path: str):
        """导出到JSONL文件"""
        # os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            for relation in self.relations:
                f.write(json.dumps(relation.to_dict(), ensure_ascii=False) + '\n')

    def load_from_jsonl(self, file_path: str):
        """从JSONL文件加载"""
        if not os.path.exists(file_path):
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    relation = FinancialRelation.from_dict(data)
                    self.add_relation(relation)

    def export_to_networkx_format(self) -> Dict:
        """导出为NetworkX可用的格式"""
        nodes = []
        edges = []

        # 添加节点
        for entity in self.entities:
            nodes.append({
                "id": entity,
                "label": entity,
                "type": "entity"
            })

        # 添加边
        for i, relation in enumerate(self.relations):
            for input_entity in relation.input_entities:
                for output_entity in relation.output_entities:
                    edges.append({
                        "source": input_entity,
                        "target": output_entity,
                        "relation": relation.relation,
                        "reasoning": relation.reasoning,
                        "confidence": relation.confidence,
                        "source_info": relation.source,
                        "timestamp": relation.timestamp
                    })

        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": self.get_entity_statistics()
        }

    def visualize_graph(self, output_path: str = "financial_knowledge_graph.html"):
        """生成可视化图表（HTML格式）"""
        try:
            import plotly.graph_objects as go
            import networkx as nx

            # 创建NetworkX图
            G = nx.DiGraph()

            # 添加节点
            for entity in self.entities:
                G.add_node(entity)

            # 添加边
            for relation in self.relations:
                for input_entity in relation.input_entities:
                    for output_entity in relation.output_entities:
                        G.add_edge(
                            input_entity,
                            output_entity,
                            relation=relation.relation,
                            confidence=relation.confidence
                        )

            # 使用spring布局
            pos = nx.spring_layout(G, k=1, iterations=50)

            # 创建边轨迹
            edge_x = []
            edge_y = []
            edge_text = []

            for edge in G.edges(data=True):
                x0, y0 = pos[edge[0]]
                x1, y1 = pos[edge[1]]
                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])
                edge_text.append(f"{edge[0]} → {edge[1]} ({edge[2]['relation']})")

            edge_trace = go.Scatter(
                x=edge_x, y=edge_y,
                line=dict(width=0.5, color='#888'),
                hoverinfo='text',
                text=edge_text,
                mode='lines')

            # 创建节点轨迹
            node_x = []
            node_y = []
            node_text = []

            for node in G.nodes():
                x, y = pos[node]
                node_x.append(x)
                node_y.append(y)
                node_text.append(node)

            node_trace = go.Scatter(
                x=node_x, y=node_y,
                mode='markers+text',
                hoverinfo='text',
                text=node_text,
                textposition="top center",
                marker=dict(
                    showscale=True,
                    colorscale='YlGnBu',
                    size=10,
                    color=[],
                    line_width=2))

            # 设置节点颜色
            node_adjacency_list = []
            for node in G.nodes():
                node_adjacency_list.append(len(list(G.neighbors(node))))
            node_trace.marker.color = node_adjacency_list

            # 创建图形
            fig = go.Figure(data=[edge_trace, node_trace],
                            layout=go.Layout(
                                title='金融知识图谱',
                                showlegend=False,
                                hovermode='closest',
                                margin=dict(b=20, l=5, r=5, t=40),
                                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                            )

            fig.write_html(output_path)
            print(f"知识图谱已保存到: {output_path}")

        except ImportError:
            print("需要安装 plotly 和 networkx 来生成可视化图表")
            print("运行: pip install plotly networkx")
