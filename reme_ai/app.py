import asyncio
import sys
from typing import List

from flowllm import FlowLLMApp, C
from flowllm.schema.flow_response import FlowResponse
from loguru import logger

from reme_ai.config.config_parser import ConfigParser


class ReMeApp(FlowLLMApp):

    def __init__(self, args: List[str] = None):
        super().__init__(args=args, parser=ConfigParser)
        self.registered_flows = C.flow_dict.keys()
        logger.info(f"registered_flows={self.registered_flows}")

    async def async_execute(self, name: str, **kwargs) -> dict:
        assert name in self.registered_flows, f"Invalid flow_name={name} !"
        result: FlowResponse = await self.async_execute_flow(name=name, **kwargs)
        return result.model_dump()

    def execute(self, name: str, **kwargs) -> dict:
        return asyncio.run(self.async_execute(name=name, **kwargs))


def main():
    with ReMeApp(args=sys.argv[1:]) as app:
        app.run_service()

if __name__ == "__main__":
    main()
