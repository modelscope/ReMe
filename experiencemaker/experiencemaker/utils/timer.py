import time

from loguru import logger


class Timer(object):
    def __init__(self, name: str, use_ms: bool = False, stack_level: int = 2):
        self.name: str = name
        self.use_ms: bool = use_ms
        self.stack_level: int = stack_level

        self.time_start: float = 0
        self.time_end: float = 0
        self.time_cost: float = 0

    def __enter__(self, *args, **kwargs):
        self.time_start = time.time()
        logger.info(f"---------- enter {self.name} ----------", stacklevel=self.stack_level)
        return self

    def __exit__(self, *args):
        self.time_end = time.time()
        self.time_cost = self.time_end - self.time_start
        if self.use_ms:
            time_str = f"{self.time_cost * 1000:.2f}ms"
        else:
            time_str = f"{self.time_cost:.3f}s"

        logger.info(f"---------- leave {self.name} [{time_str}] ----------", stacklevel=self.stack_level)


def timer(name: str = None, use_ms: bool = False, stack_level: int = 2):
    def decorator(func):
        def wrapper(*args, **kwargs):
            with Timer(name=name or func.__name__, use_ms=use_ms, stack_level=stack_level + 1):
                return func(*args, **kwargs)

        return wrapper

    return decorator


if __name__ == "__main__":
    import random


    @timer("run_func_final", use_ms=True)
    def run_func():
        time.sleep(random.uniform(0.05, 0.15))
        print("done")


    run_func()
