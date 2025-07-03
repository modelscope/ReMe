import time

from loguru import logger

from v1.op import OPERATION_REGISTRY
from v1.op.base_op import BaseOp
from v1.pipeline.pipeline_context import PipelineContext


@OPERATION_REGISTRY.register("mock1")
class MockOp1(BaseOp):

    def __init__(self, a: int, b: str, **kwargs):
        super().__init__(**kwargs)
        self.a = a
        self.b = b

    def execute(self, context: PipelineContext):
        time.sleep(3)
        logger.info(f"enter class={self.__class__.__name__}. a={self.a} b={self.b}")


@OPERATION_REGISTRY.register("mock2")
class MockOp2(MockOp1):
    ...


@OPERATION_REGISTRY.register("mock3")
class MockOp3(MockOp1):
    ...


@OPERATION_REGISTRY.register("mock4")
class MockOp4(MockOp1):
    ...


@OPERATION_REGISTRY.register("mock5")
class MockOp5(MockOp1):
    ...


@OPERATION_REGISTRY.register("mock6")
class MockOp6(MockOp1):
    ...
