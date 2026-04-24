"""Prompt for extracting user profile facts from a conversation turn.

Returns a flat JSON dict {fact_key: value} for facts explicitly stated by the user.
If the user corrects a previous fact, emit the NEW value (overwrite semantics).
"""
from __future__ import annotations

EXTRACTOR_SYSTEM = """You extract durable personal facts about the user from their message.

Rules:
- Extract ONLY explicit, long-lived personal facts (name, job, allergies, preferences, location).
- Do NOT extract ephemeral context (mood, current task).
- If the user corrects a fact ("actually, I'm allergic to soy, not milk"), emit the NEW fact.
- Normalize keys to snake_case English: name, job, allergy, location, language_preference, dietary_preference, etc.
- Normalize values to their primary form (e.g., "I love coffee" -> preference_drink: "coffee").
- If no facts, return {}.

Respond with ONLY a JSON object. Example: {"name": "Linh", "allergy": "đậu nành"}"""


def extractor_user_prompt(user_message: str) -> str:
    return f"User said: {user_message}\n\nFacts (JSON):"
