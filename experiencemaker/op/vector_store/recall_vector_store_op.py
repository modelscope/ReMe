from typing import List

from loguru import logger

from experiencemaker.op import OP_REGISTRY
from experiencemaker.op.base_op import BaseOp
from experiencemaker.schema.experience import BaseExperience, vector_node_to_experience
from experiencemaker.schema.request import RetrieverRequest
from experiencemaker.schema.response import RetrieverResponse
from experiencemaker.schema.vector_node import VectorNode


@OP_REGISTRY.register()
class RecallVectorStoreOp(BaseOp):
    SEARCH_QUERY = "search_query"
    SEARCH_MESSAGE = "search_message"

    def execute(self):
        # get query
        query = self.context.get_context(self.SEARCH_QUERY)
        assert query, "query should be not empty!"

        # retrieve from vector store
        request: RetrieverRequest = self.context.request
        nodes: List[VectorNode] = self.vector_store.search(query=query,
                                                           workspace_id=request.workspace_id,
                                                           top_k=request.top_k)

        # convert to experience, filter duplicate
        experience_list: List[BaseExperience] = []
        experience_content_list: List[str] = []
        for node in nodes:
            experience: BaseExperience = vector_node_to_experience(node)
            if experience.content not in experience_content_list:
                experience_list.append(experience)
                experience_content_list.append(experience.content)
        experience_size = len(experience_list)
        logger.info(f"retrieve experience size={experience_size}")

        # filter by score
        threshold_score: float | None = self.op_params.get("threshold_score", None)
        if threshold_score is not None:
            experience_list = [e for e in experience_list if e.score >= threshold_score or e.score is None]
            logger.info(f"after filter by threshold_score size={len(experience_list)}")

        # set response
        response: RetrieverResponse = self.context.response
        response.experience_list = experience_list
