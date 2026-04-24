"""call_llm node — builds the sectioned prompt, calls OpenAI, records token usage.
"""
from __future__ import annotations

import os

from langchain_openai import ChatOpenAI

from graph.state import MemoryState
from graph.tokens import count_tokens
from prompts.system import (
    SYSTEM_HEADER,
    build_prompt,
    render_episodic,
    render_profile,
    render_recent,
    render_semantic,
)


_CLIENT: ChatOpenAI | None = None


def _client() -> ChatOpenAI:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.2,
        )
    return _CLIENT


def call_llm(state: MemoryState) -> MemoryState:
    profile = state.get("user_profile", {}) or {}
    episodes = state.get("episodes", []) or []
    semantic_hits = state.get("semantic_hits", []) or []
    recent_messages = state.get("messages", []) or []
    query = state["current_query"]

    prompt = build_prompt(
        profile=profile,
        episodes=episodes,
        semantic_hits=semantic_hits,
        recent_messages=recent_messages,
        current_query=query,
    )

    tokens_used = {
        "system": count_tokens(SYSTEM_HEADER),
        "profile": count_tokens(render_profile(profile)),
        "episodic": count_tokens(render_episodic(episodes)),
        "semantic": count_tokens(render_semantic(semantic_hits)),
        "recent": count_tokens(render_recent(recent_messages)),
        "query": count_tokens(query),
    }
    tokens_used["total"] = sum(tokens_used.values())

    resp = _client().invoke(
        [
            {"role": "system", "content": prompt},
            {"role": "user", "content": query},
        ]
    )

    return {
        **state,
        "response": resp.content,
        "tokens_used": tokens_used,
        "full_prompt": prompt,
    }
