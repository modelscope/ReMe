from abc import ABC

from loguru import logger
from pydantic import BaseModel, Field


class BaseTool(BaseModel, ABC):
    tool_id: str = Field(default="")
    name: str = Field(..., description="tool name")
    description: str = Field(..., description="tool description")
    tool_type: str = Field(default="function")
    parameters: dict = Field(default_factory=dict, description="tool parameters")
    arguments: dict = Field(default_factory=dict, description="execute arguments")

    enable_cache: bool = Field(default=False, description="whether to cache the tool result")
    cached_result: dict = Field(default_factory=dict, description="tool execution result")

    max_retries: int = Field(default=3, description="max retries")
    raise_exception: bool = Field(default=True, description="raise exception")
    success: bool = Field(default=True, description="whether the tool executed successfully")

    def reset(self):
        self.arguments.clear()
        self.cached_result.clear()
        self.success = True

    def _execute(self, **kwargs):
        raise NotImplementedError

    def execute(self, **kwargs):
        cache_id = ""
        if self.enable_cache:
            cache_id = self.get_cache_id(**kwargs)
            if cache_id in self.cached_result:
                return self.cached_result[cache_id]

        for i in range(self.max_retries):
            try:
                if self.enable_cache:
                    self.cached_result[cache_id] = self._execute(**kwargs)
                    return self.cached_result[cache_id]

                else:
                    return self._execute(**kwargs)

            except Exception as e:
                logger.exception(f"using tool.name={self.name} encounter error with e={e.args}")
                if i == self.max_retries - 1 and self.raise_exception:
                    raise e

        return None


    def simple_dump(self) -> dict:
        """
        It may be in other different tool params formats; different versions are completed here.
        """
        return {
            "type": self.tool_type,
            self.tool_type: {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    @property
    def input_schema(self) -> dict:
        return self.parameters.get("properties", {})

    @property
    def output_schema(self) -> dict:
        raise NotImplementedError

    def refresh(self):
        # for mcp
        raise NotImplementedError

    def get_cache_id(self, **kwargs) -> str:
        raise NotImplementedError
