"""
金融实体关系的schema定义
"""

from dataclasses import dataclass
from typing import List


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

    def __post_init__(self):
        """初始化后的验证"""
        if not isinstance(self.confidence, (int, float)) or not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be a float between 0 and 1")

        if self.relation not in ["正向", "负向", "中性"]:
            raise ValueError("relation must be one of: 正向, 负向, 中性")

    def to_dict(self):
        """转换为字典格式"""
        return {
            "input_entities": self.input_entities,
            "output_entities": self.output_entities,
            "relation": self.relation,
            "reasoning": self.reasoning,
            "source": self.source,
            "confidence": self.confidence,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建实例"""
        return cls(**data)

    def __str__(self):
        return f"{self.input_entities} -> {self.output_entities} ({self.relation}, 置信度: {self.confidence})"
