import os
from typing import List, Tuple, Iterable

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from loguru import logger
from pydantic import Field, PrivateAttr, model_validator

from experiencemaker.embedding_model.openai_compatible_embedding_model import OpenAICompatibleEmbeddingModel
from experiencemaker.schema.vector_node import VectorNode
from experiencemaker.vector_store import VECTOR_STORE_REGISTRY
from experiencemaker.vector_store.base_vector_store import BaseVectorStore


@VECTOR_STORE_REGISTRY.register("elasticsearch")
class EsVectorStore(BaseVectorStore):
    hosts: str | List[str] = Field(default_factory=lambda: os.getenv("ES_HOSTS", "http://localhost:9200"))
    basic_auth: str | Tuple[str, str] | None = Field(default=None)
    retrieve_filters: List[dict] = []
    _client: Elasticsearch = PrivateAttr()

    @model_validator(mode="after")
    def init_client(self):
        if isinstance(self.hosts, str):
            self.hosts = [self.hosts]
        self._client = Elasticsearch(hosts=self.hosts, basic_auth=self.basic_auth)
        return self

    def exist_workspace(self, workspace_id: str, **kwargs) -> bool:
        return self._client.indices.exists(index=workspace_id)

    def delete_workspace(self, workspace_id: str, **kwargs):
        return self._client.indices.delete(index=workspace_id, **kwargs)

    def create_workspace(self, workspace_id: str, **kwargs):
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
        response = self._client.search(index=workspace_id, body={"query": {"match_all": {}}, "size": max_size})
        for doc in response['hits']['hits']:
            yield self.doc2node(doc, workspace_id)

    def refresh(self, workspace_id: str):
        self._client.indices.refresh(index=workspace_id)

    @staticmethod
    def doc2node(doc, workspace_id: str) -> VectorNode:
        node = VectorNode(**doc["_source"])
        node.workspace_id = workspace_id
        node.unique_id = doc["_id"]
        if "_score" in doc:
            node.metadata["_score"] = doc["_score"] - 1
        return node

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

    def search(self, query: str, workspace_id: str, top_k: int = 1, **kwargs) -> List[VectorNode]:
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
            nodes.append(self.doc2node(doc, workspace_id))

        self.retrieve_filters.clear()
        return nodes

    def insert(self, nodes: VectorNode | List[VectorNode], workspace_id: str, refresh: bool = False, **kwargs):
        if not self.exist_workspace(workspace_id=workspace_id):
            self.create_workspace(workspace_id=workspace_id)

        if isinstance(nodes, VectorNode):
            nodes = [nodes]

        embedded_nodes = [node for node in nodes if node.vector]
        not_embedded_nodes = [node for node in nodes if not node.vector]
        now_embedded_nodes = self.embedding_model.get_node_embeddings(not_embedded_nodes)

        docs = [
            {
                "_op_type": "index",
                "_index": workspace_id,
                "_id": node.unique_id,
                "_source": {
                    "workspace_id": workspace_id,
                    "content": node.content,
                    "metadata": node.metadata,
                    "vector": node.vector
                }
            } for node in embedded_nodes + now_embedded_nodes]
        status, error = bulk(self._client, docs, chunk_size=self.batch_size, **kwargs)
        logger.info(f"insert docs.size={len(docs)} status={status} error={error}")

        if refresh:
            self.refresh(workspace_id=workspace_id)

    def delete(self, node_ids: str | List[str], workspace_id: str, refresh: bool = False, **kwargs):
        if not self.exist_workspace(workspace_id=workspace_id):
            logger.warning(f"workspace_id={workspace_id} is not exists!")
            return

        if isinstance(node_ids, str):
            node_ids = [node_ids]

        actions = [
            {
                "_op_type": "delete",
                "_index": workspace_id,
                "_id": node_id
            } for node_id in node_ids]
        status, error = bulk(self._client, actions, chunk_size=self.batch_size, **kwargs)
        logger.info(f"delete actions.size={len(actions)} status={status} error={error}")

        if refresh:
            self.refresh(workspace_id=workspace_id)


def main():
    from dotenv import load_dotenv
    load_dotenv()

    embedding_model = OpenAICompatibleEmbeddingModel(dimensions=64, model_name="text-embedding-v4")
    workspace_id = "rag_nodes_index"
    hosts = "http://11.160.132.46:8200"
    es = EsVectorStore(hosts=hosts, embedding_model=embedding_model)
    if es.exist_workspace(workspace_id=workspace_id):
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
        .search("What is AI?", top_k=5, workspace_id=workspace_id)
    for r in results:
        logger.info(r.model_dump(exclude={"vector"}))
    logger.info("=" * 20)

    logger.info("=" * 20)
    results = es.search("What is AI?", top_k=5, workspace_id=workspace_id)
    for r in results:
        logger.info(r.model_dump(exclude={"vector"}))
    logger.info("=" * 20)
    es.dump_workspace(workspace_id=workspace_id)
    es.delete_workspace(workspace_id=workspace_id)


if __name__ == "__main__":
    main()
    # launch with: python -m experiencemaker.storage.es_vector_store
