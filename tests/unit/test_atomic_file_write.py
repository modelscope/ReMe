"""Memory writers publish complete files to concurrent index readers."""

import asyncio
import os
import stat
import threading

import pytest

from reme.steps.file_io._file_io import write_file_safe
from reme.components.application_context import ApplicationContext
from reme.steps.file_io.save import SaveStep


@pytest.mark.asyncio
async def test_overwrite_preserves_complete_old_content_until_commit(tmp_path, monkeypatch):
    """Readers retain the prior complete revision until atomic publication."""
    target = tmp_path / "memory.md"
    target.write_text("old complete memory", encoding="utf-8")
    target.chmod(0o640)
    replace = os.replace

    def observe_commit(source, destination):
        assert target.read_text(encoding="utf-8") == "old complete memory"
        assert source != destination
        replace(source, destination)

    monkeypatch.setattr(os, "replace", observe_commit)
    await write_file_safe(target, "new complete memory")

    assert target.read_text(encoding="utf-8") == "new complete memory"
    assert stat.S_IMODE(target.stat().st_mode) == 0o640
    assert sorted(path.name for path in tmp_path.iterdir()) == ["memory.md"]


@pytest.mark.asyncio
async def test_failed_commit_preserves_original_and_cleans_temporary_file(tmp_path, monkeypatch):
    """Failed publication leaves source bytes intact and no temporary assets."""
    target = tmp_path / "memory.md"
    target.write_bytes(b"original memory")

    def fail_commit(_source, _destination):
        raise OSError("controlled commit failure")

    monkeypatch.setattr(os, "replace", fail_commit)
    with pytest.raises(OSError, match="controlled commit failure"):
        await write_file_safe(target, "replacement")

    assert target.read_bytes() == b"original memory"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["memory.md"]


@pytest.mark.asyncio
async def test_new_encoded_file_and_binary_payload(tmp_path):
    """Atomic writes preserve the existing encoding and binary contracts."""
    target = tmp_path / "nested" / "memory.csv"
    await write_file_safe(target, "中文", encoding="gbk")
    assert target.read_bytes() == "中文".encode("gbk")
    await write_file_safe(target, b"\x00\xff")
    assert target.read_bytes() == b"\x00\xff"


@pytest.mark.asyncio
async def test_atomic_write_accepts_long_valid_filename(tmp_path):
    """Temporary names must not grow with the destination's filename."""
    target = tmp_path / ("a" * 241 + ".md")
    target.write_text("original", encoding="utf-8")

    await write_file_safe(target, "replacement")

    assert target.read_text(encoding="utf-8") == "replacement"
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.asyncio
async def test_cancelled_save_keeps_path_lock_until_publication(tmp_path, monkeypatch):
    """A repeatedly cancelled writer cannot overwrite a later successful save."""
    target = tmp_path / "memory.md"
    target.write_text("original", encoding="utf-8")
    context = ApplicationContext(workspace_dir=str(tmp_path))
    started, release = threading.Event(), threading.Event()
    replace = os.replace

    def delayed_replace(source, destination):
        if not started.is_set():
            started.set()
            assert release.wait(5)
        replace(source, destination)

    monkeypatch.setattr(os, "replace", delayed_replace)
    first = asyncio.create_task(SaveStep(app_context=context)(path="memory.md", content="cancelled write"))
    second = None
    try:
        assert await asyncio.to_thread(started.wait, 5)
        for _ in range(3):
            first.cancel()
            await asyncio.sleep(0)
        second = asyncio.create_task(SaveStep(app_context=context)(path="memory.md", content="successful write"))
        await asyncio.sleep(0)
        assert not first.done()
        assert not second.done()
    finally:
        release.set()
        results = await asyncio.gather(first, *([second] if second is not None else []), return_exceptions=True)

    assert isinstance(results[0], asyncio.CancelledError)
    assert results[1].success
    assert target.read_text(encoding="utf-8") == "successful write"
    assert list(tmp_path.iterdir()) == [target]
