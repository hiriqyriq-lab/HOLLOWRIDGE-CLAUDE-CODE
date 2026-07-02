#!/usr/bin/env python3
"""FORGE advisor — runs the FORGE rolodex persona against lattice solve output.

Loads agents/rolodex/FORGE.json, reads the current lattice solve state and
top concept nodes, then calls the Claude API with FORGE's system_prompt to
get a first-principles technical review of the lattice automation progress.

Writes:
  data/FORGE_REVIEW.md   — FORGE's latest advisory output
  data/forge_log.json    — cumulative log of every FORGE run

Usage:
  python3 scripts/forge_advisor.py [--context "optional extra context"]

Requires:
  ANTHROPIC_API_KEY env var (set as GitHub Actions secret: ANTHROPIC_API_KEY)
"""
import argparse
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
AGENTS_DIR = ROOT / "agents" / "rolodex"

FORGE_JSON = AGENTS_DIR / "FORGE.json"
STATE_JSON = DATA_DIR / "lattice_state.json"
LATTICE_JSON = DATA_DIR / "lattice_graph.json"
FORGE_REVIEW_MD = DATA_DIR / "FORGE_REVIEW.md"
FORGE_LOG_JSON = DATA_DIR / "forge_log.json"

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-haiku-4-5-20251001"   # fast + cheap for advisory runs


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def build_context(extra: str = "") -> str:
    state = load_json(STATE_JSON) if STATE_JSON.exists() else {}
    graph = load_json(LATTICE_JSON) if LATTICE_JSON.exists() else {}

    total = graph.get("node_count", "?")
    solved = state.get("total_solved", 0)
    remaining = total - solved if isinstance(total, int) else "?"
    runs = state.get("solve_runs", [])
    last_run = runs[-1] if runs else {}

    top_concepts = sorted(
        [n for n in graph.get("nodes", []) if n["type"] == "concept"],
        key=lambda n: -n["hit_count"]
    )[:10]

    concept_summary = "\n".join(
        f"  - {n['label']}: {n['hit_count']} hits across {len(n['sources'])} files, "
        f"{len([e for e in graph.get('edges', []) if n['id'] in (e['source'], e['target'])])} edges"
        for n in top_concepts
    )

    context = f"""LATTICE AUTOMATION STATUS REPORT
=================================
Total nodes: {total}
Solved: {solved}
Remaining: {remaining}
Total runs completed: {len(runs)}
Last run: solved {last_run.get('nodes_solved', '?')} nodes in {last_run.get('elapsed_s', '?')}s
Schedule: 13 fires/hour via GitHub Actions cron

TOP CONCEPT NODES (by cross-file density):
{concept_summary}

AUTOMATION PIPELINE:
- extract_transcripts.py → cross_reference_workflows.py → peaks_synthesis.py → build_lattice.py → autosolve_lattice.py
- 70 source transcripts, 813 lattice nodes, 6,770 edges
- Contrapolation docs: data/contrapolations/<node>.md (thesis/antithesis/synthesis per node)
- n8n webhook: pushes transcript_index, combined_workflows, combined_peaks, lattice_graph, lattice_solve_update

QUESTION FOR FORGE:
What is the single bottleneck in this lattice automation framework that, if removed, would unlock the most downstream progress for the NIL agency advisory use case?
{('Additional context: ' + extra) if extra else ''}"""
    return context


def call_claude(system_prompt: str, user_message: str, api_key: str) -> str:
    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 512,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}]
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        CLAUDE_API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["content"][0]["text"]
        except urllib.error.HTTPError as exc:
            body_err = exc.read().decode("utf-8", errors="replace")
            print(f"HTTP {exc.code} on attempt {attempt}: {body_err[:200]}")
        except Exception as exc:
            print(f"Error on attempt {attempt}: {exc}")
        if attempt < 3:
            time.sleep(2 ** attempt)
    raise RuntimeError("FORGE call failed after 3 attempts")


def write_review(forge_output: str, context: str, timestamp: str) -> None:
    lines = [
        "# FORGE Advisory Review",
        f"*Run:* {timestamp}",
        "",
        "## Context Submitted",
        "```",
        context,
        "```",
        "",
        "## FORGE Response",
        "",
        forge_output,
        "",
    ]
    FORGE_REVIEW_MD.write_text("\n".join(lines), encoding="utf-8")


def append_log(forge_output: str, context: str, timestamp: str) -> None:
    log = []
    if FORGE_LOG_JSON.exists():
        log = load_json(FORGE_LOG_JSON)
    log.append({
        "timestamp": timestamp,
        "context_summary": context[:400],
        "forge_response": forge_output,
        "council_member": "FORGE",
    })
    FORGE_LOG_JSON.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", default="", help="Extra context to pass to FORGE")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY not set. Add it as a GitHub Actions secret.")

    forge_data = load_json(FORGE_JSON)
    system_prompt = forge_data["rolodex_entry"]["system_prompt"]

    context = build_context(args.context)
    print("Calling FORGE...\n")
    forge_output = call_claude(system_prompt, context, api_key)

    timestamp = datetime.now(timezone.utc).isoformat()
    write_review(forge_output, context, timestamp)
    append_log(forge_output, context, timestamp)

    print("=" * 60)
    print("FORGE:")
    print(forge_output)
    print("=" * 60)
    print(f"\nWritten to {FORGE_REVIEW_MD}")


if __name__ == "__main__":
    main()
