"""macOS Seatbelt file sandbox with host-identical paths."""

import asyncio
import json
import os
import shutil
import sys
import tempfile
import warnings

from .file_sandbox_backend import FileSandboxBackend, contains


class PathSeatbeltBackend(FileSandboxBackend):
    """Run each command under a deny-by-default Seatbelt profile."""

    def __init__(
        self,
        *,
        cwd: str | os.PathLike[str],
        read_only_paths: list[str],
        writable_paths: list[str],
        memory_limit_mib: int = 0,
    ) -> None:
        if isinstance(memory_limit_mib, bool) or not isinstance(memory_limit_mib, int) or memory_limit_mib < 0:
            raise ValueError("memory_limit_mib must be a non-negative integer")
        if memory_limit_mib:
            warnings.warn(
                "PathSeatbeltBackend does not support memory_limit_mib; the limit is ignored on macOS",
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
        lines = [
            "(version 1)",
            "(deny default)",
            "(allow process*)",
            "(allow sysctl-read)",
            "(allow mach-lookup)",
            # dyld opens the root directory; /bin/sh reads the system shell selector.
            '(allow file-read* (literal "/") (literal "/private/var/select/sh"))',
        ]
        ancestors = set()
        for path in read_paths:
            parent = os.path.dirname(path)
            while parent != "/":
                ancestors.add(parent)
                parent = os.path.dirname(parent)
        lines.extend(f"(allow file-read-metadata (literal {json.dumps(path)}))" for path in sorted(ancestors))
        lines.extend(f"(allow file-read* {self._path_rule(path)})" for path in read_paths)
        # Shell redirection to the null device is safe and is accepted by
        # AutoBash's read-only policy; do not grant writes to the rest of /dev.
        lines.append('(allow file-write* (literal "/dev/null"))')
        for path in self._writable_paths + [tempdir]:
            # Seatbelt combines allow rules with OR, unlike ordered bwrap mounts.
            # Exclude read-only descendants from each writable parent's grant.
            exclusions = [
                f"(require-not {self._path_rule(read_only)})"
                for read_only in self._read_only_paths
                if contains(path, read_only)
            ]
            rule = self._path_rule(path)
            if exclusions:
                rule = f"(require-all {rule} {' '.join(exclusions)})"
            lines.append(f"(allow file-write* {rule})")
        # A writable ancestor can otherwise be renamed, moving a protected
        # subtree out of the path-based exclusion above. Pin the protected
        # path and every ancestor that falls within a writable root.
        pinned = set()
        for read_only in self._read_only_paths:
            current = read_only
            while current != "/":
                if any(contains(writable, current) for writable in self._writable_paths):
                    pinned.add(current)
                current = os.path.dirname(current)
        for path in sorted(pinned):
            rule = f"(literal {json.dumps(path)})"
            lines.append(f"(deny file-write-unlink {rule})")
            lines.append(f"(deny file-write-create {rule})")
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
