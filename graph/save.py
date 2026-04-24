"""save_memory node — extracts profile facts (LLM) and appends an episodic entry.

Profile writes use overwrite semantics (see LongTermProfile.save), so a later
correction ("actually, soy not milk") replaces the prior value rather than
appending a conflict.
"""
from __future__ import annotations

import json
import os
import re

from langchain_openai import ChatOpenAI

from graph.state import MemoryState
from memory import EpisodicMemory, LongTermProfile
from prompts.extractor import EXTRACTOR_SYSTEM, extractor_user_prompt


_CLIENT: ChatOpenAI | None = None


def _client() -> ChatOpenAI:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,
        )
    return _CLIENT


def _parse_json(text: str) -> dict:
    text = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.+?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def extract_facts(user_message: str) -> dict:
    try:
        resp = _client().invoke(
            [
                {"role": "system", "content": EXTRACTOR_SYSTEM},
                {"role": "user", "content": extractor_user_prompt(user_message)},
            ]
        )
        return _parse_json(resp.content)
    except Exception:
        return {}


def make_save_memory(profile_mem: LongTermProfile, episodic_mem: EpisodicMemory):
    def save_memory(state: MemoryState) -> MemoryState:
        user_id = state["user_id"]
        user_message = state["current_query"]
        response = state.get("response", "")

        facts = extract_facts(user_message)
        saved_facts: dict = {}
        if facts:
            saved_facts = profile_mem.save(user_id, facts)

        saved_episode = episodic_mem.save(
            user_id=user_id,
            task=user_message,
            outcome=response[:500],
            reasoning=f"intent={state.get('query_intent', {})}",
            tags=[k for k, v in (state.get("query_intent") or {}).items() if v],
        )

        return {
            **state,
            "saved_facts": saved_facts,
            "saved_episode": saved_episode,
        }

    return save_memory
