"""Keep ranged reads aligned with universal-newline chunking and large-file reads."""

import asyncio

import pytest

from reme.components import ApplicationContext
from reme.components.file_chunker import DefaultFileChunker
from reme.steps.file_io import read as read_module


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16"])
@pytest.mark.parametrize("trailing_newline", [False, True])
@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r", "mixed"])
def test_read_line_ranges_match_chunker_and_streaming_path(tmp_path, monkeypatch, encoding, trailing_newline, newline):
    """The same bytes must produce the same line ranges on both read paths."""
    logical_lines = ["first\u2028inline", "second 中文", "third\x0binline", "fourth"]
    separators = ["\r\n", "\r", "\n"] if newline == "mixed" else [newline] * 3
    text = logical_lines[0] + "".join(separator + line for separator, line in zip(separators, logical_lines[1:]))
    if trailing_newline:
        text += "\r" if newline == "mixed" else newline
    path = tmp_path / "note.md"
    source = text.encode(encoding)
    path.write_bytes(source)
    app_context = ApplicationContext(workspace_dir=str(tmp_path))

    async def run():
        # UTF-8 is the normal indexer configuration. UTF-16 still exercises the
        # read helper's BOM detection without asserting byte-chunker geometry.
        if encoding == "utf-8":
            _, chunks = await DefaultFileChunker(encoding=encoding, app_context=app_context).chunk(path)
            assert chunks[0].start_line == 1
            assert chunks[0].end_line == len(logical_lines)

        responses = []
        for threshold in (len(source) + 1, 1):
            monkeypatch.setattr(read_module, "MAX_FILE_READ_BYTES", threshold)
            step = read_module.ReadStep(app_context=app_context)
            await step(path="note.md", start_line=2, end_line=3)
            assert step.context.response.success is True
            responses.append(step.context.response.answer)

            complete = read_module.ReadStep(app_context=app_context)
            await complete(path="note.md")
            assert complete.context.response.success is True
            assert complete.context.response.answer == "\n".join(logical_lines)

            past_end = read_module.ReadStep(app_context=app_context)
            await past_end(path="note.md", start_line=5)
            assert past_end.context.response.success is False
            assert "exceeds file length (4 lines)" in past_end.context.response.answer

        assert responses == ["\n".join(logical_lines[1:3])] * 2
        assert path.read_bytes() == source

    asyncio.run(run())
