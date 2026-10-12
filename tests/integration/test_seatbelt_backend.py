"""Exercise macOS sandbox startup and file isolation using real subprocesses."""

import asyncio
import sys
import venv

import psutil

import pytest

from reme.utils.file_sandbox.path_seatbelt_backend import PathSeatbeltBackend

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="Seatbelt requires macOS")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "command",
    [
        ["/bin/sh", "-c", "pwd"],
        [sys.executable, "-c", "import os; print(os.getcwd())"],
    ],
)
async def test_seatbelt_starts_shell_and_python(tmp_path, command):
    """System runtime access permits startup and resolution of the working directory."""
    workspace = tmp_path.resolve()
    backend = PathSeatbeltBackend(cwd=workspace, read_only_paths=[], writable_paths=[])

    result = await backend.exec_shell(command, timeout=10)

    assert result.exit_code == 0, result.stderr.decode(errors="replace")
    assert result.stdout.decode().strip() == str(workspace)
    assert result.stderr == b""


@pytest.mark.asyncio
async def test_seatbelt_starts_virtual_environment_python(tmp_path):
    """A symlinked virtual environment interpreter can load its base runtime."""
    workspace = tmp_path.resolve()
    environment = workspace / "venv"
    venv.EnvBuilder(with_pip=False, symlinks=True).create(environment)
    backend = PathSeatbeltBackend(cwd=workspace, read_only_paths=[], writable_paths=[])

    result = await backend.exec_shell(
        [str(environment / "bin" / "python"), "-c", "import os; print(os.getcwd())"],
        timeout=10,
    )

    assert result.exit_code == 0, result.stderr.decode(errors="replace")
    assert result.stdout.decode().strip() == str(workspace)


@pytest.mark.asyncio
async def test_seatbelt_allows_null_device_redirection(tmp_path):
    """The shell can discard output through /dev/null inside a file sandbox."""
    backend = PathSeatbeltBackend(cwd=tmp_path.resolve(), read_only_paths=[], writable_paths=[])

    result = await backend.exec_shell(["/bin/sh", "-c", "echo hi > /dev/null"], timeout=5)

    assert result.exit_code == 0, result.stderr.decode(errors="replace")
    assert result.stdout == b""


@pytest.mark.asyncio
async def test_seatbelt_runtime_permissions_preserve_file_isolation(tmp_path):
    """Startup grants do not expose sibling files or writable access to protected children."""
    root = tmp_path.resolve()
    workspace = root / "workspace"
    protected = workspace / "protected"
    output = protected / "output"
    output.mkdir(parents=True)
    (protected / "note.txt").write_text("readable", encoding="utf-8")
    (root / "outside.txt").write_text("private", encoding="utf-8")
    backend = PathSeatbeltBackend(
        cwd=workspace,
        read_only_paths=[str(protected)],
        writable_paths=[str(workspace), str(output)],
    )
    code = """
from pathlib import Path
assert Path('protected/note.txt').read_text() == 'readable'
Path('allowed.txt').write_text('ok')
Path('protected/output/allowed.txt').write_text('ok')
for path, operation in [
    (Path('protected/denied.txt'), 'write'),
    (Path('../outside.txt'), 'read'),
    (Path('../outside.txt'), 'write'),
]:
    try:
        path.read_text() if operation == 'read' else path.write_text('denied')
    except PermissionError:
        pass
    else:
        raise AssertionError(f'{operation} unexpectedly allowed: {path}')
"""

    result = await backend.exec_shell([sys.executable, "-c", code], timeout=10)

    assert result.exit_code == 0, result.stderr.decode(errors="replace")
    assert (workspace / "allowed.txt").read_text() == "ok"
    assert (output / "allowed.txt").read_text() == "ok"
    assert not (protected / "denied.txt").exists()
    assert (root / "outside.txt").read_text() == "private"


@pytest.mark.asyncio
async def test_seatbelt_cannot_move_read_only_ancestor(tmp_path):
    """Moving a writable ancestor must not change a protected file's effective path."""
    workspace = tmp_path.resolve()
    protected = workspace / "parent" / "protected"
    protected.mkdir(parents=True)
    note = protected / "note.txt"
    note.write_text("original", encoding="utf-8")
    backend = PathSeatbeltBackend(cwd=workspace, read_only_paths=[str(protected)], writable_paths=[str(workspace)])

    result = await backend.exec_shell(
        ["/bin/sh", "-c", "mv parent renamed && echo changed > renamed/protected/note.txt"],
        timeout=5,
    )
    assert result.exit_code != 0
    assert note.read_text(encoding="utf-8") == "original"
    assert not (workspace / "renamed").exists()

    sibling = await backend.exec_shell(["/bin/sh", "-c", "echo allowed > sibling.txt"], timeout=5)
    assert sibling.exit_code == 0, sibling.stderr.decode(errors="replace")
    assert (workspace / "sibling.txt").read_text(encoding="utf-8").strip() == "allowed"


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel", [False, True], ids=["timeout", "cancel"])
async def test_seatbelt_stops_detached_child(tmp_path, cancel):
    """A child that left the launcher's process group should be stopped when observed."""
    workspace = tmp_path.resolve()
    backend = PathSeatbeltBackend(cwd=workspace, read_only_paths=[], writable_paths=[str(workspace)])
    pidfile = workspace / "child.pid"
    marker = workspace / "late.txt"
    output = workspace / "child.out"
    child_code = (
        f"import os,time;os.setsid();open({str(pidfile)!r},'w').write(str(os.getpid()));"
        f"time.sleep(1.2);open({str(marker)!r},'w').write('late')"
    )
    parent_code = (
        f"import subprocess,sys,time;f=open({str(output)!r},'w');"
        f"subprocess.Popen([sys.executable,'-c',{child_code!r}],stdin=f,stdout=f,stderr=f);"
        "f.close();time.sleep(10)"
    )
    task = asyncio.create_task(backend.exec_shell([sys.executable, "-c", parent_code], timeout=10 if cancel else 0.5))
    try:
        for _ in range(100):
            if pidfile.exists():
                break
            await asyncio.sleep(0.02)
        assert pidfile.exists(), output.read_text() if output.exists() else "child did not start"
        if cancel:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(task, timeout=4)
        else:
            result = await asyncio.wait_for(task, timeout=4)
            assert result.exit_code == -1 and result.stderr == b"timed out"
        await asyncio.sleep(1.2)
        assert not marker.exists()
    finally:
        if not task.done():
            task.cancel()
        if pidfile.exists():
            try:
                psutil.Process(int(pidfile.read_text(encoding="utf-8"))).kill()
            except psutil.Error:
                pass
