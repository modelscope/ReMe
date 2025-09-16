from typing import List

from flowllm import C, BaseAsyncOp
from flowllm.schema.message import Message
from loguru import logger

from reme_ai.schema.memory import BaseMemory, PersonalMemory


@C.register_op()
class GetReflectionSubjectOp(BaseAsyncOp):
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

    async def async_execute(self):
        """
        Generate reflection subjects (topics) from personal memories for insight extraction.

        Process:
        1. Retrieve personal memories and existing insights from context
        2. Check if sufficient memories exist for reflection
        3. Generate new reflection subjects using LLM
        4. Create insight memory objects for new subjects
        5. Store results in context for next operation
        """
        # Get memories from previous operation
        personal_memories = self.context.response.metadata.get("personal_memories", [])
        existing_insights = self.context.response.metadata.get("existing_insights", [])

        # Get operation parameters
        reflect_obs_cnt_threshold = self.op_params.get("reflect_obs_cnt_threshold", 10)
        reflect_num_questions = self.op_params.get("reflect_num_questions", 3)
        user_name = self.context.get("user_name", "user")

        # Validate sufficient memories for reflection
        if len(personal_memories) < reflect_obs_cnt_threshold:
            logger.info(f"Insufficient memories for reflection: {len(personal_memories)} < {reflect_obs_cnt_threshold}")
            self.context.response.metadata["insight_memories"] = []
            return

        # Extract existing insight subjects to avoid duplication
        existing_subjects = []
        if existing_insights:
            existing_subjects = [memory.content for memory in existing_insights if
                                 hasattr(memory, 'content') and memory.content]

        logger.info(f"Found {len(existing_subjects)} existing insight subjects")

        # Prepare memory content for LLM analysis
        memory_contents = []
        for memory in personal_memories:
            if hasattr(memory, 'content') and memory.content.strip():
                memory_contents.append(memory.content.strip())

        if not memory_contents:
            logger.warning("No valid memory content found for reflection")
            self.context.response.metadata["insight_memories"] = []
            return

        # Generate reflection subjects using LLM
        insight_memories = await self._generate_reflection_subjects(
            memory_contents, existing_subjects, user_name, reflect_num_questions
        )

        # Store results in context
        self.context.response.metadata["insight_memories"] = insight_memories
        logger.info(f"Generated {len(insight_memories)} new reflection subject memories")

    async def _generate_reflection_subjects(self, memory_contents: List[str], existing_subjects: List[str],
                                      user_name: str, num_questions: int) -> List[BaseMemory]:
        """
        Generate new reflection subjects using LLM analysis of memory contents.
        
        Args:
            memory_contents: List of memory content strings
            existing_subjects: List of already existing subject strings
            user_name: Target username
            num_questions: Maximum number of new subjects to generate
            
        Returns:
            List of PersonalMemory objects representing new reflection subjects
        """
        # Build LLM prompt
        system_prompt = self.prompt_format(
            prompt_name="get_reflection_subject_system",
            user_name=user_name,
            num_questions=num_questions
        )
        few_shot = self.prompt_format(
            prompt_name="get_reflection_subject_few_shot",
            user_name=user_name
        )
        user_query = self.prompt_format(
            prompt_name="get_reflection_subject_user_query",
            user_name=user_name,
            exist_keys=", ".join(existing_subjects) if existing_subjects else "None",
            user_query="\n".join(memory_contents)
        )

        full_prompt = f"{system_prompt}\n\n{few_shot}\n\n{user_query}"
        logger.info(f"Reflection subject prompt length: {len(full_prompt)} chars")

        def parse_reflection_response(message: Message) -> List[BaseMemory]:
            """Parse LLM response and create insight memories"""
            response_text = message.content
            logger.info(f"Reflection subjects response: {response_text}")

            # Parse new subjects using class method
            new_subjects = GetReflectionSubjectOp.parse_reflection_subjects_response(response_text, existing_subjects)

            # Create insight memory objects
            insight_memories = []
            for subject in new_subjects:
                insight_memory = self.new_insight_memory(
                    insight_content=subject,
                    target=user_name
                )
                insight_memories.append(insight_memory)
                logger.info(f"Created reflection subject: {subject}")

            return insight_memories

        # Generate subjects using LLM
        return await self.llm.achat(messages=[Message(content=full_prompt)], callback_fn=parse_reflection_response)

    def get_language_value(self, value_dict: dict):
        """Get language-specific value from dictionary"""
        return value_dict.get(self.language, value_dict.get("en"))

    @staticmethod
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
