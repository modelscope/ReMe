import re


def camel_to_snake(content: str) -> str:
    """
    BaseWorker -> base_worker
    """
    snake_str = re.sub(r'(?<!^)(?=[A-Z])', '_', content).lower()
    return snake_str


def snake_to_camel(content: str) -> str:
    """
    base_worker -> BaseWorker
    """
    camel_str = "".join(x.capitalize() for x in content.split("_"))
    return camel_str
