"""Restart Dream with fresh Applications and only workspace files carrying progress."""

# pylint: disable=protected-access

import asyncio
import copy
import json
import os
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from agentscope.model import ChatModelBase

from reme.application import Application
from reme.components.agent_wrapper import BaseAgentWrapper
from reme.config import resolve_app_config
from reme.steps.evolve.dream.checkpoint import CheckpointStore, DreamCheckpoint, source_versions
from reme.steps.evolve.dream.finish import DreamFinishStep
from reme.steps.evolve.dream.integrate import DreamIntegrateStep

DAY = "2026-10-23"
SOURCE = f"daily/{DAY}/source.md"
TARGETS = ["digest/wiki/first.md", "digest/wiki/second.md"]
UNITS = [
    {"name": name, "bucket": "wiki", "summary": f"{name} memory", "paths": [SOURCE]} for name in ("first", "second")
]


def _app(workspace, **kwargs):
    """Use configured Dream/write jobs and real catalogs, without external providers."""
    defaults = resolve_app_config(config="default", log_config=False)
    types = ("tokenizer", "keyword_index", "file_graph", "tag_index", "file_store", "file_catalog")
    return Application(
        workspace_dir=str(workspace),
        enable_logo=False,
        log_to_file=False,
        log_to_console=False,
        service={"backend": "http", "web_enabled": False, "mcp_enabled": False},
        components={name: copy.deepcopy(defaults["components"][name]) for name in types},
        jobs={name: copy.deepcopy(defaults["jobs"][name]) for name in ("auto_dream", "write")},
        **kwargs,
    )


def _source(workspace):
    path = workspace / SOURCE
    path.parent.mkdir(parents=True)
    path.write_text("Original source", encoding="utf-8")
    return path


def _agent(app, calls, *, interrupt="", fail_second=False, units=None):
    """Controlled provider: interrupted writes are reconciled instead of appended twice."""

    async def reply(message, **kwargs):
        if "list_tags" in kwargs["job_tools"]:
            return {"result": "No tags added"}
        if kwargs["job_tools"] == ["read"]:
            calls.append("extract")
            return {"result": json.dumps({"units": UNITS if units is None else units})}
        text = str(message)
        index = 0 if "first memory" in text else 1
        calls.append(UNITS[index]["name"])
        target = Path(app.context.app_config.workspace_dir) / TARGETS[index]
        if index == 1 and interrupt == "before_write":
            raise asyncio.CancelledError
        if index == 1 and fail_second:
            return {"result": "{}"}
        if target.exists():
            # In particular, a write without a completion receipt must not be blindly repeated.
            if index == 1 and "earlier Dream integration attempt" in text:
                assert "do not append duplicate evidence" in text
                assert TARGETS[index] in text
            action = "CORROBORATE"
        else:
            response = await app.run_job("write", path=TARGETS[index], content=UNITS[index]["summary"])
            assert response.success, response.answer
            action = "CREATE"
        if index == 1 and interrupt == "after_write":
            raise asyncio.CancelledError
        return {"result": json.dumps({"action": action, "target_path": TARGETS[index]})}

    agent = AsyncMock(spec=BaseAgentWrapper)
    agent.reply.side_effect = reply
    return agent


async def _run(app, calls, **kwargs):
    options = kwargs.pop("options", {})
    return await app.run_job(
        "auto_dream",
        date=DAY,
        scan_days=1,
        agent_wrapper=_agent(app, calls, **kwargs),
        as_llm=Mock(spec=ChatModelBase),
        **options,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("interruption", ["after_extract", "before_write", "after_write", "before_finish"])
async def test_restart_reuses_extraction_and_completed_units(tmp_path, interruption):
    """A fresh Application resumes pending units, including the unacknowledged-write window."""
    source = _source(tmp_path)
    original = source.read_bytes()
    first_calls = []
    app = _app(tmp_path)
    await app.start()
    try:
        with (
            (
                patch.object(
                    DreamIntegrateStep if interruption == "after_extract" else DreamFinishStep,
                    "execute",
                    side_effect=asyncio.CancelledError,
                )
                if interruption in ("after_extract", "before_finish")
                else nullcontext()
            ),
        ):
            with pytest.raises(asyncio.CancelledError):
                await _run(app, first_calls, interrupt=interruption)
        catalog = app.context.components["file_catalog"]["dream"]
        assert await catalog.get_nodes([SOURCE]) == []
    finally:
        await app.close()

    files = list((tmp_path / "metadata" / "dream").glob("*.json"))
    assert len(files) == 1
    saved = DreamCheckpoint.model_validate_json(files[0].read_text())
    assert saved.state.units == UNITS
    assert saved.completed == (
        [] if interruption == "after_extract" else [0, 1] if interruption == "before_finish" else [0]
    )
    if interruption in ("before_write", "after_write"):
        assert saved.active == 1

    second_calls, messages = [], []
    app = _app(tmp_path)
    await app.start()
    try:
        original_restore = CheckpointStore.restore

        def capture_resume(store, sources):
            store.logger = Mock(wraps=store.logger)
            restored = original_restore(store, sources)
            messages.extend(call.args[0] for call in store.logger.info.call_args_list)
            return restored

        with patch.object(CheckpointStore, "restore", capture_resume):
            response = await _run(app, second_calls)
        assert response.success, response.answer
        assert second_calls == (
            ["first", "second"]
            if interruption == "after_extract"
            else [] if interruption == "before_finish" else ["second"]
        )
        assert len(response.metadata["dream"]["integrate_results"]) == 2
        assert any(f"resuming: {len(saved.completed)} of 2 units completed" in message for message in messages)
        assert SOURCE in response.metadata["dream"]["checkpoint_paths"]
        assert not files[0].exists()
        assert source.read_bytes() == original
        for index, target in enumerate(TARGETS):
            assert (tmp_path / target).read_text().strip() == UNITS[index]["summary"]
    finally:
        await app.close()


@pytest.mark.asyncio
async def test_partial_failure_retries_only_pending_units(tmp_path):
    """Finish can checkpoint good sources without throwing away reusable extraction."""
    _source(tmp_path)
    app = _app(tmp_path)
    await app.start()
    try:
        response = await _run(app, [], fail_second=True)
        assert not response.success
        assert SOURCE not in response.metadata["dream"]["checkpoint_paths"]
    finally:
        await app.close()
    app = _app(tmp_path)
    await app.start()
    calls = []
    try:
        response = await _run(app, calls)
        assert response.success, response.answer
        assert calls == ["second"]
        assert response.metadata["dream"]["failed_units"] == []
        assert response.metadata["dream"]["errors"] == []
    finally:
        await app.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "change",
    ["edit", "same_mtime", "add", "delete", "hint", "max_units", "corrupt", "version", "invalid_progress"],
)
async def test_incompatible_checkpoint_reextracts(tmp_path, change):
    """Changed inputs/options and unusable saved JSON cannot silently reuse stale units."""
    source = _source(tmp_path)
    app = _app(tmp_path)
    await app.start()
    try:
        with patch.object(DreamIntegrateStep, "execute", side_effect=asyncio.CancelledError):
            with pytest.raises(asyncio.CancelledError):
                await _run(app, [])
    finally:
        await app.close()
    checkpoint = next((tmp_path / "metadata" / "dream").glob("*.json"))
    options = {}
    if change in ("edit", "same_mtime"):
        stat = source.stat()
        source.write_text("Modified source", encoding="utf-8")
        if change == "same_mtime":
            os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    elif change == "add":
        (source.parent / "another.md").write_text("New source")
    elif change == "delete":
        source.unlink()
    elif change in ("hint", "max_units"):
        options[change] = "New guidance" if change == "hint" else 1
    elif change == "corrupt":
        checkpoint.write_text("{incomplete JSON")
    else:
        payload = json.loads(checkpoint.read_text())
        if change == "version":
            payload["version"] = 999
        else:
            payload["completed"] = [0]
        checkpoint.write_text(json.dumps(payload))

    app, calls = _app(tmp_path), []
    await app.start()
    try:
        response = await _run(app, calls, options=options, units=[])
        assert response.success, response.answer
        assert calls == ["extract"]
    finally:
        await app.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("empty_units", [False, True])
async def test_restart_after_catalog_persistence_only_cleans_up(tmp_path, empty_units):
    """A crash after the final watermark save requires no new LLM work."""
    _source(tmp_path)
    app = _app(tmp_path, metadata_dir="custom-metadata")
    await app.start()
    try:
        with patch.object(CheckpointStore, "remove", side_effect=asyncio.CancelledError):
            with pytest.raises(asyncio.CancelledError):
                await _run(app, [], units=[] if empty_units else None)
    finally:
        await app.close()
    files = list((tmp_path / "custom-metadata" / "dream").glob("*.json"))
    assert len(files) == 1
    assert not (tmp_path / "metadata").exists()
    app = _app(tmp_path, metadata_dir="custom-metadata")
    await app.start()
    calls = []
    try:
        response = await _run(app, calls)
        assert response.success, response.answer
        assert not calls
        assert not files[0].exists()
    finally:
        await app.close()


@pytest.mark.asyncio
async def test_overlapping_invocations_do_not_replay_completed_writes(tmp_path):
    """Queued integrations refresh progress or fail explicitly if another run already finished."""
    _source(tmp_path)
    app = _app(tmp_path)
    await app.start()
    entered, release = asyncio.Event(), asyncio.Event()
    calls = []
    delegate = _agent(app, calls)

    async def reply(message, **kwargs):
        if "first memory" in str(message) and kwargs["job_tools"] != ["read"]:
            entered.set()
            await release.wait()
        return await delegate.reply(message, **kwargs)

    agent = AsyncMock(spec=BaseAgentWrapper)
    agent.reply.side_effect = reply

    async def run():
        return await app.run_job(
            "auto_dream",
            date=DAY,
            scan_days=1,
            agent_wrapper=agent,
            as_llm=Mock(spec=ChatModelBase),
        )

    tasks = [asyncio.create_task(run())]
    try:
        await asyncio.wait_for(entered.wait(), timeout=5)
        extracted = asyncio.Event()
        original_restore = CheckpointStore.restore

        def signal_restore(store, sources):
            result = original_restore(store, sources)
            extracted.set()
            return result

        with patch.object(CheckpointStore, "restore", signal_restore):
            tasks.append(asyncio.create_task(run()))
            await asyncio.wait_for(extracted.wait(), timeout=5)
            release.set()
            responses = await asyncio.gather(*tasks)
        assert responses[0].success
        assert responses[1].success or "another invocation" in responses[1].answer
        assert calls == ["extract", "first", "second"]
    finally:
        release.set()
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await app.close()


@pytest.mark.asyncio
async def test_checkpoint_directory_cannot_escape_workspace(tmp_path):
    """A metadata symlink must not let intermediate memory writes escape the workspace."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _source(workspace)
    outside = tmp_path / "outside"
    outside.mkdir()
    (workspace / "metadata").symlink_to(outside, target_is_directory=True)
    app = _app(workspace)
    await app.start()
    calls = []
    try:
        response = await _run(app, calls)
        assert not response.success
        assert "checkpoint escapes workspace" in response.answer
        assert not calls
        assert not (outside / "dream").exists()
    finally:
        await app.close()


@pytest.mark.asyncio
async def test_checkpoint_write_failure_preserves_previous_progress(tmp_path):
    """An interrupted atomic replacement leaves valid JSON and does not advance watermarks."""
    _source(tmp_path)
    app = _app(tmp_path)
    await app.start()
    original_write = CheckpointStore._write
    writes = 0

    def fail_after_first_unit(store):
        nonlocal writes
        writes += 1
        if writes == 3:
            with patch("reme.steps.evolve.dream.checkpoint.os.replace", side_effect=OSError("disk full")):
                return original_write(store)
        return original_write(store)

    try:
        with patch.object(CheckpointStore, "_write", fail_after_first_unit):
            response = await _run(app, [])
        assert not response.success
        assert "disk full" in response.answer
        assert await app.context.components["file_catalog"]["dream"].get_nodes([SOURCE]) == []
        files = list((tmp_path / "metadata" / "dream").iterdir())
        assert len(files) == 1
        saved = DreamCheckpoint.model_validate_json(files[0].read_text())
        assert saved.active == 0 and saved.completed == []
        assert (tmp_path / TARGETS[0]).is_file()
    finally:
        await app.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_receipt", ["invalid", "exception"])
@pytest.mark.parametrize("interruption", ["after_extract", "before_write"])
async def test_resume_requires_receipt_even_if_a_partial_write_lands(tmp_path, bad_receipt, interruption):
    """A changed file during reconciliation must not silently acknowledge unfinished memory."""
    _source(tmp_path)
    app = _app(tmp_path)
    await app.start()
    try:
        with (
            (
                patch.object(DreamIntegrateStep, "execute", side_effect=asyncio.CancelledError)
                if interruption == "after_extract"
                else nullcontext()
            ),
        ):
            with pytest.raises(asyncio.CancelledError):
                await _run(app, [], interrupt=interruption)
    finally:
        await app.close()

    app = _app(tmp_path)
    await app.start()
    attempts = []

    async def reply(message, **kwargs):
        if "list_tags" in kwargs["job_tools"]:
            return {"result": "No tags added"}
        assert kwargs["job_tools"] != ["read"]
        index = 0 if "first memory" in str(message) else 1
        assert "do not append duplicate evidence" in str(message)
        attempts.append(str(message))
        written = await app.run_job("write", path=TARGETS[index], content=f"Partial memory, attempt {len(attempts)}")
        assert written.success
        if bad_receipt == "exception":
            raise RuntimeError("interrupted before completing the unit")
        return {"result": "{}"}

    agent = AsyncMock(spec=BaseAgentWrapper)
    agent.reply.side_effect = reply
    try:
        response = await app.run_job(
            "auto_dream",
            date=DAY,
            scan_days=1,
            agent_wrapper=agent,
            as_llm=Mock(spec=ChatModelBase),
        )
        assert not response.success
        assert len(attempts) == (4 if interruption == "after_extract" else 2)
        assert SOURCE not in response.metadata["dream"]["checkpoint_paths"]
        saved = DreamCheckpoint.model_validate_json(next((tmp_path / "metadata" / "dream").glob("*.json")).read_text())
        assert saved.completed == ([] if interruption == "after_extract" else [0])
    finally:
        await app.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["delete", "rewrite"])
async def test_resume_rechecks_only_affected_digest_units(tmp_path, change):
    """A missing or overwritten target neither replays unaffected units nor skips lost content."""
    _source(tmp_path)
    app = _app(tmp_path)
    await app.start()
    try:
        with patch.object(DreamFinishStep, "execute", side_effect=asyncio.CancelledError):
            with pytest.raises(asyncio.CancelledError):
                await _run(app, [])
    finally:
        await app.close()
    first = tmp_path / TARGETS[0]
    second_version = (tmp_path / TARGETS[1]).stat().st_mtime_ns
    if change == "delete":
        first.unlink()
    else:
        first.write_text("Overwritten digest content")

    app, calls = _app(tmp_path), []
    await app.start()

    async def reply(message, **kwargs):
        if "list_tags" in kwargs["job_tools"]:
            return {"result": "No tags added"}
        calls.append("extract" if kwargs["job_tools"] == ["read"] else "integrate")
        assert kwargs["job_tools"] != ["read"]
        assert "first memory" in str(message)
        assert "do not append duplicate evidence" in str(message)
        existed = first.exists()
        written = await app.run_job("write", path=TARGETS[0], content=UNITS[0]["summary"])
        assert written.success
        return {"result": json.dumps({"action": "CORRECT" if existed else "CREATE", "target_path": TARGETS[0]})}

    agent = AsyncMock(spec=BaseAgentWrapper)
    agent.reply.side_effect = reply
    try:
        response = await app.run_job(
            "auto_dream",
            date=DAY,
            scan_days=1,
            agent_wrapper=agent,
            as_llm=Mock(spec=ChatModelBase),
        )
        assert response.success, response.answer
        assert calls == ["integrate"]
        assert first.read_text().strip() == UNITS[0]["summary"]
        assert (tmp_path / TARGETS[1]).stat().st_mtime_ns == second_version
    finally:
        await app.close()


@pytest.mark.asyncio
async def test_repeated_catalog_save_failure_keeps_resume_checkpoint(tmp_path):
    """In-memory mtimes after a failed dump must not cause premature checkpoint deletion."""
    _source(tmp_path)
    app = _app(tmp_path)
    await app.start()
    try:
        catalog = app.context.components["file_catalog"]["dream"]
        with patch.object(catalog, "dump", side_effect=OSError("catalog unavailable")):
            for attempt in range(2):
                calls = []
                response = await _run(app, calls)
                assert not response.success
                assert calls == (["extract", "first", "second"] if attempt == 0 else [])
                assert list((tmp_path / "metadata" / "dream").glob("*.json"))
        calls = []
        response = await _run(app, calls)
        assert response.success, response.answer
        assert not calls
        assert not list((tmp_path / "metadata" / "dream").glob("*.json"))
    finally:
        await app.close()


@pytest.mark.asyncio
async def test_completed_checkpoint_finishes_without_integration_provider(tmp_path):
    """Only pending integrations require an LLM; a recovered final commit does not."""
    _source(tmp_path)
    app = _app(tmp_path)
    await app.start()
    try:
        with patch.object(DreamFinishStep, "execute", side_effect=asyncio.CancelledError):
            with pytest.raises(asyncio.CancelledError):
                await _run(app, [])
    finally:
        await app.close()
    app, calls = _app(tmp_path), []
    await app.start()
    try:
        with patch("reme.steps.evolve.dream.integrate.llm_available", return_value=False):
            response = await _run(app, calls)
        assert response.success, response.answer
        assert not calls
        assert not list((tmp_path / "metadata" / "dream").glob("*.json"))
    finally:
        await app.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("delete_completed", [False, True])
async def test_partial_catalog_progress_keeps_all_extracted_units(tmp_path, delete_completed):
    """Successful source watermarks do not hide saved units needed to repair a missing target."""
    _source(tmp_path)
    bad_source = f"daily/{DAY}/other.md"
    (tmp_path / bad_source).write_text("Another source")
    units = copy.deepcopy(UNITS)
    units[1]["paths"] = [bad_source]
    app = _app(tmp_path)
    await app.start()
    try:
        response = await _run(app, [], units=units, fail_second=True)
        assert not response.success
        assert SOURCE in response.metadata["dream"]["checkpoint_paths"]
        assert bad_source not in response.metadata["dream"]["checkpoint_paths"]
    finally:
        await app.close()
    if delete_completed:
        (tmp_path / TARGETS[0]).unlink()
    app, calls = _app(tmp_path), []
    await app.start()
    try:
        response = await _run(app, calls)
        assert response.success, response.answer
        assert calls == (["first", "second"] if delete_completed else ["second"])
        assert len(response.metadata["dream"]["integrate_results"]) == 2
        assert all((tmp_path / target).is_file() for target in TARGETS)
    finally:
        await app.close()


@pytest.mark.asyncio
async def test_rechecking_earlier_unit_preserves_later_unacknowledged_write(tmp_path):
    """Repairing an earlier target must not erase the evidence of a later interrupted write."""
    _source(tmp_path)
    app = _app(tmp_path)
    await app.start()
    try:
        with pytest.raises(asyncio.CancelledError):
            await _run(app, [], interrupt="after_write")
    finally:
        await app.close()
    (tmp_path / TARGETS[0]).write_text("Overwritten first unit")
    second_version = (tmp_path / TARGETS[1]).stat().st_mtime_ns
    app, calls = _app(tmp_path), []
    await app.start()
    delegate = _agent(app, calls)

    async def reply(message, **kwargs):
        if kwargs["job_tools"] != ["read"] and "list_tags" not in kwargs["job_tools"]:
            assert TARGETS[1] in str(message)
            assert "do not append duplicate evidence" in str(message)
            if "first memory" in str(message):
                written = await app.run_job("write", path=TARGETS[0], content=UNITS[0]["summary"])
                assert written.success
        return await delegate.reply(message, **kwargs)

    agent = AsyncMock(spec=BaseAgentWrapper)
    agent.reply.side_effect = reply
    try:
        response = await app.run_job(
            "auto_dream",
            date=DAY,
            scan_days=1,
            agent_wrapper=agent,
            as_llm=Mock(spec=ChatModelBase),
        )
        assert response.success, response.answer
        assert calls == ["first", "second"]
        assert (tmp_path / TARGETS[1]).stat().st_mtime_ns == second_version
    finally:
        await app.close()


@pytest.mark.asyncio
async def test_edit_between_scan_and_fingerprint_cannot_acknowledge_stale_mtime(tmp_path):
    """Do not pair extraction of a newer version with the scan's older catalog watermark."""
    source = _source(tmp_path)
    app, calls = _app(tmp_path), []
    await app.start()

    def edit_then_fingerprint(workspace, existing):
        previous = source.stat().st_mtime
        source.write_text("Changed between scan and extraction")
        os.utime(source, (previous + 2, previous + 2))
        return source_versions(workspace, existing)

    try:
        with patch("reme.steps.evolve.dream.extract.source_versions", edit_then_fingerprint):
            response = await _run(app, calls)
        assert not response.success
        assert "changed after scanning" in response.answer
        assert not calls
        assert await app.context.components["file_catalog"]["dream"].get_nodes([SOURCE]) == []
        response = await _run(app, calls)
        assert response.success, response.answer
        assert calls == ["extract", "first", "second"]
    finally:
        await app.close()


@pytest.mark.asyncio
async def test_late_finish_cannot_overwrite_a_newer_runs_watermark(tmp_path):
    """A superseded finalizer must not make already processed new inputs eligible again."""
    source = _source(tmp_path)
    app = _app(tmp_path)
    await app.start()
    entered, release = asyncio.Event(), asyncio.Event()
    original_execute = DreamFinishStep.execute
    finishes = 0

    async def delayed_finish(step):
        nonlocal finishes
        finishes += 1
        if finishes == 1:
            entered.set()
            await release.wait()
        return await original_execute(step)

    first = None
    try:
        with patch.object(DreamFinishStep, "execute", delayed_finish):
            first = asyncio.create_task(_run(app, []))
            await asyncio.wait_for(entered.wait(), timeout=5)
            previous = source.stat().st_mtime
            source.write_text("New source version")
            os.utime(source, (previous + 2, previous + 2))
            second = await _run(app, [])
            assert second.success, second.answer
            release.set()
            stale = await first
        assert not stale.success
        assert "another invocation" in stale.answer
        nodes = await app.context.components["file_catalog"]["dream"].get_nodes([SOURCE])
        assert nodes[0].st_mtime == source.stat().st_mtime
        calls = []
        third = await _run(app, calls)
        assert third.success, third.answer
        assert not calls
    finally:
        release.set()
        if first is not None:
            if not first.done():
                first.cancel()
            await asyncio.gather(first, return_exceptions=True)
        await app.close()
