from abc import abstractmethod, ABC
from concurrent.futures import Future
from pathlib import Path
from typing import List

from loguru import logger
from tqdm import tqdm

from experiencemaker.embedding_model import EMBEDDING_MODEL_REGISTRY
from experiencemaker.embedding_model.base_embedding_model import BaseEmbeddingModel
from experiencemaker.llm import LLM_REGISTRY
from experiencemaker.llm.base_llm import BaseLLM
from experiencemaker.op.prompt_mixin import PromptMixin
from experiencemaker.pipeline.pipeline_context import PipelineContext
from experiencemaker.schema.app_config import OpConfig, LLMConfig, EmbeddingModelConfig
from experiencemaker.utils.common_utils import camel_to_snake
from experiencemaker.utils.timer import Timer
from experiencemaker.vector_store.base_vector_store import BaseVectorStore


class BaseOp(PromptMixin, ABC):
    current_path: str = __file__

    def __init__(self, context: PipelineContext, op_config: OpConfig):
        super().__init__()
        self.context: PipelineContext = context
        self.op_config: OpConfig = op_config
        self.timer = Timer(name=self.simple_name)

        self._prepare_prompt()

        self._llm: BaseLLM | None = None
        self._embedding_model: BaseEmbeddingModel | None = None
        self._vector_store: BaseVectorStore | None = None

        self.task_list: List[Future] = []

    def _prepare_prompt(self):
        if self.op_config.prompt_file_path:
            prompt_file_path = self.op_config.prompt_file_path
        else:
            prompt_name = self.simple_name.replace("_op", "_prompt.yaml")
            prompt_file_path = Path(self.current_path).parent / prompt_name

        # Load custom prompts from prompt file
        self.load_prompt_by_file(prompt_file_path=prompt_file_path)

        # Load custom prompts from config
        self.load_prompt_dict(prompt_dict=self.op_config.prompt_dict)

    @property
    def simple_name(self) -> str:
        return camel_to_snake(self.__class__.__name__)

    @property
    def op_params(self) -> dict:
        return self.op_config.params

    @abstractmethod
    def execute(self):
        ...

    def execute_wrap(self):
        try:
            with self.timer:
                return self.execute()

        except Exception as e:
            logger.exception(f"op={self.simple_name} execute failed, error={e.args}")

    def submit_task(self, fn, *args, **kwargs):
        task = self.context.thread_pool.submit(fn, *args, **kwargs)
        self.task_list.append(task)
        return self

    def join_task(self, task_desc: str = None) -> list:
        result = []
        for task in tqdm(self.task_list, desc=task_desc or (self.simple_name + ".join_task")):
            t_result = task.result()
            if t_result:
                if isinstance(t_result, list):
                    result.extend(t_result)
                else:
                    result.append(t_result)
        self.task_list.clear()
        return result

    @property
    def llm(self) -> BaseLLM:
        if self._llm is None:
            llm_name: str = self.op_config.llm
            assert llm_name in self.context.app_config.llm, f"llm={llm_name} not found in app_config.llm!"
            llm_config: LLMConfig = self.context.app_config.llm[llm_name]

            assert llm_config.backend in LLM_REGISTRY, f"llm.backend={llm_config.backend} not found in LLM_REGISTRY!"
            llm_cls = LLM_REGISTRY[llm_config.backend]
            self._llm = llm_cls(model_name=llm_config.model_name, **llm_config.params)

        return self._llm

    @property
    def embedding_model(self):
        if self._embedding_model is None:
            embedding_model_name: str = self.op_config.embedding_model
            assert embedding_model_name in self.context.app_config.embedding_model, \
                f"embedding_model={embedding_model_name} not found in app_config.embedding_model!"
            embedding_model_config: EmbeddingModelConfig = self.context.app_config.embedding_model[embedding_model_name]

            assert embedding_model_config.backend in EMBEDDING_MODEL_REGISTRY, \
                f"embedding_model.backend={embedding_model_config.backend} not found in EMBEDDING_MODEL_REGISTRY!"
            embedding_model_cls = EMBEDDING_MODEL_REGISTRY[embedding_model_config.backend]
            self._embedding_model = embedding_model_cls(model_name=embedding_model_config.model_name,
                                                        **embedding_model_config.params)

        return self._embedding_model

    @property
    def vector_store(self):
        if self._vector_store is None:
            vector_store_name: str = self.op_config.vector_store
            assert vector_store_name in self.context.vector_store_dict, \
                f"vector_store={vector_store_name} not found in vector_store_dict!"
            self._vector_store = self.context.vector_store_dict[vector_store_name]

        return self._vector_store
