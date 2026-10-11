"""Shared file sandbox selection and macOS policy construction."""

import sys

import pytest
from agentscope.tool import ExecResult

from reme.components.application_context import ApplicationContext
from reme.steps.common.python_execute import PythonExecuteStep
from reme.utils.file_sandbox import create_file_sandbox_backend
from reme.utils.path_bubble_backend import PathBubbleBackend
from reme.utils.path_seatbelt_backend import PathSeatbeltBackend


def test_platform_selection_and_memory_defaults(tmp_path, monkeypatch):
    """Linux retains cgroups while macOS defaults to no unsupported memory cap."""
    monkeypatch.setattr("reme.utils.file_sandbox.sys.platform", "linux")
    linux = create_file_sandbox_backend(cwd=tmp_path, read_only_paths=[], writable_paths=[])
    assert isinstance(linux, PathBubbleBackend)
    assert linux._memory_limit_bytes == 4 * 1024**3  # pylint: disable=protected-access

    monkeypatch.setattr("reme.utils.file_sandbox.sys.platform", "darwin")
    mac = create_file_sandbox_backend(cwd=tmp_path, read_only_paths=[], writable_paths=[])
    assert isinstance(mac, PathSeatbeltBackend)
    with pytest.warns(RuntimeWarning, match="limit is ignored on macOS"):
        limited = create_file_sandbox_backend(
            cwd=tmp_path,
            read_only_paths=[],
            writable_paths=[],
            memory_limit_bytes=1024,
        )
    assert isinstance(limited, PathSeatbeltBackend)


@pytest.mark.asyncio
async def test_unsupported_platform_requires_backend_only_for_path_policy(tmp_path, monkeypatch):
    """An unsupported platform runs ordinary Python but rejects a requested sandbox."""
    monkeypatch.setattr("reme.utils.file_sandbox.sys.platform", "unsupported")
    step = PythonExecuteStep(app_context=ApplicationContext(workspace_dir=str(tmp_path)))

    plain = await step(code="print('host')")
    assert plain.success is True
    assert plain.answer == "host\n"

    restricted = await step(code="print('blocked')", read_only_paths=[])
    assert restricted.success is False
    assert restricted.answer == "No file sandbox backend for unsupported"


def test_seatbelt_profile_limits_file_access(tmp_path):
    """The profile grants configured paths and a separate per-run temporary directory."""
    output = tmp_path / "output"
    output.mkdir()
    backend = PathSeatbeltBackend(cwd=tmp_path, read_only_paths=[str(tmp_path)], writable_paths=[str(output)])
    profile = backend._profile(str(tmp_path / "temporary"))  # pylint: disable=protected-access
    assert "(deny default)" in profile
    assert f'(allow file-read* (subpath "{tmp_path}"))' in profile
    assert f'(allow file-write* (subpath "{output}"))' in profile
    assert f'(allow file-write* (subpath "{tmp_path}"))' not in profile
    assert "network*" not in profile


def test_seatbelt_excludes_read_only_child_from_writable_parent(tmp_path):
    """A parent write grant must not override a nested read-only restriction."""
    protected = tmp_path / "protected"
    protected.mkdir()
    output = protected / "output"
    output.mkdir()
    backend = PathSeatbeltBackend(
        cwd=tmp_path,
        read_only_paths=[str(protected)],
        writable_paths=[str(tmp_path), str(output)],
    )
    profile = backend._profile(str(tmp_path / "temporary"))  # pylint: disable=protected-access
    assert (
        f'(allow file-write* (require-all (subpath "{tmp_path}") ' f'(require-not (subpath "{protected}"))))'
    ) in profile
    assert f'(allow file-write* (subpath "{output}"))' in profile


@pytest.mark.asyncio
async def test_seatbelt_launch_failure_cleans_up_without_host_fallback(tmp_path, monkeypatch):
    """A failed sandbox launcher never starts the requested command directly."""
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr("reme.utils.path_seatbelt_backend.shutil.which", lambda _: "/usr/bin/sandbox-exec")
    calls = []

    async def fail(*argv, **_kwargs):
        calls.append(argv)
        raise OSError("sandbox unavailable")

    monkeypatch.setattr("reme.utils.path_seatbelt_backend.asyncio.create_subprocess_exec", fail)
    backend = PathSeatbeltBackend(cwd=tmp_path, read_only_paths=[], writable_paths=[])
    with pytest.raises(OSError, match="sandbox unavailable"):
        await backend.exec_shell(["/bin/echo", "unsafe"])
    assert calls[0][0] == "/usr/bin/sandbox-exec"
    assert calls[0][-2:] == ("/bin/echo", "unsafe")
    assert not backend._process_tempdirs  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_python_job_selects_seatbelt_on_macos(tmp_path, monkeypatch):
    """Path injection reaches the macOS backend with no implicit memory cap."""
    monkeypatch.setattr("reme.utils.file_sandbox.sys.platform", "darwin")
    seen = {}

    async def fake_exec(self, command, *, cwd=None, timeout=None):
        seen.update(backend=self, command=command, cwd=cwd, timeout=timeout)
        return ExecResult(exit_code=0, stdout=b"ok\n", stderr=b"")

    monkeypatch.setattr(PathSeatbeltBackend, "exec_shell", fake_exec)
    step = PythonExecuteStep(app_context=ApplicationContext(workspace_dir=str(tmp_path)))
    response = await step(code="print('ok')", read_only_paths=[])
    assert response.success is True
    assert isinstance(seen["backend"], PathSeatbeltBackend)
    assert seen["command"] == [sys.executable, "-c", "print('ok')"]
