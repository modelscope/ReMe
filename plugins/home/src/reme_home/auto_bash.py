"""Run allowlisted shell commands without an approval prompt."""

from agentscope.message import TextBlock, ToolResultState
from agentscope.permission import PermissionBehavior, PermissionContext, PermissionDecision
from agentscope.tool import Bash, ToolChunk

from reme.utils.file_sandbox import create_file_sandbox_backend
from reme.steps.base_step import BaseStep

_READ_COMMANDS = {
    ":": {},
    "cat": {},
    "cd": {},
    "cmp": {},
    "diff": {"denied": ["--output"]},
    "echo": {},
    "false": {},
    "file": {},
    "find": {"denied": ["-delete", "-exec", "-execdir", "-fls", "-fprint", "-fprint0", "-fprintf", "-ok", "-okdir"]},
    "git": {
        "allow": ["status", "diff", "log", "show", "rev-parse", "ls-files"],
        "denied": ["--output", "--ext-diff", "--textconv", "--paginate"],
    },
    "grep": {},
    "head": {},
    "ls": {},
    "pwd": {},
    "rg": {"denied": ["--pre", "--pre-glob", "--replace"]},
    "sort": {"denied": ["-o", "--output", "--compress-program", "--temporary-directory"]},
    "stat": {},
    "tail": {},
    "true": {},
    "wc": {},
    "which": {},
}
_SAFE_DESTINATIONS = {"/dev/null"}


class AutoBash(Bash):
    """AgentScope Bash with an optional read-only execution guard."""

    name = "AutoBash"
    description = "Execute shell commands; read-only mode denies commands that may write or run other commands."
    input_schema = {
        **Bash.input_schema,
        "properties": {
            **Bash.input_schema["properties"],
            "timeout": {
                **Bash.input_schema["properties"]["timeout"],
                "description": "Optional timeout in milliseconds (default: 60000, max: 600000)",
                "default": 60000,
            },
        },
    }

    def __init__(self, *, is_read_only: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.is_read_only = is_read_only

    @staticmethod
    def _is_read_only(command: str) -> bool:
        """Use safecmd's Bash parser and a strict command policy."""
        if not isinstance(command, str) or not command.strip():
            return False
        # Variable and command expansion can hide a second operation in an
        # argument. Keep this first version literal while safecmd checks the
        # remaining shell syntax and nested commands.
        if "$" in command or "`" in command:
            return False
        from safecmd import CmdSpec, validate  # pylint: disable=import-outside-toplevel
        from safecmd.bashxtract import extract_commands  # pylint: disable=import-outside-toplevel
        from safecmd.core import normalize_dest  # pylint: disable=import-outside-toplevel

        specs = {CmdSpec(name, denied=options.get("denied")) for name, options in _READ_COMMANDS.items()}
        try:
            validate(command, cmds=specs, dests=_SAFE_DESTINATIONS)
            commands, operators, redirects = extract_commands(command)
            for tokens in commands:
                options = _READ_COMMANDS[tokens[0]]
                # An allow list constrains the first argument (for git, its subcommand).
                # CmdSpec independently rejects every denied argument.
                if "allow" in options and (len(tokens) < 2 or tokens[1] not in options["allow"]):
                    return False
            if "=" in operators or any(normalize_dest(destination) != "/dev/null" for _, destination in redirects):
                return False
        except Exception:  # pylint: disable=broad-exception-caught
            # Parser failures and missing shfmt must never allow execution.
            return False
        return True

    async def check_read_only(self, tool_input: dict) -> bool:
        """Report the same policy used by the execution guard."""
        return self.is_read_only and self._is_read_only(tool_input.get("command", ""))

    async def check_permissions(self, tool_input: dict, _context: PermissionContext) -> PermissionDecision:
        """Resolve permission automatically, without an ASK decision."""
        if not self.is_read_only:
            return PermissionDecision(behavior=PermissionBehavior.ALLOW, message="Command allowed")
        allowed = await self.check_read_only(tool_input)
        return PermissionDecision(
            behavior=PermissionBehavior.ALLOW if allowed else PermissionBehavior.DENY,
            message=(
                "Read-only command allowed" if allowed else "Permission denied: only read-only commands are allowed"
            ),
        )

    async def call(self, command: str, description: str = "", timeout: int = 60000):
        """Apply the read-only guard when configured, then run the command."""
        if self.is_read_only and (not isinstance(command, str) or not self._is_read_only(command)):
            yield ToolChunk(
                content=[TextBlock(text="Permission denied: only read-only shell commands are allowed.")],
                state=ToolResultState.ERROR,
                is_last=True,
            )
            return
        # Git status may otherwise refresh the index, and Git's pager may run
        # a configured program. These exports apply only in read-only mode.
        if self.is_read_only:
            command = "export GIT_OPTIONAL_LOCKS=0 GIT_PAGER=/bin/cat; " + command
        async for chunk in super().call(command=command, description=description, timeout=timeout):
            yield chunk


class AutoBashStep(BaseStep):
    """Expose AgentScope Bash with configurable read-only mode as a ReMe job."""

    async def execute(self):
        assert self.context is not None
        command = self.context.get("command", "")
        timeout = self.context.get("timeout", self.kwargs.get("timeout", 60000))
        is_read_only = self.context.get("is_read_only", self.kwargs.get("is_read_only", True))
        read_only_paths = self.context.get("read_only_paths", self.kwargs.get("read_only_paths"))
        writable_paths = self.context.get("writable_paths", self.kwargs.get("writable_paths"))
        memory_limit_bytes = self.context.get("memory_limit_bytes", self.kwargs.get("memory_limit_bytes"))
        if not isinstance(command, str) or not command.strip():
            self.context.response.success = False
            self.context.response.answer = "command is required"
            return self.context.response
        if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
            self.context.response.success = False
            self.context.response.answer = "timeout must be a positive integer in milliseconds"
            return self.context.response
        if not isinstance(is_read_only, bool):
            self.context.response.success = False
            self.context.response.answer = "is_read_only must be a boolean"
            return self.context.response

        try:
            backend = (
                create_file_sandbox_backend(
                    cwd=self.workspace_path,
                    read_only_paths=[] if read_only_paths is None else read_only_paths,
                    writable_paths=[] if writable_paths is None else writable_paths,
                    memory_limit_bytes=memory_limit_bytes,
                )
                if read_only_paths is not None or writable_paths is not None
                else None
            )
        except (TypeError, ValueError, RuntimeError) as exc:
            self.context.response.success = False
            self.context.response.answer = str(exc)
            return self.context.response

        tool = AutoBash(cwd=self.workspace_path, is_read_only=is_read_only, backend=backend)
        chunks = [chunk async for chunk in tool.call(command=command, timeout=timeout)]
        self.context.response.success = all(chunk.state != ToolResultState.ERROR for chunk in chunks)
        self.context.response.answer = "".join(
            block.text for chunk in chunks for block in chunk.content if isinstance(block, TextBlock)
        )
        return self.context.response
