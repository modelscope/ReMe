from typing import List

from experiencemaker.module.context_generator.base_context_generator import BaseContextGenerator, \
    CONTEXT_GENERATOR_REGISTRY
from experiencemaker.schema.trajectory import Trajectory, ContextMessage
from experiencemaker.schema.vector_store_node import VectorStoreNode


class SimpleContextGenerator(BaseContextGenerator):

    def _build_retrieve_query(self, trajectory: Trajectory, **kwargs) -> str:
        query = ""
        if trajectory.current_step == 0:
            query = trajectory.query
        return query

    def _retrieve_by_query(self, trajectory: Trajectory, query: str, **kwargs) -> List[VectorStoreNode]:
        if not query:
            return []

        return self.vector_store.retrieve_by_query(query=query, top_k=self.vector_store_top_k)

    def _generate_context_message(self,
                                  trajectory: Trajectory,
                                  nodes: List[VectorStoreNode],
                                  **kwargs) -> ContextMessage:
        if not nodes:
            return ContextMessage(content="")

        content = ""
        for node in nodes:
            experience = node.metadata.get("experience", "")
            if not experience:
                continue

            content += f"- {node.content} {experience}\n"
        return ContextMessage(content=content.strip())


CONTEXT_GENERATOR_REGISTRY.register(SimpleContextGenerator, "simple")
