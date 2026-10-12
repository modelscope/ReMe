"""Pool ordering, reuse, and cleanup without Docker or model calls."""

# pylint: disable=missing-class-docstring,missing-function-docstring,unused-argument

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from deploy.benchmark_docker import (
    BenchmarkDockerPool,
    CasePlan,
    DockerReMeSandboxFactory,
    EvaluationQuery,
    JobRequest,
    SourceCandidate,
    SourceSnapshot,
)
from deploy.benchmark_docker.worker import _start_case_log


class FakeCase:
    def __init__(self, name: str, events: list[tuple]) -> None:
        self.name = name
        self.events = events
        self.case_id = name

    async def reset_case(self, case_id: str) -> None:
        self.case_id = case_id
        self.events.append((case_id, "reset"))

    async def upload_workspace(self, source: Path) -> None:
        assert source.exists()
        self.events.append((self.case_id, "upload", source.read_text(encoding="utf-8")))

    async def run_build(self, jobs: list[JobRequest]) -> dict:
        self.events.append((self.case_id, "build", len(jobs)))
        await asyncio.sleep(0)
        return {"success": True}

    async def export_workspace(self, destination: Path) -> Path:
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(self.case_id, encoding="utf-8")
        self.events.append((self.case_id, "export_workspace"))
        return destination

    async def run_queries(self, queries: list[EvaluationQuery]) -> dict:
        self.events.append((self.case_id, "query", len(queries)))
        return {"success": True}

    async def export_evaluation(self, destination: Path) -> Path:
        self.events.append((self.case_id, "export_evaluation"))
        return destination

    async def export_build_log(self, destination: Path) -> Path:
        destination = Path(destination)
        destination.write_text("build failed", encoding="utf-8")
        self.events.append((self.case_id, "export_build_log"))
        return destination

    async def read_build_log(self) -> str:
        self.events.append((self.case_id, "read_build_log"))
        return "build failed"

    async def close(self) -> None:
        self.events.append((self.name, "close"))


class FakeFactory:
    def __init__(self, events: list[tuple]) -> None:
        self.events = events

    async def create_cases(self, case_ids: list[str], *, concurrency: int) -> list[FakeCase]:
        assert len(case_ids) <= concurrency
        return [FakeCase(name, self.events) for name in case_ids]


@pytest.mark.asyncio
async def test_pool_builds_and_queries_each_case_then_reuses_workspace():
    events: list[tuple] = []
    pool = BenchmarkDockerPool(FakeFactory(events), concurrency=1)
    # Put the dependent first to exercise task scheduling independently of input order.
    plans = [
        CasePlan("child", queries=(EvaluationQuery("q2", "question", "secret"),), reuse_workspace_from="parent"),
        CasePlan("parent", build_jobs=(JobRequest("build"),), queries=(EvaluationQuery("q1", "question", "secret"),)),
    ]
    results = await pool.run(plans)

    assert [result.case_id for result in results] == ["child", "parent"]
    assert all(result.success for result in results)
    assert ("child", "upload", "parent") in events
    assert events.index(("parent", "build", 1)) < events.index(("parent", "query", 1))
    assert events.index(("parent", "export_workspace")) < events.index(("parent", "query", 1))
    assert events.index(("parent", "query", 1)) < events.index(("child", "query", 1))
    assert events[-1] == ("pool-0", "close")
    assert all(result.workspace_snapshot is None for result in results)


@pytest.mark.asyncio
async def test_pool_rejects_workspace_cycle_before_creating_containers():
    events: list[tuple] = []
    pool = BenchmarkDockerPool(FakeFactory(events), concurrency=2)
    with pytest.raises(ValueError, match="cycle"):
        await pool.run([CasePlan("a", reuse_workspace_from="b"), CasePlan("b", reuse_workspace_from="a")])
    assert not events


@pytest.mark.asyncio
async def test_pool_exports_query_only_case_from_reused_workspace(tmp_path):
    events: list[tuple] = []
    archive = tmp_path / "evaluation.tar.gz"
    plans = [
        CasePlan("parent", build_jobs=(JobRequest("build"),)),
        CasePlan(
            "child",
            queries=(EvaluationQuery("q1", "question", "secret"),),
            reuse_workspace_from="parent",
            export_evaluation_to=archive,
        ),
    ]

    results = await BenchmarkDockerPool(FakeFactory(events), concurrency=1).run(plans)

    assert all(result.success for result in results)
    assert ("child", "export_evaluation") in events


@pytest.mark.asyncio
async def test_pool_keeps_build_log_on_failure(tmp_path):
    class FailedBuildCase(FakeCase):
        async def run_build(self, jobs):
            self.events.append((self.case_id, "build_failed"))
            return {"success": False, "jobs": [{"error": "failed"}]}

    class FailedBuildFactory(FakeFactory):
        async def create_cases(self, case_ids, *, concurrency):
            return [FailedBuildCase(name, self.events) for name in case_ids]

    events: list[tuple] = []
    log_path = tmp_path / "build.log"
    plan = CasePlan("failed", build_jobs=(JobRequest("build"),), export_build_log_to=log_path)

    result = (await BenchmarkDockerPool(FailedBuildFactory(events), concurrency=1).run([plan]))[0]

    assert not result.success
    assert result.build == {"success": False, "jobs": [{"error": "failed"}]}
    assert result.build_log == "build failed"
    assert log_path.read_text(encoding="utf-8") == "build failed"
    assert events.index(("failed", "read_build_log")) < events.index(("pool-0", "close"))


@pytest.mark.asyncio
async def test_pool_keeps_build_log_when_build_raises(tmp_path):
    class TimedOutBuildCase(FakeCase):
        async def run_build(self, jobs):
            self.events.append((self.case_id, "build_timed_out"))
            raise TimeoutError("build exceeded command timeout")

    class TimedOutBuildFactory(FakeFactory):
        async def create_cases(self, case_ids, *, concurrency):
            return [TimedOutBuildCase(name, self.events) for name in case_ids]

    events: list[tuple] = []
    log_path = tmp_path / "build.log"
    plan = CasePlan("timed-out", build_jobs=(JobRequest("build"),), export_build_log_to=log_path)

    result = (await BenchmarkDockerPool(TimedOutBuildFactory(events), concurrency=1).run([plan]))[0]

    assert result.error == "TimeoutError: build exceeded command timeout"
    assert result.build is None
    assert result.build_log == "build failed"
    assert log_path.read_text(encoding="utf-8") == "build failed"
    assert events.index(("timed-out", "read_build_log")) < events.index(("pool-0", "close"))


@pytest.mark.asyncio
async def test_pool_cancels_case_before_closing_container():
    started = asyncio.Event()
    events: list[tuple] = []

    class BlockingCase(FakeCase):
        async def run_queries(self, queries):
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                self.events.append((self.case_id, "query_stopped"))

    class BlockingFactory(FakeFactory):
        async def create_cases(self, case_ids, *, concurrency):
            return [BlockingCase(name, self.events) for name in case_ids]

    plan = CasePlan("case", workspace_source=Path(__file__), queries=(EvaluationQuery("q", "question", "secret"),))
    task = asyncio.create_task(BenchmarkDockerPool(BlockingFactory(events), concurrency=1).run([plan]))
    await asyncio.wait_for(started.wait(), timeout=2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert events.index(("case", "query_stopped")) < events.index(("pool-0", "close"))


def test_source_snapshot_excludes_unrelated_and_secret_files(tmp_path):
    (tmp_path / "reme").mkdir()
    (tmp_path / "reme" / "__init__.py").write_text("ok", encoding="utf-8")
    (tmp_path / "baselines").mkdir()
    (tmp_path / "baselines" / "large.json").write_text("private", encoding="utf-8")
    (tmp_path / ".env").write_text("secret", encoding="utf-8")
    snapshot = SourceSnapshot.from_directory(tmp_path)
    assert snapshot.file_count == 1


def test_worker_writes_log_to_requested_artifact_path(tmp_path):
    """The current ReMe logger accepts a directory, so bind the exact log file explicitly."""
    from reme.utils import get_logger

    path = tmp_path / "build_log" / "build.log"
    logger = _start_case_log(path)
    try:
        logger.info("benchmark marker")
    finally:
        get_logger(log_to_console=False, log_to_file=False, force_init=True)
    assert "benchmark marker" in path.read_text(encoding="utf-8")


class FakeBackend:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.commands: list[list[str]] = []

    async def write_file(self, path: str, data: bytes) -> None:
        self.files[path] = data

    async def read_file(self, path: str) -> bytes:
        try:
            return self.files[path]
        except KeyError as exc:
            raise FileNotFoundError(path) from exc

    async def exec_shell(self, command: list[str], *, cwd=None, timeout=None):
        import json
        from types import SimpleNamespace

        self.commands.append(command)
        output = b""
        if len(command) > 2 and command[1] == "-c":
            output = json.dumps(
                {
                    "reme": "/workspace/candidate/reme/__init__.py",
                    "agentscope": "2.0.9",
                    "plugins": {"lme": "/workspace/candidate/plugins/lme/src/reme_lme/__init__.py"},
                },
            ).encode()
        if "/workspace/harness/worker.py" in command:
            request = json.loads(self.files[command[command.index("--request") + 1]])
            response = {"success": True, "jobs": []} if request.get("mode") == "build" else {"success": True}
            self.files[command[command.index("--response") + 1]] = json.dumps(response).encode()
        if command[:2] == ["tar", "-czf"]:
            self.files[command[2]] = b"workspace archive"
        return SimpleNamespace(exit_code=0, stdout=output, stderr=b"", ok=lambda: True)


class FakeWorkspace:
    def __init__(self, backend: FakeBackend) -> None:
        self.backend = backend
        self.closed = False

    async def initialize(self) -> None:
        pass

    def get_backend(self) -> FakeBackend:
        return self.backend

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_source_candidate_installs_plugin_and_closes_container(tmp_path):
    (tmp_path / "reme").mkdir()
    (tmp_path / "reme" / "__init__.py").write_text("ok", encoding="utf-8")
    backend = FakeBackend()
    workspace = FakeWorkspace(backend)
    factory = DockerReMeSandboxFactory(
        SourceCandidate(SourceSnapshot.from_directory(tmp_path), install_projects=(".", "plugins/lme")),
        plugins=("lme",),
        workspace_builder=lambda _id, _image, _env: workspace,
    )
    case = await factory.create_case("example")
    try:
        assert any(command[-1] == "/workspace/candidate/plugins/lme" for command in backend.commands)
        assert "/workspace/candidate.tar.gz" in backend.files
        assert "/workspace/harness/worker.py" in backend.files
        assert (await case.run_build([JobRequest("auto_memory")]))["success"]
        exported = await case.export_workspace(tmp_path / "workspace.tar.gz")
        assert exported.read_bytes() == b"workspace archive"
        with pytest.raises(ValueError, match="private"):
            await case.run_queries(
                [EvaluationQuery("q1", "question", "secret", answer_arguments={"golden_answer": "secret"})],
            )
    finally:
        await case.close()
    assert workspace.closed


@pytest.mark.asyncio
async def test_query_only_evaluation_export_omits_missing_build_log(tmp_path):
    (tmp_path / "reme").mkdir()
    (tmp_path / "reme" / "__init__.py").write_text("ok", encoding="utf-8")
    backend = FakeBackend()
    workspace = FakeWorkspace(backend)
    factory = DockerReMeSandboxFactory(
        SourceCandidate(SourceSnapshot.from_directory(tmp_path)),
        plugins=("lme",),
        workspace_builder=lambda _id, _image, _env: workspace,
    )
    case = await factory.create_case("query-only")
    try:
        backend.files["/workspace/case/queries/summary.json"] = b"{}"
        await case.export_evaluation(tmp_path / "evaluation.tar.gz")
        export = next(
            command for command in backend.commands if command[:3] == ["tar", "-czf", "/tmp/reme-case-export.tar.gz"]
        )
        assert "reme_workspace" in export
        assert "queries" in export
        assert "build_log" not in export
    finally:
        await case.close()


@pytest.mark.asyncio
async def test_cancelled_case_initialization_closes_workspace(tmp_path):
    (tmp_path / "reme").mkdir()
    (tmp_path / "reme" / "__init__.py").write_text("ok", encoding="utf-8")
    started = asyncio.Event()

    class BlockingWorkspace(FakeWorkspace):
        async def initialize(self):
            started.set()
            await asyncio.Event().wait()

    workspace = BlockingWorkspace(FakeBackend())
    factory = DockerReMeSandboxFactory(
        SourceCandidate(SourceSnapshot.from_directory(tmp_path)),
        workspace_builder=lambda _id, _image, _env: workspace,
    )
    task = asyncio.create_task(factory.create_case("cancelled"))
    await asyncio.wait_for(started.wait(), timeout=2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert workspace.closed


@pytest.mark.asyncio
async def test_cancelled_batch_creation_closes_completed_workspace(tmp_path):
    (tmp_path / "reme").mkdir()
    (tmp_path / "reme" / "__init__.py").write_text("ok", encoding="utf-8")
    second_started = asyncio.Event()

    class BlockingWorkspace(FakeWorkspace):
        async def initialize(self):
            second_started.set()
            await asyncio.Event().wait()

    first = FakeWorkspace(FakeBackend())
    second = BlockingWorkspace(FakeBackend())
    workspaces = iter((first, second))
    factory = DockerReMeSandboxFactory(
        SourceCandidate(SourceSnapshot.from_directory(tmp_path)),
        plugins=("lme",),
        workspace_builder=lambda _id, _image, _env: next(workspaces),
    )
    task = asyncio.create_task(factory.create_cases(["first", "second"], concurrency=2))
    await asyncio.wait_for(second_started.wait(), timeout=2)
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert first.closed and second.closed
