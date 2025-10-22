import datetime
from abc import ABC
from typing import List
from uuid import uuid4

from flowllm.schema.vector_node import VectorNode
from mcp.types import CallToolResult, TextContent
from pydantic import BaseModel, Field


class BaseMemory(BaseModel, ABC):
    workspace_id: str = Field(default="")
    memory_id: str = Field(default_factory=lambda: uuid4().hex)
    memory_type: str = Field(default=...)

    when_to_use: str = Field(default="")
    content: str | bytes = Field(default="")
    score: float = Field(default=0)

    time_created: str = Field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    time_modified: str = Field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    author: str = Field(default="")

    metadata: dict = Field(default_factory=dict)

    def update_modified_time(self):
        self.time_modified = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def update_metadata(self, new_metadata):
        self.metadata = new_metadata

    def to_vector_node(self) -> VectorNode:
        raise NotImplementedError

    @classmethod
    def from_vector_node(cls, node: VectorNode):
        raise NotImplementedError


class TaskMemory(BaseMemory):
    memory_type: str = Field(default="task")

    def to_vector_node(self) -> VectorNode:
        return VectorNode(unique_id=self.memory_id,
                          workspace_id=self.workspace_id,
                          content=self.when_to_use,
                          metadata={
                              "memory_type": self.memory_type,
                              "content": self.content,
                              "score": self.score,
                              "time_created": self.time_created,
                              "time_modified": self.time_modified,
                              "author": self.author,
                              "metadata": self.metadata,
                          })

    @classmethod
    def from_vector_node(cls, node: VectorNode) -> "TaskMemory":
        metadata = node.metadata.copy()
        return cls(workspace_id=node.workspace_id,
                   memory_id=node.unique_id,
                   memory_type=metadata.pop("memory_type"),
                   when_to_use=node.content,
                   content=metadata.pop("content"),
                   score=metadata.pop("score"),
                   time_created=metadata.pop("time_created"),
                   time_modified=metadata.pop("time_modified"),
                   author=metadata.pop("author"),
                   metadata=metadata.pop("metadata", {}))


class PersonalMemory(BaseMemory):
    memory_type: str = Field(default="personal")
    target: str = Field(default="")
    reflection_subject: str = Field(default="")  # For storing reflection subject attributes

    def to_vector_node(self) -> VectorNode:
        return VectorNode(unique_id=self.memory_id,
                          workspace_id=self.workspace_id,
                          content=self.when_to_use,
                          metadata={
                              "memory_type": self.memory_type,
                              "content": self.content,
                              "target": self.target,
                              "reflection_subject": self.reflection_subject,
                              "score": self.score,
                              "time_created": self.time_created,
                              "time_modified": self.time_modified,
                              "author": self.author,
                              "metadata": self.metadata,
                          })

    @classmethod
    def from_vector_node(cls, node: VectorNode) -> "PersonalMemory":
        metadata = node.metadata.copy()
        return cls(workspace_id=node.workspace_id,
                   memory_id=node.unique_id,
                   memory_type=metadata.pop("memory_type"),
                   when_to_use=node.content,
                   content=metadata.pop("content"),
                   target=metadata.pop("target", ""),
                   reflection_subject=metadata.pop("reflection_subject", ""),
                   score=metadata.pop("score"),
                   time_created=metadata.pop("time_created"),
                   time_modified=metadata.pop("time_modified"),
                   author=metadata.pop("author"),
                   metadata=metadata.pop("metadata", {}))


class ToolCallResult(BaseModel):
    create_time: str = Field(default="", description="Time of tool invocation")
    tool_name: str = Field(default=..., description="Name of the tool")
    input: dict | str = Field(default="", description="Tool input")
    output: str = Field(default="", description="Tool output")
    token_cost: int = Field(default=-1, description="Token consumption of the tool")
    success: bool = Field(default=True, description="Whether the tool invocation was successful")
    time_cost: float = Field(default=0, description="Time consumed by the tool invocation, in seconds")
    summary: str = Field(default="", description="Brief summary of the tool call result")
    evaluation: str = Field(default="", description="Detailed evaluation for the tool invocation")
    score: float = Field(default=0, description="Score of the Evaluation (0.0 for failure, 1.0 for complete success)")
    is_summarized: bool = Field(default=False, description="Whether this tool call has been included in a summary")

    metadata: dict = Field(default_factory=dict)

    def from_mcp_tool_result(self, tool_result: CallToolResult, max_char_len: int = None):
        text_list = []
        for content in tool_result.content:
            if isinstance(content, TextContent):
                text_list.append(content.text)

            else:
                raise NotImplementedError(f"content.type={type(content)} not supported")
        content = "\n".join(text_list)

        if max_char_len:
            content = content[:max_char_len]
        self.output = content

        self.success = not tool_result.is_error
        self.metadata.update(tool_result.meta)


class ToolMemory(BaseMemory):
    memory_type: str = Field(default="tool")
    tool_call_results: List[ToolCallResult] = Field(default_factory=list)

    def to_vector_node(self) -> VectorNode:
        return VectorNode(unique_id=self.memory_id,
                          workspace_id=self.workspace_id,
                          content=self.when_to_use,
                          metadata={
                              "memory_type": self.memory_type,
                              "content": self.content,
                              "score": self.score,
                              "time_created": self.time_created,
                              "time_modified": self.time_modified,
                              "author": self.author,
                              "tool_call_results": [x.model_dump() for x in self.tool_call_results],
                              "metadata": self.metadata,
                          })

    def statistic(self, recent_frequency: int = 20) -> dict:
        """
        Calculate statistical information for the most recent N tool calls.
        Returns avg token_cost, success rate, avg time_cost, and avg score.
        """
        if not self.tool_call_results:
            return {
                "total_calls": 0,
                "recent_calls_analyzed": 0,
                "avg_token_cost": 0.0,
                "success_rate": 0.0,
                "avg_time_cost": 0.0,
                "avg_score": 0.0
            }
        
        # Get the most recent N tool calls (or all if less than N)
        recent_calls = self.tool_call_results[-recent_frequency:]
        total_calls = len(self.tool_call_results)
        recent_calls_count = len(recent_calls)
        
        # Calculate statistics
        total_token_cost = sum(call.token_cost for call in recent_calls if call.token_cost >= 0)
        valid_token_calls = [call for call in recent_calls if call.token_cost >= 0]
        avg_token_cost = total_token_cost / len(valid_token_calls) if valid_token_calls else 0.0
        
        successful_calls = sum(1 for call in recent_calls if call.success)
        success_rate = successful_calls / recent_calls_count if recent_calls_count > 0 else 0.0
        
        total_time_cost = sum(call.time_cost for call in recent_calls)
        avg_time_cost = total_time_cost / recent_calls_count if recent_calls_count > 0 else 0.0
        
        total_score = sum(call.score for call in recent_calls)
        avg_score = total_score / recent_calls_count if recent_calls_count > 0 else 0.0
        
        return {
            "avg_token_cost": round(avg_token_cost, 2),
            "avg_time_cost": round(avg_time_cost, 3),
            "success_rate": round(success_rate, 4),
            "avg_score": round(avg_score, 3)
        }

    @classmethod
    def from_vector_node(cls, node: VectorNode) -> "ToolMemory":
        metadata = node.metadata.copy()
        tool_call_results = [ToolCallResult(**result) for result in metadata.pop("tool_call_results", [])]
        return cls(workspace_id=node.workspace_id,
                   memory_id=node.unique_id,
                   when_to_use=node.content,
                   memory_type=metadata.pop("memory_type"),
                   content=metadata.pop("content"),
                   score=metadata.pop("score"),
                   time_created=metadata.pop("time_created"),
                   time_modified=metadata.pop("time_modified"),
                   author=metadata.pop("author"),
                   tool_call_results=tool_call_results,
                   metadata=metadata.pop("metadata", {}))



def vector_node_to_memory(node: VectorNode):
    memory_type = node.metadata.get("memory_type")
    if memory_type == "task":
        return TaskMemory.from_vector_node(node)

    elif memory_type == "personal":
        return PersonalMemory.from_vector_node(node)

    elif memory_type == "tool":
        return ToolMemory.from_vector_node(node)

    else:
        raise RuntimeError(f"memory_type={memory_type} not supported!")


def dict_to_memory(memory_dict: dict):
    memory_type = memory_dict.get("memory_type", "task")
    if memory_type == "task":
        return TaskMemory(**memory_dict)

    elif memory_type == "personal":
        return PersonalMemory(**memory_dict)

    elif memory_type == "tool":
        return ToolMemory(**memory_dict)

    else:
        raise RuntimeError(f"memory_type={memory_type} not supported!")


def task_main():
    e1 = TaskMemory(
        workspace_id="w_1024",
        memory_id="123",
        when_to_use="test case use",
        content="test content",
        score=0.99,
        metadata={})
    print(e1.model_dump_json(indent=2))
    v1 = e1.to_vector_node()
    print(v1.model_dump_json(indent=2))
    e2 = vector_node_to_memory(v1)
    print(e2.model_dump_json(indent=2))


def personal_main():
    p1 = PersonalMemory(
        workspace_id="w_2048",
        memory_id="456",
        when_to_use="personal memory test case",
        content="personal test content",
        target="user_preferences",
        reflection_subject="learning_style",
        score=0.85,
        metadata={"category": "user_profile"})
    print("PersonalMemory test:")
    print(p1.model_dump_json(indent=2))
    v1 = p1.to_vector_node()
    print("VectorNode:")
    print(v1.model_dump_json(indent=2))
    p2 = vector_node_to_memory(v1)
    print("Reconstructed PersonalMemory:")
    print(p2.model_dump_json(indent=2))


def tool_main():
    # Create sample tool call results
    tool_result1 = ToolCallResult(
        create_time="2025-10-15 10:30:00",
        tool_name="file_reader",
        input={"file_path": "/test/file.txt"},
        output="File content successfully read",
        token_cost=50,
        success=True,
        time_cost=0.5,
        evaluation="Successfully executed",
        score=0.95
    )
    
    tool_result2 = ToolCallResult(
        create_time="2025-10-15 10:31:00",
        tool_name="data_processor",
        input={"data": "sample_data", "format": "json"},
        output="Data processed successfully",
        token_cost=75,
        success=True,
        time_cost=1.2,
        evaluation="Good performance",
        score=0.88
    )
    
    t1 = ToolMemory(
        workspace_id="w_4096",
        memory_id="789",
        memory_type="tool",
        when_to_use="tool execution memory test",
        content="tool execution test content",
        score=0.92,
        tool_call_results=[tool_result1, tool_result2],
        metadata={"execution_context": "test_environment"})
    
    print("ToolMemory test:")
    print(t1.model_dump_json(indent=2))
    v1 = t1.to_vector_node()
    print("VectorNode:")
    print(v1.model_dump_json(indent=2))
    t2 = ToolMemory.from_vector_node(v1)
    print("Reconstructed ToolMemory:")
    print(t2.model_dump_json(indent=2))


if __name__ == "__main__":
    print("=== Task Memory Test ===")
    # task_main()
    print("\n=== Personal Memory Test ===")
    # personal_main()
    print("\n=== Tool Memory Test ===")
    tool_main()
