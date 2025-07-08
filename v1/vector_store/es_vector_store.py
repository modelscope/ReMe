import os
from typing import List, Tuple, Iterable

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from loguru import logger
from pydantic import Field, PrivateAttr, model_validator

from v1.embedding_model.openai_compatible_embedding_model import OpenAICompatibleEmbeddingModel
from v1.schema.vector_node import VectorNode
from v1.vector_store import VECTOR_STORE_REGISTRY
from v1.vector_store.base_vector_store import BaseVectorStore


@VECTOR_STORE_REGISTRY.register("elasticsearch")
class EsVectorStore(BaseVectorStore):
    hosts: str | List[str] = Field(default_factory=lambda: os.getenv("ES_HOSTS", "http://localhost:9200"))
    basic_auth: str | Tuple[str, str] | None = Field(default=None)
    bulk_chunk_size: int = Field(default=512)
    retrieve_filters: List[dict] = []
    _client: Elasticsearch = PrivateAttr()

    @model_validator(mode="after")
    def init_client(self):
        if isinstance(self.hosts, str):
            hosts = [self.hosts]
        else:
            hosts = self.hosts
        self._client = Elasticsearch(hosts=hosts, basic_auth=self.basic_auth)
        return self

    def exist_workspace(self, workspace_id: str, **kwargs) -> bool:
        return self._client.indices.exists(index=workspace_id)

    def _delete_workspace(self, workspace_id: str, **kwargs):
        self._client.indices.delete(index=workspace_id, **kwargs)

    def _create_workspace(self, workspace_id: str, **kwargs):
        body = {
            "mappings": {
                "properties": {
                    "workspace_id": {"type": "keyword"},
                    "content": {"type": "text"},
                    "metadata": {"type": "object"},
                    "vector": {
                        "type": "dense_vector",
                        "dims": self.embedding_model.dimensions
                    }
                }
            }
        }

        return self._client.indices.create(index=workspace_id, body=body)

    def _iter_workspace_nodes(self, workspace_id: str, max_size: int = 10000, **kwargs) -> Iterable[VectorNode]:
        response = self._client.search(
            index=workspace_id,
            body={"query": {"match_all": {}}},
            scroll='5m',
            size=max_size
        )

        for doc in response['hits']['hits']:
            yield self.doc2node(doc)

    def refresh(self, workspace_id: str):
        self._client.indices.refresh(index=workspace_id)

    @staticmethod
    def doc2node(doc) -> VectorNode:
        node = VectorNode(**doc["_source"])
        node.unique_id = doc["_id"]
        if "_score" in doc:
            node.metadata["_score"] = doc["_score"] - 1
        return node

    def exist_id(self, unique_id: str, workspace_id: str = None, **kwargs) -> bool:
        response = self._client.exists(index=workspace_id, id=unique_id)
        return response.body

    def node2doc(self, node: VectorNode, add_op_type: bool = False) -> dict:
        doc: dict = {
            "_index": node.workspace_id,
            "_id": node.unique_id,
            "_source": {
                "workspace_id": node.workspace_id,
                "content": node.content,
                "metadata": node.metadata,
                "vector": node.vector
            }
        }

        if add_op_type:
            doc["_op_type"] = "update" if self.exist_id(node.unique_id, node.workspace_id) else "index",
        return doc

    def add_term_filter(self, key: str, value):
        if key:
            self.retrieve_filters.append({"term": {key: value}})
        return self

    def add_range_filter(self, key: str, gte=None, lte=None):
        if key:
            if gte is not None and lte is not None:
                self.retrieve_filters.append({"range": {key: {"gte": gte, "lte": lte}}})
            elif gte is not None:
                self.retrieve_filters.append({"range": {key: {"gte": gte}}})
            elif lte is not None:
                self.retrieve_filters.append({"range": {key: {"lte": lte}}})
        return self

    def clear_filter(self):
        self.retrieve_filters.clear()
        return self

    def retrieve_by_query(self, query: str, workspace_id: str, top_k: int = 1, **kwargs) -> List[VectorNode]:
        if not self.exist_workspace(workspace_id=workspace_id):
            logger.warning(f"workspace_id={workspace_id} is not exists!")
            return []

        query_vector = self.embedding_model.get_embeddings(query)
        body = {
            "query": {
                "script_score": {
                    "query": {"bool": {"must": self.retrieve_filters}},
                    "script": {
                        "source": "cosineSimilarity(params.query_vector, 'vector') + 1.0",
                        "params": {"query_vector": query_vector},
                    }
                }
            },
            "size": top_k
        }
        response = self._client.search(index=workspace_id, body=body, **kwargs)

        nodes: List[VectorNode] = []
        for doc in response['hits']['hits']:
            nodes.append(self.doc2node(doc))

        self.retrieve_filters.clear()
        return nodes

    def insert(self, nodes: VectorNode | List[VectorNode], workspace_id: str, refresh: bool = True, **kwargs):
        self.create_workspace(workspace_id=workspace_id)
        if isinstance(nodes, VectorNode):
            nodes = [nodes]

        embedded_nodes = [node for node in nodes if node.vector]
        not_embedded_nodes = [node for node in nodes if not node.vector]
        now_embedded_nodes = self.embedding_model.get_node_embeddings(not_embedded_nodes)

        docs = [self.node2doc(node, False) for node in embedded_nodes + now_embedded_nodes]
        status, error = bulk(self._client, docs, chunk_size=self.bulk_chunk_size, **kwargs)
        logger.info(f"insert sample.size={len(nodes)} status={status} error={error}")

        if refresh:
            self.refresh(workspace_id=workspace_id)

    def update(self, nodes: VectorNode | List[VectorNode], workspace_id: str, refresh: bool = True, **kwargs):
        self.create_workspace(workspace_id=workspace_id)
        if isinstance(nodes, VectorNode):
            nodes = [nodes]

        nodes = self.embedding_model.get_node_embeddings(nodes)
        docs = [self.node2doc(node, True) for node in nodes]
        status, error = bulk(self._client, docs, chunk_size=self.bulk_chunk_size, **kwargs)
        update_size = sum([1 if doc["_op_type"] == "update" else 0 for doc in docs])
        insert_size = len(docs) - update_size
        logger.info(f"update update_size={update_size} insert_size={insert_size} status={status} error={error}")

        if refresh:
            self.refresh(workspace_id=workspace_id)

def main():
    from experiencemaker.utils.util_function import load_env_keys
    load_env_keys()
    load_env_keys("../../.env")

    embedding_model = OpenAICompatibleEmbeddingModel(dimensions=1024)
    workspace_id = "rag_nodes_index"
    hosts = "http://11.160.132.46:8200"
    es = EsVectorStore(hosts=hosts, embedding_model=embedding_model)
    es.delete_workspace(workspace_id=workspace_id)
    es.create_workspace(workspace_id=workspace_id)

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

    es.insert(sample_nodes, workspace_id=workspace_id, refresh=True)

    logger.info("=" * 20)
    results = es.add_term_filter(key="metadata.node_type", value="n1") \
        .retrieve_by_query("What is AI?", top_k=5, workspace_id=workspace_id)
    for r in results:
        logger.info(r.model_dump(exclude={"vector"}))
    logger.info("=" * 20)

    logger.info("=" * 20)
    results = es.retrieve_by_query("What is AI?", top_k=5, workspace_id=workspace_id)
    for r in results:
        logger.info(r.model_dump(exclude={"vector"}))
    logger.info("=" * 20)

    es.delete_workspace(workspace_id=workspace_id)


if __name__ == "__main__":
    main()
    # launch with: python -m experiencemaker.storage.es_vector_store
