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
    retriever: str = field(default="")
    summarizer: str = field(default="")
    vector_store: str = field(default="")
    agent: str = field(default="")


@dataclass
class OpConfig:
    backend: str = field(default="")
    prompt_file_path: str = field(default="")
    prompt_dict: dict = field(default_factory=dict)
    llm: str = field(default="")
    embedding_model: str = field(default="")
    vector_store: str = field(default="")
    params: dict = field(default_factory=dict)


@dataclass
class LLMConfig:
    backend: str = field(default="")
    model_name: str = field(default="")
    params: dict = field(default_factory=dict)


@dataclass
class EmbeddingModelConfig:
    backend: str = field(default="")
    model_name: str = field(default="")
    params: dict = field(default_factory=dict)


@dataclass
class VectorStoreConfig:
    backend: str = field(default="")
    embedding_model: str = field(default="")
    params: dict = field(default_factory=dict)


@dataclass
class AppConfig:
    pre_defined_config: str = field(default="default_config")
    config_path: str = field(default="")
    http_service: HttpServiceConfig = field(default_factory=HttpServiceConfig)
    thread_pool: ThreadPoolConfig = field(default_factory=ThreadPoolConfig)
    api: APIConfig = field(default_factory=APIConfig)
    op: Dict[str, OpConfig] = field(default_factory=dict)
    llm: Dict[str, LLMConfig] = field(default_factory=dict)
    embedding_model: Dict[str, EmbeddingModelConfig] = field(default_factory=dict)
    vector_store: Dict[str, VectorStoreConfig] = field(default_factory=dict)
