import faiss
import numpy as np
from typing import List
from pydantic import Field, model_validator, PrivateAttr
from experiencemaker.model.base_embedding_model import BaseEmbeddingModel
from experiencemaker.schema.vector_store_node import VectorStoreNode
from experiencemaker.storage.base_vector_store import BaseVectorStore, VECTOR_STORE_REGISTRY

@VECTOR_STORE_REGISTRY.register("faiss")
class FaissVectorStore(BaseVectorStore):
    dim: int = Field(default=768)
    _index: faiss.IndexFlatIP = PrivateAttr()
    _id_map: dict = PrivateAttr(default_factory=dict)
    _vectors: list = PrivateAttr(default_factory=list)

    @model_validator(mode="after")
    def init_faiss(self):
        self._index = faiss.IndexFlatIP(self.dim)
        self._id_map = {}
        self._vectors = []
        return self

    def exist_index(self, index_name: str | None = None) -> bool:
        return hasattr(self, '_index')

    def create_index(self, index_name: str | None = None):
        self._index = faiss.IndexFlatIP(self.dim)
        self._id_map = {}
        self._vectors = []

    def delete_index(self, index_name: str | None = None):
        self._index = faiss.IndexFlatIP(self.dim)
        self._id_map = {}
        self._vectors = []

    def exist_id(self, unique_id: str, index_name: str | None = None):
        return unique_id in self._id_map

    def insert(self, nodes: VectorStoreNode | List[VectorStoreNode], index_name: str | None = None, **kwargs):
        if isinstance(nodes, VectorStoreNode):
            nodes = [nodes]
        nodes = self.embedding_model.get_node_embeddings(nodes)
        for node in nodes:
            vec = np.array(node.vector, dtype=np.float32)
            self._index.add(vec.reshape(1, -1))
            self._id_map[len(self._vectors)] = node.unique_id
            self._vectors.append(node)

    def update(self, nodes: VectorStoreNode | List[VectorStoreNode], index_name: str | None = None, **kwargs):
        self.delete_index()
        all_nodes = self._vectors + (nodes if isinstance(nodes, list) else [nodes])
        self.insert(all_nodes)

    def delete_by_id(self, unique_id: str, index_name: str | None = None, **kwargs):
        idx_to_remove = [i for i, node in enumerate(self._vectors) if node.unique_id == unique_id]
        if idx_to_remove:
            self._vectors = [node for node in self._vectors if node.unique_id != unique_id]
            self.create_index()
            self.insert(self._vectors)

    def retrieve_by_id(self, unique_id: str, index_name: str | None = None, **kwargs) -> VectorStoreNode | None:
        for node in self._vectors:
            if node.unique_id == unique_id:
                return node
        return None

    def retrieve_by_query(self, query: str, top_k: int = 1, index_name: str | None = None, **kwargs) -> List[VectorStoreNode]:
        query_vec = np.array(self.embedding_model.get_embeddings(query), dtype=np.float32).reshape(1, -1)
        D, I = self._index.search(query_vec, top_k)
        return [self._vectors[i] for i in I[0] if i >= 0] 