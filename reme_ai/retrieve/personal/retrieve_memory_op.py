from flowllm import C

from reme_ai.vector_store import RecallVectorStoreOp


@C.register_op()
class RetrieveMemoryOp(RecallVectorStoreOp):
    """
    Retrieves memories based on specified criteria such as status, type, and timestamp.
    Processes these memories concurrently, sorts them by similarity, and logs the activity,
    facilitating efficient memory retrieval operations within a given scope.
    """
    file_path: str = __file__
