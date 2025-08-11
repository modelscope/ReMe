from loguru import logger

from experiencemaker.op import OP_REGISTRY
from experiencemaker.op.base_op import BaseOp
from experiencemaker.schema.request import RetrieverRequest
from experiencemaker.utils.op_utils import merge_messages_content


@OP_REGISTRY.register()
class BuildQueryOp(BaseOp):
    current_path: str = __file__

    def execute(self):
        request: RetrieverRequest = self.context.request
        if request.query:
            query = request.query

        elif request.messages:
            enable_llm_build: str = str(self.op_params.get("enable_llm_build"))
            if enable_llm_build and enable_llm_build.lower() == "true":
                execution_process = merge_messages_content(request.messages)
                query = self.prompt_format(prompt_name="query_build", execution_process=execution_process)

            else:
                context_parts = []
                message_summaries = []
                for message in request.messages[-3:]:  # Last 3 messages
                    content = message.content[:200] + "..." if len(message.content) > 200 else message.content
                    message_summaries.append(f"- {message.role.value}: {content}")
                if message_summaries:
                    context_parts.append("Recent messages:\n" + "\n".join(message_summaries))

                query = "\n\n".join(context_parts)

        else:
            raise RuntimeError("query or messages is required!")

        logger.info(f"build.query={query}")

        from experiencemaker.op.vector_store.recall_vector_store_op import RecallVectorStoreOp
        self.context.set_context(RecallVectorStoreOp.SEARCH_QUERY, query)
        self.context.set_context(RecallVectorStoreOp.SEARCH_MESSAGE, request.messages)
