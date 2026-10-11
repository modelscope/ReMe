"""macOS Seatbelt file sandbox with host-identical paths."""

import asyncio
import json
import os
import shutil
import sys
import tempfile
import warnings

from .file_sandbox_backend import FileSandboxBackend


class PathSeatbeltBackend(FileSandboxBackend):
    """Run each command under a deny-by-default Seatbelt profile."""

    def __init__(
        self,
        *,
        cwd: str | os.PathLike[str],
        read_only_paths: list[str],
        writable_paths: list[str],
        memory_limit_bytes: int = 0,
    ) -> None:
        if isinstance(memory_limit_bytes, bool) or not isinstance(memory_limit_bytes, int) or memory_limit_bytes < 0:
            raise ValueError("memory_limit_bytes must be a non-negative integer")
        if memory_limit_bytes:
            warnings.warn(
                "PathSeatbeltBackend does not support memory_limit_bytes; the limit is ignored on macOS",
                RuntimeWarning,
                stacklevel=2,
            )
        super().__init__(cwd=cwd, read_only_paths=read_only_paths, writable_paths=writable_paths)
        self._process_tempdirs: dict[int, str] = {}

    @staticmethod
    def _path_rule(path: str) -> str:
        """Quote a path as one Seatbelt profile string, never as profile syntax."""
        return f"(subpath {json.dumps(path)})" if os.path.isdir(path) else f"(literal {json.dumps(path)})"

    def _profile(self, tempdir: str) -> str:
        """Allow only configured files plus the system runtime needed to launch tools."""
        system_roots = ("/System", "/usr", "/bin", "/sbin", "/private/etc", "/dev")
        read_paths = [path for path in system_roots if os.path.exists(path)]
        read_paths += self._read_only_paths + self._writable_paths + [tempdir]
        lines = ["(version 1)", "(deny default)", "(allow process*)", "(allow sysctl-read)", "(allow mach-lookup)"]
        lines.extend(f"(allow file-read* {self._path_rule(path)})" for path in read_paths)
        lines.extend(f"(allow file-write* {self._path_rule(path)})" for path in self._writable_paths + [tempdir])
        return "\n".join(lines)

    async def _start_process(self, command: list[str], cwd: str, *, stdin=asyncio.subprocess.DEVNULL):
        if sys.platform != "darwin":
            raise RuntimeError("PathSeatbeltBackend requires macOS")
        if shutil.which("sandbox-exec") is None:
            raise RuntimeError("PathSeatbeltBackend requires sandbox-exec on PATH")
        if not command:
            raise ValueError("command must not be empty")
        self._check_paths(cwd)
        tempdir = tempfile.mkdtemp(prefix="reme-seatbelt-", dir=os.path.realpath(tempfile.gettempdir()))
        try:
            env = {**os.environ, "HOME": self._cwd, "TMPDIR": tempdir}
            process = await asyncio.create_subprocess_exec(
                "/usr/bin/sandbox-exec",
                "-p",
                self._profile(tempdir),
                *command,
                cwd=cwd,
                env=env,
                stdin=stdin,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=True,
            )
        except BaseException:
            shutil.rmtree(tempdir)
            raise
        self._process_tempdirs[process.pid] = tempdir
        return process

    def _release_process(self, process: asyncio.subprocess.Process) -> None:
        tempdir = self._process_tempdirs.pop(process.pid, None)
        if tempdir is not None:
            shutil.rmtree(tempdir)
