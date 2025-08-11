import os
from typing import Literal, List

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import Field, PrivateAttr, model_validator

from experiencemaker.embedding_model import EMBEDDING_MODEL_REGISTRY
from experiencemaker.embedding_model.base_embedding_model import BaseEmbeddingModel


@EMBEDDING_MODEL_REGISTRY.register("openai_compatible")
class OpenAICompatibleEmbeddingModel(BaseEmbeddingModel):
    """
    OpenAI-compatible embedding model implementation.
    
    This class provides an implementation of BaseEmbeddingModel that works with
    OpenAI-compatible embedding APIs, including OpenAI's official API and
    other services that follow the same interface.
    """
    # API configuration fields
    api_key: str = Field(default_factory=lambda: os.getenv("EMBEDDING_API_KEY"), description="API key for authentication")
    base_url: str = Field(default_factory=lambda: os.getenv("EMBEDDING_BASE_URL"), description="Base URL for the API endpoint")
    model_name: str = Field(default="", description="Name of the embedding model to use")
    dimensions: int = Field(default=1024, description="Dimensionality of the embedding vectors")
    encoding_format: Literal["float", "base64"] = Field(default="float", description="Encoding format for embeddings")
    
    # Private OpenAI client instance
    _client: OpenAI = PrivateAttr()

    @model_validator(mode="after")
    def init_client(self):
        """
        Initialize the OpenAI client after model validation.
        
        This method is called automatically after Pydantic model validation
        to set up the OpenAI client with the provided API key and base URL.
        
        Returns:
            self: The model instance for method chaining
        """
        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self

    def _get_embeddings(self, input_text: str | List[str]):
        """
        Get embeddings from the OpenAI-compatible API.
        
        This method implements the abstract _get_embeddings method from BaseEmbeddingModel
        by calling the OpenAI-compatible embeddings API.
        
        Args:
            input_text: Single text string or list of text strings to embed
            
        Returns:
            Embedding vector(s) corresponding to the input text(s)
            
        Raises:
            RuntimeError: If unsupported input type is provided
        """
        completion = self._client.embeddings.create(
            model=self.model_name,
            input=input_text,
            dimensions=self.dimensions,
            encoding_format=self.encoding_format
        )

        if isinstance(input_text, str):
            return completion.data[0].embedding

        elif isinstance(input_text, list):
            result_emb = [[] for _ in range(len(input_text))]
            for emb in completion.data:
                result_emb[emb.index] = emb.embedding
            return result_emb

        else:
            raise RuntimeError(f"unsupported type={type(input_text)}")


def main():
    load_dotenv()
    model = OpenAICompatibleEmbeddingModel(dimensions=64, model_name="text-embedding-v4")
    res1 = model.get_embeddings(
        "The clothes are of good quality and look good, definitely worth the wait. I love them.")
    res2 = model.get_embeddings(["aa", "bb"])
    print(res1)
    print(res2)


if __name__ == "__main__":
    main()
    # launch with: python -m experiencemaker.model.openai_compatible_embedding_model
