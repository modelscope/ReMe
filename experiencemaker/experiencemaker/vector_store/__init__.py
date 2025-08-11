from experiencemaker.utils.registry import Registry

VECTOR_STORE_REGISTRY = Registry()

from experiencemaker.vector_store.es_vector_store import EsVectorStore
from experiencemaker.vector_store.chroma_vector_store import ChromaVectorStore
from experiencemaker.vector_store.file_vector_store import FileVectorStore
