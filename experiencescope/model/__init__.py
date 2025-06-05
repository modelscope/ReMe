from experiencescope.model.openai_compatible_embedding_model import OpenAICompatibleEmbeddingModel
from experiencescope.model.openai_compatible_llm import OpenAICompatibleBaseLLM

from experiencescope.utils.registry import Registry

LLM_REGISTRY = Registry("llm")
LLM_REGISTRY.register(OpenAICompatibleBaseLLM, "openai_compatible")

EMBEDDING_MODEL_REGISTRY = Registry("embedding_model")
EMBEDDING_MODEL_REGISTRY.register(OpenAICompatibleEmbeddingModel, "openai_compatible")
