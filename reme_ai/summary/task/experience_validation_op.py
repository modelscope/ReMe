import re
from typing import List, Dict, Any
from loguru import logger
import json

from flowllm import C, BaseLLMOp
from reme_ai.schema.memory import BaseMemory
from reme_ai.schema.message import Message


@C.register_op()
class ExperienceValidationOp(BaseLLMOp):
    current_path: str = __file__

    def execute(self):
        """Validate quality of extracted experiences"""
        experiences: List[BaseMemory] = self.context.get("experiences", [])
        
        if not experiences:
            logger.info("No experiences found for validation")
            return

        logger.info(f"Validating {len(experiences)} extracted experiences")

        # Validate experiences
        validated_experiences = []
        
        for experience in experiences:
            validation_result = self._validate_single_experience(experience)
            if validation_result and validation_result.get("is_valid", False):
                validated_experiences.append(experience)
            else:
                reason = validation_result.get("reason", "Unknown reason") if validation_result else "Validation failed"
                logger.warning(f"Experience validation failed: {reason}")

        logger.info(f"Validated {len(validated_experiences)} out of {len(experiences)} experiences")
        
        # Update context
        self.context.validated_experiences = validated_experiences

    def _validate_single_experience(self, experience: BaseMemory) -> Dict[str, Any]:
        """Validate single experience"""
        validation_info = self._llm_validate_experience(experience)
        logger.info(f"Validating: {validation_info}")
        return validation_info

    def _llm_validate_experience(self, experience: BaseMemory) -> Dict[str, Any]:
        """Validate experience using LLM"""
        try:
            prompt = self.prompt_format(
                prompt_name="experience_validation_prompt",
                condition=experience.when_to_use,
                experience_content=experience.content
            )

            def parse_validation(message: Message) -> Dict[str, Any]:
                try:
                    response_content = message.content
                    
                    # Parse validation result
                    # Extract JSON blocks
                    json_pattern = r'```json\s*([\s\S]*?)\s*```'
                    json_blocks = re.findall(json_pattern, response_content)

                    if json_blocks:
                        parsed = json.loads(json_blocks[0])
                    else:
                        parsed = {}

                    is_valid = parsed.get("is_valid",True)
                    score = parsed.get("score",0.5)

                    # Set validation threshold
                    validation_threshold = self.op_params.get("validation_threshold", 0.5)
                    
                    return {
                        "is_valid": is_valid and score >= validation_threshold,
                        "score": score,
                        "feedback": response_content,
                        "reason": "" if (is_valid and score >= validation_threshold) else f"Low validation score ({score:.2f}) or marked as invalid"
                    }
                    
                except Exception as e:
                    logger.error(f"Error parsing validation response: {e}")
                    return {
                        "is_valid": False,
                        "score": 0.0,
                        "feedback": "",
                        "reason": f"Parse error: {str(e)}"
                    }

            return self.llm.chat(messages=[Message(content=prompt)], callback_fn=parse_validation)

        except Exception as e:
            logger.error(f"LLM validation failed: {e}")
            return {
                "is_valid": False,
                "score": 0.0,
                "feedback": "",
                "reason": f"LLM validation error: {str(e)}"
            }