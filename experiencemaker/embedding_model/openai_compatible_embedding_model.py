import os
from typing import Literal, List

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import Field, PrivateAttr, model_validator

from experiencemaker.embedding_model import EMBEDDING_MODEL_REGISTRY
from experiencemaker.embedding_model.base_embedding_model import BaseEmbeddingModel


@EMBEDDING_MODEL_REGISTRY.register("openai_compatible")
class OpenAICompatibleEmbeddingModel(BaseEmbeddingModel):
    api_key: str = Field(default_factory=lambda: os.getenv("EMBEDDING_API_KEY"), description="api key")
    base_url: str = Field(default_factory=lambda: os.getenv("EMBEDDING_BASE_URL"), description="base url")
    model_name: str = Field(default="", description="model name")
    dimensions: int = Field(default=1024, description="dimensions")
    encoding_format: Literal["float", "base64"] = Field(default="float", description="encoding_format")
    _client: OpenAI = PrivateAttr()

    @model_validator(mode="after")
    def init_client(self):
        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self

    def _get_embeddings(self, input_text: str | List[str]):
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
