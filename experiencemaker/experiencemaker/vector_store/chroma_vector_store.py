from typing import List, Iterable

import chromadb
from chromadb import Collection
from chromadb.config import Settings
from loguru import logger
from pydantic import Field, PrivateAttr, model_validator

from experiencemaker.embedding_model.openai_compatible_embedding_model import OpenAICompatibleEmbeddingModel
from experiencemaker.schema.vector_node import VectorNode
from experiencemaker.vector_store import VECTOR_STORE_REGISTRY
from experiencemaker.vector_store.base_vector_store import BaseVectorStore


@VECTOR_STORE_REGISTRY.register("chroma")
class ChromaVectorStore(BaseVectorStore):
    store_dir: str = Field(default="./chroma_vector_store")
    collections: dict = Field(default_factory=dict)
    _client: chromadb.Client = PrivateAttr()

    @model_validator(mode="after")
    def init_client(self):
        self._client = chromadb.Client(Settings(persist_directory=self.store_dir))
        return self

    def _get_collection(self, workspace_id: str) -> Collection:
        if workspace_id not in self.collections:
            self.collections[workspace_id] = self._client.get_or_create_collection(workspace_id)
        return self.collections[workspace_id]

    def exist_workspace(self, workspace_id: str, **kwargs) -> bool:
        return workspace_id in [c.name for c in self._client.list_collections()]

    def delete_workspace(self, workspace_id: str, **kwargs):
        self._client.delete_collection(workspace_id)
        if workspace_id in self.collections:
            del self.collections[workspace_id]

    def create_workspace(self, workspace_id: str, **kwargs):
        self.collections[workspace_id] = self._client.get_or_create_collection(workspace_id)

    def _iter_workspace_nodes(self, workspace_id: str, **kwargs) -> Iterable[VectorNode]:
        collection: Collection = self._get_collection(workspace_id)
        results = collection.get()
        for i in range(len(results["ids"])):
            node = VectorNode(workspace_id=workspace_id,
                              unique_id=results["ids"][i],
                              content=results["documents"][i],
                              metadata=results["metadatas"][i])
            yield node

    def search(self, query: str, workspace_id: str, top_k: int = 1, **kwargs) -> List[VectorNode]:
        if not self.exist_workspace(workspace_id=workspace_id):
            logger.warning(f"workspace_id={workspace_id} is not exists!")
            return []

        collection: Collection = self._get_collection(workspace_id)
        query_vector = self.embedding_model.get_embeddings(query)
        results = collection.query(query_embeddings=[query_vector], n_results=top_k)
        nodes = []
        for i in range(len(results["ids"][0])):
            node = VectorNode(workspace_id=workspace_id,
                              unique_id=results["ids"][0][i],
                              content=results["documents"][0][i],
                              metadata=results["metadatas"][0][i])
            nodes.append(node)
        return nodes

    def insert(self, nodes: VectorNode | List[VectorNode], workspace_id: str, **kwargs):
        if not self.exist_workspace(workspace_id=workspace_id):
            self.create_workspace(workspace_id=workspace_id)

        if isinstance(nodes, VectorNode):
            nodes = [nodes]

        embedded_nodes = [node for node in nodes if node.vector]
        not_embedded_nodes = [node for node in nodes if not node.vector]
        now_embedded_nodes = self.embedding_model.get_node_embeddings(not_embedded_nodes)
        all_nodes = embedded_nodes + now_embedded_nodes

        collection: Collection = self._get_collection(workspace_id)
        collection.add(ids=[n.unique_id for n in all_nodes],
                       embeddings=[n.vector for n in all_nodes],
                       documents=[n.content for n in all_nodes],
                       metadatas=[n.metadata for n in all_nodes])

    def delete(self, node_ids: str | List[str], workspace_id: str, **kwargs):
        if not self.exist_workspace(workspace_id=workspace_id):
            logger.warning(f"workspace_id={workspace_id} is not exists!")
            return

        if isinstance(node_ids, str):
            node_ids = [node_ids]

        collection: Collection = self._get_collection(workspace_id)
        collection.delete(ids=node_ids)


def main():
    from dotenv import load_dotenv
    load_dotenv()

    embedding_model = OpenAICompatibleEmbeddingModel(dimensions=64, model_name="text-embedding-v4")
    workspace_id = "chroma_test_index"

    chroma_store = ChromaVectorStore(
        embedding_model=embedding_model,
        store_dir="./chroma_test_db"
    )

    if chroma_store.exist_workspace(workspace_id):
        chroma_store.delete_workspace(workspace_id)
    chroma_store.create_workspace(workspace_id)

    sample_nodes = [
        VectorNode(
            unique_id="node1",
            workspace_id=workspace_id,
            content="Artificial intelligence is a technology that simulates human intelligence.",
            metadata={
                "node_type": "n1",
                "category": "tech"
            }
        ),
        VectorNode(
            unique_id="node2",
            workspace_id=workspace_id,
            content="AI is the future of mankind.",
            metadata={
                "node_type": "n1",
                "category": "tech"
            }
        ),
        VectorNode(
            unique_id="node3",
            workspace_id=workspace_id,
            content="I want to eat fish!",
            metadata={
                "node_type": "n2",
                "category": "food"
            }
        ),
        VectorNode(
            unique_id="node4",
            workspace_id=workspace_id,
            content="The bigger the storm, the more expensive the fish.",
            metadata={
                "node_type": "n1",
                "category": "food"
            }
        ),
    ]

    chroma_store.insert(sample_nodes, workspace_id=workspace_id)

    logger.info("=" * 20)
    results = chroma_store.search("What is AI?", top_k=5, workspace_id=workspace_id)
    for r in results:
        logger.info(r.model_dump(exclude={"vector"}))
    logger.info("=" * 20)

    node2_update = VectorNode(
        unique_id="node2",
        workspace_id=workspace_id,
        content="AI is the future of humanity and technology.",
        metadata={
            "node_type": "n1",
            "category": "tech",
            "updated": True
        }
    )
    chroma_store.delete(node2_update.unique_id, workspace_id=workspace_id)
    chroma_store.insert(node2_update, workspace_id=workspace_id)

    logger.info("Updated Result:")
    results = chroma_store.search("fish?", top_k=10, workspace_id=workspace_id)
    for r in results:
        logger.info(r.model_dump(exclude={"vector"}))
    logger.info("=" * 20)

    chroma_store.dump_workspace(workspace_id=workspace_id)

    chroma_store.delete_workspace(workspace_id=workspace_id)


if __name__ == "__main__":
    main()
    # launch with: python -m experiencemaker.storage.chroma_vector_store
