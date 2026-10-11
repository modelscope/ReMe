"""Common contract and path validation for subprocess file sandboxes."""

import asyncio
import os
import signal
import sys
from abc import abstractmethod

from agentscope.tool import BackendBase, ExecResult


def contains(root: str, path: str) -> bool:
    """Whether a path is inside a configured root."""
    return os.path.commonpath((root, path)) == root


class FileSandboxBackend(BackendBase):
    """Execute subprocesses with explicit host-path read and write access."""

    def __init__(self, *, cwd: str | os.PathLike[str], read_only_paths: list[str], writable_paths: list[str]) -> None:
        self._cwd = self._validate_path(os.fspath(cwd))
        if not os.path.isdir(self._cwd):
            raise ValueError("sandbox working directory must be a directory")
        self._read_only_paths = self._validate_paths(read_only_paths, "read_only_paths")
        self._writable_paths = self._validate_paths(writable_paths, "writable_paths")
        if not any(contains(path, self._cwd) for path in self._read_only_paths + self._writable_paths):
            self._read_only_paths.append(self._cwd)
        runtime_prefix = os.path.realpath(sys.prefix)
        if runtime_prefix not in ("/", "/usr", "/usr/local") and not runtime_prefix.startswith("/usr/"):
            if not any(contains(path, runtime_prefix) for path in self._read_only_paths + self._writable_paths):
                self._read_only_paths.append(self._validate_path(runtime_prefix))
        paths = self._read_only_paths + self._writable_paths
        if len(set(paths)) != len(paths):
            raise ValueError("sandbox paths must not contain duplicates")
        self._path_identities = {path: self._identity(path) for path in paths}

    @staticmethod
    def _identity(path: str) -> tuple[int, int]:
        info = os.stat(path, follow_symlinks=False)
        return info.st_dev, info.st_ino

    @staticmethod
    def _validate_path(raw: str) -> str:
        if not isinstance(raw, str) or not raw or not os.path.isabs(raw):
            raise ValueError("sandbox paths must be non-empty absolute paths")
        path = os.path.normpath(raw)
        if path == "/" or not os.path.exists(path) or os.path.realpath(path) != path:
            raise ValueError(f"sandbox path must exist without symlinks and cannot be root: {raw}")
        return path

    @classmethod
    def _validate_paths(cls, raw: list[str], name: str) -> list[str]:
        if not isinstance(raw, list) or any(not isinstance(item, str) for item in raw):
            raise ValueError(f"{name} must be a list of absolute paths")
        return [cls._validate_path(path) for path in raw]

    def _check_paths(self, cwd: str) -> None:
        if not any(contains(path, cwd) for path in self._read_only_paths + self._writable_paths):
            raise ValueError("command working directory must be inside a sandbox path")
        for path, identity in self._path_identities.items():
            if not os.path.exists(path) or os.path.realpath(path) != path or self._identity(path) != identity:
                raise RuntimeError(f"sandbox path changed before execution: {path}")

    async def getcwd(self) -> str:
        """Return the host-identical sandbox working directory."""
        return self._cwd

    @abstractmethod
    async def _start_process(self, command: list[str], cwd: str, *, stdin=asyncio.subprocess.DEVNULL):
        """Start one sandboxed process, never falling back to host execution."""

    def _release_process(self, process: asyncio.subprocess.Process) -> None:
        """Release platform resources after the child has exited."""

    async def exec_shell(
        self,
        command: list[str],
        *,
        cwd: str | None = None,
        timeout: float | None = None,
    ) -> ExecResult:
        """Execute an argv list with a timeout inside the platform sandbox."""
        process = await self._start_process(command, cwd or self._cwd)
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except TimeoutError:
            self._kill_process(process)
            await process.communicate()
            return ExecResult(exit_code=-1, stdout=b"", stderr=b"timed out")
        except BaseException:
            self._kill_process(process)
            await asyncio.shield(process.communicate())
            raise
        finally:
            self._release_process(process)
        return ExecResult(exit_code=process.returncode, stdout=stdout, stderr=stderr)

    @staticmethod
    def _kill_process(process: asyncio.subprocess.Process) -> None:
        """Terminate the sandbox launcher and its process group."""
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    async def read_file(self, path: str) -> bytes:
        """Read through a sandboxed command so file rules still apply."""
        result = await self.exec_shell(["cat", path])
        if not result.ok():
            raise OSError(result.stderr.decode(errors="replace"))
        return result.stdout

    async def write_file(self, path: str, data: bytes) -> None:
        """Write through a sandboxed command so file rules still apply."""
        if not isinstance(data, bytes):
            raise TypeError("data must be bytes")
        script = 'mkdir -p -- "$(dirname -- "$1")" && cat > "$1"'
        process = await self._start_process(
            ["/bin/sh", "-c", script, "sh", path],
            self._cwd,
            stdin=asyncio.subprocess.PIPE,
        )
        try:
            _stdout, stderr = await process.communicate(data)
        except BaseException:
            self._kill_process(process)
            await asyncio.shield(process.communicate())
            raise
        finally:
            self._release_process(process)
        if process.returncode != 0:
            raise OSError(stderr.decode(errors="replace"))
