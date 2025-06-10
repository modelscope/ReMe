from experiencemaker.tool.base_tool import BaseTool
from experiencemaker.tool.code_tool import CodeTool
from experiencemaker.tool.dashscope_search_tool import DashscopeSearchTool
from experiencemaker.tool.terminate_tool import TerminateTool

from experiencemaker.utils.registry import Registry

TOOL_REGISTRY = Registry[BaseTool]("tool")

TOOL_REGISTRY.register(CodeTool, "code")
TOOL_REGISTRY.register(DashscopeSearchTool, "web_search")
TOOL_REGISTRY.register(TerminateTool, "terminate")
