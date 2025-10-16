from flowllm import C, BaseAsyncOp
from loguru import logger

@C.register_op()
class ParseToolCallResultOp(BaseAsyncOp):
    file_path: str = __file__

    async def async_execute(self):
        tool_call_results: list = self.context.get("tool_call_results", [])
        logger.info(f"tool_call_results={tool_call_results}")


        self.context.response.answer = "haha"