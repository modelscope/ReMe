"""Pool ordering, reuse, and cleanup without Docker or model calls."""

# pylint: disable=missing-class-docstring,missing-function-docstring,protected-access,unused-argument

from __future__ import annotations

import asyncio
import io
import json
from pathlib import Path
import subprocess
import tarfile

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
from deploy.benchmark_docker.docker_sandbox import SandboxCommandError, SandboxCommandTimeoutError
from deploy.benchmark_docker import worker as sandbox_worker


class FakeCase:
    def __init__(self, name: str, events: list[tuple]) -> None:
        self.name = name
        self.events = events
        self.case_id = name
        self.reusable = True

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
@pytest.mark.parametrize("raises", [False, True], ids=["failed-result", "exception"])
async def test_pool_keeps_build_log_on_failure(tmp_path, raises):
    class FailedBuildCase(FakeCase):
        async def run_build(self, jobs):
            if raises:
                raise TimeoutError("build exceeded command timeout")
            return {"success": False, "jobs": [{"error": "failed"}]}

    class FailedBuildFactory(FakeFactory):
        async def create_cases(self, case_ids, *, concurrency):
            return [FailedBuildCase(name, self.events) for name in case_ids]

    events: list[tuple] = []
    log_path = tmp_path / "build.log"
    plan = CasePlan("failed", build_jobs=(JobRequest("build"),), export_build_log_to=log_path)

    result = (await BenchmarkDockerPool(FailedBuildFactory(events), concurrency=1).run([plan]))[0]

    assert not result.success
    if raises:
        assert result.error == "TimeoutError: build exceeded command timeout"
        assert result.build is None
    else:
        assert result.error == "build failed"
        assert result.build == {"success": False, "jobs": [{"error": "failed"}]}
    assert result.build_log == "build failed"
    assert log_path.read_text(encoding="utf-8") == "build failed"
    assert events.index(("failed", "read_build_log")) < events.index(("pool-0", "close"))


@pytest.mark.asyncio
async def test_pool_replacement_failure_preserves_healthy_cases():
    events: list[tuple] = []

    class Worker(FakeCase):
        async def run_build(self, jobs):
            if self.case_id == "broken":
                self.reusable = False
                raise RuntimeError("command failed")
            await asyncio.sleep(0.02)
            self.events.append((self.case_id, "finished"))
            return {"success": True}

    class Factory(FakeFactory):
        async def create_cases(self, case_ids, *, concurrency):
            return [Worker(name, self.events) for name in case_ids]

        async def create_case(self, case_id):
            raise RuntimeError("replacement failed")

    plans = [CasePlan(case_id, build_jobs=(JobRequest("build"),)) for case_id in ("broken", "healthy", "waiting")]
    results = await asyncio.wait_for(BenchmarkDockerPool(Factory(events), concurrency=2).run(plans), timeout=2)

    assert [result.case_id for result in results] == ["broken", "healthy", "waiting"]
    assert "command failed" in results[0].error
    assert "replacement failed" in results[0].error
    assert results[1].success and results[2].success
    assert ("healthy", "finished") in events and ("waiting", "finished") in events


@pytest.mark.asyncio
async def test_pool_exhaustion_fails_waiting_cases():
    events: list[tuple] = []

    class BrokenCase(FakeCase):
        async def run_build(self, jobs):
            self.reusable = False
            raise RuntimeError("command failed")

    class Factory(FakeFactory):
        async def create_cases(self, case_ids, *, concurrency):
            return [BrokenCase(name, self.events) for name in case_ids]

        async def create_case(self, case_id):
            raise RuntimeError("replacement failed")

    plans = [CasePlan(case_id, build_jobs=(JobRequest("build"),)) for case_id in ("broken", "waiting-1", "waiting-2")]
    results = await asyncio.wait_for(BenchmarkDockerPool(Factory(events), concurrency=1).run(plans), timeout=2)

    assert "replacement failed" in results[0].error
    assert all("no available workers" in result.error for result in results[1:])
    assert not any(case_id.startswith("waiting") for case_id, action in events if action == "reset")


@pytest.mark.asyncio
async def test_pool_exhaustion_unblocks_dependent_cases():
    events: list[tuple] = []

    class BrokenCase(FakeCase):
        async def run_build(self, jobs):
            self.reusable = False
            raise RuntimeError("command failed")

    class Factory(FakeFactory):
        async def create_cases(self, case_ids, *, concurrency):
            return [BrokenCase(name, self.events) for name in case_ids]

        async def create_case(self, case_id):
            raise RuntimeError("replacement failed")

    plans = [
        CasePlan("dependent", reuse_workspace_from="waiting"),
        CasePlan("broken", build_jobs=(JobRequest("build"),)),
        CasePlan("waiting", build_jobs=(JobRequest("build"),)),
    ]
    results = await asyncio.wait_for(BenchmarkDockerPool(Factory(events), concurrency=1).run(plans), timeout=2)

    assert results[0].error == "source case 'waiting' failed"
    assert "replacement failed" in results[1].error
    assert "no available workers" in results[2].error


@pytest.mark.asyncio
async def test_pool_close_failure_retires_slot_without_replacement():
    events: list[tuple] = []

    class BrokenCase(FakeCase):
        async def run_build(self, jobs):
            self.reusable = False
            raise RuntimeError("command failed")

        async def close(self):
            self.events.append((self.name, "close failed"))
            raise RuntimeError("close failed")

    class Factory(FakeFactory):
        async def create_cases(self, case_ids, *, concurrency):
            return [BrokenCase(name, self.events) for name in case_ids]

        async def create_case(self, case_id):
            pytest.fail("replacement must not start while the old container may still be running")

    plans = [CasePlan(case_id, build_jobs=(JobRequest("build"),)) for case_id in ("broken", "next")]
    results = await asyncio.wait_for(BenchmarkDockerPool(Factory(events), concurrency=1).run(plans), timeout=2)

    assert "close failed" in results[0].error
    assert results[1].error == "no available workers"
    assert ("next", "build", 1) not in events


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


@pytest.mark.asyncio
@pytest.mark.parametrize("failure_phase", ["config", "application"])
async def test_build_log_captures_initialization_failure(tmp_path, monkeypatch, failure_phase):
    if failure_phase == "config":

        def fail_config(_request):
            raise ValueError("invalid benchmark config")

        monkeypatch.setattr(sandbox_worker, "_prepare_runtime", fail_config)
        expected = "ValueError: invalid benchmark config"
    else:
        config = {
            "workspace_dir": str(tmp_path / "workspace"),
            "service": {"backend": "cli"},
            "jobs": {"broken": {"backend": "missing"}},
            "enable_logo": False,
            "log_to_console": False,
            "log_to_file": False,
        }
        monkeypatch.setattr(sandbox_worker, "_prepare_runtime", lambda _request: (tmp_path, config))
        expected = "ValueError: Unregistered backend 'missing' for Job 'broken'"

    with pytest.raises(ValueError, match="invalid benchmark config|Unregistered backend"):
        await sandbox_worker._run_build({"case_root": str(tmp_path), "jobs": [{"job": "build"}]})

    log_text = (tmp_path / "build_log" / "build.log").read_text(encoding="utf-8")
    assert "Traceback (most recent call last):" in log_text
    assert expected in log_text


@pytest.mark.asyncio
async def test_build_log_remains_bound_after_application_initializes_logger(tmp_path, monkeypatch):
    import reme.reme as reme_module

    monkeypatch.setattr(sandbox_worker, "_prepare_runtime", lambda _request: (tmp_path, {}))

    class FakeReMe:
        def __init__(self, **_kwargs):
            from reme.utils import get_logger

            get_logger(log_to_console=False, log_to_file=False, force_init=True)

        async def start(self):
            pass

        async def close(self):
            pass

    async def run_job(_app, _job, _arguments):
        return {"success": True}

    monkeypatch.setattr(reme_module, "ReMe", FakeReMe)
    monkeypatch.setattr(sandbox_worker, "_run_job_on_app", run_job)

    result = await sandbox_worker._run_build({"case_root": str(tmp_path), "jobs": [{"job": "build"}]})

    assert result["success"]
    log_text = (tmp_path / "build_log" / "build.log").read_text(encoding="utf-8")
    assert "[sandbox] build phase started" in log_text
    assert "[sandbox] build phase finished" in log_text


@pytest.mark.asyncio
async def test_worker_clears_search_budget_between_queries(tmp_path, monkeypatch):
    import reme.reme as reme_module

    monkeypatch.setattr(sandbox_worker, "_prepare_runtime", lambda _request: (tmp_path, {}))
    seen_metadata: list[dict] = []
    apps = []

    class FakeReMe:
        def __init__(self, **_kwargs):
            from types import SimpleNamespace

            self.context = SimpleNamespace(metadata={"shared": "retained"})
            apps.append(self)

        async def start(self):
            pass

        async def close(self):
            pass

    async def run_job(app, _job, _arguments):
        seen_metadata.append(dict(app.context.metadata))
        app.context.metadata["tool_contexts"] = {"same-id": {"seen": True}}
        app.context.metadata["__search_call_budgets"] = {"same-id": {"count": 1}}
        return {"success": True, "answer": "ok", "metadata": {}, "error": None}

    monkeypatch.setattr(reme_module, "ReMe", FakeReMe)
    monkeypatch.setattr(sandbox_worker, "_run_job_on_app", run_job)

    result = await sandbox_worker._run_queries(
        {
            "case_root": str(tmp_path),
            "queries": [
                {"query_id": "q1", "question": "first"},
                {"query_id": "q2", "question": "second"},
            ],
        },
    )

    assert result["success"]
    assert len(apps) == 1
    assert seen_metadata == [{"shared": "retained"}, {"shared": "retained"}]
    assert apps[0].context.metadata == {"shared": "retained"}


@pytest.mark.asyncio
async def test_worker_checkpoint_commits_only_memory_paths(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    subprocess.run(["git", "init", "--quiet", str(workspace)], check=True)
    (workspace / "daily").mkdir()
    (workspace / "daily" / "note.md").write_text("memory", encoding="utf-8")
    (workspace / "digest").mkdir()
    (workspace / "digest" / "note.md").write_text("digest", encoding="utf-8")
    (workspace / "sessions").mkdir()
    (workspace / "sessions" / "note.md").write_text("session", encoding="utf-8")
    (workspace / "other.txt").write_text("unrelated", encoding="utf-8")
    config = {"workspace_dir": str(workspace), "daily_dir": "daily", "digest_dir": "digest", "session_dir": "sessions"}
    monkeypatch.setattr(sandbox_worker, "_prepare_runtime", lambda _request: (tmp_path, config))

    result = await sandbox_worker._run_checkpoint({"message": "memory boundary"})

    assert result["success"] is True
    assert result["memory_checkpoint"]["message"] == "memory boundary"
    committed = subprocess.run(
        ["git", "show", "--pretty=format:", "--name-only", "HEAD"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=True,
    )
    assert set(committed.stdout.splitlines()) == {"daily/note.md", "digest/note.md", "sessions/note.md"}
    assert result["memory_checkpoint"]["paths"] == ["daily", "digest", "sessions"]
    second = await sandbox_worker._run_checkpoint({"message": "empty boundary"})
    assert second["memory_checkpoint"]["commit_sha"] != result["memory_checkpoint"]["commit_sha"]

    config["daily_dir"] = "../outside"
    with pytest.raises(ValueError, match="escapes the runtime workspace"):
        await sandbox_worker._run_checkpoint({"message": "unsafe boundary"})


class FakeBackend:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.commands: list[list[str]] = []
        self.worker_responses: dict[str, dict] = {}

    async def write_file(self, path: str, data: bytes) -> None:
        self.files[path] = data

    async def read_file(self, path: str) -> bytes:
        try:
            return self.files[path]
        except KeyError as exc:
            raise FileNotFoundError(path) from exc

    async def exec_shell(self, command: list[str], *, cwd=None, timeout=None):
        from types import SimpleNamespace

        self.commands.append(command)
        output = b""
        exit_code = 0
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
            mode = request.get("mode", "job")
            default = {"success": True, "jobs": []} if mode == "build" else {"success": True}
            response = self.worker_responses.get(mode, default)
            self.files[command[command.index("--response") + 1]] = json.dumps(response).encode()
            exit_code = 0 if response["success"] else 1
        if command[:2] == ["tar", "-czf"]:
            self.files[command[2]] = b"workspace archive"
        return SimpleNamespace(exit_code=exit_code, stdout=output, stderr=b"", ok=lambda: exit_code == 0)


class TimedOutBackend(FakeBackend):
    async def exec_shell(self, command: list[str], *, cwd=None, timeout=None):
        if "/workspace/harness/worker.py" in command:
            from types import SimpleNamespace

            self.commands.append(command)
            self.files["/workspace/case/build_log/build.log"] = b"build still running"
            return SimpleNamespace(exit_code=-1, stdout=b"", stderr=b"timed out", ok=lambda: False)
        return await super().exec_shell(command, cwd=cwd, timeout=timeout)


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


def _fake_docker_factory(tmp_path, workspace_builder, *, install_projects=(".",)):
    (tmp_path / "reme").mkdir()
    (tmp_path / "reme" / "__init__.py").write_text("ok", encoding="utf-8")
    return DockerReMeSandboxFactory(
        SourceCandidate(SourceSnapshot.from_directory(tmp_path), install_projects=install_projects),
        plugins=("lme",),
        workspace_builder=workspace_builder,
    )


@pytest.mark.asyncio
async def test_backend_timeout_prevents_direct_case_reset(tmp_path):
    workspace = FakeWorkspace(TimedOutBackend())
    factory = _fake_docker_factory(tmp_path, lambda _id, _image, _env: workspace)
    case = await factory.create_case("timed-out")
    try:
        with pytest.raises(SandboxCommandTimeoutError):
            await case.run_build([JobRequest("build")])
        assert not case.reusable
        assert case.actions[-1].exit_code == -1
        assert await case.read_build_log() == "build still running"
        with pytest.raises(SandboxCommandError, match="no longer reusable"):
            await case.reset_case("next")
    finally:
        await case.close()
    assert workspace.closed


@pytest.mark.asyncio
async def test_external_timeout_prevents_case_reset(tmp_path):
    started = asyncio.Event()

    class BlockingBackend(FakeBackend):
        async def exec_shell(self, command, *, cwd=None, timeout=None):
            if "/workspace/harness/worker.py" in command:
                self.commands.append(command)
                started.set()
                await asyncio.Event().wait()
            return await super().exec_shell(command, cwd=cwd, timeout=timeout)

    workspace = FakeWorkspace(BlockingBackend())
    factory = _fake_docker_factory(tmp_path, lambda _id, _image, _env: workspace)
    case = await factory.create_case("timed-out")
    try:
        build = asyncio.create_task(case.run_build([JobRequest("build")]))
        await asyncio.wait_for(started.wait(), timeout=2)
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(build, timeout=0.01)
        assert not case.reusable
        with pytest.raises(SandboxCommandError, match="no longer reusable"):
            await case.reset_case("next")
        inbox_count = sum("/inbox/" in path for path in workspace.backend.files)
        with pytest.raises(SandboxCommandError, match="no longer reusable"):
            await case.run_build([JobRequest("build")])
        assert sum("/inbox/" in path for path in workspace.backend.files) == inbox_count
    finally:
        await case.close()
    assert workspace.closed


@pytest.mark.asyncio
async def test_cancelled_request_upload_prevents_case_reset(tmp_path):
    started = asyncio.Event()

    class BlockingBackend(FakeBackend):
        async def write_file(self, path, data):
            if "/inbox/" in path:
                started.set()
                await asyncio.Event().wait()
            await super().write_file(path, data)

    workspace = FakeWorkspace(BlockingBackend())
    factory = _fake_docker_factory(tmp_path, lambda _id, _image, _env: workspace)
    case = await factory.create_case("cancelled-upload")
    try:
        build = asyncio.create_task(case.run_build([JobRequest("build")]))
        await asyncio.wait_for(started.wait(), timeout=2)
        build.cancel()
        with pytest.raises(asyncio.CancelledError):
            await build
        assert not case.reusable
        with pytest.raises(SandboxCommandError, match="no longer reusable"):
            await case.reset_case("next")
    finally:
        await case.close()
    assert workspace.closed


@pytest.mark.asyncio
async def test_backend_write_error_prevents_case_reset(tmp_path):
    class FailingBackend(FakeBackend):
        async def write_file(self, path, data):
            if "/inbox/" in path:
                raise RuntimeError("Docker upload stream failed")
            await super().write_file(path, data)

    workspace = FakeWorkspace(FailingBackend())
    factory = _fake_docker_factory(tmp_path, lambda _id, _image, _env: workspace)
    case = await factory.create_case("write-error")
    try:
        with pytest.raises(RuntimeError, match="Docker upload stream failed"):
            await case.run_build([JobRequest("build")])
        assert not case.reusable
        with pytest.raises(SandboxCommandError, match="no longer reusable"):
            await case.reset_case("next")
    finally:
        await case.close()
    assert workspace.closed


@pytest.mark.asyncio
async def test_backend_exec_error_prevents_case_reset(tmp_path):
    class FailingBackend(FakeBackend):
        async def exec_shell(self, command, *, cwd=None, timeout=None):
            if "/workspace/harness/worker.py" in command:
                raise RuntimeError("Docker exec stream failed")
            return await super().exec_shell(command, cwd=cwd, timeout=timeout)

    workspace = FakeWorkspace(FailingBackend())
    factory = _fake_docker_factory(tmp_path, lambda _id, _image, _env: workspace)
    case = await factory.create_case("exec-error")
    try:
        with pytest.raises(RuntimeError, match="Docker exec stream failed"):
            await case.run_build([JobRequest("build")])
        assert not case.reusable
        with pytest.raises(SandboxCommandError, match="no longer reusable"):
            await case.reset_case("next")
    finally:
        await case.close()
    assert workspace.closed


@pytest.mark.asyncio
async def test_cancelled_close_can_be_retried(tmp_path):
    started = asyncio.Event()

    class InterruptibleWorkspace(FakeWorkspace):
        def __init__(self):
            super().__init__(FakeBackend())
            self.close_calls = 0

        async def close(self):
            self.close_calls += 1
            if self.close_calls == 1:
                started.set()
                await asyncio.Event().wait()
            self.closed = True

    workspace = InterruptibleWorkspace()
    factory = _fake_docker_factory(tmp_path, lambda _id, _image, _env: workspace)
    case = await factory.create_case("close-retry")
    closing = asyncio.create_task(case.close())
    await asyncio.wait_for(started.wait(), timeout=2)
    closing.cancel()
    with pytest.raises(asyncio.CancelledError):
        await closing
    assert not case.reusable
    assert not workspace.closed

    await case.close()
    assert workspace.closed
    assert workspace.close_calls == 2


@pytest.mark.asyncio
async def test_source_candidate_installs_plugin_and_closes_container(tmp_path):
    backend = FakeBackend()
    workspace = FakeWorkspace(backend)
    factory = _fake_docker_factory(
        tmp_path,
        lambda _id, _image, _env: workspace,
        install_projects=(".", "plugins/lme"),
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
async def test_job_and_checkpoint_share_worker_request_path(tmp_path):
    backend = FakeBackend()
    workspace = FakeWorkspace(backend)
    factory = _fake_docker_factory(tmp_path, lambda _id, _image, _env: workspace)
    case = await factory.create_case("example")
    try:
        result = await case.run_job("answer", {"query": "hello"})
        assert result.success
        assert case.actions[-1].name == "job:answer"
        job_request = json.loads(backend.files[next(path for path in backend.files if "/inbox/" in path)])
        assert job_request["mode"] == "job"
        assert job_request["arguments"] == {"query": "hello"}

        await case.commit_memory_history("memory boundary")
        assert case.actions[-1].name == "worker:checkpoint"
        requests = [json.loads(content) for path, content in backend.files.items() if "/inbox/" in path]
        assert requests[-1]["mode"] == "checkpoint"
        assert requests[-1]["message"] == "memory boundary"
        assert not any(command[0] == "git" and "commit" in command for command in backend.commands)
        with pytest.raises(ValueError, match="non-empty"):
            await case.commit_memory_history(" ")

        backend.worker_responses["checkpoint"] = {"success": False, "error": "git commit failed"}
        with pytest.raises(SandboxCommandError, match="git commit failed"):
            await case.commit_memory_history("next boundary")
        assert case.actions[-1].exit_code == 1
    finally:
        await case.close()


@pytest.mark.asyncio
async def test_pool_replaces_worker_after_backend_timeout(tmp_path):
    timed_out_workspace = FakeWorkspace(TimedOutBackend())
    replacement_workspace = FakeWorkspace(FakeBackend())
    workspaces = iter((timed_out_workspace, replacement_workspace))
    factory = _fake_docker_factory(tmp_path, lambda _id, _image, _env: next(workspaces))
    plans = [
        CasePlan("timed-out", build_jobs=(JobRequest("build"),), export_build_log_to=tmp_path / "build.log"),
        CasePlan("next", build_jobs=(JobRequest("build"),)),
    ]

    results = await BenchmarkDockerPool(factory, concurrency=1).run(plans)

    assert "SandboxCommandTimeoutError" in results[0].error
    assert results[0].build_log == "build still running"
    assert (tmp_path / "build.log").read_text(encoding="utf-8") == "build still running"
    assert results[1].success
    assert timed_out_workspace.closed and replacement_workspace.closed
    assert sum(command[:2] == ["rm", "-rf"] for command in timed_out_workspace.backend.commands) == 1


@pytest.mark.asyncio
async def test_query_only_evaluation_export_omits_missing_build_log(tmp_path):
    backend = FakeBackend()
    workspace = FakeWorkspace(backend)
    factory = _fake_docker_factory(tmp_path, lambda _id, _image, _env: workspace)
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
@pytest.mark.parametrize(
    ("method", "required", "members"),
    [
        ("export_memory_construction", "build_log/build.log", ["reme_workspace", "build_log"]),
        ("export_queries", "queries/summary.json", ["queries"]),
        ("export_query", "queries/q1/result.json", ["queries/q1"]),
    ],
)
async def test_archive_exports_check_required_artifacts(tmp_path, method, required, members):
    backend = FakeBackend()
    case = await _fake_docker_factory(tmp_path, lambda _id, _image, _env: FakeWorkspace(backend)).create_case("example")
    destination = tmp_path / "exports" / "result.tar.gz"
    export = getattr(case, method)
    args = ("q1", destination) if method == "export_query" else (destination,)
    try:
        with pytest.raises(SandboxCommandError, match="missing required artifact"):
            await export(*args)
        backend.files[f"/workspace/case/{required}"] = b"{}"
        assert await export(*args) == destination
        assert destination.read_bytes() == b"workspace archive"
        assert ["tar", "-czf", "/tmp/reme-case-export.tar.gz", "-C", "/workspace/case", *members] in backend.commands
    finally:
        await case.close()


@pytest.mark.asyncio
async def test_default_analysis_export_saves_logs_outside_archive(tmp_path):
    class AnalysisBackend(FakeBackend):
        async def exec_shell(self, command, *, cwd=None, timeout=None):
            result = await super().exec_shell(command, cwd=cwd, timeout=timeout)
            if command[:2] == ["tar", "-czf"] and command[-1] == "queries":
                stream = io.BytesIO()
                with tarfile.open(fileobj=stream, mode="w:gz") as archive:
                    for name, content in (
                        ("queries/summary.json", b"{}"),
                        ("queries/q1/answer.log", b"answer log"),
                    ):
                        info = tarfile.TarInfo(name)
                        info.size = len(content)
                        archive.addfile(info, io.BytesIO(content))
                self.files[command[2]] = stream.getvalue()
            return result

    backend = AnalysisBackend()
    workspace = FakeWorkspace(backend)
    factory = _fake_docker_factory(tmp_path, lambda _id, _image, _env: workspace)
    case = await factory.create_case("example")
    try:
        backend.files["/workspace/case/runtime-layout.json"] = (
            b'{"workspace_root":"reme_workspace","analysis_excludes":[]}'
        )
        backend.files["/workspace/case/build_log/build.log"] = b"build log"
        backend.files["/workspace/case/queries/summary.json"] = b"{}"
        archive = tmp_path / "analysis.tar.gz"
        assert await case.export(archive) == archive
        assert archive.read_bytes() == b"workspace archive"
        artifacts = tmp_path / "analysis.tar.gz.artifacts"
        assert (artifacts / "build_log" / "build.log").read_bytes() == b"build log"
        assert (artifacts / "queries" / "summary.json").read_bytes() == b"{}"
        assert (artifacts / "queries" / "q1" / "answer.log").read_bytes() == b"answer log"
        archive_command = next(
            command for command in backend.commands if command[:3] == ["tar", "-czf", "/tmp/reme-case-export.tar.gz"]
        )
        assert "build_log" not in archive_command
        assert "queries" not in archive_command
    finally:
        await case.close()


@pytest.mark.asyncio
async def test_cancelled_case_initialization_closes_workspace(tmp_path):
    started = asyncio.Event()

    class BlockingWorkspace(FakeWorkspace):
        async def initialize(self):
            started.set()
            await asyncio.Event().wait()

    workspace = BlockingWorkspace(FakeBackend())
    factory = _fake_docker_factory(tmp_path, lambda _id, _image, _env: workspace)
    task = asyncio.create_task(factory.create_case("cancelled"))
    await asyncio.wait_for(started.wait(), timeout=2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert workspace.closed


@pytest.mark.asyncio
async def test_cancelled_batch_creation_closes_completed_workspace(tmp_path):
    second_started = asyncio.Event()

    class BlockingWorkspace(FakeWorkspace):
        async def initialize(self):
            second_started.set()
            await asyncio.Event().wait()

    first = FakeWorkspace(FakeBackend())
    second = BlockingWorkspace(FakeBackend())
    workspaces = iter((first, second))
    factory = _fake_docker_factory(tmp_path, lambda _id, _image, _env: next(workspaces))
    task = asyncio.create_task(factory.create_cases(["first", "second"], concurrency=2))
    await asyncio.wait_for(second_started.wait(), timeout=2)
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert first.closed and second.closed


@pytest.mark.asyncio
async def test_failed_case_creation_preserves_initialization_error_when_close_fails(tmp_path):
    class BrokenWorkspace(FakeWorkspace):
        async def initialize(self):
            raise RuntimeError("initialization failed")

        async def close(self):
            raise RuntimeError("close failed")

    factory = _fake_docker_factory(tmp_path, lambda _id, _image, _env: BrokenWorkspace(FakeBackend()))
    with pytest.raises(RuntimeError, match="initialization failed") as failure:
        await factory.create_case("broken")
    assert any("close failed" in note for note in failure.value.__notes__)


@pytest.mark.asyncio
async def test_failed_batch_creation_preserves_creation_error_when_close_fails(tmp_path):
    class CloseFailsWorkspace(FakeWorkspace):
        async def close(self):
            raise RuntimeError("close failed")

    class InitializeFailsWorkspace(FakeWorkspace):
        async def initialize(self):
            raise RuntimeError("initialization failed")

    workspaces = iter((CloseFailsWorkspace(FakeBackend()), InitializeFailsWorkspace(FakeBackend())))
    factory = _fake_docker_factory(tmp_path, lambda _id, _image, _env: next(workspaces))
    with pytest.raises(RuntimeError, match="initialization failed"):
        await factory.create_cases(["first", "second"], concurrency=2)
