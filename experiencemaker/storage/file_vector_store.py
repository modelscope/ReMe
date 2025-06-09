import json
import math
import threading
from pathlib import Path
from typing import List, Any

from loguru import logger
from pydantic import Field, model_validator, PrivateAttr

from experiencemaker.model.openai_compatible_embedding_model import OpenAICompatibleEmbeddingModel
from experiencemaker.schema.vector_store_node import VectorStoreNode
from experiencemaker.storage.base_vector_store import BaseVectorStore, VECTOR_STORE_REGISTRY


class FileVectorStore(BaseVectorStore):
    store_dir: str = Field(default="./")
    index_name: str = Field(default=...)
    index_path: Path | None = Field(default=None)
    _thread_lock: Any = PrivateAttr()

    @model_validator(mode="after")
    def init_client(self):
        self._thread_lock = threading.Lock()

        store_path = Path(self.store_dir)
        store_path.mkdir(parents=True, exist_ok=True)
        self.index_path = store_path / f"{self.index_name}.jsonl"
        if not self.index_path.exists():
            self.index_path.touch(exist_ok=True)
        return self

    def delete_index(self):
        with self._thread_lock:
            if self.index_path.exists() and self.index_path.is_file():
                self.index_path.unlink()

    def create_index(self):
        with self._thread_lock:
            if not self.index_path.exists():
                self.index_path.touch(exist_ok=True)

    def load(self) -> List[VectorStoreNode]:
        nodes = []
        with self._thread_lock:
            with open(self.index_path) as f:
                for line in f:
                    if line.strip():
                        nodes.append(VectorStoreNode(**json.loads(line)))
        return nodes

    def _load(self) -> List[VectorStoreNode]:
        nodes = []
        with self._thread_lock:
            with open(self.index_path) as f:
                for line in f:
                    if line.strip():
                        nodes.append(VectorStoreNode(**json.loads(line)))
        return nodes

    def _dump(self, nodes: List[VectorStoreNode]):
        with self._thread_lock:
            with open(self.index_path, "w") as f:
                for doc in nodes:
                    f.write(doc.model_dump_json() + "\n")

    def exist_id(self, unique_id: str):
        nodes = self._load()
        for node in nodes:
            if node.unique_id == unique_id:
                return True
        return False

    def insert(self, nodes: VectorStoreNode | List[VectorStoreNode], **kwargs):
        return self.update(nodes, **kwargs)

    def update(self, nodes: VectorStoreNode | List[VectorStoreNode], **kwargs):
        if isinstance(nodes, VectorStoreNode):
            nodes = [nodes]

        all_node_dict = {}
        nodes: List[VectorStoreNode] = self.embedding_model.get_node_embeddings(nodes)
        exist_nodes: List[VectorStoreNode] = self._load()
        for node in exist_nodes:
            all_node_dict[node.unique_id] = node

        update_cnt = 0
        for node in nodes:
            if node.unique_id in all_node_dict:
                update_cnt += 1

            all_node_dict[node.unique_id] = node

        self._dump(list(all_node_dict.values()))
        logger.info(f"update nodes.size={len(nodes)} all.size={len(all_node_dict)} update_cnt={update_cnt}")

    def delete_by_id(self, unique_id: str, **kwargs):
        nodes = self._load()
        dump_nodes: List[VectorStoreNode] = []
        for node in nodes:
            if node.unique_id != unique_id:
                dump_nodes.append(node)

        if len(dump_nodes) < len(nodes):
            self._dump(dump_nodes)
            logger.info(f"delete_by_id unique_id={unique_id}")

    def retrieve_by_id(self, unique_id: str, **kwargs) -> VectorStoreNode | None:
        nodes = self._load()
        for node in nodes:
            if node.unique_id == unique_id:
                return node
        return None

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

    def retrieve_by_query(self, query: str, top_k: int = 3, **kwargs) -> List[VectorStoreNode]:
        query_vector = self.embedding_model.get_embeddings(query)
        nodes: List[VectorStoreNode] = self._load()
        for node in nodes:
            node.metadata["score"] = self.calculate_similarity(query_vector, node.vector)

        nodes = sorted(nodes, key=lambda x: x.metadata["score"], reverse=True)
        return nodes[:top_k]


VECTOR_STORE_REGISTRY.register(FileVectorStore, "local_file")


def main():
    from experiencemaker.utils.util_function import load_env_keys
    load_env_keys()

    embedding_model = OpenAICompatibleEmbeddingModel(dimensions=1024)
    index_name = "rag_nodes_index"
    client = FileVectorStore(embedding_model=embedding_model, index_name=index_name)
    client.delete_index()
    client.create_index()

    sample_nodes = [
        VectorStoreNode(
            workspace_id="w1",
            content="Artificial intelligence is a technology that simulates human intelligence.",
            metadata={
                "node_type": "n1",
            }
        ),
        VectorStoreNode(
            workspace_id="w1",
            content="AI is the future of mankind.",
            metadata={
                "node_type": "n1",
            }
        ),
        VectorStoreNode(
            workspace_id="w1",
            content="I want to eat fish!",
            metadata={
                "node_type": "n2",
            }
        ),
        VectorStoreNode(
            workspace_id="w2",
            content="The bigger the storm, the more expensive the fish.",
            metadata={
                "node_type": "n1",
            }
        ),
    ]

    client.insert(sample_nodes)

    logger.info("=" * 20)
    results = client.retrieve_by_query("What is AI?", top_k=5)
    for r in results:
        logger.info(r.model_dump(exclude={"vector"}))
    logger.info("=" * 20)


if __name__ == "__main__":
    main()
    # launch with: python -m experiencemaker.storage.file_vector_store
