from experiencemaker.tool.code_tool import CodeTool
from experiencemaker.tool.dashscope_search_tool import DashscopeSearchTool
from experiencemaker.tool.terminate_tool import TerminateTool

from experiencemaker.utils.registry import Registry

TOOL_REGISTRY = Registry("tools")
TOOL_REGISTRY.register(CodeTool)
TOOL_REGISTRY.register(DashscopeSearchTool)
TOOL_REGISTRY.register(TerminateTool)
