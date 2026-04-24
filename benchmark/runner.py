"""Run the benchmark suite and generate BENCHMARK.md.

For each conversation:
  1. Reset user memory (profile + episodic + short-term).
  2. Run setup turns through the agent (populates memory).
  3. Run the test query.
  4. Score pass/fail, record intent correctness and token breakdown.

Usage:
  python -m benchmark.runner              # all conversations
  python -m benchmark.runner --only 3     # single conversation (rubric allergy test)
  python -m benchmark.runner --skip-no-memory  # only run with-memory
"""
from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()

from benchmark.conversations import CONVERSATIONS
from benchmark.no_memory_agent import NoMemoryAgent
from graph.build import build_agent


@dataclass
class TurnResult:
    query: str
    response: str
    intent: dict = field(default_factory=dict)
    tokens: dict = field(default_factory=dict)
    retrieved_profile: dict = field(default_factory=dict)
    retrieved_episodes: list = field(default_factory=list)
    retrieved_semantic: list = field(default_factory=list)
    trim_log: list = field(default_factory=list)


@dataclass
class ConversationResult:
    conv: dict
    with_memory_turns: list[TurnResult] = field(default_factory=list)
    no_memory_turns: list[TurnResult] = field(default_factory=list)
    passed_with: bool = False
    passed_no: bool = False
    intent_correct: bool = False


def _check_pass(response: str, conv: dict) -> bool:
    text = response.lower()
    for needle in conv.get("expected_contains", []):
        if needle.lower() not in text:
            return False
    any_of = conv.get("expected_contains_any")
    if any_of and not any(n.lower() in text for n in any_of):
        return False
    for forbidden in conv.get("expected_absent", []):
        if forbidden.lower() in text:
            return False
    return True


def _intent_correct(actual: dict, expected: dict) -> bool:
    """Expected keys that are True must be True in actual. Extras allowed."""
    for key, value in expected.items():
        if value and not actual.get(key):
            return False
    return True


def run_with_memory(conv: dict, agent, short_term, profile_mem, episodic_mem) -> list[TurnResult]:
    user_id = conv["user_id"]
    profile_mem.delete(user_id)
    episodic_mem.clear(user_id)
    short_term.clear()

    turns: list[TurnResult] = []
    budget = int(os.getenv("MEMORY_BUDGET_TOKENS", "1500"))

    all_turns = list(conv["setup_turns"]) + [conv["test_query"]]
    for query in all_turns:
        state = {
            "user_id": user_id,
            "current_query": query,
            "messages": [{"role": m.role, "content": m.content} for m in short_term.retrieve()],
            "memory_budget": budget,
        }
        result = agent.invoke(state)
        short_term.save("user", query)
        short_term.save("assistant", result["response"])

        turns.append(
            TurnResult(
                query=query,
                response=result["response"],
                intent=result.get("query_intent", {}),
                tokens=result.get("tokens_used", {}),
                retrieved_profile=result.get("user_profile", {}),
                retrieved_episodes=result.get("episodes", []),
                retrieved_semantic=result.get("semantic_hits", []),
                trim_log=result.get("trim_log", []),
            )
        )
    return turns


def run_no_memory(conv: dict) -> list[TurnResult]:
    agent = NoMemoryAgent()
    turns: list[TurnResult] = []
    all_turns = list(conv["setup_turns"]) + [conv["test_query"]]
    for query in all_turns:
        out = agent.turn(query)
        turns.append(TurnResult(query=query, response=out["response"], tokens=out["tokens_used"]))
    return turns


def run_all(only: int | None, skip_no_memory: bool) -> list[ConversationResult]:
    print("Building with-memory agent...")
    agent, short_term, profile_mem, episodic_mem, _ = build_agent()

    results: list[ConversationResult] = []
    for conv in CONVERSATIONS:
        if only is not None and conv["id"] != only:
            continue
        print(f"\n=== Conv #{conv['id']} [{conv['group']}] {conv['title']} ===")

        with_turns = run_with_memory(conv, agent, short_term, profile_mem, episodic_mem)
        no_turns: list[TurnResult] = []
        if not skip_no_memory:
            no_turns = run_no_memory(conv)

        passed_with = _check_pass(with_turns[-1].response, conv)
        passed_no = _check_pass(no_turns[-1].response, conv) if no_turns else False
        intent_ok = _intent_correct(with_turns[-1].intent, conv.get("expected_intent", {}))

        print(f"  with-memory: {'PASS' if passed_with else 'FAIL'}")
        if not skip_no_memory:
            print(f"  no-memory:   {'PASS' if passed_no else 'FAIL'}")
        print(f"  intent correct: {intent_ok}")

        results.append(
            ConversationResult(
                conv=conv,
                with_memory_turns=with_turns,
                no_memory_turns=no_turns,
                passed_with=passed_with,
                passed_no=passed_no,
                intent_correct=intent_ok,
            )
        )
    return results


def _summary_row(r: ConversationResult) -> str:
    conv = r.conv
    with_resp = r.with_memory_turns[-1].response.replace("\n", " ")[:80] if r.with_memory_turns else ""
    no_resp = r.no_memory_turns[-1].response.replace("\n", " ")[:80] if r.no_memory_turns else "(skipped)"
    status = "Pass" if r.passed_with else "Fail"
    return f"| {conv['id']} | {conv['group']} | {conv['title']} | {no_resp} | {with_resp} | {status} |"


def _hit_rate_table(results: list[ConversationResult]) -> str:
    # Count intent calls per backend, and count correct calls (matched expectation where set).
    calls = {"use_profile": 0, "use_episodic": 0, "use_semantic": 0}
    correct = {"use_profile": 0, "use_episodic": 0, "use_semantic": 0}
    expected_totals = {"use_profile": 0, "use_episodic": 0, "use_semantic": 0}

    for r in results:
        actual = r.with_memory_turns[-1].intent if r.with_memory_turns else {}
        expected = r.conv.get("expected_intent", {})
        for key in calls:
            if actual.get(key):
                calls[key] += 1
            if expected.get(key):
                expected_totals[key] += 1
                if actual.get(key):
                    correct[key] += 1

    lines = ["| Backend | Router calls | Correct routes | Expected total | Hit rate |",
             "|---------|--------------|----------------|----------------|----------|"]
    for key in calls:
        name = key.replace("use_", "")
        total = expected_totals[key]
        hit = f"{correct[key]}/{total}" if total else "n/a"
        rate = f"{correct[key] / total:.0%}" if total else "-"
        lines.append(f"| {name} | {calls[key]} | {correct[key]} | {total} | {rate} |")
    return "\n".join(lines)


def _token_breakdown_table(results: list[ConversationResult]) -> str:
    sums: dict[str, int] = {}
    n = 0
    for r in results:
        if not r.with_memory_turns:
            continue
        for t in r.with_memory_turns:
            n += 1
            for k, v in (t.tokens or {}).items():
                sums[k] = sums.get(k, 0) + v
    if n == 0:
        return "(no data)"

    avg = {k: v / n for k, v in sums.items()}
    total = avg.get("total", sum(v for k, v in avg.items() if k != "total")) or 1
    lines = ["| Section | Avg tokens | % of prompt |", "|---------|------------|-------------|"]
    order = ["system", "profile", "episodic", "semantic", "recent", "query", "total"]
    for k in order:
        if k not in avg:
            continue
        pct = "100%" if k == "total" else f"{avg[k] / total:.0%}"
        lines.append(f"| {k} | {avg[k]:.0f} | {pct} |")
    return "\n".join(lines)


def _transcript(r: ConversationResult) -> str:
    lines = [f"### Conversation #{r.conv['id']} — {r.conv['title']}", ""]
    lines.append(f"**Group:** {r.conv['group']}   **User ID:** `{r.conv['user_id']}`")
    lines.append("")
    lines.append("#### Turn-by-turn (with-memory)")
    lines.append("")
    for i, t in enumerate(r.with_memory_turns):
        is_test = i == len(r.with_memory_turns) - 1
        tag = " **(test)**" if is_test else ""
        lines.append(f"- **User{tag}:** {t.query}")
        lines.append(f"- **Agent:** {t.response}")
        if is_test:
            lines.append("")
            lines.append(f"  - Router intent: `{t.intent}`")
            lines.append(f"  - Profile retrieved: `{t.retrieved_profile}`")
            lines.append(f"  - Episodic retrieved: `{len(t.retrieved_episodes)}` items")
            lines.append(
                f"  - Semantic retrieved: `{[h.get('id') for h in t.retrieved_semantic]}`"
            )
            lines.append(f"  - Tokens: `{t.tokens}`")
            if t.trim_log:
                lines.append(f"  - Trim log: `{t.trim_log}`")
        lines.append("")

    if r.no_memory_turns:
        lines.append("#### No-memory baseline (test turn only)")
        lines.append(f"- **User:** {r.no_memory_turns[-1].query}")
        lines.append(f"- **Baseline:** {r.no_memory_turns[-1].response}")
        lines.append("")

    lines.append(f"**With-memory pass:** {r.passed_with}   **No-memory pass:** {r.passed_no}   **Intent correct:** {r.intent_correct}")
    lines.append("")
    lines.append("---")
    return "\n".join(lines)


def generate_report(results: list[ConversationResult], output_path: str) -> None:
    with_pass = sum(1 for r in results if r.passed_with)
    no_pass = sum(1 for r in results if r.passed_no)
    intent_pass = sum(1 for r in results if r.intent_correct)
    total = len(results)

    out: list[str] = []
    out.append("# Benchmark Report — Multi-Memory Agent")
    out.append("")
    out.append(f"**Model:** `{os.getenv('OPENAI_MODEL', 'gpt-4o-mini')}`")
    out.append(f"**Memory budget:** {os.getenv('MEMORY_BUDGET_TOKENS', '1500')} tokens")
    out.append(f"**Conversations:** {total} (5 test groups × 2 conversations each)")
    out.append("")
    out.append("## Summary")
    out.append("")
    out.append(f"- With-memory pass rate: **{with_pass}/{total}** ({with_pass / total:.0%})" if total else "")
    out.append(f"- No-memory pass rate: **{no_pass}/{total}** ({no_pass / total:.0%})" if total else "")
    out.append(f"- Router intent correctness: **{intent_pass}/{total}** ({intent_pass / total:.0%})" if total else "")
    out.append("")
    out.append("## Per-conversation comparison")
    out.append("")
    out.append("| # | Group | Scenario | No-memory | With-memory | Pass (with) |")
    out.append("|---|-------|----------|-----------|-------------|-------------|")
    for r in results:
        out.append(_summary_row(r))
    out.append("")
    out.append("## Memory hit rate")
    out.append("")
    out.append(_hit_rate_table(results))
    out.append("")
    out.append("## Token budget breakdown (average across all with-memory turns)")
    out.append("")
    out.append(_token_breakdown_table(results))
    out.append("")
    out.append("## Per-conversation transcripts")
    out.append("")
    for r in results:
        out.append(_transcript(r))

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"\nReport written to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", type=int, default=None, help="Run a single conversation by id")
    parser.add_argument("--skip-no-memory", action="store_true", help="Only run the with-memory agent")
    parser.add_argument("--output", default="benchmark/BENCHMARK.md")
    args = parser.parse_args()

    results = run_all(args.only, args.skip_no_memory)
    generate_report(results, args.output)


if __name__ == "__main__":
    main()
