"""Episodic memory: append-only JSON log of agent trajectories.

Each episode records a completed interaction with task/outcome/reasoning,
so the agent can later recall 'how did I solve this last time?'.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path


_STOPWORDS = {
    "the", "and", "for", "with", "that", "what", "which", "how", "was", "were",
    "are", "is", "you", "your", "mine", "not", "have", "has", "had", "did",
    "this", "these", "those", "from", "into", "ago", "bạn", "tôi", "của", "là",
    "không", "có", "trong", "thì", "đã", "được", "các", "một", "cái", "này",
    "đó", "kia", "gì", "nào", "sao", "vậy", "mà", "để", "cho", "với", "từ",
    "hôm", "qua", "đề", "xuất", "tôi",
}


def _tokenize(text: str) -> list[str]:
    return [w for w in re.findall(r"[\w\-]+", text.lower()) if w not in _STOPWORDS]


class EpisodicMemory:
    def __init__(self, log_path: str | None = None):
        self.path = Path(log_path or os.getenv("EPISODIC_LOG_PATH", "./data/episodic_log.json"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def _load(self) -> list[dict]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write(self, episodes: list[dict]) -> None:
        self.path.write_text(json.dumps(episodes, ensure_ascii=False, indent=2), encoding="utf-8")

    def save(
        self,
        user_id: str,
        task: str,
        outcome: str,
        reasoning: str = "",
        tags: list[str] | None = None,
    ) -> dict:
        episode = {
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task": task,
            "outcome": outcome,
            "reasoning": reasoning,
            "tags": tags or [],
        }
        episodes = self._load()
        episodes.append(episode)
        self._write(episodes)
        return episode

    def retrieve(
        self,
        user_id: str,
        query: str | None = None,
        limit: int = 5,
    ) -> list[dict]:
        """Return most recent episodes for user; if query provided, prefer episodes
        that share a content word with the query, falling back to most-recent if
        no word-level matches exist.
        """
        episodes = [e for e in self._load() if e.get("user_id") == user_id]
        if not episodes:
            return []
        if query:
            tokens = {w for w in _tokenize(query) if len(w) > 2}
            scored: list[tuple[int, dict]] = []
            for e in episodes:
                haystack = " ".join(
                    [
                        e.get("task", ""),
                        e.get("outcome", ""),
                        " ".join(e.get("tags", [])),
                    ]
                ).lower()
                score = sum(1 for t in tokens if t in haystack)
                scored.append((score, e))
            if any(s > 0 for s, _ in scored):
                scored.sort(key=lambda x: (-x[0], episodes.index(x[1])))
                return [e for _, e in scored][:limit]
        return list(reversed(episodes))[:limit]

    def clear(self, user_id: str | None = None) -> int:
        episodes = self._load()
        if user_id is None:
            count = len(episodes)
            self._write([])
            return count
        remaining = [e for e in episodes if e.get("user_id") != user_id]
        removed = len(episodes) - len(remaining)
        self._write(remaining)
        return removed
