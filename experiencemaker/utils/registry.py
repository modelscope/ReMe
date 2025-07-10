from typing import List

from loguru import logger

from experiencemaker.utils.common_utils import camel_to_snake


class Registry(object):
    def __init__(self):
        self._registry = {}

    def register(self, name: str = ""):

        def decorator(cls):
            class_name = name if name else camel_to_snake(cls.__name__)
            if class_name in self._registry:
                logger.warning(f"name={class_name} is already registered, will be overwritten.")
            self._registry[class_name] = cls
            return cls

        return decorator

    def __getitem__(self, name: str):
        if name not in self._registry:
            raise KeyError(f"name={name} is not registered!")
        return self._registry[name]

    def __contains__(self, name: str):
        return name in self._registry

    @property
    def registered_names(self) -> List[str]:
        return sorted(self._registry.keys())
