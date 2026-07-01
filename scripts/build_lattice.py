#!/usr/bin/env python3
"""Build a lattice graph structure from all transcript content.

Extracts every lattice-related passage from data/transcripts.json,
identifies named nodes (coordinates, concepts, themes), maps edges
between nodes that co-occur in the same source file, and writes:

  data/lattice_graph.json   — nodes + edges (importable into n8n / vis tools)
  data/LATTICE.md           — human-readable lattice index

Re-invokable any time transcripts.json is refreshed.

Usage:
  python3 scripts/build_lattice.py
"""
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
TRANSCRIPTS_JSON = DATA_DIR / "transcripts.json"

# ── Pattern matchers ──────────────────────────────────────────────────────────

LATTICE_LINE = re.compile(r"\blattice\b", re.IGNORECASE)

# Numbered coordinates like 001, 393, 396, etc.
COORD_NUM = re.compile(r"\b(\d{3})\b")

# Named concept nodes we want to track as lattice nodes.
CONCEPT_PATTERNS: dict[str, re.Pattern] = {
    "genome":          re.compile(r"\b(genome|genomic)\b", re.IGNORECASE),
    "peak":            re.compile(r"\bpeak\b", re.IGNORECASE),
    "contrapolation":  re.compile(r"\bcontrapolat\w*\b", re.IGNORECASE),
    "coordinate":      re.compile(r"\bcoordinate[s]?\b", re.IGNORECASE),
    "terminal":        re.compile(r"\bterminal[\s\-]?[a-z0-9]*\b", re.IGNORECASE),
    "bloodline":       re.compile(r"\bbloodline[s]?\b", re.IGNORECASE),
    "eschatology":     re.compile(r"\beschatolog\w*\b", re.IGNORECASE),
    "node":            re.compile(r"\bnode[s]?\b", re.IGNORECASE),
    "star_chart":      re.compile(r"\bstar[\s\-]chart\b", re.IGNORECASE),
    "nil":             re.compile(r"\bNIL\b"),
    "hollow_ridge":    re.compile(r"\bhollow[\s\-]ridge\b", re.IGNORECASE),
    "totem":           re.compile(r"\btotem\b", re.IGNORECASE),
    "synthesis":       re.compile(r"\bsynthesis\b", re.IGNORECASE),
    "topology":        re.compile(r"\btopolog\w*\b", re.IGNORECASE),
    "polytope":        re.compile(r"\bpolytope\b", re.IGNORECASE),
    "exe":             re.compile(r"\b\.?exe\b", re.IGNORECASE),
    "worldbuilding":   re.compile(r"\bworld[\s\-]?building\b", re.IGNORECASE),
    "pipeline":        re.compile(r"\bpipeline\b", re.IGNORECASE),
    "automation":      re.compile(r"\bautomat\w*\b", re.IGNORECASE),
}


def load_transcripts() -> list[dict]:
    if not TRANSCRIPTS_JSON.exists():
        raise SystemExit(f"{TRANSCRIPTS_JSON} not found. Run extract_transcripts.py first.")
    return json.loads(TRANSCRIPTS_JSON.read_text(encoding="utf-8"))


def build_lattice(records: list[dict]) -> dict:
    # node_id -> {label, type, sources: [filenames], hit_count}
    nodes: dict[str, dict] = {}
    # (node_a, node_b) -> {weight, sources}
    edges: dict[tuple, dict] = {}

    def add_node(node_id: str, label: str, node_type: str, source: str) -> None:
        if node_id not in nodes:
            nodes[node_id] = {"id": node_id, "label": label, "type": node_type,
                              "sources": [], "hit_count": 0}
        if source not in nodes[node_id]["sources"]:
            nodes[node_id]["sources"].append(source)
        nodes[node_id]["hit_count"] += 1

    def add_edge(a: str, b: str, source: str) -> None:
        if a == b:
            return
        key = (min(a, b), max(a, b))
        if key not in edges:
            edges[key] = {"source": key[0], "target": key[1], "weight": 0, "sources": []}
        edges[key]["weight"] += 1
        if source not in edges[key]["sources"]:
            edges[key]["sources"].append(source)

    for record in records:
        filename = record["filename"]
        text = record["text"]

        # Only process files that mention lattice at all.
        if not LATTICE_LINE.search(text):
            continue

        # Extract concept nodes present in this file.
        file_concepts: list[str] = []
        for concept_id, pattern in CONCEPT_PATTERNS.items():
            if pattern.search(text):
                add_node(concept_id, concept_id.replace("_", " ").title(),
                         "concept", filename)
                file_concepts.append(concept_id)

        # Extract numeric coordinate nodes (e.g. 001, 396).
        coord_hits = set(COORD_NUM.findall(text))
        coord_ids = []
        for coord in coord_hits:
            node_id = f"coord_{coord}"
            add_node(node_id, f"Coordinate {coord}", "coordinate", filename)
            coord_ids.append(node_id)

        # Add file node itself.
        file_node_id = f"file::{filename}"
        add_node(file_node_id, filename, "file", filename)

        # Edges: file → each concept/coordinate it contains.
        all_nodes_in_file = file_concepts + coord_ids
        for nid in all_nodes_in_file:
            add_edge(file_node_id, nid, filename)

        # Edges: concept ↔ concept co-occurrence within the same file.
        for i, a in enumerate(file_concepts):
            for b in file_concepts[i + 1:]:
                add_edge(a, b, filename)

        # Edges: concept ↔ coordinate co-occurrence (top coords only to avoid explosion).
        for concept_id in file_concepts:
            for coord_id in coord_ids[:20]:
                add_edge(concept_id, coord_id, filename)

    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": list(nodes.values()),
        "edges": [
            {"source": e["source"], "target": e["target"],
             "weight": e["weight"], "sources": e["sources"]}
            for e in edges.values()
        ],
    }


def write_outputs(graph: dict) -> None:
    (DATA_DIR / "lattice_graph.json").write_text(
        json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Separate nodes by type for the markdown index.
    by_type: dict[str, list] = defaultdict(list)
    for node in graph["nodes"]:
        by_type[node["type"]].append(node)

    lines = ["# Hollowridge Lattice Structure", ""]
    lines.append(f"**{graph['node_count']} nodes · {graph['edge_count']} edges**")
    lines.append("")

    # Concept nodes — most connected first.
    concept_nodes = sorted(by_type["concept"], key=lambda n: -n["hit_count"])
    lines.append("## Concept Nodes")
    for node in concept_nodes:
        lines.append(
            f"- **{node['label']}** — {node['hit_count']} hits across "
            f"{len(node['sources'])} file(s)"
        )
    lines.append("")

    # Coordinate nodes — sorted numerically.
    coord_nodes = sorted(
        by_type["coordinate"],
        key=lambda n: int(n["id"].split("_")[1]),
    )
    lines.append("## Coordinate Nodes")
    lines.append(f"({len(coord_nodes)} unique numeric coordinates detected)")
    lines.append("")
    for node in coord_nodes[:50]:
        lines.append(f"- {node['label']} — found in {len(node['sources'])} file(s)")
    if len(coord_nodes) > 50:
        lines.append(f"- … and {len(coord_nodes) - 50} more")
    lines.append("")

    # File nodes — most connected first.
    file_nodes = sorted(by_type["file"], key=lambda n: -n["hit_count"])
    lines.append("## File Nodes (lattice-active transcripts)")
    for node in file_nodes:
        lines.append(f"- {node['label']} (connections: {node['hit_count']})")
    lines.append("")

    # Top edges by weight.
    top_edges = sorted(graph["edges"], key=lambda e: -e["weight"])[:30]
    lines.append("## Strongest Lattice Connections (top 30 edges by weight)")
    for edge in top_edges:
        lines.append(
            f"- `{edge['source']}` ↔ `{edge['target']}` "
            f"(weight {edge['weight']}, {len(edge['sources'])} file(s))"
        )
    lines.append("")

    (DATA_DIR / "LATTICE.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    records = load_transcripts()
    graph = build_lattice(records)
    write_outputs(graph)
    print(
        f"Lattice built: {graph['node_count']} nodes, {graph['edge_count']} edges\n"
        f"  -> {DATA_DIR / 'lattice_graph.json'}\n"
        f"  -> {DATA_DIR / 'LATTICE.md'}"
    )


if __name__ == "__main__":
    main()
