from concurrent.futures import ThreadPoolExecutor
from typing import Dict

from experiencemaker.schema.app_config import AppConfig
from experiencemaker.vector_store.base_vector_store import BaseVectorStore


class PipelineContext:

    def __init__(self, **kwargs):
        self._context: dict = {**kwargs}

    def get_context(self, key: str, default=None):
        return self._context.get(key, default)

    def set_context(self, key: str, value):
        self._context[key] = value

    @property
    def request(self):
        return self._context["request"]

    @property
    def response(self):
        return self._context["response"]

    @property
    def app_config(self) -> AppConfig:
        return self._context["app_config"]

    @property
    def thread_pool(self) -> ThreadPoolExecutor:
        return self._context["thread_pool"]

    @property
    def vector_store_dict(self) -> Dict[str, BaseVectorStore]:
        return self._context["vector_store_dict"]
