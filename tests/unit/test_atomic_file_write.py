"""Memory writers publish complete files to concurrent index readers."""

import os
import stat

import pytest

from reme.steps.file_io._file_io import write_file_safe


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
