"""Shared state for the memory agent graph.

Matches rubric section 2 expected shape: messages, user_profile, episodes,
semantic_hits, memory_budget.
"""
from __future__ import annotations

from typing import TypedDict


class MemoryState(TypedDict, total=False):
    user_id: str
    current_query: str

    query_intent: dict  # {use_profile, use_episodic, use_semantic}

    messages: list  # [{role, content}]
    user_profile: dict  # from Redis
    episodes: list[dict]  # from episodic JSON
    semantic_hits: list[dict]  # from Chroma

    memory_budget: int
    tokens_used: dict  # per-section breakdown
    trim_log: list[str]

    response: str
    saved_facts: dict
    saved_episode: dict | None
    full_prompt: str
