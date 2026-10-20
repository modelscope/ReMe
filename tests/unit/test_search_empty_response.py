"""Empty search answers distinguish missing results from previously returned content."""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from reme.components import ApplicationContext
from reme.components.file_store import BaseFileStore
from reme.components.runtime_context import RuntimeContext
from reme.schema import FileChunk
from reme.steps.index import SearchStep
from reme.steps.index._source_format import ALL_RETURNED_MESSAGE, NO_RESULTS_MESSAGE


def _chunk(chunk_id="match", score=2.0):
    """Create a scored hit with an embedding that must not appear in results."""
    return FileChunk(
        id=chunk_id,
        path=f"daily/{chunk_id}.md",
        text=f"memory {chunk_id}",
        start_line=1,
        end_line=2,
        embedding=[0.1, 0.2],
        scores={"score": score},
    )


def _store(chunks=(), mode="keyword"):
    """Mock retrieval boundaries without starting indexes or model providers."""
    store = Mock(spec=BaseFileStore)
    store.vector_search = AsyncMock(return_value=list(chunks) if mode in {"vector", "hybrid"} else [])
    store.keyword_search = AsyncMock(return_value=list(chunks) if mode in {"keyword", "hybrid"} else [])
    return store


def _step(tmp_path, store, *, app_context=None, vector_weight=0.0):
    """Use an isolated application, sharing it explicitly for repeated calls."""
    return SearchStep(
        app_context=app_context if app_context is not None else ApplicationContext(workspace_dir=str(tmp_path)),
        file_store=store,
        vector_weight=vector_weight,
        expand_links=False,
    )


@pytest.mark.parametrize("tool_context_id", ["", "ctx-1"], ids=["without-context", "with-context"])
def test_search_no_matches_has_explicit_answer(tmp_path, tool_context_id):
    """An empty retrieval succeeds with a notice and the ordinary empty metadata."""
    response = asyncio.run(
        _step(tmp_path, _store(), vector_weight=0.7)(
            RuntimeContext(query="missing", tool_context_id=tool_context_id),
        ),
    )

    assert response.success
    assert response.answer == NO_RESULTS_MESSAGE
    assert response.metadata["results"] == []
    assert response.metadata["link_expansion"] == {}
    assert response.metadata["counts"] == {"vector": 0, "keyword": 0, "returned": 0, "hybrid": False}
    if tool_context_id:
        assert response.metadata["dedup"]["skipped_seen"] == 0
    else:
        assert "dedup" not in response.metadata


@pytest.mark.parametrize("mode,weight", [("keyword", 0.0), ("vector", 1.0), ("hybrid", 0.7)])
@pytest.mark.parametrize("tool_context_id", ["", "ctx-1"], ids=["without-context", "with-context"])
def test_search_score_filter_has_no_results_answer(tmp_path, mode, weight, tool_context_id):
    """Results below min_score are missing eligible results, not previously returned content."""
    response = asyncio.run(
        _step(tmp_path, _store([_chunk(score=0.1)], mode), vector_weight=weight)(
            RuntimeContext(query="memory", min_score=1.0, tool_context_id=tool_context_id),
        ),
    )

    assert response.success
    assert response.answer == NO_RESULTS_MESSAGE
    assert response.metadata["results"] == []
    assert response.metadata["link_expansion"] == {}
    assert response.metadata["counts"] == {
        "vector": int(mode in {"vector", "hybrid"}),
        "keyword": int(mode in {"keyword", "hybrid"}),
        "returned": 0,
        "hybrid": mode == "hybrid",
    }
    if tool_context_id:
        assert response.metadata["dedup"]["skipped_seen"] == 0


def test_search_all_seen_has_explicit_answer_across_step_instances(tmp_path):
    """Fresh Step instances share previously returned content through the application."""

    async def run():
        app_context = ApplicationContext(workspace_dir=str(tmp_path))
        store = _store([_chunk()])
        first = await _step(tmp_path, store, app_context=app_context)(
            RuntimeContext(query="memory", tool_context_id="ctx-1"),
        )
        second = await _step(tmp_path, store, app_context=app_context)(
            RuntimeContext(query="memory", tool_context_id="ctx-1"),
        )

        assert first.metadata["counts"]["returned"] == 1
        assert second.success
        assert second.answer == ALL_RETURNED_MESSAGE
        assert second.metadata["results"] == []
        assert second.metadata["link_expansion"] == {}
        assert second.metadata["counts"] == {"vector": 0, "keyword": 1, "returned": 0, "hybrid": False}
        assert second.metadata["dedup"]["seen_before"] == 1
        assert second.metadata["dedup"]["skipped_seen"] == 1

    asyncio.run(run())


@pytest.mark.parametrize("min_score", [0.0, 3.0], ids=["no-matches", "below-threshold"])
def test_search_history_does_not_turn_missing_results_into_all_returned(tmp_path, min_score):
    """Past hits do not explain a new query with no eligible candidates."""

    async def run():
        app_context = ApplicationContext(workspace_dir=str(tmp_path))
        store = _store([_chunk()])
        first = await _step(tmp_path, store, app_context=app_context)(
            RuntimeContext(query="memory", tool_context_id="ctx-1"),
        )
        assert first.metadata["counts"]["returned"] == 1
        if not min_score:
            store.keyword_search.return_value = []
        response = await _step(tmp_path, store, app_context=app_context)(
            RuntimeContext(query="another query", min_score=min_score, tool_context_id="ctx-1"),
        )

        assert response.success
        assert response.answer == NO_RESULTS_MESSAGE
        assert response.metadata["results"] == []
        assert response.metadata["counts"]["returned"] == 0
        assert response.metadata["dedup"]["seen_before"] == 1
        assert response.metadata["dedup"]["skipped_seen"] == 0

    asyncio.run(run())


@pytest.mark.parametrize("tool_context_id", ["", "ctx-1"], ids=["without-context", "with-context"])
def test_search_hit_keeps_answer_and_structured_results(tmp_path, tool_context_id):
    """A normal hit keeps its exact rendering and excludes the embedding from metadata."""
    chunk = _chunk()
    response = asyncio.run(
        _step(tmp_path, _store([chunk]))(RuntimeContext(query="memory", tool_context_id=tool_context_id)),
    )

    assert response.success
    assert response.answer == "========== daily/match.md:1-2 [score=2.0000] ==========\nmemory match"
    assert response.metadata["results"] == [chunk.model_dump(exclude_none=True, exclude={"embedding"})]
    assert response.metadata["link_expansion"] == {}
    assert response.metadata["counts"] == {"vector": 0, "keyword": 1, "returned": 1, "hybrid": False}


def test_search_partial_dedup_and_context_isolation_keep_hit_answers(tmp_path):
    """Unseen content still renders normally and another context can retrieve seen content."""

    async def run():
        app_context = ApplicationContext(workspace_dir=str(tmp_path))
        store = _store([_chunk()])
        await _step(tmp_path, store, app_context=app_context)(
            RuntimeContext(query="memory", tool_context_id="ctx-1"),
        )
        store.keyword_search.return_value = [_chunk(), _chunk("new")]
        response = await _step(tmp_path, store, app_context=app_context)(
            RuntimeContext(query="memory", tool_context_id="ctx-1"),
        )

        assert response.success
        assert response.answer == "========== daily/new.md:1-2 [score=2.0000] ==========\nmemory new"
        assert [result["id"] for result in response.metadata["results"]] == ["new"]
        assert response.metadata["dedup"]["skipped_seen"] == 1

        other = await _step(tmp_path, store, app_context=app_context)(
            RuntimeContext(query="memory", tool_context_id="ctx-2"),
        )
        assert [result["id"] for result in other.metadata["results"]] == ["match", "new"]
        assert "memory match" in other.answer
        assert "memory new" in other.answer
        assert other.metadata["dedup"]["skipped_seen"] == 0

    asyncio.run(run())
