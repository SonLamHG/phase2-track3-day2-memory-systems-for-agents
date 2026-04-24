"""classify_intent node — routes the query to memory backends.

Uses the OpenAI LLM configured via OPENAI_API_KEY. JSON parsing is robust to
minor formatting issues (strips code fences, falls back to rule-based keywords).
"""
from __future__ import annotations

import json
import os
import re

from langchain_openai import ChatOpenAI

from graph.state import MemoryState
from prompts.router import ROUTER_SYSTEM, router_user_prompt


_CLIENT: ChatOpenAI | None = None


def _client() -> ChatOpenAI:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,
        )
    return _CLIENT


def _rule_based_fallback(query: str) -> dict:
    q = query.lower()
    profile_kw = ["tôi", "của tôi", "my ", "i am", "i'm", "mình", "dị ứng", "allergy", "prefer", "favorite"]
    episodic_kw = ["lần trước", "hôm qua", "yesterday", "last time", "trước đây", "đã làm", "we did", "we solved"]
    semantic_kw = ["thủ đô", "capital", "what is", "định nghĩa", "how does", "who is", "population", "dân số"]
    return {
        "use_profile": any(k in q for k in profile_kw),
        "use_episodic": any(k in q for k in episodic_kw),
        "use_semantic": any(k in q for k in semantic_kw),
    }


def _parse_json(text: str) -> dict:
    text = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.+?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    return json.loads(text)


def classify_intent(state: MemoryState) -> MemoryState:
    query = state["current_query"]
    try:
        resp = _client().invoke(
            [
                {"role": "system", "content": ROUTER_SYSTEM},
                {"role": "user", "content": router_user_prompt(query)},
            ]
        )
        data = _parse_json(resp.content)
        intent = {
            "use_profile": bool(data.get("use_profile", False)),
            "use_episodic": bool(data.get("use_episodic", False)),
            "use_semantic": bool(data.get("use_semantic", False)),
        }
    except Exception:
        intent = _rule_based_fallback(query)

    # Profile is cheap and often useful for continuity; retrieve it by default
    # if the query contains any first-person reference.
    if any(w in query.lower() for w in [" tôi", "tôi ", "mình ", " i ", "my ", "i'm", "i am"]):
        intent["use_profile"] = True

    return {**state, "query_intent": intent}
