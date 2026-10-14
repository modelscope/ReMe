"""Classifier registration, optional config, and secret redaction."""

# pylint: disable=redefined-outer-name,unused-argument

import asyncio
from pathlib import Path
import subprocess
import sys
import tomllib

import pytest

from reme.application import Application
from reme.components import R
from reme.components.as_classifier import JevAsClassifier
from reme.components.as_classifier import jev as jev_module
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
    assert "classifier_demo" not in default["jobs"]


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
    assert config["service"]["backend"] == "cli"
    assert list(config["jobs"]) == ["classifier_demo"]
    assert config["jobs"]["classifier_demo"]["enable_serve"] is False


def test_application_starts_without_optional_imports_and_redacts_key(classifier_env, monkeypatch, tmp_path):
    """The standalone demo config wires components without creating a client."""
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
