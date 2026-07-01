#!/usr/bin/env python3
"""Push extracted Hollowridge transcript data to an n8n webhook.

Sends three sequential POST requests to the configured webhook URL:
  1. Transcript index  (summary row per file — no raw text, keeps payload small)
  2. Combined workflows (cross-referenced workflow/automation lines by theme)
  3. Combined peaks    (cross-referenced peak sentences by source file)

Re-invokable at any time to refresh n8n with the latest extracted data.

Usage:
  python3 scripts/push_to_n8n.py [--webhook-url URL]

  If --webhook-url is omitted the N8N_WEBHOOK_URL env var is used,
  falling back to the default URL baked in below.
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

DEFAULT_WEBHOOK_URL = "https://humble-frost-01.webhook.cool"


def load(filename: str) -> dict | list:
    path = DATA_DIR / filename
    if not path.exists():
        raise SystemExit(
            f"{path} not found. Run extract_transcripts.py and cross_reference_workflows.py first."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def build_index(records: list[dict]) -> list[dict]:
    return [
        {
            "filename": r["filename"],
            "filetype": r["filetype"],
            "word_count": r["word_count"],
            "workflow_automation_line_count": len(r.get("workflow_automation_lines", [])),
        }
        for r in records
    ]


def post(url: str, payload: dict, label: str) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    for attempt in range(1, 5):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                status = resp.status
                response_body = resp.read().decode("utf-8", errors="replace")[:200]
            print(f"  [{label}] HTTP {status} — {response_body or '(no body)'}")
            return
        except urllib.error.HTTPError as exc:
            print(f"  [{label}] HTTP {exc.code} on attempt {attempt}: {exc.reason}")
        except urllib.error.URLError as exc:
            print(f"  [{label}] Network error on attempt {attempt}: {exc.reason}")
        if attempt < 4:
            wait = 2 ** attempt
            print(f"  Retrying in {wait}s …")
            time.sleep(wait)
    print(f"  [{label}] All retries exhausted — payload NOT delivered.")
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--webhook-url", default=None)
    args = parser.parse_args()

    import os
    url = args.webhook_url or os.environ.get("N8N_WEBHOOK_URL", DEFAULT_WEBHOOK_URL)
    print(f"Pushing to: {url}\n")

    # 1. Transcript index
    records = load("transcripts.json")
    index = build_index(records)
    print(f"Sending transcript index ({len(index)} files) …")
    post(url, {"event": "transcript_index", "file_count": len(index), "transcripts": index}, "transcript_index")

    # 2. Combined workflows
    workflows = load("combined_workflows.json")
    print(f"\nSending combined workflows ({len(workflows)} themes) …")
    post(url, {"event": "combined_workflows", "themes": workflows}, "combined_workflows")

    # 3. Combined peaks
    peaks = load("combined_peaks.json")
    print(f"\nSending combined peaks ({peaks.get('file_count', '?')} files, {peaks.get('sentence_count', '?')} sentences) …")
    post(url, {"event": "combined_peaks", **peaks}, "combined_peaks")

    # 4. Lattice graph
    lattice = load("lattice_graph.json")
    print(f"\nSending lattice graph ({lattice.get('node_count', '?')} nodes, {lattice.get('edge_count', '?')} edges) …")
    post(url, {"event": "lattice_graph", **lattice}, "lattice_graph")

    print("\nAll payloads delivered successfully.")


if __name__ == "__main__":
    main()
