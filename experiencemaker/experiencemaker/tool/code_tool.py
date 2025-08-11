import sys
from io import StringIO

from experiencemaker.tool import TOOL_REGISTRY
from experiencemaker.tool.base_tool import BaseTool


@TOOL_REGISTRY.register()
class CodeTool(BaseTool):
    name: str = "python_execute"
    description: str = "Execute python code can be used in scenarios such as analysis or calculation, and the final result can be printed using the `print` function."
    parameters: dict = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "code to be executed. Please do not execute any matplotlib code here.",
            }
        },
        "required": ["code"]
    }

    def _execute(self, code: str, **kwargs):
        old_stdout = sys.stdout
        redirected_output = sys.stdout = StringIO()

        try:
            exec(code)
            result = redirected_output.getvalue()

        except Exception as e:
            self.success = False
            result = str(e)

        sys.stdout = old_stdout

        return result


if __name__ == '__main__':
    tool = CodeTool()
    print(tool.execute(code="print('Hello World')"))
    print(tool.execute(code="print('Hello World!'"))
