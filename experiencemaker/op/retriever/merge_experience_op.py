from typing import List

from loguru import logger

from experiencemaker.op import OP_REGISTRY
from experiencemaker.op.base_op import BaseOp
from experiencemaker.schema.experience import BaseExperience
from experiencemaker.schema.response import RetrieverResponse


@OP_REGISTRY.register()
class MergeExperienceOp(BaseOp):

    def execute(self):
        response: RetrieverResponse = self.context.response
        experience_list: List[BaseExperience] = response.experience_list

        if not experience_list:
            return

        content_collector = ["Previous Experience"]
        for experience in experience_list:
            if not experience.content:
                continue

            content_collector.append(f"- when_to_use: {experience.when_to_use}\n"
                                     f"content: {experience.content}\n")
        content_collector.append("Please consider the helpful parts from these in answering the question, "
                                 "to make the response more comprehensive and substantial.")
        response.experience_merged = "\n".join(content_collector)
        logger.info(f"experience_merged={response.experience_merged}")
