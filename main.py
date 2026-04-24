"""Interactive CLI demo for the Multi-Memory Agent.

Usage:
  python main.py                       # default user_id=demo
  python main.py --user alice          # named user
  python main.py --user alice --reset  # wipe this user's profile + episodic first
  python main.py --verbose             # show router decision, retrieved memory, prompt

Type '/quit' to exit, '/profile' to print stored profile, '/reset' to wipe user memory.
"""
from __future__ import annotations

import argparse
import os

from dotenv import load_dotenv

load_dotenv()

from graph.build import build_agent


def run(user_id: str, reset: bool, verbose: bool) -> None:
    print("Building agent (Redis + Chroma)...")
    agent, short_term, profile_mem, episodic_mem, _ = build_agent()

    if reset:
        profile_mem.delete(user_id)
        episodic_mem.clear(user_id)
        print(f"Reset memory for user '{user_id}'.")

    print(f"Multi-Memory Agent ready. user_id={user_id}. Type '/quit' to exit.\n")

    while True:
        try:
            query = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not query:
            continue
        if query == "/quit":
            break
        if query == "/profile":
            print(profile_mem.retrieve(user_id))
            continue
        if query == "/reset":
            profile_mem.delete(user_id)
            episodic_mem.clear(user_id)
            short_term.clear()
            print("Reset.")
            continue

        state = {
            "user_id": user_id,
            "current_query": query,
            "messages": [{"role": m.role, "content": m.content} for m in short_term.retrieve()],
            "memory_budget": int(os.getenv("MEMORY_BUDGET_TOKENS", "1500")),
        }
        result = agent.invoke(state)

        short_term.save("user", query)
        short_term.save("assistant", result["response"])

        if verbose:
            print("--- router intent ---", result.get("query_intent"))
            print("--- profile ---", result.get("user_profile"))
            print("--- episodic ---", result.get("episodes"))
            print("--- semantic ---", [h.get("id") for h in result.get("semantic_hits", [])])
            print("--- tokens ---", result.get("tokens_used"))
            print("--- trim log ---", result.get("trim_log"))

        print(f"Agent: {result['response']}\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", default="demo")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()
    run(args.user, args.reset, args.verbose)


if __name__ == "__main__":
    main()
