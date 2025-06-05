from beyondagent.core.model.openai_compatible_embedding_model import OpenAICompatibleEmbeddingModel
from beyondagent.core.model.openai_compatible_llm import OpenAICompatibleBaseLLM

from beyondagent.core.utils.registry import Registry

LLM_REGISTRY = Registry("llm")
LLM_REGISTRY.register(OpenAICompatibleBaseLLM, "openai_compatible")

EMBEDDING_MODEL_REGISTRY = Registry("embedding_model")
EMBEDDING_MODEL_REGISTRY.register(OpenAICompatibleEmbeddingModel, "openai_compatible")
