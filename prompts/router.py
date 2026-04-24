"""Prompt for the intent classifier (memory router).

Returns strict JSON indicating which memory backends should be queried.
"""
from __future__ import annotations

ROUTER_SYSTEM = """You are a memory router. Classify the user's query to decide which memory backends to query.

Decide three booleans:
- use_profile: true if the query refers to personal facts about the user (name, preferences, allergies, settings, history of the user themselves).
- use_episodic: true if the query references a past interaction ("last time", "yesterday you said", "how did we solve X before").
- use_semantic: true if the query asks for general factual knowledge (geography, science, how-to, definitions).

A query can have multiple trues. Default to false if uncertain.
Respond with ONLY a JSON object, no prose. Example: {"use_profile": true, "use_episodic": false, "use_semantic": false}"""


def router_user_prompt(query: str) -> str:
    return f"Query: {query}\n\nJSON:"
