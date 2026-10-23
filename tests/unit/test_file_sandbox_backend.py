"""Shared file sandbox selection and macOS policy construction."""

import asyncio
import os
import plistlib
import sys
from contextlib import nullcontext
from pathlib import Path

import pytest
from agentscope.tool import ExecResult

from reme.components.application_context import ApplicationContext
from reme.steps.common.python_execute import PythonExecuteStep
from reme.utils.local_backend import LocalProcessBackend
from reme.utils.file_sandbox import create_file_sandbox_backend
from reme.utils.file_sandbox.path_bubble_backend import PathBubbleBackend
from reme.utils.file_sandbox.path_seatbelt_backend import PathSeatbeltBackend


def test_platform_selection_and_memory_defaults(tmp_path, monkeypatch):
    """Linux retains cgroups while macOS defaults to no unsupported memory cap."""
    monkeypatch.setattr("reme.utils.file_sandbox.sys.platform", "linux")
    linux = create_file_sandbox_backend(cwd=tmp_path, read_only_paths=[], writable_paths=[])
    assert isinstance(linux, PathBubbleBackend)
    assert linux._memory_limit_mib == 4096  # pylint: disable=protected-access

    monkeypatch.setattr("reme.utils.file_sandbox.sys.platform", "darwin")
    mac = create_file_sandbox_backend(cwd=tmp_path, read_only_paths=[], writable_paths=[])
    assert isinstance(mac, PathSeatbeltBackend)
    with pytest.warns(RuntimeWarning, match="limit is ignored on macOS"):
        limited = create_file_sandbox_backend(
            cwd=tmp_path,
            read_only_paths=[],
            writable_paths=[],
            memory_limit_mib=1024,
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
    assert '(allow file-write* (literal "/dev/null"))' in profile
    assert '(allow file-write* (subpath "/dev"))' not in profile
    assert "network*" not in profile


def test_sandbox_reads_virtual_environment_base_runtime(tmp_path, monkeypatch):
    """A virtual environment grants its real base interpreter without widening writes."""
    workspace = tmp_path / "workspace"
    venv = tmp_path / "venv"
    runtime = tmp_path / "runtime"
    interpreter = tmp_path / "interpreter" / "python"
    workspace.mkdir()
    (venv / "bin").mkdir(parents=True)
    runtime.mkdir()
    interpreter.parent.mkdir(parents=True)
    interpreter.touch()
    (venv / "bin" / "python").symlink_to(interpreter)
    monkeypatch.setattr(sys, "prefix", str(venv))
    monkeypatch.setattr(sys, "base_prefix", str(runtime))
    monkeypatch.setattr(sys, "executable", str(venv / "bin" / "python"))

    backend = PathSeatbeltBackend(cwd=workspace, read_only_paths=[], writable_paths=[str(workspace)])
    profile = backend._profile(str(workspace / "temporary"))  # pylint: disable=protected-access

    assert f'(allow file-read* (subpath "{runtime}"))' in profile
    assert f'(allow file-read* (literal "{interpreter}"))' in profile
    assert f'(allow file-write* (subpath "{runtime}"))' not in profile
    assert f'(allow file-write* (literal "{interpreter}"))' not in profile


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
@pytest.mark.parametrize("backend_class", [PathBubbleBackend, PathSeatbeltBackend])
@pytest.mark.parametrize("data", [b"", b"hello\x00\n\xff"])
async def test_sandbox_file_io_round_trip(tmp_path, monkeypatch, backend_class, data):
    """The common file helpers preserve binary stdin, literal paths and write errors."""
    from unittest.mock import AsyncMock

    backend = backend_class(cwd=tmp_path, read_only_paths=[], writable_paths=[str(tmp_path)])
    # Exercise shared file I/O with real pipes; OS isolation is checked separately.
    monkeypatch.setattr(
        backend,
        "_start_process",
        LocalProcessBackend()._start_process,  # pylint: disable=protected-access
    )
    if backend_class is PathSeatbeltBackend:
        monkeypatch.setattr(sys, "platform", "darwin")
        monkeypatch.setattr("reme.utils.file_sandbox.path_seatbelt_backend.shutil.which", lambda _: "sandbox-exec")
        monkeypatch.setattr(backend, "_has_gui_launchd", AsyncMock(return_value=False))
    warning = (
        pytest.warns(RuntimeWarning, match="No macOS GUI launchd domain")
        if backend_class is PathSeatbeltBackend
        else nullcontext()
    )
    with warning:
        path = str(tmp_path / "nested directory" / "literal ' ; name.bin")
        await backend.write_file(path, data)
        assert await backend.read_file(path) == data
        with pytest.raises(TypeError, match="data must be bytes"):
            await backend.write_file(path, "invalid")
        with pytest.raises(OSError):
            await backend.write_file(str(tmp_path), data)


@pytest.mark.asyncio
@pytest.mark.parametrize("sandbox", [False, True])
@pytest.mark.parametrize("cancel", [False, True])
async def test_inherited_pipe_cleanup_is_bounded(tmp_path, monkeypatch, sandbox, cancel):
    """A surviving child with an output pipe must not hold the timeout response open."""
    from unittest.mock import Mock

    backend = (
        PathBubbleBackend(cwd=tmp_path, read_only_paths=[], writable_paths=[], memory_limit_mib=0)
        if sandbox
        else LocalProcessBackend()
    )
    started = asyncio.Event()
    cancelled = asyncio.Event()

    class StuckPipe:
        """Model an inherited pipe held open after termination."""

        async def read(self, _size):
            """Wait forever until the caller cancels pipe draining."""
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

    class StuckProcess:
        """Model a child that keeps its output pipe open after termination."""

        pid = 12345
        _transport = Mock()
        stdout = StuckPipe()
        stderr = StuckPipe()
        stdin = None

        async def wait(self):
            """A stale process transport must also have a bounded wait."""
            await asyncio.Event().wait()

    async def start(*_args, **_kwargs):
        return StuckProcess()

    monkeypatch.setattr(backend, "_start_process", start)
    monkeypatch.setattr(backend, "_kill_process", lambda _process: None)
    monkeypatch.setattr("reme.utils.local_backend._CLEANUP_TIMEOUT", 0.01)

    task = asyncio.create_task(backend.exec_shell(["true"], timeout=None if cancel else 0.01))
    await asyncio.wait_for(started.wait(), timeout=1)
    if cancel:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, timeout=1)
    else:
        result = await asyncio.wait_for(task, timeout=1)
        assert result.exit_code == -1 and result.stderr == b"timed out"
    assert cancelled.is_set()
    StuckProcess._transport.close.assert_called_once()  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_seatbelt_launch_failure_cleans_up_without_host_fallback(tmp_path, monkeypatch):
    """A failed sandbox launcher never starts the requested command directly."""
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr("reme.utils.file_sandbox.path_seatbelt_backend.shutil.which", lambda _: "/usr/bin/sandbox-exec")
    seen = {}

    async def fail(*arguments):
        if arguments[0] == "bootout":
            import errno
            from reme.utils.file_sandbox.path_seatbelt_backend import LaunchctlError

            raise LaunchctlError("service not found", errno.ESRCH)
        seen["arguments"] = arguments
        with open(arguments[-1], "rb") as stream:
            seen["job"] = plistlib.load(stream)
        raise RuntimeError("launchd unavailable")

    backend = PathSeatbeltBackend(cwd=tmp_path, read_only_paths=[], writable_paths=[])
    monkeypatch.setattr(backend, "_launchctl", fail)

    async def available(_domain):
        return True

    monkeypatch.setattr(backend, "_has_gui_launchd", available)
    with pytest.raises(RuntimeError, match="launchd unavailable"):
        await backend.exec_shell(["/bin/echo", "unsafe"])
    assert seen["arguments"][0] == "bootstrap"
    assert seen["job"]["AbandonProcessGroup"] is False
    assert seen["job"]["ProgramArguments"][-2:] == ["/bin/echo", "unsafe"]
    assert not Path(seen["arguments"][-1]).exists()


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


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["success", "failure", "timeout", "cancel", "error", "kickstart_error", "write"])
async def test_seatbelt_launchd_lifecycle(tmp_path, monkeypatch, mode):
    """Every launchd outcome unregisters the job and removes its control files."""
    from unittest.mock import AsyncMock, Mock

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr("reme.utils.file_sandbox.path_seatbelt_backend.shutil.which", lambda _: "sandbox-exec")
    backend = PathSeatbeltBackend(cwd=tmp_path, read_only_paths=[], writable_paths=[])
    monkeypatch.setattr(backend, "_has_gui_launchd", AsyncMock(return_value=True))
    killed = Mock()
    monkeypatch.setattr(backend, "_kill_process", killed)
    calls = []
    control = None
    started = asyncio.Event()

    async def launchctl(*args):
        nonlocal control
        calls.append(args[0])
        if args[0] == "bootstrap":
            control = Path(args[-1]).parent
            if mode == "write":
                with open(args[-1], "rb") as stream:
                    job = plistlib.load(stream)
                assert Path(job["StandardInPath"]).read_bytes() == b"binary\x00\xff"
        if args[0] == "kickstart" and mode == "kickstart_error":
            raise RuntimeError("kickstart failed")
        if args[0] == "bootout":
            # Output is collected after launchd has reaped the process group.
            (control / "stdout").write_bytes(b"output")
            (control / "stderr").write_bytes(b"diagnostic")
        return "12345"

    async def wait_status(*_args):
        started.set()
        if mode == "error":
            raise RuntimeError("status failed")
        if mode in ("timeout", "cancel"):
            await asyncio.Event().wait()
        return 7 if mode == "failure" else 0

    monkeypatch.setattr(backend, "_launchctl", launchctl)
    monkeypatch.setattr(backend, "_wait_status", wait_status)
    operation = (
        backend.write_file(str(tmp_path / "note.bin"), b"binary\x00\xff")
        if mode == "write"
        else backend.exec_shell(["true"], timeout=0.01 if mode == "timeout" else None)
    )
    task = asyncio.create_task(operation)
    if mode == "cancel":
        await asyncio.wait_for(started.wait(), timeout=1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, timeout=1)
    elif mode in ("error", "kickstart_error"):
        with pytest.raises(RuntimeError, match="failed"):
            await asyncio.wait_for(task, timeout=1)
    else:
        result = await asyncio.wait_for(task, timeout=1)
        if mode == "write":
            assert result is None
        elif mode == "timeout":
            assert result == ExecResult(exit_code=-1, stdout=b"", stderr=b"timed out")
        else:
            assert result.exit_code == (7 if mode == "failure" else 0)
            assert result.stdout == b"output" and result.stderr == b"diagnostic"
    assert calls == ["bootstrap", "kickstart", "bootout"]
    assert not control.exists()
    assert killed.call_count == int(mode in ("timeout", "cancel", "error"))


@pytest.mark.asyncio
async def test_python_timeout_preserves_exit_status_and_stderr(tmp_path):
    """The shared executor retains the existing unsandboxed Python metadata."""
    step = PythonExecuteStep(app_context=ApplicationContext(workspace_dir=str(tmp_path)))
    response = await step(
        code="import sys, time; print('diagnostic', file=sys.stderr, flush=True); time.sleep(60)",
        python_timeout=0.3,
    )
    assert response.success is False
    assert response.answer == "Python execution timed out after 0.3s"
    assert response.metadata == {
        "returncode": -9 if os.name == "posix" else 1,
        "stderr": "diagnostic\n",
        "python_timeout": 0.3,
    }
