import datetime
from typing import Tuple

from flowllm import C, BaseAsyncOp
from loguru import logger

from reme_ai.constants.common_constants import QUERY_WITH_TS


@C.register_op()
class SetQueryOp(BaseAsyncOp):
    """
    The `SetQueryOp` class is responsible for setting a query and its associated timestamp
    into the context, utilizing either provided parameters or details from the context.
    """

    async def async_execute(self):
        """
        Executes the operation's primary function, which involves determining the query and its
        timestamp, then storing these values within the context.

        Input requirement: self.context.query must exist (flow input requirement)
        """
        # Flow guarantees query exists - use it directly
        query: str = self.context.query
        timestamp: int = int(datetime.datetime.now().timestamp())

        # Set timestamp if provided in op_params
        _timestamp = self.op_params.get("timestamp")
        if _timestamp and isinstance(_timestamp, int):
            timestamp = _timestamp

        # Store the query and its timestamp in the context
        query_with_ts: Tuple[str, int] = (query, timestamp)
        self.context[QUERY_WITH_TS] = query_with_ts

        logger.info(f"Set query with timestamp: query='{query}', timestamp={timestamp}")
