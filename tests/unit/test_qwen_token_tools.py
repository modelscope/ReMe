"""Qwen tokenizer utility tests without external downloads."""

import warnings
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from time import sleep
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from reme.utils import QwenTokenTools, estimate_token_count
from reme.utils import qwen_token_tools


class _Tokenizer:
    def encode(self, text, add_special_tokens):
        """Return one fake token per character."""
        assert add_special_tokens is False
        return SimpleNamespace(ids=list(text), offsets=[(index, index + 1) for index in range(len(text))])


def test_injected_tokenizer_counts_and_truncates():
    """Use an injected tokenizer for exact counting and truncation."""
    tools = QwenTokenTools(tokenizer=_Tokenizer())

    assert tools.count("你好 world") == 8
    assert tools.truncate("你好 world", 3) == ("你好 ", 3, True)
    assert tools.truncate("hi", 3) == ("hi", 2, False)


@pytest.mark.parametrize(
    "error, reason",
    [(ImportError, "missing 'tokenizers' package"), (RuntimeError, "load failed")],
)
def test_unavailable_tokenizer_warns_once_and_estimates(monkeypatch, error, reason):
    """Both failure paths estimate counts and truncation without retrying."""
    load = Mock(side_effect=error("unavailable"))
    monkeypatch.setattr(qwen_token_tools, "_load_tokenizer", load)
    tools = QwenTokenTools()

    with pytest.warns(RuntimeWarning, match=reason) as caught:
        assert tools.count("你好 world") == estimate_token_count("你好 world")
        assert tools.count("a") == 1
        assert tools.count("") == 0
        assert tools.truncate("abcdefghij", 1) == ("abcde", 1, True)
        assert tools.truncate("你好", 1) == ("你", 1, True)
        assert tools.truncate("abc", 1) == ("abc", 1, False)
        assert tools.truncate("", 1) == ("", 0, False)
        assert tools.tokenizer is None
    assert len(caught) == 1
    assert "pip install 'reme-ai[qwen-tokenizer]'" in str(caught[0].message)
    load.assert_called_once_with(tools.tokenizer_source)


@pytest.mark.parametrize("failure", [None, RuntimeError])
def test_concurrent_initialization_loads_and_warns_once(monkeypatch, failure):
    """Concurrent property and count access share one initialization attempt."""
    load_attempts = []
    tokenizer = _Tokenizer()
    ready = Barrier(8)

    def load(source):
        load_attempts.append(source)
        sleep(0.01)  # Allow competing callers to reach the initialization lock.
        if failure is not None:
            raise failure("unavailable")
        return tokenizer

    def access(index):
        ready.wait(timeout=5)
        return tools.tokenizer if index % 2 else tools.count("hello")

    monkeypatch.setattr(qwen_token_tools, "_load_tokenizer", load)
    tools = QwenTokenTools()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(access, range(8)))
        assert tools.tokenizer is (None if failure else tokenizer)
    assert load_attempts == [tools.tokenizer_source]
    assert results[::2] == [1 if failure else 5] * 4
    assert all(result is (None if failure else tokenizer) for result in results[1::2])
    assert len(caught) == (1 if failure else 0)


@pytest.fixture(name="byte_tokenizer")
def _byte_tokenizer():
    """Build a byte-level tokenizer locally, including partial Unicode tokens."""
    tokenizers = pytest.importorskip("tokenizers")
    alphabet = tokenizers.pre_tokenizers.ByteLevel.alphabet()
    tokenizer = tokenizers.Tokenizer(tokenizers.models.BPE({char: index for index, char in enumerate(alphabet)}, []))
    tokenizer.pre_tokenizer = tokenizers.pre_tokenizers.ByteLevel(add_prefix_space=False, use_regex=False)
    tokenizer.decoder = tokenizers.decoders.ByteLevel()
    return tokenizer


@pytest.mark.parametrize("text", ["🦄abc", "𠮷abc", "e\u0301abc"])
def test_unicode_truncation_preserves_original_prefix(byte_tokenizer, text):
    """Never decode incomplete UTF-8 tokens or change the source spelling."""
    tools = QwenTokenTools(tokenizer=byte_tokenizer)
    for budget in range(1, tools.count(text) + 1):
        truncated, count, changed = tools.truncate(text, budget)
        assert text.startswith(truncated)
        assert "�" not in truncated
        assert count == tools.count(truncated)
        assert count <= budget
        assert changed == (truncated != text)
    if text[0] != "e":
        assert tools.truncate(text, 1) == ("", 0, True)
        assert tools.truncate(text, 4) == (text[0], 4, True)


def test_normalized_truncation_preserves_original_prefix():
    """NFC output must never replace the original decomposed spelling."""
    tokenizers = pytest.importorskip("tokenizers")
    tokenizer = tokenizers.Tokenizer(
        tokenizers.models.WordPiece({"[UNK]": 0, "é": 1, "##a": 2, "##b": 3, "##c": 4}),
    )
    tokenizer.normalizer = tokenizers.normalizers.NFC()
    tools = QwenTokenTools(tokenizer=tokenizer)
    text = "e\u0301abc"
    assert tools.count(text) == 4
    truncated, count, changed = tools.truncate(text, 1)
    assert truncated
    assert text.startswith(truncated)
    assert count == tools.count(truncated) == 1
    assert changed is True


@pytest.mark.parametrize("source_kind", ["file", "directory", "remote"])
def test_loading_disables_saved_limits_and_isolates_instances(tmp_path, monkeypatch, source_kind):
    """Saved limits and mutations of another instance cannot corrupt counts."""
    tokenizers = pytest.importorskip("tokenizers")
    tokenizer = tokenizers.Tokenizer(
        tokenizers.models.WordLevel({"[UNK]": 0, "[PAD]": 1, "one": 2, "two": 3, "three": 4, "four": 5}),
    )
    tokenizer.pre_tokenizer = tokenizers.pre_tokenizers.Whitespace()
    tokenizer.enable_truncation(max_length=1)
    tokenizer.enable_padding(length=8, pad_id=1, pad_token="[PAD]")
    path = tmp_path / "tokenizer.json"
    tokenizer.save(str(path))
    if source_kind == "remote":
        source = f"test/{tmp_path.name}"
        load = Mock(return_value=tokenizer)
        monkeypatch.setattr(tokenizers.Tokenizer, "from_pretrained", load)
    else:
        source = str(path if source_kind == "file" else tmp_path)
    first = QwenTokenTools(source)
    text = "one two three four"
    assert first.count(text) == 4
    assert first.count("") == 0
    assert first.truncate(text, 1) == ("one", 1, True)
    first.tokenizer.enable_truncation(max_length=1)
    first.tokenizer.enable_padding(length=8, pad_id=1, pad_token="[PAD]")
    second = QwenTokenTools(source)
    assert second.tokenizer is not first.tokenizer
    assert second.count(text) == 4
    assert second.count("") == 0
    assert second.truncate(text, 1) == ("one", 1, True)
    if source_kind == "remote":
        load.assert_called_once_with(source)
