from typing import Dict, List

from flowllm import C, BaseLLMOp
from loguru import logger

from reme_ai.constants.common_constants import EXTRACT_TIME_DICT
from reme_ai.schema.memory import BaseMemory
from reme_ai.utils.datetime_handler import DatetimeHandler


@C.register_op()
class FuseRerankOp(BaseLLMOp):
    """
    Reranks the memory nodes by scores, types, and temporal relevance. Formats the top-K reranked nodes to print.
    """
    file_path: str = __file__

    @staticmethod
    def match_memory_time(extract_time_dict: Dict[str, str], memory: BaseMemory):
        """
        Determines whether the memory is relevant based on time matching.
        """
        if extract_time_dict:
            match_event_flag = True
            for k, v in extract_time_dict.items():
                event_value = memory.metadata.get(f"event_{k}", "")
                if event_value in ["-1", v]:
                    continue
                else:
                    match_event_flag = False
                    break

            match_msg_flag = True
            for k, v in extract_time_dict.items():
                msg_value = memory.metadata.get(f"msg_{k}", "")
                if msg_value == v:
                    continue
                else:
                    match_msg_flag = False
                    break
        else:
            match_event_flag = False
            match_msg_flag = False

        memory.metadata["match_event_flag"] = str(int(match_event_flag))
        memory.metadata["match_msg_flag"] = str(int(match_msg_flag))
        return match_event_flag, match_msg_flag

    def execute(self):
        """
        Executes the reranking process on memories considering their scores, types, and temporal relevance.

        This method performs the following steps:
        1. Retrieves extraction time data and a list of memories from the context.
        2. Reranks memories based on a combination of their original score, type,
           and temporal alignment with extracted events/messages.
        3. Selects the top-K reranked memories according to the predefined threshold.
        4. Optionally infuses inferred time information into the content of selected memories.
        5. Logs reranking details and formats the final list of memories for output.
        """
        # Get operation parameters
        fuse_score_threshold = self.op_params.get("fuse_score_threshold", 0.1)
        fuse_ratio_dict = self.op_params.get("fuse_ratio_dict", {})
        fuse_time_ratio = self.op_params.get("fuse_time_ratio", 2.0)
        output_memory_max_count = self.op_params.get("output_memory_max_count", 5)

        # Parse input parameters from the context
        extract_time_dict: Dict[str, str] = self.context.get(EXTRACT_TIME_DICT, {})
        memory_list: List[BaseMemory] = self.context.response.metadata.get("memory_list", [])

        # Check if memories are available; warn and return if not
        if not memory_list:
            logger.warning("Memory list is empty.")
            self.context.response.answer = ""
            return

        logger.info(f"Fuse reranking {len(memory_list)} memories")

        # Perform reranking based on score, type, and time relevance
        reranked_memories = []
        for memory in memory_list:
            # Skip memories below the fuse score threshold
            memory_score = memory.score or 0.0
            if memory_score < fuse_score_threshold:
                continue

            # Calculate type-based adjustment factor
            memory_type = memory.metadata.get("memory_type", "default")
            if memory_type not in fuse_ratio_dict:
                logger.warning(f"{memory_type} factor is not configured!")
            type_ratio: float = fuse_ratio_dict.get(memory_type, 0.1)

            # Determine time relevance adjustment factor
            match_event_flag, match_msg_flag = self.match_memory_time(
                extract_time_dict=extract_time_dict, memory=memory)
            time_ratio: float = fuse_time_ratio if match_event_flag or match_msg_flag else 1.0

            # Apply reranking score adjustments
            memory.score = memory_score * type_ratio * time_ratio
            reranked_memories.append(memory)

        # Sort and select top-k memories
        reranked_memories = sorted(reranked_memories,
                                   key=lambda x: x.score or 0.0,
                                   reverse=True)[:output_memory_max_count]

        # Build result
        formatted_memories = []
        for memory in reranked_memories:
            # Log reranking details including flags for event and message matches
            logger.info(f"Rerank Stage: Content={memory.content}, Score={memory.score}, "
                        f"Event Flag={memory.metadata.get('match_event_flag', '0')}, "
                        f"Message Flag={memory.metadata.get('match_msg_flag', '0')}")

            # Format memory with timestamp if available
            if hasattr(memory, 'timestamp') and memory.timestamp:
                dt_handler = DatetimeHandler(memory.timestamp)
                datetime_str = dt_handler.datetime_format("%Y-%m-%d %H:%M:%S")
                weekday = dt_handler.get_dt_info_dict(self.language)["weekday"]
                formatted_content = f"[{datetime_str} {weekday}] {memory.content}"
            else:
                formatted_content = memory.content

            formatted_memories.append(formatted_content)

        # Store results in context
        self.context.response.metadata["memory_list"] = reranked_memories
        self.context.response.answer = "\n".join(formatted_memories)
