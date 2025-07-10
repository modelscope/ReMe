from loguru import logger

from experiencemaker.op import OP_REGISTRY
from experiencemaker.op.base_op import BaseOp
from experiencemaker.schema.request import RetrieverRequest
from experiencemaker.utils.op_utils import merge_messages_content


@OP_REGISTRY.register()
class BuildQueryOp(BaseOp):
    RETRIEVE_QUERY = "retrieve_query"

    def execute(self):
        request: RetrieverRequest = self.context.request
        if request.query:
            query = request.query

        elif request.messages:
            if not self.op_params.get("enable_llm_build"):
                execution_process = merge_messages_content(request.messages)
                query = self.prompt_format(prompt_name="query_build", execution_process=execution_process)
            else:
                query = request.messages[-1].content

        else:
            raise RuntimeError("query or messages is required!")

        logger.info(f"build.query={query}")

        self.context.set_context(self.RETRIEVE_QUERY, query)
