import time

from loguru import logger

from experiencemaker.op import OP_REGISTRY
from experiencemaker.op.base_op import BaseOp


@OP_REGISTRY.register()
class Mock1Op(BaseOp):

    def __init__(self, a: int = 1, b: str = "2", **kwargs):
        super().__init__(**kwargs)
        self.a = a
        self.b = b

    def execute(self):
        time.sleep(3)
        logger.info(f"enter class={self.__class__.__name__}. a={self.a} b={self.b}")


@OP_REGISTRY.register()
class Mock2Op(Mock1Op):
    ...


@OP_REGISTRY.register()
class Mock3Op(Mock1Op):
    ...


@OP_REGISTRY.register()
class Mock4Op(Mock1Op):
    ...


@OP_REGISTRY.register()
class Mock5Op(Mock1Op):
    ...


@OP_REGISTRY.register()
class Mock6Op(Mock1Op):
    ...
