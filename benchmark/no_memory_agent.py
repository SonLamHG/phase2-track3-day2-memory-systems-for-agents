"""Baseline agent: only a short-term conversation buffer, no retrieval stack.

Used as the comparison point for the with-memory agent in the benchmark.
"""
from __future__ import annotations

import os

from langchain_openai import ChatOpenAI

from graph.tokens import count_tokens
from memory import ShortTermMemory


_BASELINE_SYSTEM = (
    "You are a helpful assistant. Use only the recent conversation below. "
    "You do not have any long-term memory about the user."
)


class NoMemoryAgent:
    def __init__(self, max_messages: int = 10):
        self.short_term = ShortTermMemory(max_messages=max_messages)
        self.client = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.2,
        )

    def reset(self) -> None:
        self.short_term.clear()

    def turn(self, user_message: str) -> dict:
        recent = self.short_term.retrieve()
        history_str = "\n".join(f"{m.role}: {m.content}" for m in recent) or "(none)"
        prompt = f"{_BASELINE_SYSTEM}\n\n[RECENT CONVERSATION]\n{history_str}"

        tokens = {
            "system": count_tokens(_BASELINE_SYSTEM),
            "recent": count_tokens(history_str),
            "query": count_tokens(user_message),
        }
        tokens["total"] = sum(tokens.values())

        resp = self.client.invoke(
            [
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_message},
            ]
        )
        self.short_term.save("user", user_message)
        self.short_term.save("assistant", resp.content)

        return {
            "response": resp.content,
            "tokens_used": tokens,
            "full_prompt": prompt,
        }
