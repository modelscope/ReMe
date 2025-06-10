import os
from typing import Literal, List

from openai import OpenAI
from pydantic import Field, PrivateAttr, model_validator

from experiencemaker.model.base_embedding_model import BaseEmbeddingModel


class OpenAICompatibleEmbeddingModel(BaseEmbeddingModel):
    api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY"), description="api key")
    base_url: str = Field(default_factory=lambda: os.getenv("OPENAI_BASE_URL"), description="base url")
    model_name: str = Field(default="text-embedding-v4", description="model name")
    dimensions: int = Field(default=1024, description="dimensions")
    encoding_format: Literal["float", "base64"] = Field(default="float", description="encoding_format")
    _client: OpenAI = PrivateAttr()

    @model_validator(mode="after")
    def init_client(self):
        """
        Initialize the OpenAI client after model validation.

        This method is called after the model's data has been validated,
        ensuring that all necessary attributes are correctly set before
        initializing the OpenAI client. It creates an instance of the OpenAI
        client using the provided API key and base URL, storing it in the

        Returns:
            self: Returns the instance of the current class for method chaining.
        """
        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self

    def _get_embeddings(self, input_text: str | List[str]):
        """
        Generate embeddings for the input text.

        This method accepts either a single string or a list of strings as input,
        and returns the corresponding embeddings based on the specified model.

        Parameters:
        - input_text (str | List[str]): The input text, which can be a single string or a list of strings.

        Returns:
        - List[float]: If the input is a single string, returns a list of floating-point numbers representing the embedding.
        - List[List[float]]: If the input is a list of strings, returns a list where each item is a list of floating-point numbers representing the embedding of each string.
        - Raises RuntimeError: If the input type is unsupported.
        """

        # Create embeddings using the specified model, input text, dimensions, and encoding format
        completion = self._client.embeddings.create(
            model=self.model_name,
            input=input_text,
            dimensions=self.dimensions,
            encoding_format=self.encoding_format
        )

        # Determine the type of input and process accordingly
        if isinstance(input_text, str):
            # If the input is a single string, return the embedding of that string
            return completion.data[0].embedding

        elif isinstance(input_text, list):
            # If the input is a list of strings, initialize a list to hold the embeddings of each string
            result_emb = [[] for _ in range(len(input_text))]
            # Iterate through the generated embeddings and assign them to the corresponding positions in the result list
            for emb in completion.data:
                result_emb[emb.index] = emb.embedding
            return result_emb

        else:
            # If the input type is neither a string nor a list of strings, throw an exception
            raise RuntimeError(f"unsupported type={type(input_text)}")


def main():
    from experiencemaker.utils.util_function import load_env_keys
    load_env_keys()

    model = OpenAICompatibleEmbeddingModel(dimensions=64, model_name="text-embedding-v4")
    res1 = model.get_embeddings(
        "The clothes are of good quality and look good, definitely worth the wait. I love them.")
    res2 = model.get_embeddings(["aa", "bb"])
    print(res1)
    print(res2)


if __name__ == "__main__":
    main()
    # launch with: python -m experiencemaker.model.openai_compatible_embedding_model
