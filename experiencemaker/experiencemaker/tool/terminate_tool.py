from experiencemaker.tool import TOOL_REGISTRY
from experiencemaker.tool.base_tool import BaseTool


@TOOL_REGISTRY.register()
class TerminateTool(BaseTool):
    name: str = "terminate"
    description: str = "If you can answer the user's question based on the context, be sure to use the **terminate** tool."
    parameters: dict = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "description": "Please determine whether the user's question has been completed. (success / failure)",
                "enum": ["success", "failure"],
            }
        },
        "required": ["status"],
    }

    def execute(self, status: str):
        self.success = status in ["success", "failure"]
        return f"The interaction has been completed with status: {status}"
