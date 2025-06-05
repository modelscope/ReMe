from abc import ABC

from loguru import logger
from pydantic import BaseModel, Field, model_validator

from experiencemaker.model import LLM_REGISTRY, EMBEDDING_MODEL_REGISTRY
from experiencemaker.model.base_embedding_model import BaseEmbeddingModel
from experiencemaker.model.base_llm import BaseLLM
from experiencemaker.utils.prompt_handler import PromptHandler


class BaseModule(BaseModel, ABC):
    prompt_dir: str | None = Field(default=None)
    prompt_file: str | None = Field(default=None)
    prompt_handler: PromptHandler | None = Field(default=None)

    llm: BaseLLM | None = Field(default=None)
    embedding_model: BaseEmbeddingModel | None = Field(default=None)

    @model_validator(mode="before")  # noqa
    @classmethod
    def init_model(cls, data: dict):
        if "llm" in data and isinstance(data["llm"], dict):
            backend = data["llm"].pop("backend", None)
            assert backend is not None, "llm must have a backend"
            module = LLM_REGISTRY[backend]
            params = data["llm"]
            data["llm"] = module(**params)
            logger.info(f"{cls.__name__} load llm.backend={backend} params={params}")

        if "embedding_model" in data and isinstance(data["embedding_model"], dict):
            backend = data["embedding_model"].pop("backend", None)
            assert backend is not None, "embedding_model must have a backend"
            module = EMBEDDING_MODEL_REGISTRY[backend]
            params = data["embedding_model"]
            data["embedding_model"] = module(**params)
            logger.info(f"{cls.__name__} load embedding_model.backend={backend} params={params}")

        if "prompt_dir" in data:
            handler = PromptHandler(dir_path=data.get("prompt_dir"))
            data["prompt_handler"] = handler
            if data.get("prompt_file"):
                handler.add_prompt_file(data.get("prompt_file"))

        return data

    def execute(self, **kwargs):
        raise NotImplementedError
