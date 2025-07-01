from abc import ABC
from typing import List

from pydantic import BaseModel, Field

from experiencemaker.schema.trajectory import Trajectory


class BaseRequest(BaseModel, ABC):
    metadata: dict = Field(default_factory=dict)
    workspace_id: str = Field(default="")


# class AgentWrapperRequest(BaseRequest):
#     query: str = Field(default="")

# Experience retriever
class ContextGeneratorRequest(BaseRequest):
    messages: List[dict] = Field(default_factory=list)
    query: str = Field(default="")
    retrieve_top_k: int = Field(default=1)

# Experience summarizer
class SummarizerRequest(BaseRequest):
    messages_list: List[List[dict]] | List[dict] = Field(default_factory=list)
    scores: List[float] | float = Field(default_factory=list, description="scores 要看summarizer对于score的定义")
    summarizer_config: str = "如何summary "

"""
class DB相关操作

清空db
db复制

1. 新增es数据库
2. cursor帮忙写两个
3. 导出功能，上传Experience

"""
#