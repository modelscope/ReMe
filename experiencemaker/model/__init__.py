from experiencemaker.model.base_embedding_model import BaseEmbeddingModel
from experiencemaker.model.base_llm import BaseLLM
from experiencemaker.model.openai_compatible_embedding_model import OpenAICompatibleEmbeddingModel
from experiencemaker.model.openai_compatible_llm import OpenAICompatibleBaseLLM
from experiencemaker.utils.registry import Registry

EMBEDDING_MODEL_REGISTRY = Registry[BaseEmbeddingModel]("embedding_model")

EMBEDDING_MODEL_REGISTRY.register(OpenAICompatibleEmbeddingModel, "openai_compatible")

LLM_REGISTRY = Registry[BaseLLM]("llm")

LLM_REGISTRY.register(OpenAICompatibleBaseLLM, "openai_compatible")
