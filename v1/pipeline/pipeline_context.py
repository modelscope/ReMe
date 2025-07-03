from concurrent.futures import ThreadPoolExecutor
from typing import Any

from v1.schema.app_config import AppConfig


class PipelineContext(object):

    def __init__(self, app_config: AppConfig, thread_pool: ThreadPoolExecutor):
        self.app_config: AppConfig = app_config
        self.thread_pool: ThreadPoolExecutor = thread_pool
        self.context: dict = {}

    def set_context(self, key: str, value: Any):
        self.context[key] = value

    def get_context(self, key: str):
        return self.context.get(key)
