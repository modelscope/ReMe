from experiencescope.tool.python_tools.code_tool import CodeTool
from experiencescope.tool.python_tools.dashscope_search_tool import DashscopeSearchTool
from experiencescope.tool.python_tools.terminate_tool import TerminateTool

from experiencescope.utils.registry import Registry

TOOL_REGISTRY = Registry("tools")
TOOL_REGISTRY.register(CodeTool)
TOOL_REGISTRY.register(DashscopeSearchTool)
TOOL_REGISTRY.register(TerminateTool)
