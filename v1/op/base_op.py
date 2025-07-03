from abc import abstractmethod, ABC

from loguru import logger

from v1.pipeline.pipeline_context import PipelineContext
from v1.utils.timer import Timer


class BaseOp(ABC):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.timer = Timer(name=self.__class__.__name__)

    @abstractmethod
    def execute(self, context: PipelineContext):
        ...

    def execute_wrap(self, context: PipelineContext):
        try:
            with self.timer:
                return self.execute(context)

        except Exception as e:
            logger.exception(f"OP.{self.__class__.__name__} execute failed, error={e.args}")
