import datetime
from typing import Tuple

from flowllm import C, BaseOp
from loguru import logger

from reme_ai.constants.common_constants import QUERY_WITH_TS


@C.register_op()
class SetQueryOp(BaseOp):
    """
    The `SetQueryOp` class is responsible for setting a query and its associated timestamp
    into the context, utilizing either provided parameters or details from the context.
    """
    file_path: str = __file__

    def execute(self):
        """
        Executes the operation's primary function, which involves determining the query and its
        timestamp, then storing these values within the context.

        If 'query' exists in context, it is used directly. Otherwise, extracts query from
        messages or other context parameters.
        """
        query = ""  # Default query value
        timestamp = int(datetime.datetime.now().timestamp())  # Current timestamp as default

        try:
            # Check if query already exists in context
            if hasattr(self.context, 'query') and self.context.query:
                query = str(self.context.query).strip()
                logger.info(f"Using existing query from context: {query}")

            # Check for query in op_params
            elif "query" in self.op_params:
                query = self.op_params["query"]
                if not query:
                    query = ""
                query = query.strip()
                logger.info(f"Using query from op_params: {query}")

            # Check for messages in context
            elif hasattr(self.context, 'messages') and self.context.messages:
                # Use the last message content as query
                last_message = self.context.messages[-1]
                query = last_message.content.strip() if hasattr(last_message, 'content') else ""
                logger.info(f"Using query from last message: {query}")

            # Set timestamp if provided in op_params
            _timestamp = self.op_params.get("timestamp")
            if _timestamp and isinstance(_timestamp, int):
                timestamp = _timestamp

            # Store the determined query and its timestamp in the context
            query_with_ts: Tuple[str, int] = (query, timestamp)
            self.context[QUERY_WITH_TS] = query_with_ts

            logger.info(f"Set query with timestamp: query='{query}', timestamp={timestamp}")

        except Exception as e:
            logger.error(f"Error in SetQueryOp execution: {e}")
            # Fallback: set empty query with current timestamp
            self.context[QUERY_WITH_TS] = ("", timestamp)
