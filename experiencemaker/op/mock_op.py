import time

from loguru import logger

from experiencemaker.op import OP_REGISTRY
from experiencemaker.op.base_op import BaseOp


@OP_REGISTRY.register()
class Mock1Op(BaseOp):
    def execute(self):
        time.sleep(1)
        a: int = self.op_params["a"]
        b: str = self.op_params["b"]
        logger.info(f"enter class={self.simple_name}. a={a} b={b}")


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
