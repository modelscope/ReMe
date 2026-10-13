"""Qwen tokenizer utility tests without external downloads."""

import warnings
from types import SimpleNamespace

import pytest

from reme.utils import QwenTokenTools, estimate_token_count
from reme.utils import qwen_token_tools


class _Tokenizer:
    def encode(self, text, add_special_tokens):
        """Return one fake token per character."""
        assert add_special_tokens is False
        return SimpleNamespace(ids=list(text))

    def decode(self, ids, skip_special_tokens):
        """Reassemble fake character tokens."""
        assert skip_special_tokens is False
        return "".join(ids)


def test_injected_tokenizer_counts_and_truncates():
    """Use an injected tokenizer for exact counting and truncation."""
    tools = QwenTokenTools(tokenizer=_Tokenizer())

    assert tools.count("你好 world") == 8
    assert tools.truncate("你好 world", 3) == ("你好 ", 3, True)
    assert tools.truncate("hi", 3) == ("hi", 2, False)


def test_missing_package_warns_and_estimates_count(monkeypatch):
    """Warn once per instance and estimate when tokenizers is missing."""

    def missing_tokenizer(_source):
        raise ImportError("tokenizers is missing")

    monkeypatch.setattr(qwen_token_tools, "_load_tokenizer", missing_tokenizer)
    tools = QwenTokenTools()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert tools.count("你好 world") == estimate_token_count("你好 world")
        assert tools.count("a") == 1
        assert tools.count("") == 0
        assert tools.truncate("你好", 1) == ("你", 1, True)
        assert QwenTokenTools().count("a") == 1
    assert len(caught) == 2
    assert "missing 'tokenizers' package" in str(caught[0].message)


def test_missing_package_warns_and_truncates_by_estimate(monkeypatch):
    """Truncate within the estimated token budget without tokenizers."""

    def missing_tokenizer(_source):
        raise ImportError("tokenizers is missing")

    monkeypatch.setattr(qwen_token_tools, "_load_tokenizer", missing_tokenizer)
    tools = QwenTokenTools()

    with pytest.warns(RuntimeWarning, match="missing 'tokenizers' package"):
        assert tools.truncate("abcdefghij", 1) == ("abcde", 1, True)
        assert tools.truncate("你好", 1) == ("你", 1, True)
        assert tools.truncate("abc", 1) == ("abc", 1, False)
        assert tools.truncate("", 1) == ("", 0, False)


def test_tokenizer_load_failure_warns_and_uses_estimate(monkeypatch):
    """Reuse the estimate after a tokenizer load fails."""
    load_attempts = 0

    def broken_tokenizer(_source):
        nonlocal load_attempts
        load_attempts += 1
        raise RuntimeError("tokenizer file is invalid")

    monkeypatch.setattr(qwen_token_tools, "_load_tokenizer", broken_tokenizer)

    tools = QwenTokenTools()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert tools.count("hello") == 1
        assert tools.truncate("abcdefghij", 1) == ("abcde", 1, True)
    assert len(caught) == 1
    assert "load failed" in str(caught[0].message)
    assert load_attempts == 1
