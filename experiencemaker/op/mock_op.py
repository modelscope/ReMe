import time

from loguru import logger

from experiencemaker.op import OP_REGISTRY
from experiencemaker.op.base_op import BaseOp


@OP_REGISTRY.register("mock1_op")
class MockOp1(BaseOp):

    def __init__(self, a: int = 1, b: str = "2", **kwargs):
        super().__init__(**kwargs)
        self.a = a
        self.b = b

    def execute(self):
        time.sleep(3)
        logger.info(f"enter class={self.__class__.__name__}. a={self.a} b={self.b}")


@OP_REGISTRY.register("mock2_op")
class MockOp2(MockOp1):
    ...


@OP_REGISTRY.register("mock3_op")
class MockOp3(MockOp1):
    ...


@OP_REGISTRY.register("mock4_op")
class MockOp4(MockOp1):
    ...


@OP_REGISTRY.register("mock5_op")
class MockOp5(MockOp1):
    ...


@OP_REGISTRY.register("mock6_op")
class MockOp6(MockOp1):
    ...
