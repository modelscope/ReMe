import math
from pathlib import Path
from typing import List, Iterable

from loguru import logger
from pydantic import Field, model_validator

from v1.embedding_model.openai_compatible_embedding_model import OpenAICompatibleEmbeddingModel
from v1.schema.vector_node import VectorNode
from v1.vector_store import VECTOR_STORE_REGISTRY
from v1.vector_store.base_vector_store import BaseVectorStore


@VECTOR_STORE_REGISTRY.register("local_file")
class FileVectorStore(BaseVectorStore):
    store_dir: str = Field(default="./file_vector_store")

    @model_validator(mode="after")
    def init_client(self):
        store_path = Path(self.store_dir)
        store_path.mkdir(parents=True, exist_ok=True)
        return self

    @property
    def store_path(self) -> Path:
        return Path(self.store_dir)

    def exist_workspace(self, workspace_id: str, **kwargs) -> bool:
        return (self.store_path / f"{workspace_id}.jsonl").exists()

    def _delete_workspace(self, workspace_id: str, **kwargs):
        workspace_path = self.store_path / f"{workspace_id}.jsonl"
        if workspace_path.is_file():
            workspace_path.unlink()

    def _create_workspace(self, workspace_id: str, **kwargs):
        self._dump_to_path(nodes=[], workspace_id=workspace_id, path=self.store_path, **kwargs)

    def _iter_workspace_nodes(self, workspace_id: str, max_size: int = 10000, **kwargs) -> Iterable[VectorNode]:
        for i, node in enumerate(self._load_from_path(path=self.store_path, workspace_id=workspace_id, **kwargs)):
            if i < max_size:
                yield node

    @staticmethod
    def calculate_similarity(query_vector: List[float], node_vector: List[float]):
        assert query_vector, f"query_vector is empty!"
        assert node_vector, f"node_vector is empty!"
        assert len(query_vector) == len(node_vector), \
            f"query_vector.size={len(query_vector)} node_vector.size={len(node_vector)}"

        dot_product = sum(x * y for x, y in zip(query_vector, node_vector))
        norm_v1 = math.sqrt(sum(x ** 2 for x in query_vector))
        norm_v2 = math.sqrt(sum(y ** 2 for y in node_vector))
        return dot_product / (norm_v1 * norm_v2)

    def retrieve_by_query(self, query: str, workspace_id: str, top_k: int = 1, **kwargs) -> List[VectorNode]:
        query_vector = self.embedding_model.get_embeddings(query)
        nodes: List[VectorNode] = []
        for node in self._load_from_path(path=self.store_path, workspace_id=workspace_id, **kwargs):
            node.metadata["score"] = self.calculate_similarity(query_vector, node.vector)
            nodes.append(node)

        nodes = sorted(nodes, key=lambda x: x.metadata["score"], reverse=True)
        return nodes[:top_k]

    def insert(self, nodes: VectorNode | List[VectorNode], workspace_id: str, **kwargs):
        return self.update(nodes=nodes, workspace_id=workspace_id, **kwargs)

    def update(self, nodes: VectorNode | List[VectorNode], workspace_id: str, **kwargs):
        if isinstance(nodes, VectorNode):
            nodes = [nodes]

        all_node_dict = {}
        nodes: List[VectorNode] = self.embedding_model.get_node_embeddings(nodes)
        exist_nodes: List[VectorNode] = list(self._load_from_path(path=self.store_path, workspace_id=workspace_id))
        for node in exist_nodes:
            all_node_dict[node.unique_id] = node

        update_cnt = 0
        for node in nodes:
            if node.unique_id in all_node_dict:
                update_cnt += 1

            all_node_dict[node.unique_id] = node

        self._dump_to_path(nodes=list(all_node_dict.values()),
                           workspace_id=workspace_id,
                           path=self.store_path,
                           **kwargs)
        logger.info(f"update workspace_id={workspace_id} nodes.size={len(nodes)} all.size={len(all_node_dict)} "
                    f"update_cnt={update_cnt}")


def main():
    from experiencemaker.utils.util_function import load_env_keys
    load_env_keys()
    load_env_keys("../../.env")

    embedding_model = OpenAICompatibleEmbeddingModel(dimensions=1024)
    workspace_id = "rag_nodes_index"
    client = FileVectorStore(embedding_model=embedding_model)
    client.delete_workspace(workspace_id)
    client.create_workspace(workspace_id)

    sample_nodes = [
        VectorNode(
            workspace_id=workspace_id,
            content="Artificial intelligence is a technology that simulates human intelligence.",
            metadata={
                "node_type": "n1",
            }
        ),
        VectorNode(
            workspace_id=workspace_id,
            content="AI is the future of mankind.",
            metadata={
                "node_type": "n1",
            }
        ),
        VectorNode(
            workspace_id=workspace_id,
            content="I want to eat fish!",
            metadata={
                "node_type": "n2",
            }
        ),
        VectorNode(
            workspace_id=workspace_id,
            content="The bigger the storm, the more expensive the fish.",
            metadata={
                "node_type": "n1",
            }
        ),
    ]

    client.insert(sample_nodes, workspace_id)

    logger.info("=" * 20)
    results = client.retrieve_by_query("What is AI?", workspace_id=workspace_id, top_k=5)
    for r in results:
        logger.info(r.model_dump(exclude={"vector"}))
    logger.info("=" * 20)

    client.delete_workspace(workspace_id)
    client.dump_workspace(workspace_id)


if __name__ == "__main__":
    main()
    # launch with: python -m experiencemaker.storage.file_vector_store
