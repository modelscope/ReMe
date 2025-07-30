import json
import os
from pathlib import Path

from tavily import TavilyClient

cache_path: Path = Path("./web_search_cache")
cache_path.mkdir(parents=True, exist_ok=True)


def web_search(query: str, enable_print: bool = True, enable_cache: bool = True):
    if enable_cache:
        ...

    client = TavilyClient(api_key=os.environ["TVLY_API_KEY"])
    response = client.search(
        include_answer=True,
        include_raw_content=True,
        query=query)

    # response = client.get_search_context(query=query)
    # response = json.loads(response)
    if enable_print:
        print(json.dumps(response, indent=2, ensure_ascii=False))

    return response


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv("../../.env")
    web_search("恒生医药为什么一直涨")
