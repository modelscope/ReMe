from flowllm.context import C
from flowllm.schema.tool_call import ToolCall

from reme_ai.agent.tools.llm_mock_search_op import LLMMockSearchOp


@C.register_op()
class SearchToolA(LLMMockSearchOp):
    def __init__(self, llm: str = "qwen3_30b_instruct", **kwargs):
        # Configure for fast but shallow performance
        simple_config = {
            "success_rate": 0.9,  # High success rate for simple queries
            "extra_time": 0,  # Very fast (0.2-0.5s range)
            "relevance_ratio": 0.9,  # High relevance
            "content_length": "short"  # Concise answers
        }

        medium_config = {
            "success_rate": 0.2,  # Lower success for medium queries
            "extra_time": 0,  # Still fast
            "relevance_ratio": 0.2,  # Moderate relevance
            "content_length": "short"  # Limited depth
        }

        complex_config = {
            "success_rate": 0.5,  # Poor success rate for complex queries
            "extra_time": 0,  # Fast but insufficient
            "relevance_ratio": 0.5,  # Low relevance (often misses key aspects)
            "content_length": "short"  # Too shallow for complex topics
        }

        super().__init__(llm=llm,
                         simple_config=simple_config,
                         medium_config=medium_config,
                         complex_config=complex_config,
                         **kwargs)

    def build_tool_call(self) -> ToolCall:
        tool_call = super().build_tool_call()
        tool_call.description += " Best suited for simple queries."
        return tool_call

@C.register_op()
class SearchToolB(LLMMockSearchOp):
    def __init__(self, llm: str = "qwen3_30b_instruct", **kwargs):
        # Configure for balanced performance
        simple_config = {
            "success_rate": 0.3,  # Very high success rate
            "extra_time": 0,  # Moderate speed (1.0-1.5s range)
            "relevance_ratio": 0.3,  # High relevance
            "content_length": "medium"  # More detailed than needed for simple
        }

        medium_config = {
            "success_rate": 0.9,  # Excellent success rate
            "extra_time": 0,  # Balanced speed
            "relevance_ratio": 0.9,  # High relevance
            "content_length": "medium"  # Perfect depth for medium queries
        }

        complex_config = {
            "success_rate": 0.5,  # Good success rate
            "extra_time": 0,  # Still reasonable speed
            "relevance_ratio": 0.5,  # Decent relevance but not exhaustive
            "content_length": "medium"  # Covers main points but lacks depth
        }

        super().__init__(llm=llm,
                         simple_config=simple_config,
                         medium_config=medium_config,
                         complex_config=complex_config,
                         **kwargs)

    def build_tool_call(self) -> ToolCall:
        tool_call = super().build_tool_call()
        tool_call.description += " Best suited for medium complexity queries."
        return tool_call


@C.register_op()
class SearchToolC(LLMMockSearchOp):

    def __init__(self, llm: str = "qwen3_30b_instruct", **kwargs):
        # Configure for comprehensive but costly performance
        simple_config = {
            "success_rate": 0.3,  # Good but not optimal (over-processing)
            "extra_time": 0,  # Slow (3.0-4.0s range)
            "relevance_ratio": 0.3,  # High relevance but unnecessary depth
            "content_length": "long"  # Too detailed for simple queries
        }

        medium_config = {
            "success_rate": 0.4,  # High success rate
            "extra_time": 0,  # Slow but thorough
            "relevance_ratio": 0.4,  # High relevance with extra context
            "content_length": "long"  # More depth than needed
        }

        complex_config = {
            "success_rate": 0.9,  # Excellent success rate
            "extra_time": 0,  # Slow but comprehensive (3.5-5.0s range)
            "relevance_ratio": 0.9,  # Very high relevance
            "content_length": "long"  # Perfect depth for complex queries
        }

        super().__init__(llm=llm,
                         simple_config=simple_config,
                         medium_config=medium_config,
                         complex_config=complex_config,
                         **kwargs)

    def build_tool_call(self) -> ToolCall:
        tool_call = super().build_tool_call()
        tool_call.description += " Best suited for complex queries."
        return tool_call
