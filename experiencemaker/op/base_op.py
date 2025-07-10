from abc import abstractmethod, ABCMeta

from loguru import logger

from experiencemaker.op.prompt_mixin import PromptMixin
from experiencemaker.pipeline.pipeline_context import PipelineContext
from experiencemaker.utils.timer import Timer


class BaseOp(PromptMixin, metaclass=ABCMeta):

    def __init__(self, context: PipelineContext, **kwargs):
        super().__init__(**kwargs)
        self.context: PipelineContext = context
        self.timer = Timer(name=self.simple_name)

    @property
    def simple_name(self) -> str:
        return self.__class__.__name__.lower()

    @abstractmethod
    def execute(self):
        ...

    def execute_wrap(self):
        try:
            with self.timer:
                return self.execute()

        except Exception as e:
            logger.exception(f"op={self.simple_name} execute failed, error={e.args}")
