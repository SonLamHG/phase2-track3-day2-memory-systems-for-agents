"""retrieve_memory node — gathers memory from the three persistent backends
according to the router's intent decision.

Short-term memory is injected separately in the build step (it's per-session, not retrieved).
"""
from __future__ import annotations

from graph.state import MemoryState
from memory import EpisodicMemory, LongTermProfile, SemanticMemory


def make_retrieve_memory(
    profile_mem: LongTermProfile,
    episodic_mem: EpisodicMemory,
    semantic_mem: SemanticMemory,
    top_k_episodic: int = 3,
    top_k_semantic: int = 3,
):
    def retrieve_memory(state: MemoryState) -> MemoryState:
        user_id = state["user_id"]
        query = state["current_query"]
        intent = state.get("query_intent", {})

        user_profile: dict = {}
        episodes: list[dict] = []
        semantic_hits: list[dict] = []

        if intent.get("use_profile"):
            user_profile = profile_mem.retrieve(user_id)

        if intent.get("use_episodic"):
            episodes = episodic_mem.retrieve(user_id, query=query, limit=top_k_episodic)

        if intent.get("use_semantic"):
            semantic_hits = semantic_mem.retrieve(query, k=top_k_semantic)

        return {
            **state,
            "user_profile": user_profile,
            "episodes": episodes,
            "semantic_hits": semantic_hits,
        }

    return retrieve_memory
