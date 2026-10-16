"""Auto Dream checkpoints must acknowledge the versions observed by Extract."""

import asyncio
import copy
import json
import os
from unittest.mock import AsyncMock, Mock

import frontmatter
import pytest
from agentscope.model import ChatModelBase

from reme.application import Application
from reme.components.agent_wrapper import BaseAgentWrapper
from reme.components.application_context import ApplicationContext
from reme.components.file_catalog import LocalFileCatalog
from reme.components.runtime_context import RuntimeContext
from reme.config import resolve_app_config
from reme.schema import DreamState
from reme.steps.evolve.dream.finish import DreamFinishStep

DAY = "2026-05-28"
SOURCE = f"daily/{DAY}/deployment.md"
TARGET = "digest/wiki/deployment.md"
OLD = "Deploy to the staging cluster."
NEW = "Deploy to the production cluster."


def _app(workspace):
    """Build the default dream/write jobs with real local storage and no model providers."""
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
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("edit_phase", ["extract", "integrate", None])
async def test_dream_reprocesses_concurrent_source_edits_after_restart(tmp_path, edit_phase):
    """A real catalog restart retries later edits while unchanged sources stay deduplicated."""
    source = tmp_path / SOURCE
    source.parent.mkdir(parents=True)
    source.write_text(frontmatter.dumps(frontmatter.Post(OLD, name="deployment", description="Deployment policy")))
    scanned_mtime = source.stat().st_mtime
    entered, release = asyncio.Event(), asyncio.Event()
    calls = []

    def agent_for(app, blocked=False):
        async def reply(message, **kwargs):
            if "list_tags" in kwargs["job_tools"]:
                return {"result": "No tags added by the controlled provider"}
            phase = "extract" if kwargs["job_tools"] == ["read"] else "integrate"
            prompt = str(message)
            calls.append((phase, prompt))
            fact = NEW if NEW in prompt else OLD
            if blocked and phase == (edit_phase or "integrate"):
                assert OLD in prompt and NEW not in prompt
                entered.set()
                await release.wait()
            if phase == "extract":
                unit = {"name": "deployment", "bucket": "wiki", "summary": fact, "paths": [SOURCE]}
                return {"result": json.dumps({"units": [unit]})}
            action = "CORRECT" if (tmp_path / TARGET).exists() else "CREATE"
            response = await app.run_job("write", path=TARGET, content=fact)
            assert response.success, response.answer
            return {"result": json.dumps({"action": action, "target_path": TARGET})}

        agent = AsyncMock(spec=BaseAgentWrapper)
        agent.reply.side_effect = reply
        return agent

    app = _app(tmp_path)
    await app.start()
    task = asyncio.create_task(
        app.run_job(
            "auto_dream",
            date=DAY,
            scan_days=1,
            agent_wrapper=agent_for(app, True),
            as_llm=Mock(spec=ChatModelBase),
        ),
    )
    try:
        await asyncio.wait_for(entered.wait(), timeout=5)
        if edit_phase is not None:
            response = await app.run_job(
                "write",
                path=SOURCE,
                content=frontmatter.dumps(frontmatter.Post(NEW, name="deployment", description="Deployment policy")),
            )
            assert response.success, response.answer
            os.utime(source, (scanned_mtime + 2, scanned_mtime + 2))
        release.set()
        first = await asyncio.wait_for(task, timeout=5)
        assert first.success, first.answer
        assert first.metadata["dream"]["warnings"] == []
        nodes = await app.context.components["file_catalog"]["dream"].get_nodes([SOURCE])
        first_checkpoint = nodes[0].st_mtime
        if edit_phase == "integrate":
            assert OLD in (tmp_path / TARGET).read_text()
    finally:
        release.set()
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        await app.close()

    before_retry = len(calls)
    app = _app(tmp_path)
    await app.start()
    try:
        second = await app.run_job(
            "auto_dream",
            date=DAY,
            scan_days=1,
            agent_wrapper=agent_for(app),
            as_llm=Mock(spec=ChatModelBase),
        )
        assert second.success, second.answer
        assert second.metadata["dream"]["warnings"] == []
        assert first_checkpoint == scanned_mtime
        if edit_phase is None:
            assert second.metadata["dream"]["changed_paths"] == []
            assert len(calls) == before_retry
        else:
            assert second.metadata["dream"]["integrate_results"][0]["action"] == "CORRECT"
            assert SOURCE in second.metadata["dream"]["changed_paths"]
            assert NEW in (tmp_path / TARGET).read_text()
            assert NEW in source.read_text()
            assert len(calls) == before_retry + 2
            nodes = await app.context.components["file_catalog"]["dream"].get_nodes([SOURCE])
            assert nodes[0].st_mtime == source.stat().st_mtime
    finally:
        await app.close()


@pytest.mark.asyncio
async def test_finish_keeps_scanned_versions_for_changed_sources_and_day_indexes(tmp_path):
    """Supplemental indexes obey the same snapshot and failed-source rules as notes."""
    good, failed, index, unscanned = "daily/good.md", "daily/failed.md", f"daily/{DAY}.md", "daily/2026-05-27.md"
    observed = {}
    for rel in (good, failed, index):
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("scanned input")
        observed[rel] = path.stat().st_mtime
        path.write_text("later input")
        os.utime(path, (observed[rel] + 2, observed[rel] + 2))
    (tmp_path / unscanned).write_text("created after the scan")
    state = DreamState(
        date=DAY,
        dates=["2026-05-27", DAY],
        workspace=str(tmp_path),
        daily_dir="daily",
        changed_paths=[good, failed],
        failed_paths=[failed],
        existing=observed,
    )
    context = ApplicationContext(workspace_dir=str(tmp_path))
    catalog = LocalFileCatalog(name="dream", app_context=context)
    await catalog.start()
    try:
        response = await DreamFinishStep(app_context=context)(
            RuntimeContext(dream=state.model_dump(), file_catalog=catalog),
        )
        assert response.success
        assert response.metadata["dream"]["checkpoint_paths"] == [good]
        assert {node.path: node.st_mtime for node in await catalog.get_nodes()} == {
            good: observed[good],
            index: observed[index],
        }
    finally:
        await catalog.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("replacement", [False, True])
async def test_finish_handles_a_removed_or_replaced_source(tmp_path, replacement):
    """A replacement stays eligible; a missing source cannot create a fresh checkpoint."""
    source = tmp_path / SOURCE
    source.parent.mkdir(parents=True)
    source.write_text(OLD)
    observed = source.stat().st_mtime
    source.unlink()
    if replacement:
        source.write_text(NEW)
        os.utime(source, (observed + 2, observed + 2))
    state = DreamState(date=DAY, workspace=str(tmp_path), changed_paths=[SOURCE], existing={SOURCE: observed})
    context = ApplicationContext(workspace_dir=str(tmp_path))
    catalog = LocalFileCatalog(name="dream", app_context=context)
    await catalog.start()
    try:
        await DreamFinishStep(app_context=context)(RuntimeContext(dream=state.model_dump(), file_catalog=catalog))
        assert {node.path: node.st_mtime for node in await catalog.get_nodes()} == (
            {SOURCE: observed} if replacement else {}
        )
    finally:
        await catalog.close()
