"""Long-term profile memory backed by Redis.

Stores per-user facts as a Redis hash: user:{id}:profile -> {fact_key: JSON(value, updated_at)}.
Updates overwrite by key (no append), satisfying the conflict-handling requirement.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import redis


class LongTermProfile:
    def __init__(self, redis_url: str | None = None):
        self.url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.client = redis.Redis.from_url(self.url, decode_responses=True)
        try:
            self.client.ping()
        except redis.ConnectionError as exc:
            raise RuntimeError(
                f"Cannot connect to Redis at {self.url}. "
                "Start Redis (e.g. `docker run -d -p 6379:6379 redis:7`) "
                "or update REDIS_URL in .env."
            ) from exc

    def _key(self, user_id: str) -> str:
        return f"user:{user_id}:profile"

    def save(self, user_id: str, facts: dict[str, str]) -> dict[str, str]:
        """Upsert fact(s) for a user. Returns the facts that were written.

        Each value is stored as JSON {value, updated_at}. Overwrite semantics:
        calling save with the same key updates the value and timestamp.
        """
        if not facts:
            return {}
        now = datetime.now(timezone.utc).isoformat()
        payload = {
            key: json.dumps({"value": value, "updated_at": now})
            for key, value in facts.items()
            if value is not None and value != ""
        }
        if payload:
            self.client.hset(self._key(user_id), mapping=payload)
        return {k: json.loads(v)["value"] for k, v in payload.items()}

    def retrieve(self, user_id: str) -> dict[str, dict]:
        """Return {fact_key: {value, updated_at}} for the user (empty if none)."""
        raw = self.client.hgetall(self._key(user_id))
        if not raw:
            return {}
        result: dict[str, dict] = {}
        for key, value in raw.items():
            try:
                result[key] = json.loads(value)
            except json.JSONDecodeError:
                result[key] = {"value": value, "updated_at": None}
        return result

    def retrieve_values(self, user_id: str) -> dict[str, str]:
        """Convenience: return just {fact_key: value}."""
        return {k: v["value"] for k, v in self.retrieve(user_id).items()}

    def delete(self, user_id: str) -> int:
        return int(self.client.delete(self._key(user_id)))

    def delete_fact(self, user_id: str, fact_key: str) -> int:
        return int(self.client.hdel(self._key(user_id), fact_key))
