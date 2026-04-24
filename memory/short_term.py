"""Short-term memory: sliding-window conversation buffer.

Stores the most recent N messages for immediate conversational continuity.
Purely in-process; resets per session.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Message:
    role: Literal["user", "assistant", "system"]
    content: str


@dataclass
class ShortTermMemory:
    max_messages: int = 10
    _buffer: deque[Message] = field(default_factory=deque)

    def save(self, role: str, content: str) -> None:
        self._buffer.append(Message(role=role, content=content))
        while len(self._buffer) > self.max_messages:
            self._buffer.popleft()

    def retrieve(self, n: int | None = None) -> list[Message]:
        messages = list(self._buffer)
        if n is not None:
            messages = messages[-n:]
        return messages

    def clear(self) -> None:
        self._buffer.clear()

    def __len__(self) -> int:
        return len(self._buffer)
