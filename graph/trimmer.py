"""trim_context node — 4-level priority eviction.

Eviction order when retrieved memory exceeds budget:
  L4 (first): semantic hits with worst relevance (highest distance)
  L3:        oldest episodic entries (keep at least 1)
  L2:        non-core profile fields (keep core: name, allergy, critical)
  L1 (never): system prompt + core profile fields

Critical profile keys are kept as long as budget allows; system prompt tokens
are counted but never removed (they belong to the agent's identity).
"""
from __future__ import annotations

from graph.state import MemoryState
from graph.tokens import count_tokens
from prompts.system import render_episodic, render_profile, render_semantic


CORE_PROFILE_KEYS = {"name", "allergy", "allergies", "dietary_preference", "emergency_contact"}


def _profile_tokens(profile: dict) -> int:
    return count_tokens(render_profile(profile))


def _episodes_tokens(episodes: list[dict]) -> int:
    return count_tokens(render_episodic(episodes))


def _semantic_tokens(hits: list[dict]) -> int:
    return count_tokens(render_semantic(hits))


def trim_context(state: MemoryState) -> MemoryState:
    budget = int(state.get("memory_budget", 1500))
    profile = dict(state.get("user_profile", {}) or {})
    episodes = list(state.get("episodes", []) or [])
    semantic_hits = list(state.get("semantic_hits", []) or [])
    trim_log: list[str] = []

    def total() -> int:
        return _profile_tokens(profile) + _episodes_tokens(episodes) + _semantic_tokens(semantic_hits)

    # L4: semantic hits — evict highest distance first (least relevant)
    while total() > budget and semantic_hits:
        semantic_hits.sort(key=lambda h: h.get("distance") or 0.0, reverse=True)
        evicted = semantic_hits.pop(0)
        trim_log.append(f"L4 evicted semantic hit id={evicted.get('id')}")

    # L3: oldest episodic entries, keep at least the most recent one
    while total() > budget and len(episodes) > 1:
        evicted = episodes.pop()  # retrieve returned most-recent-first, so pop() drops oldest
        trim_log.append(f"L3 evicted episode ts={evicted.get('timestamp', '')[:10]}")

    # L2: non-core profile fields
    while total() > budget:
        removable = [k for k in profile.keys() if k not in CORE_PROFILE_KEYS]
        if not removable:
            break
        key = removable[0]
        del profile[key]
        trim_log.append(f"L2 evicted profile field {key}")

    return {
        **state,
        "user_profile": profile,
        "episodes": episodes,
        "semantic_hits": semantic_hits,
        "trim_log": trim_log,
    }
