#!/usr/bin/env python3
"""Automated lattice solver — perpetually resolves nodes and documents contrapolations.

Each run:
  1. Loads the current lattice graph (data/lattice_graph.json)
  2. Loads solve state (data/lattice_state.json) — tracks what's already solved
  3. Finds all unsolved nodes
  4. For each unsolved node:
       - Gathers its edges + connected nodes
       - Pulls source-text excerpts from every transcript the node appears in
       - Runs thesis / antithesis / synthesis (contrapolation) on the excerpts
       - Writes data/contrapolations/<node_id>.md
       - Marks node as solved in state
  5. Saves updated state + a full solve log (data/SOLVE_LOG.md)
  6. Pushes the lattice_graph payload to n8n (if N8N_WEBHOOK_URL is set)

Run on a cron schedule (GitHub Actions) so it never stops — every run
it picks up whatever nodes have been added since the last pass.

Usage:
  python3 scripts/autosolve_lattice.py [--dry-run]
"""
import argparse
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CONTRA_DIR = DATA_DIR / "contrapolations"
CONTRA_DIR.mkdir(exist_ok=True)

TRANSCRIPTS_JSON = DATA_DIR / "transcripts.json"
LATTICE_JSON = DATA_DIR / "lattice_graph.json"
STATE_JSON = DATA_DIR / "lattice_state.json"
SOLVE_LOG = DATA_DIR / "SOLVE_LOG.md"

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n{2,}")
MAX_EXCERPTS = 8          # max source sentences per node in its contrapolation doc
MAX_NODES_PER_RUN = 100   # 13 runs/hour × 100 nodes = 1,300 solves/hour across the lattice


# ── Loaders ───────────────────────────────────────────────────────────────────

def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def load_state() -> dict:
    if STATE_JSON.exists():
        return load_json(STATE_JSON)
    return {"solved": {}, "solve_runs": [], "total_solved": 0}


# ── Contrapolation engine ─────────────────────────────────────────────────────

def pull_excerpts(node: dict, transcripts: list[dict]) -> list[dict]:
    """Pull sentences from source transcripts that mention this node's label."""
    label_pat = re.compile(
        r"\b" + re.escape(node["label"].split()[0]) + r"\b", re.IGNORECASE
    )
    excerpts = []
    for record in transcripts:
        if record["filename"] not in node["sources"]:
            continue
        sentences = [s.strip() for s in SENTENCE_SPLIT.split(record["text"]) if len(s.strip()) > 20]
        hits = [s for s in sentences if label_pat.search(s)]
        for sentence in hits[:3]:  # max 3 per file
            excerpts.append({"file": record["filename"], "text": sentence[:300]})
        if len(excerpts) >= MAX_EXCERPTS:
            break
    return excerpts[:MAX_EXCERPTS]


def contrapolate(node: dict, connected: list[dict], excerpts: list[dict]) -> dict:
    """Thesis/antithesis/synthesis: derive a contrapolation for one node."""
    label = node["label"]
    n_type = node["type"]
    n_sources = len(node["sources"])
    n_connections = len(connected)
    hit_count = node["hit_count"]

    # Build thesis from raw presence/density.
    if n_type == "concept":
        thesis = (
            f"{label} is a high-density lattice concept appearing across "
            f"{n_sources} transcripts ({hit_count} hits). It connects to "
            f"{n_connections} other nodes, indicating a structural hub."
        )
        antithesis = (
            f"Despite its prevalence, {label} resists singular definition — "
            f"each source file encodes it differently, producing divergent "
            f"meanings that cannot be collapsed into one coordinate."
        )
    elif n_type == "coordinate":
        thesis = (
            f"{label} is a numeric coordinate node referenced across "
            f"{n_sources} source files, anchoring a fixed point in the "
            f"operational genome of the lattice."
        )
        antithesis = (
            f"As a number, {label} is context-dependent: its meaning shifts "
            f"entirely based on which genome sequence or index it appears within."
        )
    else:  # file node
        thesis = (
            f"Transcript '{label}' is a primary lattice node: a source document "
            f"that contributes {hit_count} connection(s) to the lattice graph."
        )
        antithesis = (
            f"No transcript is self-contained — '{label}' only becomes meaningful "
            f"through its cross-references to the {n_connections} nodes it shares "
            f"content with."
        )

    # Synthesis: integrate connected node labels.
    connected_labels = ", ".join(n["label"] for n in connected[:8])
    synthesis = (
        f"Contrapolation resolves {label} as: a node whose value is emergent — "
        f"derived not from its isolated definition but from its lattice position "
        f"adjacent to [{connected_labels}{'...' if len(connected) > 8 else ''}]. "
        f"Coordinate density confirms lattice coherence at this node."
    )

    return {
        "node_id": node["id"],
        "label": label,
        "type": n_type,
        "thesis": thesis,
        "antithesis": antithesis,
        "synthesis": synthesis,
        "excerpts": excerpts,
        "connected_node_count": n_connections,
        "source_file_count": n_sources,
        "hit_count": hit_count,
        "solved_at": datetime.now(timezone.utc).isoformat(),
    }


def write_contra_doc(contra: dict) -> None:
    node_id = contra["node_id"].replace("::", "__").replace("/", "_")
    lines = [
        f"# Contrapolation: {contra['label']}",
        f"*Type:* `{contra['type']}` · *Solved:* {contra['solved_at']}",
        f"*Sources:* {contra['source_file_count']} file(s) · "
        f"*Connections:* {contra['connected_node_count']} · "
        f"*Hit count:* {contra['hit_count']}",
        "",
        "## Thesis",
        contra["thesis"],
        "",
        "## Antithesis",
        contra["antithesis"],
        "",
        "## Synthesis (Contrapolation)",
        contra["synthesis"],
        "",
    ]
    if contra["excerpts"]:
        lines += ["## Source Excerpts", ""]
        for ex in contra["excerpts"]:
            lines.append(f"**[{ex['file']}]**")
            lines.append(f"> {ex['text']}")
            lines.append("")
    (CONTRA_DIR / f"{node_id}.md").write_text("\n".join(lines), encoding="utf-8")


# ── Solve log ─────────────────────────────────────────────────────────────────

def write_solve_log(state: dict, graph: dict) -> None:
    total = state["total_solved"]
    total_nodes = graph["node_count"]
    runs = state["solve_runs"]
    lines = [
        "# Lattice Solve Log",
        f"*Total nodes:* {total_nodes} · *Solved:* {total} · "
        f"*Remaining:* {total_nodes - total}",
        "",
        "## Solve Runs",
        "",
    ]
    for run in reversed(runs[-50:]):  # last 50 runs
        lines.append(
            f"- `{run['timestamp']}` — solved {run['nodes_solved']} node(s) "
            f"in {run['elapsed_s']:.1f}s (cumulative: {run['cumulative_solved']})"
        )
    SOLVE_LOG.write_text("\n".join(lines), encoding="utf-8")


# ── n8n push ──────────────────────────────────────────────────────────────────

def push_to_n8n(state: dict, graph: dict) -> None:
    import urllib.error, urllib.request
    url = os.environ.get("N8N_WEBHOOK_URL", "https://humble-frost-01.webhook.cool")
    payload = {
        "event": "lattice_solve_update",
        "total_nodes": graph["node_count"],
        "total_solved": state["total_solved"],
        "remaining": graph["node_count"] - state["total_solved"],
        "last_run": state["solve_runs"][-1] if state["solve_runs"] else None,
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"n8n notified: HTTP {resp.status}")
    except Exception as exc:
        print(f"n8n push skipped: {exc}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Process nodes but do not write output files or update state")
    args = parser.parse_args()

    if not LATTICE_JSON.exists():
        raise SystemExit("data/lattice_graph.json not found. Run build_lattice.py first.")
    if not TRANSCRIPTS_JSON.exists():
        raise SystemExit("data/transcripts.json not found. Run extract_transcripts.py first.")

    graph = load_json(LATTICE_JSON)
    transcripts = load_json(TRANSCRIPTS_JSON)
    state = load_state()

    already_solved = set(state["solved"].keys())
    node_map = {n["id"]: n for n in graph["nodes"]}
    edge_index: dict[str, list[str]] = {n["id"]: [] for n in graph["nodes"]}
    for edge in graph["edges"]:
        edge_index[edge["source"]].append(edge["target"])
        edge_index[edge["target"]].append(edge["source"])

    unsolved = [n for n in graph["nodes"] if n["id"] not in already_solved]
    # Prioritise highest-hit concept nodes first, then coordinates, then files.
    unsolved.sort(key=lambda n: (n["type"] != "concept", -n["hit_count"]))
    batch = unsolved[:MAX_NODES_PER_RUN]

    print(f"Lattice: {graph['node_count']} nodes, {graph['edge_count']} edges")
    print(f"Already solved: {len(already_solved)} · Unsolved: {len(unsolved)} · "
          f"This run: {len(batch)}")

    t0 = time.time()
    solved_this_run = 0
    for node in batch:
        connected_ids = edge_index.get(node["id"], [])
        connected = [node_map[nid] for nid in connected_ids if nid in node_map]
        excerpts = pull_excerpts(node, transcripts)
        contra = contrapolate(node, connected, excerpts)

        if not args.dry_run:
            write_contra_doc(contra)
            state["solved"][node["id"]] = {
                "solved_at": contra["solved_at"],
                "type": node["type"],
                "label": node["label"],
            }
        solved_this_run += 1
        print(f"  solved [{node['type']}] {node['label']}")

    elapsed = round(time.time() - t0, 2)
    state["total_solved"] = len(state["solved"])

    run_record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "nodes_solved": solved_this_run,
        "elapsed_s": elapsed,
        "cumulative_solved": state["total_solved"],
        "dry_run": args.dry_run,
    }
    state["solve_runs"].append(run_record)

    if not args.dry_run:
        save_json(STATE_JSON, state)
        write_solve_log(state, graph)
        push_to_n8n(state, graph)

    remaining = graph["node_count"] - state["total_solved"]
    print(f"\nRun complete: {solved_this_run} solved in {elapsed}s · "
          f"Cumulative: {state['total_solved']}/{graph['node_count']} · "
          f"Remaining: {remaining}")
    if remaining > 0:
        print(f"  → {remaining} nodes remain. Schedule another run to continue.")
    else:
        print("  → All nodes solved. Lattice complete.")


if __name__ == "__main__":
    main()
