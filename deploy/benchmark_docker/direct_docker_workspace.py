"""Minimal AgentScope 2.0.9 DockerWorkspace for direct ReMe jobs.

The stock workspace builds and starts an MCP gateway. The benchmark harness
uses only DockerBackend's exec/read/write primitives, so building that gateway
would add an unrelated network-dependent image layer and process.
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any

from aiodocker.exceptions import DockerError
from agentscope.workspace import DockerWorkspace


class DirectDockerWorkspace(DockerWorkspace):
    """Use the supplied image directly and skip the unused MCP gateway."""

    _image_tag: str
    _backend: Any
    _container: Any
    _client: Any
    is_alive: bool

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._lifecycle_lock = asyncio.Lock()

    async def _build_or_reuse_image(self) -> None:
        """Select the caller-provided image instead of deriving a gateway image."""
        self._image_tag = self.base_image

    async def initialize(self) -> None:
        """Start one Docker container and expose its filesystem/exec backend."""
        async with self._lifecycle_lock:
            if self.is_alive:
                return
            if self._container is not None or self._client is not None:
                raise RuntimeError("Docker workspace cleanup must complete before initialization")
            try:
                await self._provision_backend()
                backend = self.get_backend()
                result = await backend.exec_shell(["mkdir", "-p", self.workdir], cwd="/")
                if not result.ok():
                    raise RuntimeError(
                        f"failed to create Docker workspace {self.workdir!r}: "
                        f"{result.stderr.decode('utf-8', errors='replace')}",
                    )
            except BaseException as exc:
                try:
                    await self._teardown_backend()
                except Exception as close_exc:
                    exc.add_note(f"workspace close failed: {type(close_exc).__name__}: {close_exc}")
                raise
            self.is_alive = True

    async def _teardown_backend(self) -> None:
        """Remove the container, preserving handles until cleanup is confirmed."""
        self.is_alive = False
        if self._container is not None:
            # Preserve AgentScope's bind-mount ownership repair on native Linux.
            if self.host_workdir is not None and sys.platform == "linux" and self._backend is not None:
                try:
                    await self._backend.exec_shell(
                        ["chown", "-R", f"{os.getuid()}:{os.getgid()}", self.workdir],
                        timeout=10.0,
                    )
                except Exception:
                    pass
            try:
                # Force deletion also stops a running container; a separate kill
                # would add a failure point without proving that removal succeeded.
                await self._container.delete(force=True)
            except DockerError as exc:
                if exc.status != 404:
                    raise
            self._container = None
            self._backend = None
        if self._client is not None:
            await self._client.close()
            self._client = None
        self._backend = None

    async def close(self) -> None:
        """Report cleanup errors and allow another call to retry unfinished work."""
        # The inherited close clears backend state in a finally block. This
        # direct workspace has no gateway and must retain state on failure.
        async with self._lifecycle_lock:
            await self._teardown_backend()
