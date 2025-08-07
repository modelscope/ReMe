import json
import os
import re
import time
from typing import Literal

from loguru import logger
from pydantic import Field, model_validator, PrivateAttr
from tavily import TavilyClient

from experiencemaker.tool import TOOL_REGISTRY
from experiencemaker.tool.base_tool import BaseTool


@TOOL_REGISTRY.register()
class TavilySearchTool(BaseTool):
    name: str = "web_search"
    description: str = "Use query to retrieve relevant information from the internet."
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "search query",
            }
        },
        "required": ["query"]
    }
    enable_print: bool = Field(default=True)
    enable_cache: bool = Field(default=False)
    cache_path: str = Field(default="./web_search_cache")
    topic: Literal["general", "news", "finance"] = Field(default="general")

    _client: TavilyClient | None = PrivateAttr()

    @model_validator(mode="after")
    def init(self):
        if not os.path.exists(self.cache_path):
            os.makedirs(self.cache_path)

        self._client = TavilyClient()
        return self

    def load_cache(self, cache_name: str = "default") -> dict:
        cache_file = os.path.join(self.cache_path, cache_name + ".jsonl")
        if not os.path.exists(cache_file):
            return {}

        with open(cache_file) as f:
            return json.load(f)

    def dump_cache(self, cache_dict: dict, cache_name: str = "default"):
        cache_file = os.path.join(self.cache_path, cache_name + ".jsonl")
        with open(cache_file, "w") as f:
            return json.dump(cache_dict, f, indent=2, ensure_ascii=False)

    @staticmethod
    def remove_urls_and_images(text):
        pattern = re.compile(r'https?://[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|]')
        result = pattern.sub("", text)
        return result

    def post_process(self, response):
        if self.enable_print:
            logger.info("response=\n" + json.dumps(response, indent=2, ensure_ascii=False))

        return response

    def execute(self, query: str = "", **kwargs):
        assert query, "Query cannot be empty"

        cache_dict = {}
        if self.enable_cache:
            cache_dict = self.load_cache()
            if query in cache_dict:
                return self.post_process(cache_dict[query])

        for i in range(self.max_retries):
            try:
                response = self._client.search(query=query, topic=self.topic)
                url_info_dict = {item["url"]: item for item in response["results"]}
                response_extract = self._client.extract(urls=[item["url"] for item in response["results"]],
                                                        format="text")

                final_result = {}
                for item in response_extract["results"]:
                    url = item["url"]
                    final_result[url] = url_info_dict[url]
                    final_result[url]["raw_content"] = item["raw_content"]

                if self.enable_cache:
                    cache_dict[query] = final_result
                    self.dump_cache(cache_dict)

                return self.post_process(final_result)

            except Exception as e:
                logger.exception(f"tavily search with query={query} encounter error with e={e.args}")
                time.sleep(i + 1)

        return None


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    tool = TavilySearchTool()
    tool.execute(query="恒生医药为什么一直涨")
