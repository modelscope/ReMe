from v1.utils.registry import Registry

VECTOR_STORE_REGISTRY = Registry()

from v1.vector_store.es_vector_store import EsVectorStore
from v1.vector_store.chroma_vector_store import ChromaVectorStore
from v1.vector_store.file_vector_store import FileVectorStore
