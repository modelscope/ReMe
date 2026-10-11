"""Shell job and its optional read-only execution guard."""

import inspect
from importlib.metadata import EntryPoint
from pathlib import Path

import pytest
import yaml

from agentscope.message import ToolResultState
from agentscope.permission import PermissionBehavior
from agentscope.tool import ExecResult
from reme_home.auto_bash import AutoBash, AutoBashStep

from reme.utils.path_bubble_backend import PathBubbleBackend
from reme.components.application_context import ApplicationContext
from reme.config.config_parser import _load_config
from reme.enumeration import ComponentEnum
from reme.plugin import resolve_plugin_runtime


@pytest.fixture(autouse=True)
def linux_backend_selection(monkeypatch):
    """Keep existing backend integration assertions on the Linux implementation."""
    monkeypatch.setattr("reme.utils.file_sandbox.sys.platform", "linux")


@pytest.mark.asyncio
async def test_auto_bash_runs_in_workspace(tmp_path):
    """Approved commands run relative to the configured workspace."""
    (tmp_path / "note.txt").write_text("hello", encoding="utf-8")
    step = AutoBashStep(app_context=ApplicationContext(workspace_dir=str(tmp_path)))

    response = await step(command="cat note.txt")

    assert response.success is True
    assert response.answer == "hello"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "command",
    [
        "touch denied.txt",
        "cat note.txt > denied.txt",
        "echo hello > /dev/null-extra",
        "cat $(touch denied.txt)",
        "echo ${X:-$(touch denied.txt)}",
        "cat note.txt; touch denied.txt",
        "cat note.txt\ntouch denied.txt",
        "tee denied.txt",
        "find . -delete",
        "find . -exec touch denied.txt {} \\;",
        "find . -fprint denied.txt",
        "sort -o denied.txt note.txt",
        "sort --compress-program='touch denied.txt' note.txt",
        "diff --output=denied.txt note.txt note.txt",
        "git add note.txt",
        "git branch new-branch",
        "git diff --output=denied.txt",
        "git log --ext-diff",
        "git -c alias.status=add status",
        "GIT_OPTIONAL_LOCKS=1 git status",
        "GIT_PAGER=sh git log",
        "nop",
        "rg --pre='touch denied.txt' pattern .",
    ],
)
async def test_auto_bash_denies_mutation_before_execution(tmp_path, command):
    """Writing and dynamic shell forms fail before a child process starts."""
    (tmp_path / "note.txt").write_text("hello", encoding="utf-8")
    tool = AutoBash(cwd=tmp_path)

    chunks = [chunk async for chunk in tool.call(command)]

    assert len(chunks) == 1
    assert chunks[0].state == ToolResultState.ERROR
    assert "Permission denied" in chunks[0].content[0].text
    assert not (tmp_path / "denied.txt").exists()


@pytest.mark.asyncio
async def test_step_returns_permission_error(tmp_path):
    """The job exposes a denied command as an unsuccessful response."""
    step = AutoBashStep(app_context=ApplicationContext(workspace_dir=str(tmp_path)))

    response = await step(command="touch denied.txt")

    assert response.success is False
    assert "Permission denied" in response.answer
    assert not (tmp_path / "denied.txt").exists()


@pytest.mark.asyncio
async def test_step_can_run_unrestricted_commands(tmp_path):
    """Job input can disable the guard for commands that write files."""
    step = AutoBashStep(app_context=ApplicationContext(workspace_dir=str(tmp_path)))

    response = await step(command="echo hello > written.txt", is_read_only=False)

    assert response.success is True
    assert (tmp_path / "written.txt").read_text(encoding="utf-8") == "hello\n"


@pytest.mark.asyncio
async def test_unsupported_platform_runs_without_paths_but_rejects_path_policy(tmp_path, monkeypatch):
    """AutoBash never drops an explicitly requested sandbox on unsupported systems."""
    monkeypatch.setattr("reme.utils.file_sandbox.sys.platform", "unsupported")
    step = AutoBashStep(app_context=ApplicationContext(workspace_dir=str(tmp_path)))

    plain = await step(command="echo host", is_read_only=False)
    assert plain.success is True
    assert plain.answer.strip() == "host"

    restricted = await step(command="echo blocked", is_read_only=False, read_only_paths=[])
    assert restricted.success is False
    assert restricted.answer == "No file sandbox backend for unsupported"


@pytest.mark.asyncio
async def test_step_configuration_can_disable_read_only(tmp_path):
    """Step configuration applies when the job does not supply the flag."""
    step = AutoBashStep(app_context=ApplicationContext(workspace_dir=str(tmp_path)), is_read_only=False)

    response = await step(command="touch written.txt")

    assert response.success is True
    assert (tmp_path / "written.txt").exists()


@pytest.mark.asyncio
async def test_step_rejects_non_boolean_mode(tmp_path):
    """A string false value must not silently enable unrestricted execution."""
    step = AutoBashStep(app_context=ApplicationContext(workspace_dir=str(tmp_path)))

    response = await step(command="touch denied.txt", is_read_only="false")

    assert response.success is False
    assert response.answer == "is_read_only must be a boolean"
    assert not (tmp_path / "denied.txt").exists()


@pytest.mark.asyncio
async def test_permission_decisions_never_ask(tmp_path):
    """Direct AgentScope use makes allow/deny decisions without ASK."""
    tool = AutoBash(cwd=tmp_path)

    allowed = await tool.check_permissions({"command": "ls"}, None)
    denied = await tool.check_permissions({"command": "touch denied.txt"}, None)

    assert allowed.behavior == PermissionBehavior.ALLOW
    assert denied.behavior == PermissionBehavior.DENY


@pytest.mark.asyncio
async def test_unrestricted_tool_allows_commands_without_read_only_check(tmp_path, monkeypatch):
    """The unrestricted tool never invokes the read-only parser."""
    tool = AutoBash(cwd=tmp_path, is_read_only=False)
    monkeypatch.setattr(tool, "_is_read_only", lambda _command: pytest.fail("read-only parser was called"))

    decision = await tool.check_permissions({"command": "touch written.txt"}, None)
    chunks = [chunk async for chunk in tool.call("touch written.txt")]

    assert decision.behavior == PermissionBehavior.ALLOW
    assert all(chunk.state != ToolResultState.ERROR for chunk in chunks)
    assert (tmp_path / "written.txt").exists()


def test_auto_bash_defaults_to_sixty_seconds():
    """Tool and default job expose the same 60-second timeout."""
    manifest = Path(__file__).parents[1] / "src" / "reme_home" / "plugin.yaml"
    with manifest.open(encoding="utf-8") as config_file:
        job = yaml.safe_load(config_file)["application_defaults"]["jobs"]["auto_bash"]

    assert inspect.signature(AutoBash.call).parameters["timeout"].default == 60000
    assert AutoBash.input_schema["properties"]["timeout"]["default"] == 60000
    assert job["parameters"]["properties"]["timeout"]["default"] == 60000
    assert job["parameters"]["properties"]["is_read_only"]["default"] is True


@pytest.mark.asyncio
async def test_auto_bash_uses_path_backend_when_paths_supplied(tmp_path, monkeypatch):
    """AutoBash routes an injected path policy through the backend."""
    seen = {}

    async def fake_exec(self, command, *, cwd=None, timeout=None):
        seen.update(command=command, cwd=cwd, timeout=timeout, backend=self)
        return ExecResult(exit_code=0, stdout=b"ok", stderr=b"")

    monkeypatch.setattr(PathBubbleBackend, "exec_shell", fake_exec)
    step = AutoBashStep(app_context=ApplicationContext(workspace_dir=str(tmp_path)))
    response = await step(command="printf ok", is_read_only=False, read_only_paths=[], writable_paths=[str(tmp_path)])

    assert response.success is True
    assert response.answer == "ok"
    assert seen["command"] == ["/bin/sh", "-c", "printf ok"]
    assert seen["cwd"] == str(tmp_path)
    assert seen["timeout"] == 60


@pytest.mark.asyncio
async def test_sandbox_start_failure_does_not_run_on_host(tmp_path, monkeypatch):
    """The plugin reports a sandbox failure instead of executing on the host."""

    async def unavailable(*_args, **_kwargs):
        raise RuntimeError("bwrap unavailable")

    monkeypatch.setattr(PathBubbleBackend, "_start_process", unavailable)
    step = AutoBashStep(app_context=ApplicationContext(workspace_dir=str(tmp_path)))
    result = await step(command="printf host", is_read_only=False, read_only_paths=[])

    assert result.success is False
    assert "bwrap unavailable" in result.answer


def test_home_manifest_declares_step_and_job():
    """The installed manifest is the source for backend and job registration."""
    manifest = Path(__file__).parents[1] / "src" / "reme_home" / "plugin.yaml"
    config = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    assert config["backends"]["auto_bash_step"] == "reme_home.auto_bash:AutoBashStep"
    job = config["application_defaults"]["jobs"]["auto_bash"]
    assert job["steps"] == [{"backend": "auto_bash_step"}]
    assert job["parameters"]["properties"]["read_only_paths"]["type"] == "array"
    assert job["parameters"]["properties"]["writable_paths"]["type"] == "array"


def test_home_plugin_registers_job_and_step(monkeypatch):
    """Enabling home adds its job and Step to one application runtime."""
    entry = EntryPoint(name="home", value="reme_home", group="reme.plugins")
    monkeypatch.setattr("reme.plugin.find_entry_points", lambda group, name: [entry] if name == "home" else [])
    config = _load_config("default")
    assert "auto_bash" not in config["jobs"]
    config["plugins"] = ["home"]

    runtime = resolve_plugin_runtime(config)

    assert runtime.registry.get(ComponentEnum.STEP, "auto_bash_step") is AutoBashStep
    assert runtime.config["jobs"]["auto_bash"]["steps"] == [{"backend": "auto_bash_step"}]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "command",
    [
        ":",
        "cd . && pwd",
        "echo hello",
        "true",
        "false",
        "grep hello note.txt",
        "rg hello note.txt",
        "find . -name note.txt",
        "sort note.txt",
        "diff note.txt note.txt",
        "cmp note.txt note.txt",
        "git status --short",
        "git diff --stat",
        "git log --oneline",
        "git show HEAD",
        "git rev-parse HEAD",
        "git ls-files",
    ],
)
async def test_safe_command_forms_are_allowed(tmp_path, command):
    """Common non-writing commands pass the policy regardless of exit code."""
    (tmp_path / "note.txt").write_text("hello\n", encoding="utf-8")
    tool = AutoBash(cwd=tmp_path)

    assert await tool.check_read_only({"command": command})


@pytest.mark.asyncio
async def test_safe_redirection_is_allowed(tmp_path):
    """safecmd allows output to /dev/null and input from workspace files."""
    (tmp_path / "note.txt").write_text("hello\n", encoding="utf-8")
    tool = AutoBash(cwd=tmp_path)

    assert await tool.check_read_only({"command": "echo hello > /dev/null"})
    assert await tool.check_read_only({"command": "cat < note.txt"})


@pytest.mark.asyncio
async def test_allow_and_denied_command_options_are_combined(tmp_path, monkeypatch):
    """Allow constrains the first argument while denied still checks later flags."""
    from reme_home import auto_bash

    commands = auto_bash._READ_COMMANDS  # pylint: disable=protected-access
    monkeypatch.setitem(commands, "echo", {"allow": ["hello"]})
    tool = AutoBash(cwd=tmp_path)

    assert await tool.check_read_only({"command": "echo hello"})
    assert not await tool.check_read_only({"command": "echo goodbye"})

    monkeypatch.setitem(commands, "echo", {"allow": ["hello"], "denied": ["-n"]})
    assert not await tool.check_read_only({"command": "echo hello -n"})
    assert await tool.check_read_only({"command": "find . -name note.txt"})
    assert not await tool.check_read_only({"command": "find . -delete"})
