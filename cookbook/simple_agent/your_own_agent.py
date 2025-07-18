import json

from dotenv import load_dotenv
from loguru import logger

from experiencemaker.schema.request import AgentRequest
from experiencemaker.service.experience_maker_client import ExperienceMakerClient

load_dotenv()


def main():
    # query = "Analyze Xiaomi Corporation."
    query = "分析一下小米公司"

    client = ExperienceMakerClient()
    request = AgentRequest(query=query)
    response = client.call_agent(request)
    logger.info(response.answer)
    with open("messages.jsonl", "w") as f:
        f.write(json.dumps([x.model_dump() for x in response.messages], indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
