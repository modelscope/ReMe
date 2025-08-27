import json
import re
from typing import List

from flowllm.schema.message import Message, Trajectory
from flowllm.utils.llm_utils import merge_messages_content as merge_messages_content_flowllm
from loguru import logger


def merge_messages_content(messages: List[Message | dict]) -> str:
    return merge_messages_content_flowllm(messages)

def parse_json_experience_response(response: str) -> List[dict]:
    """Parse JSON formatted experience response"""
    try:
        # Extract JSON blocks
        json_pattern = r'```json\s*([\s\S]*?)\s*```'
        json_blocks = re.findall(json_pattern, response)

        if json_blocks:
            parsed = json.loads(json_blocks[0])

            # Handle array format
            if isinstance(parsed, list):
                experiences = []
                for exp_data in parsed:
                    if isinstance(exp_data, dict) and (
                            ("when_to_use" in exp_data and "experience" in exp_data) or
                            ("condition" in exp_data and "experience" in exp_data)
                    ):
                        experiences.append(exp_data)

                return experiences


            # Handle single object
            elif isinstance(parsed, dict) and (
                    ("when_to_use" in parsed and "experience" in parsed) or
                    ("condition" in parsed and "experience" in parsed)
            ):
                return [parsed]

        # Fallback: try to parse entire response
        parsed = json.loads(response)
        if isinstance(parsed, list):
            return parsed
        elif isinstance(parsed, dict):
            return [parsed]

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON experience response: {e}")

    return []


def get_trajectory_context(trajectory: Trajectory, step_sequence: List[Message]) -> str:
    """Get context of step sequence within trajectory"""
    try:
        # Find position of step sequence in trajectory
        start_idx = 0
        for i, step in enumerate(trajectory.messages):
            if step == step_sequence[0]:
                start_idx = i
                break

        # Extract before and after context
        context_before = trajectory.messages[max(0, start_idx - 2):start_idx]
        context_after = trajectory.messages[start_idx + len(step_sequence):start_idx + len(step_sequence) + 2]

        context = f"Query: {trajectory.metadata.get('query', 'N/A')}\n"

        if context_before:
            context += "Previous steps:\n" + "\n".join(
                [f"- {step.content[:100]}..." for step in context_before]) + "\n"

        if context_after:
            context += "Following steps:\n" + "\n".join([f"- {step.content[:100]}..." for step in context_after])

        return context

    except Exception as e:
        logger.error(f"Error getting trajectory context: {e}")
        return f"Query: {trajectory.metadata.get('query', 'N/A')}"


def parse_observation_response(response_text: str) -> List[dict]:
    """Parse observation response to extract structured data"""
    # Pattern to match both Chinese and English observation formats
    pattern = r"信息：<(\d+)>\s*<>\s*<([^<>]+)>\s*<([^<>]*)>|Information:\s*<(\d+)>\s*<>\s*<([^<>]+)>\s*<([^<>]*)>"
    matches = re.findall(pattern, response_text, re.IGNORECASE | re.MULTILINE)

    observations = []
    for match in matches:
        # Handle both Chinese and English patterns
        if match[0]:  # Chinese pattern
            idx_str, content, keywords = match[0], match[1], match[2]
        else:  # English pattern  
            idx_str, content, keywords = match[3], match[4], match[5]

        try:
            idx = int(idx_str)
            # Skip if content indicates no meaningful observation
            content_lower = content.lower().strip()
            if content_lower not in ['无', 'none', '', 'repeat']:
                observations.append({
                    "index": idx,
                    "content": content.strip(),
                    "keywords": keywords.strip() if keywords else ""
                })
        except ValueError:
            logger.warning(f"Invalid index format: {idx_str}")
            continue

    return observations


def parse_observation_with_time_response(response_text: str) -> List[dict]:
    """Parse observation with time response to extract structured data"""
    # Pattern to match both Chinese and English observation formats with time information
    # Chinese: 信息：<1> <时间信息或不输出> <明确的重要信息或"无"> <关键词>
    # English: Information: <1> <Time information or do not output> <Clear important information or "None"> <Keywords>
    pattern = r"信息：<(\d+)>\s*<([^<>]*)>\s*<([^<>]+)>\s*<([^<>]*)>|Information:\s*<(\d+)>\s*<([^<>]*)>\s*<([^<>]+)>\s*<([^<>]*)>"
    matches = re.findall(pattern, response_text, re.IGNORECASE | re.MULTILINE)

    observations = []
    for match in matches:
        # Handle both Chinese and English patterns
        if match[0]:  # Chinese pattern
            idx_str, time_info, content, keywords = match[0], match[1], match[2], match[3]
        else:  # English pattern  
            idx_str, time_info, content, keywords = match[4], match[5], match[6], match[7]

        try:
            idx = int(idx_str)
            # Skip if content indicates no meaningful observation
            content_lower = content.lower().strip()
            if content_lower not in ['无', 'none', '', 'repeat']:
                observations.append({
                    "index": idx,
                    "time_info": time_info.strip() if time_info else "",
                    "content": content.strip(),
                    "keywords": keywords.strip() if keywords else ""
                })
        except ValueError:
            logger.warning(f"Invalid index format: {idx_str}")
            continue

    return observations


def parse_reflection_subjects_response(response_text: str, existing_subjects: List[str] = None) -> List[str]:
    """Parse reflection subjects response to extract new subject attributes"""
    if existing_subjects is None:
        existing_subjects = []

    # Split response into lines and clean up
    lines = response_text.strip().split('\n')
    subjects = []

    for line in lines:
        line = line.strip()
        # Skip empty lines, "None" responses, and existing subjects
        if (line and
                line not in ['无', 'None', ''] and
                line not in existing_subjects and
                not line.startswith('新增') and  # Skip Chinese header
                not line.startswith('New ') and  # Skip English header
                len(line) > 1):  # Skip single character responses
            subjects.append(line)

    logger.info(f"Parsed {len(subjects)} new reflection subjects from response")
    return subjects


def parse_info_filter_response(response_text: str) -> List[tuple]:
    """Parse info filter response to extract message scores"""
    import re

    # Pattern to match both Chinese and English result formats
    # Chinese: 结果：<序号> <分数>
    # English: Result: <Index> <Score>
    pattern = r"结果：<(\d+)>\s*<([0-3])>|Result:\s*<(\d+)>\s*<([0-3])>"
    matches = re.findall(pattern, response_text, re.IGNORECASE | re.MULTILINE)

    scores = []
    for match in matches:
        # Handle both Chinese and English patterns
        if match[0]:  # Chinese pattern
            idx_str, score_str = match[0], match[1]
        else:  # English pattern
            idx_str, score_str = match[2], match[3]

        try:
            idx = int(idx_str)
            score = score_str
            scores.append((idx, score))
        except ValueError:
            logger.warning(f"Invalid index or score format: {idx_str}, {score_str}")
            continue

    logger.info(f"Parsed {len(scores)} info filter scores from response")
    return scores


def parse_long_contra_repeat_response(response_text: str) -> List[tuple]:
    """Parse long contra repeat response to extract judgments"""
    import re

    # Pattern to match both Chinese and English judgment formats
    # Chinese: 判断：<序号> <矛盾|被包含|无> <修改后的内容>
    # English: Judgment: <Index> <Contradiction|Contained|None> <Modified content>
    pattern = r"判断：<(\d+)>\s*<(矛盾|被包含|无)>\s*<([^<>]*)>|Judgment:\s*<(\d+)>\s*<(Contradiction|Contained|None)>\s*<([^<>]*)>"
    matches = re.findall(pattern, response_text, re.IGNORECASE | re.MULTILINE)

    judgments = []
    for match in matches:
        # Handle both Chinese and English patterns
        if match[0]:  # Chinese pattern
            idx_str, judgment, modified_content = match[0], match[1], match[2]
        else:  # English pattern
            idx_str, judgment, modified_content = match[3], match[4], match[5]

        try:
            idx = int(idx_str)
            judgments.append((idx, judgment, modified_content))
        except ValueError:
            logger.warning(f"Invalid index format: {idx_str}")
            continue

    logger.info(f"Parsed {len(judgments)} long contra repeat judgments from response")
    return judgments


def parse_update_insight_response(response_text: str, language: str = "en") -> str:
    """Parse update insight response to extract updated insight content"""
    import re

    # Pattern to match both Chinese and English insight formats
    # Chinese: {user_name}的资料: <信息>
    # English: {user_name}'s profile: <Information>
    if language in ["zh", "cn"]:
        pattern = r"的资料[：:]\s*<([^<>]+)>"
    else:
        pattern = r"profile[：:]\s*<([^<>]+)>"

    matches = re.findall(pattern, response_text, re.IGNORECASE | re.MULTILINE)

    if matches:
        insight_content = matches[0].strip()
        logger.info(f"Parsed insight content: {insight_content}")
        return insight_content

    # Fallback: try to find content between angle brackets
    fallback_pattern = r"<([^<>]+)>"
    fallback_matches = re.findall(fallback_pattern, response_text)
    if fallback_matches:
        # Get the last match as it's likely the final answer
        insight_content = fallback_matches[-1].strip()
        logger.info(f"Parsed insight content (fallback): {insight_content}")
        return insight_content

    logger.warning("No insight content found in response")
    return ""


def load_memories_from_vector_store(workspace_id: str, filter_criteria: dict, top_k: int,
                                    memory_category: str = ""):
    """
    Load memories from vector store based on filter criteria.
    
    Args:
        workspace_id: The workspace identifier
        filter_criteria: Dictionary containing filter criteria for memory retrieval
        top_k: Maximum number of memories to retrieve
        memory_category: Category label to add to memory metadata
        
    Returns:
        List of PersonalMemory objects loaded from vector store
    """
    from reme_ai.schema.memory import PersonalMemory

    try:
        # This is a placeholder implementation - in a real scenario, you would
        # integrate with your actual vector store (e.g., Chroma, Pinecone, etc.)
        logger.info(f"Loading memories from vector store for workspace: {workspace_id}")
        logger.info(f"Filter criteria: {filter_criteria}")
        logger.info(f"Top K: {top_k}")

        # For now, return empty list as placeholder
        # In real implementation, this would:
        # 1. Connect to vector store
        # 2. Apply filter criteria
        # 3. Retrieve top_k memories
        # 4. Convert vector nodes to PersonalMemory objects
        # 5. Add memory_category to metadata

        memories = []

        # Placeholder: Create some example memories for testing
        if memory_category == "insight":
            for i in range(min(top_k, 2)):
                memory = PersonalMemory(
                    workspace_id=workspace_id,
                    memory_type="personal_insight",
                    content=f"Sample insight memory {i + 1} for {filter_criteria.get('target', 'user')}",
                    target=filter_criteria.get('target', 'user'),
                    when_to_use=f"When analyzing user behavior patterns {i + 1}",
                    author="system",
                    metadata={
                        "memory_category": memory_category,
                        "filter_criteria": filter_criteria
                    }
                )
                memories.append(memory)

        logger.info(f"Loaded {len(memories)} memories from vector store")
        return memories

    except Exception as e:
        logger.error(f"Error loading memories from vector store: {e}")
        return []
