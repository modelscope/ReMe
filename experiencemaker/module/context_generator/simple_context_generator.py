from typing import List

from experiencemaker.module.context_generator.base_context_generator import BaseContextGenerator, \
    CONTEXT_GENERATOR_REGISTRY
from experiencemaker.schema.experience import Experience
from experiencemaker.schema.trajectory import Trajectory, ContextMessage
from experiencemaker.schema.vector_store_node import VectorStoreNode


@CONTEXT_GENERATOR_REGISTRY.register(name="simple")
class SimpleContextGenerator(BaseContextGenerator):

    def _build_retrieve_query(self, trajectory: Trajectory, **kwargs) -> str:
        query = ""
        if trajectory.current_step == 0:
            query = trajectory.query
        return query

    def _retrieve_by_query(self, trajectory: Trajectory, query: str, workspace_id: str, retrieve_top_k: int,
                           **kwargs) -> List[VectorStoreNode]:
        if not query:
            return []

        return self.vector_store.retrieve_by_query(query=query, top_k=retrieve_top_k, index_name=workspace_id, **kwargs)

    def _generate_context_message(self,
                                  trajectory: Trajectory,
                                  nodes: List[VectorStoreNode],
                                  **kwargs) -> ContextMessage:
        if not nodes:
            return ContextMessage(content="")

        content = "Previous Experience\n"
        for node in nodes:
            experience: Experience = Experience.from_vector_store_node(node)
            if not experience.experience_content:
                continue

            content += f"- {experience.experience_desc} {experience.experience_content}\n"
        content += "Please consider the helpful parts from these in answering the question, to make the response more comprehensive and substantial."

        return ContextMessage(content=content.strip())
