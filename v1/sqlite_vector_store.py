import sqlite3
import json
from typing import List
from pydantic import Field, model_validator, PrivateAttr
from experiencemaker.model.base_embedding_model import BaseEmbeddingModel
from experiencemaker.schema.vector_store_node import VectorStoreNode
from experiencemaker.storage.base_vector_store import BaseVectorStore, VECTOR_STORE_REGISTRY

@VECTOR_STORE_REGISTRY.register("sqlite")
class SQLiteVectorStore(BaseVectorStore):
    db_path: str = Field(default="./vector_store.db")
    _conn: sqlite3.Connection = PrivateAttr()

    @model_validator(mode="after")
    def init_db(self):
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.index_name} (
                unique_id TEXT PRIMARY KEY,
                workspace_id TEXT,
                content TEXT,
                metadata TEXT,
                vector TEXT
            )
        """)
        self._conn.commit()
        return self

    def exist_index(self, index_name: str | None = None) -> bool:
        index = index_name or self.index_name
        cursor = self._conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (index,))
        return cursor.fetchone() is not None

    def create_index(self, index_name: str | None = None):
        index = index_name or self.index_name
        self._conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {index} (
                unique_id TEXT PRIMARY KEY,
                workspace_id TEXT,
                content TEXT,
                metadata TEXT,
                vector TEXT
            )
        """)
        self._conn.commit()

    def delete_index(self, index_name: str | None = None):
        index = index_name or self.index_name
        self._conn.execute(f"DROP TABLE IF EXISTS {index}")
        self._conn.commit()

    def exist_id(self, unique_id: str, index_name: str | None = None):
        index = index_name or self.index_name
        cursor = self._conn.execute(f"SELECT 1 FROM {index} WHERE unique_id=?", (unique_id,))
        return cursor.fetchone() is not None

    def insert(self, nodes: VectorStoreNode | List[VectorStoreNode], index_name: str | None = None, **kwargs):
        index = index_name or self.index_name
        if isinstance(nodes, VectorStoreNode):
            nodes = [nodes]
        nodes = self.embedding_model.get_node_embeddings(nodes)
        for node in nodes:
            self._conn.execute(f"REPLACE INTO {index} (unique_id, workspace_id, content, metadata, vector) VALUES (?, ?, ?, ?, ?)",
                (node.unique_id, node.workspace_id, node.content, json.dumps(node.metadata), json.dumps(node.vector)))
        self._conn.commit()

    def update(self, nodes: VectorStoreNode | List[VectorStoreNode], index_name: str | None = None, **kwargs):
        self.insert(nodes, index_name=index_name)

    def delete_by_id(self, unique_id: str, index_name: str | None = None, **kwargs):
        index = index_name or self.index_name
        self._conn.execute(f"DELETE FROM {index} WHERE unique_id=?", (unique_id,))
        self._conn.commit()

    def retrieve_by_id(self, unique_id: str, index_name: str | None = None, **kwargs) -> VectorStoreNode | None:
        index = index_name or self.index_name
        cursor = self._conn.execute(f"SELECT unique_id, workspace_id, content, metadata, vector FROM {index} WHERE unique_id=?", (unique_id,))
        row = cursor.fetchone()
        if row:
            return VectorStoreNode(
                unique_id=row[0],
                workspace_id=row[1],
                content=row[2],
                metadata=json.loads(row[3]),
                vector=json.loads(row[4])
            )
        return None

    def retrieve_by_query(self, query: str, top_k: int = 1, index_name: str | None = None, **kwargs) -> List[VectorStoreNode]:
        index = index_name or self.index_name
        query_vec = self.embedding_model.get_embeddings(query)
        cursor = self._conn.execute(f"SELECT unique_id, workspace_id, content, metadata, vector FROM {index}")
        results = []
        for row in cursor:
            node = VectorStoreNode(
                unique_id=row[0],
                workspace_id=row[1],
                content=row[2],
                metadata=json.loads(row[3]),
                vector=json.loads(row[4])
            )
            node.metadata["score"] = self._cosine_similarity(query_vec, node.vector)
            results.append(node)
        results.sort(key=lambda x: x.metadata["score"], reverse=True)
        return results[:top_k]

    @staticmethod
    def _cosine_similarity(vec1, vec2):
        import math
        dot = sum(x * y for x, y in zip(vec1, vec2))
        norm1 = math.sqrt(sum(x * x for x in vec1))
        norm2 = math.sqrt(sum(y * y for y in vec2))
        return dot / (norm1 * norm2) if norm1 and norm2 else 0.0 