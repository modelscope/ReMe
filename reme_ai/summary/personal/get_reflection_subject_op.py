from typing import List

from flowllm import C, BaseLLMOp
from flowllm.schema.message import Message
from loguru import logger

from reme_ai.schema.memory import BaseMemory, PersonalMemory
from reme_ai.utils.op_utils import parse_reflection_subjects_response


@C.register_op()
class GetReflectionSubjectOp(BaseLLMOp):
    """
    A specialized operation class responsible for retrieving unreflected memory nodes,
    generating reflection prompts with current insights, invoking an LLM for fresh insights,
    parsing the LLM responses, forming new insight nodes, and updating memory statuses accordingly.
    """
    file_path: str = __file__

    def new_insight_memory(self, insight_content: str, target: str) -> PersonalMemory:
        """
        Creates a new PersonalMemory for an insight with the given content.

        Args:
            insight_content (str): The content of the insight.
            target (str): The target person the insight is about.

        Returns:
            PersonalMemory: A new PersonalMemory instance representing the insight.
        """
        return PersonalMemory(
            workspace_id=self.context.get("workspace_id", ""),
            content=insight_content,
            target=target,
            reflection_subject=insight_content,  # Store the subject in the dedicated field
            author=getattr(self.llm, "model_name", "system"),
            metadata={
                "insight_type": "reflection_subject",
                "memory_type": "personal_topic"
            }
        )

    def execute(self):
        """
        Executes the main logic of reflecting on personal memories to derive new insights.

        Steps include:
        - Retrieving personal memories from context.
        - Checking if there are enough memories to process.
        - Compiling existing insight subjects.
        - Generating a reflection prompt with system message, few-shot examples, and user queries.
        - Calling the language model for new insights.
        - Parsing the model's responses for new insight subjects.
        - Creating new insight memories and storing them in context.
        """
        # Get personal memories from context
        personal_memories: List[BaseMemory] = self.context.response.metadata.get("personal_memories", [])
        existing_insights: List[BaseMemory] = self.context.response.metadata.get("existing_insights", [])

        # Get parameters from operation config
        reflect_obs_cnt_threshold: int = self.op_params.get("reflect_obs_cnt_threshold", 10)
        reflect_num_questions: int = self.op_params.get("reflect_num_questions", 1)

        user_name = self.context.get("user_name", "user")

        # Check if we have enough memories to reflect on
        if len(personal_memories) < reflect_obs_cnt_threshold:
            logger.info(
                f"personal_memories count({len(personal_memories)}) < threshold({reflect_obs_cnt_threshold}), skip reflection.")
            return

        # Compile existing insight subjects
        exist_keys: List[str] = []
        if existing_insights:
            exist_keys = [memory.content for memory in existing_insights if hasattr(memory, 'content')]

        logger.info(f"exist_keys={exist_keys}")

        # Generate reflection prompt components
        user_query_list = []
        for memory in personal_memories:
            if hasattr(memory, 'content') and memory.content:
                user_query_list.append(memory.content)

        # Determine number of questions to ask
        if reflect_num_questions > 0:
            num_questions = reflect_num_questions
        else:
            num_questions = len(user_query_list)

        # Create prompt using the prompt format method
        system_prompt = self.prompt_format(prompt_name="get_reflection_subject_system",
                                           user_name=user_name,
                                           num_questions=num_questions)
        few_shot = self.prompt_format(prompt_name="get_reflection_subject_few_shot", user_name=user_name)
        user_query = self.prompt_format(prompt_name="get_reflection_subject_user_query",
                                        user_name=user_name,
                                        exist_keys=", ".join(exist_keys),
                                        user_query="\n".join(user_query_list))

        full_prompt = f"{system_prompt}\n\n{few_shot}\n\n{user_query}"
        logger.info(f"reflection_subject_prompt={full_prompt}")

        def parse_reflection_subjects(message: Message) -> List[BaseMemory]:
            """Parse LLM response and create insight memories"""
            response_text = message.content
            logger.info(f"reflection_subject_response={response_text}")

            # Parse new insight subjects using utility function
            new_subjects = parse_reflection_subjects_response(response_text, exist_keys)

            insight_memories = []
            for subject in new_subjects:
                # Create insight memory
                insight_memory = self.new_insight_memory(
                    insight_content=subject,
                    target=user_name
                )
                insight_memories.append(insight_memory)
                logger.info(f"Created reflection subject: {subject}")

            return insight_memories

        # Use LLM chat with callback function
        insight_memories = self.llm.chat(messages=[Message(content=full_prompt)], callback_fn=parse_reflection_subjects)

        # Store results in context
        self.context.response.metadata["insight_memories"] = insight_memories
        logger.info(f"Generated {len(insight_memories)} reflection subject memories")

    def get_language_value(self, value_dict: dict):
        """Get language-specific value from dictionary"""
        return value_dict.get(self.language, value_dict.get("en"))
