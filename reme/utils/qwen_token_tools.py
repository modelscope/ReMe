"""Local Qwen token counting and truncation utilities."""

from __future__ import annotations

import warnings
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Any

from .token_utils import estimate_token_count

DEFAULT_TOKENIZER = "Qwen/Qwen3.5-122B-A10B"


def _estimated_count(text: str) -> int:
    return max(1, estimate_token_count(text)) if text else 0


class QwenTokenTools:
    """Count and truncate text with a lazily loaded Hugging Face tokenizer."""

    def __init__(self, tokenizer_source: str = DEFAULT_TOKENIZER, *, tokenizer: Any | None = None) -> None:
        if not isinstance(tokenizer_source, str) or not tokenizer_source.strip():
            raise ValueError("tokenizer_source must be a non-empty string")
        self.tokenizer_source = tokenizer_source.strip()
        self._tokenizer = tokenizer
        self._missing_tokenizer_warning_lock = Lock()
        self._missing_tokenizer_warned = False
        self._tokenizer_unavailable = False

    def _warn_missing_tokenizer(self, reason: str) -> None:
        with self._missing_tokenizer_warning_lock:
            if self._missing_tokenizer_warned:
                return
            self._missing_tokenizer_warned = True
        warnings.warn(
            f"Qwen tokenizer is unavailable ({reason}); token count is estimated from UTF-8 byte length.",
            RuntimeWarning,
            stacklevel=3,
        )

    @property
    def tokenizer(self) -> Any:
        """Load the configured tokenizer on first use."""
        if self._tokenizer is None:
            self._tokenizer = _load_tokenizer(self.tokenizer_source)
        return self._tokenizer

    def _available_tokenizer(self) -> Any | None:
        with self._missing_tokenizer_warning_lock:
            if self._tokenizer_unavailable:
                return None
            try:
                return self.tokenizer
            except (ImportError, RuntimeError) as exc:
                self._tokenizer_unavailable = True
                reason = "missing 'tokenizers' package" if isinstance(exc, ImportError) else "load failed"
        self._warn_missing_tokenizer(reason)
        return None

    def count(self, text: str) -> int:
        """Count tokenizer IDs, or estimate from bytes when the tokenizer is unavailable."""
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        tokenizer = self._available_tokenizer()
        if tokenizer is None:
            return _estimated_count(text)
        return len(tokenizer.encode(text, add_special_tokens=False).ids)

    def truncate(self, text: str, max_tokens: int) -> tuple[str, int, bool]:
        """Truncate to a tokenizer prefix and return text, count, and change flag."""
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or max_tokens < 1:
            raise ValueError("max_tokens must be a positive integer")
        tokenizer = self._available_tokenizer()
        if tokenizer is None:
            token_count = _estimated_count(text)
            if token_count <= max_tokens:
                return text, token_count, False
            low, high = 0, len(text)
            while low < high:
                middle = (low + high + 1) // 2
                if _estimated_count(text[:middle]) <= max_tokens:
                    low = middle
                else:
                    high = middle - 1
            truncated = text[:low]
            return truncated, _estimated_count(truncated), True

        encoding = tokenizer.encode(text, add_special_tokens=False)
        token_count = len(encoding.ids)
        if token_count <= max_tokens:
            return text, token_count, False

        truncated = tokenizer.decode(encoding.ids[:max_tokens], skip_special_tokens=False)
        while truncated and self.count(truncated) > max_tokens:
            truncated = truncated[:-1]
        return truncated, self.count(truncated), True


@lru_cache(maxsize=4)
def _load_tokenizer(source: str) -> Any:
    """Load and cache one tokenizer without importing the optional package eagerly."""
    try:
        from tokenizers import Tokenizer
    except ImportError as exc:
        raise ImportError("Qwen token tools require the 'tokenizers' package for exact tokenization") from exc
    try:
        local_path = Path(source)
        if local_path.is_dir():
            return Tokenizer.from_file(str(local_path / "tokenizer.json"))
        if local_path.is_file():
            return Tokenizer.from_file(str(local_path))
        return Tokenizer.from_pretrained(source)
    except Exception as exc:
        raise RuntimeError(f"Unable to load Qwen tokenizer {source!r}: {exc}") from exc
