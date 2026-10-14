"""Classifier registration, optional config, and secret redaction."""

# pylint: disable=redefined-outer-name,unused-argument

import asyncio
from dataclasses import dataclass, field
from importlib import import_module
import json
from pathlib import Path
import subprocess
import sys
import tomllib

import pytest
import httpx

from reme.application import Application
from reme.components import R
from reme.components.as_classifier import JevAsClassifier
from reme.components.as_classifier import jev as jev_module
from reme.components.client import HttpClient
from reme.config import parse_kwargs, resolve_app_config
from reme.enumeration import ComponentEnum
from reme.steps.common.app_config import AppConfigStep
from reme.steps.common.classifier_demo import ClassifierDemoStep


@pytest.fixture
def classifier_env(monkeypatch):
    """Keep all examples independent of the user's local provider settings."""
    for name in ("CLASSIFIER_BACKEND", "CLASSIFIER_MODEL_NAME", "CLASSIFIER_API_KEY", "CLASSIFIER_BASE_URL"):
        monkeypatch.delenv(name, raising=False)


def test_registration_and_default_opt_in(classifier_env):
    """Imports register providers, but default jobs never enable classification."""
    assert R.get(ComponentEnum.AS_CLASSIFIER, "jev") is JevAsClassifier
    assert R.get(ComponentEnum.STEP, "classifier_demo_step") is ClassifierDemoStep
    default = resolve_app_config(log_config=False)
    assert "as_classifier" not in default["components"]
    assert "jev" not in default["jobs"]


def test_demo_config_env_and_cli_override(classifier_env, monkeypatch):
    """Provider env expands and CLI transport settings deep-merge over the file."""
    monkeypatch.setenv("CLASSIFIER_API_KEY", "test-key")
    monkeypatch.setenv("CLASSIFIER_MODEL_NAME", "jev-test")
    config = resolve_app_config(
        log_config=False,
        **parse_kwargs(
            "config=classifier_demo",
            "components.as_classifier.default.timeout=12",
        ),
    )
    component = config["components"]["as_classifier"]["default"]
    assert component == {
        "backend": "jev",
        "model": "jev-test",
        "credential": {"api_key": "test-key", "base_url": None},
        "timeout": 12,
        "max_retries": 2,
        "retry_delay": 0.5,
    }
    default = resolve_app_config(log_config=False)
    assert config["service"] == default["service"]
    assert config["service"]["backend"] == "http"
    assert config["jobs"]["jev"]["enable_serve"] is True
    assert "classifier_demo" not in config["jobs"]
    assert {name: job for name, job in config["jobs"].items() if name != "jev"} == default["jobs"]
    assert {name: group for name, group in config["components"].items() if name != "as_classifier"} == default[
        "components"
    ]


def test_application_starts_without_optional_imports_and_redacts_key(classifier_env, monkeypatch, tmp_path):
    """The inherited config wires components without creating a classifier client."""
    monkeypatch.setenv("CLASSIFIER_API_KEY", "test-key")
    monkeypatch.setattr(jev_module, "import_module", lambda _: pytest.fail("Unexpected optional import"))
    config = resolve_app_config(config="classifier_demo", log_config=False)

    async def run():
        app = Application(
            **config,
            workspace_dir=str(tmp_path),
            enable_logo=False,
            log_to_console=False,
            log_to_file=False,
        )
        async with app:
            response = await AppConfigStep(app_context=app.context)()
            assert response.answer["components"]["as_classifier"]["default"]["credential"]["api_key"] == "***"

    asyncio.run(run())


def test_jev_client_calls_inherited_http_service(classifier_env, monkeypatch, tmp_path, capsys):
    """The two-stage workflow exposes /jev and sends client payloads to its Step."""

    @dataclass
    class Result:
        """Mock only the classifier boundary; exercise the actual service and client."""

        model: str = "jev-test"
        content: dict = field(default_factory=lambda: {"urgent": {"type": "binary_answer", "probability": 0.8}})

    calls = []

    async def classify(_self, state, questions):
        calls.append((state, questions))
        return Result()

    monkeypatch.setattr(JevAsClassifier, "__call__", classify)
    config = resolve_app_config(config="classifier_demo", log_config=False)
    reme_module = import_module("reme.reme")
    monkeypatch.setattr(reme_module, "running_app_config", lambda: config)

    async def run():
        app = Application(
            **config,
            workspace_dir=str(tmp_path),
            enable_logo=False,
            log_to_console=False,
            log_to_file=False,
        )
        service = app.context.service
        service.build_service(app)
        service.add_jobs(app)
        assert "/jev" in {route.path for route in service.service.routes}
        assert service.mcp_server is not None
        assert "jev" in {tool.name for tool in await service.mcp_server.list_tools()}

        async def start_client(client):
            client.client = httpx.AsyncClient(
                transport=httpx.ASGITransport(app=service.service),
                base_url=client.base_url,
            )

        monkeypatch.setattr(HttpClient, "_start", start_client)
        async with app:
            await reme_module.call_server("jev", state="I was charged twice.")
            displayed = json.loads(capsys.readouterr().out)
            assert displayed["success"] is True
            assert displayed["answer"]["content"]["urgent"]["probability"] == 0.8
            assert calls[0][0] == "I was charged twice."
            assert {q["type"] for q in calls[0][1].values()} == {"binary", "choice", "score"}
            custom = {"only": {"type": "binary", "instructions": "Is this urgent?"}}
            await reme_module.call_server("jev", state={"request": "hello"}, questions=custom)
            assert calls[1] == ({"request": "hello"}, custom)
            assert json.loads(capsys.readouterr().out)["success"] is True

    asyncio.run(run())


def test_import_with_optional_modules_blocked():
    """A fresh interpreter catches accidental optional imports anywhere in bootstrap."""
    script = """
import sys
from importlib.abc import MetaPathFinder
class BlockOptional(MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'agentscope.classifier' or fullname.startswith('typesafe_sdk'):
            raise ModuleNotFoundError(fullname)
sys.meta_path.insert(0, BlockOptional())
import reme
from reme.components.as_classifier import JevAsClassifier
from reme.steps.common.classifier_demo import ClassifierDemoStep
"""
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_extra_reuses_agentscope_pin():
    """Installing core and classifier together must not request different AgentScope versions."""
    config = tomllib.loads((Path(__file__).resolve().parents[2] / "pyproject.toml").read_text())
    extras = config["project"]["optional-dependencies"]
    assert extras["classifier-jev"] == ["agentscope[classifier-jev]==2.0.10"]
    assert extras["as"] == ["agentscope[model-ollama]==2.0.10"]
    assert "reme-ai[classifier-jev]" in extras["full"]
    assert "reme-ai[classifier-jev]" not in extras["core"]
