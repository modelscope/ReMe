from experiencemaker.storage.base_vector_store import BaseVectorStore
from experiencemaker.storage.es_vector_store import EsVectorStore
from experiencemaker.storage.file_vector_store import FileVectorStore
from experiencemaker.utils.registry import Registry

VECTOR_STORE_REGISTRY = Registry[BaseVectorStore]("vector_store")
VECTOR_STORE_REGISTRY.register(EsVectorStore, "elasticsearch")
VECTOR_STORE_REGISTRY.register(FileVectorStore, "local_file")
