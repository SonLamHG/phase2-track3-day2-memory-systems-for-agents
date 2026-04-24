"""Wire memory backends + nodes into a LangGraph StateGraph."""
from __future__ import annotations

import os

from langgraph.graph import END, StateGraph

from graph.llm import call_llm
from graph.retrieve import make_retrieve_memory
from graph.router import classify_intent
from graph.save import make_save_memory
from graph.state import MemoryState
from graph.trimmer import trim_context
from memory import EpisodicMemory, LongTermProfile, SemanticMemory, ShortTermMemory


def build_agent():
    """Return (compiled_graph, short_term_memory, profile, episodic, semantic).

    The short-term buffer lives outside the graph (per-session state the caller
    owns) — the caller injects `messages` into state on each invocation.
    """
    profile_mem = LongTermProfile()
    episodic_mem = EpisodicMemory()
    semantic_mem = SemanticMemory()
    short_term = ShortTermMemory(max_messages=int(os.getenv("SHORT_TERM_MAX_MESSAGES", "10")))

    retrieve = make_retrieve_memory(profile_mem, episodic_mem, semantic_mem)
    save = make_save_memory(profile_mem, episodic_mem)

    graph = StateGraph(MemoryState)
    graph.add_node("classify", classify_intent)
    graph.add_node("retrieve", retrieve)
    graph.add_node("trim", trim_context)
    graph.add_node("generate", call_llm)
    graph.add_node("save", save)

    graph.set_entry_point("classify")
    graph.add_edge("classify", "retrieve")
    graph.add_edge("retrieve", "trim")
    graph.add_edge("trim", "generate")
    graph.add_edge("generate", "save")
    graph.add_edge("save", END)

    compiled = graph.compile()
    return compiled, short_term, profile_mem, episodic_mem, semantic_mem
