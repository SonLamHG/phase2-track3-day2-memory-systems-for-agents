"""Token counting helpers using tiktoken (with a char-based fallback)."""
from __future__ import annotations

try:
    import tiktoken

    _ENCODER = tiktoken.get_encoding("cl100k_base")

    def count_tokens(text: str) -> int:
        if not text:
            return 0
        return len(_ENCODER.encode(text))

except Exception:  # pragma: no cover - fallback path
    def count_tokens(text: str) -> int:
        if not text:
            return 0
        return max(1, len(text) // 4)
