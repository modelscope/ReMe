from dataclasses import dataclass, field
from typing import Dict


@dataclass
class HttpServiceConfig:
    host: str = field(default="0.0.0.0")
    port: int = field(default=8001)
    timeout_keep_alive: int = field(default=600)
    limit_concurrency: int = field(default=64)


@dataclass
class ThreadPoolConfig:
    max_workers: int = field(default=10)


@dataclass
class APIConfig:
    retriever_pipeline: str = field(default="")
    summarizer_pipeline: str = field(default="")
    vector_store_pipeline: str = field(default="")
    agent_pipeline: str = field(default="")


@dataclass
class OpConfig:
    backend: str = field(default="")
    llm: str = field(default="")
    embedding_model: str = field(default="")
    vector_store: str = field(default="")
    params: dict = field(default_factory=dict)


@dataclass
class LLMConfig:
    backend: str = field(default="")
    model: str = field(default="")
    params: dict = field(default_factory=dict)


@dataclass
class EmbeddingModelConfig:
    backend: str = field(default="")
    model: str = field(default="")
    params: dict = field(default_factory=dict)


@dataclass
class VectorStoreConfig:
    backend: str = field(default="")
    embedding_model: str = field(default="")
    params: dict = field(default_factory=dict)


class AppConfig:
    http_service: HttpServiceConfig = field(default_factory=HttpServiceConfig)
    thread_pool: ThreadPoolConfig = field(default_factory=ThreadPoolConfig)
    api: APIConfig = field(default_factory=APIConfig)
    op: Dict[str, OpConfig] = field(default_factory=dict)
    llm: Dict[str, LLMConfig] = field(default_factory=dict)
    embedding_model: Dict[str, EmbeddingModelConfig] = field(default_factory=dict)
    vector_store: Dict[str, VectorStoreConfig] = field(default_factory=dict)
