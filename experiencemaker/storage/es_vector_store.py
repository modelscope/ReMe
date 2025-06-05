import os
from typing import List, Tuple

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from loguru import logger
from pydantic import Field, PrivateAttr, model_validator

from experiencemaker.schema.vector_store_node import VectorStoreNode
from experiencemaker.storage.base_vector_store import BaseVectorStore


class EsVectorStore(BaseVectorStore):
    hosts: str | List[str] = Field(default_factory=lambda: os.getenv("ES_HOSTS", "http://localhost:9200"))
    index_name: str = Field(default=...)
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

    def delete_index(self):
        if self._client.indices.exists(index=self.index_name):
            self._client.indices.delete(index=self.index_name)

    def create_index(self):
        if self._client.indices.exists(index=self.index_name):
            logger.warning(f"index_name={self.index_name} is already exists!")
            return None

        index = {
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

        return self._client.indices.create(index=self.index_name, body=index)

    def refresh_index(self):
        self._client.indices.refresh(index=self.index_name)

    @staticmethod
    def doc2node(doc) -> VectorStoreNode:
        node = VectorStoreNode(**doc["_source"])
        node.unique_id = doc["_id"]
        if "_score" in doc:
            node.metadata["score"] = doc["_score"] - 1
        return node

    def exist_id(self, doc_id: str):
        return self._client.exists(index=self.index_name, id=doc_id)

    def node2doc(self, node: VectorStoreNode, add_op_type: bool = False) -> dict:
        doc: dict = {
            "_index": self.index_name,
            "_id": node.unique_id,
            "_source": {
                "workspace_id": node.workspace_id,
                "content": node.content,
                "metadata": node.metadata,
                "vector": node.vector
            }
        }

        if add_op_type:
            doc["_op_type"] = "update" if self.exist_id(node.unique_id) else "index",
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

    def insert(self, nodes: VectorStoreNode | List[VectorStoreNode], refresh_index: bool = False, **kwargs):
        if isinstance(nodes, VectorStoreNode):
            nodes = [nodes]

        embedded_nodes = [node for node in nodes if node.vector]
        not_embedded_nodes = [node for node in nodes if not node.vector]
        now_embedded_nodes = self.embedding_model.get_node_embeddings(not_embedded_nodes)

        docs = [self.node2doc(node, False) for node in embedded_nodes + now_embedded_nodes]
        status, error = bulk(self._client, docs, chunk_size=self.bulk_chunk_size, **kwargs)
        logger.info(f"insert sample.size={len(nodes)} status={status} error={error}")

        if refresh_index:
            self.refresh_index()

    def update(self, nodes: VectorStoreNode | List[VectorStoreNode], refresh_index: bool = False, **kwargs):
        if isinstance(nodes, VectorStoreNode):
            nodes = [nodes]

        nodes = self.embedding_model.get_node_embeddings(nodes)
        docs = [self.node2doc(node, True) for node in nodes]
        status, error = bulk(self._client, docs, chunk_size=self.bulk_chunk_size, **kwargs)
        update_size = sum([1 if doc["_op_type"] == "update" else 0 for doc in docs])
        insert_size = len(docs) - update_size
        logger.info(f"update update_size={update_size} insert_size={insert_size} status={status} error={error}")

        if refresh_index:
            self.refresh_index()

    def delete_by_id(self, unique_id: str, **kwargs):
        return self._client.delete(index=self.index_name, id=unique_id, **kwargs)

    def retrieve_by_id(self, unique_id: str, **kwargs) -> VectorStoreNode | None:
        try:
            doc = self._client.get(index=self.index_name, id=unique_id, **kwargs)
            return self.doc2node(doc)

        except Exception as e:
            logger.warning(f"retrieve_by_id unique_id={unique_id} is not found with error={e.args}")
            return None

    def retrieve_by_query(self, query: str, top_k: int = 3, **kwargs) -> List[VectorStoreNode]:
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
        response = self._client.search(index=self.index_name, body=body, **kwargs)

        nodes: List[VectorStoreNode] = []
        for doc in response['hits']['hits']:
            nodes.append(self.doc2node(doc))

        self.retrieve_filters.clear()
        return nodes
