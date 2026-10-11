"""Exercise macOS sandbox startup and file isolation using real subprocesses."""

import sys

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
