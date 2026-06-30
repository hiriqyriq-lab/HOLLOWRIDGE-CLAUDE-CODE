#!/usr/bin/env python3
"""Cross-reference and re-summarize transcripts into combined workflows.

Reads data/transcripts.json (produced by extract_transcripts.py) and groups
the workflow/automation lines detected across all transcripts by shared
theme/keyword, producing a synthesized "combined workflow" per theme that
spans multiple source files.

This is a re-invokable batch script, not a long-running process: run it
again any time transcripts.json changes (e.g. after re-running
extract_transcripts.py) to refresh the cross-referenced output.

Usage:
  python3 scripts/cross_reference_workflows.py
"""
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
TRANSCRIPTS_JSON = DATA_DIR / "transcripts.json"

# Themes to cross-reference across transcripts. Each theme is matched against
# workflow/automation lines (and surrounding text) via its keyword pattern.
THEMES = {
    "scheduling_triggers": re.compile(r"\b(schedule|cron|trigger|webhook)\b", re.IGNORECASE),
    "no_code_platforms": re.compile(r"\b(n8n|zapier|make\.com|integration)\b", re.IGNORECASE),
    "pipelines": re.compile(r"\b(pipeline|step \d+)\b", re.IGNORECASE),
    "apis": re.compile(r"\b(api call|api)\b", re.IGNORECASE),
    "automation_general": re.compile(r"\b(automation|automate)\b", re.IGNORECASE),
    "workflow_general": re.compile(r"\bworkflow\b", re.IGNORECASE),
}


def load_transcripts() -> list[dict]:
    if not TRANSCRIPTS_JSON.exists():
        raise SystemExit(
            f"{TRANSCRIPTS_JSON} not found. Run scripts/extract_transcripts.py first."
        )
    return json.loads(TRANSCRIPTS_JSON.read_text(encoding="utf-8"))


def cross_reference(records: list[dict]) -> dict:
    themes: dict[str, dict] = {
        theme: {"contributing_files": [], "lines": []} for theme in THEMES
    }

    for record in records:
        filename = record["filename"]
        for line in record.get("workflow_automation_lines", []):
            for theme, pattern in THEMES.items():
                if pattern.search(line):
                    themes[theme]["lines"].append({"file": filename, "line": line})
                    if filename not in themes[theme]["contributing_files"]:
                        themes[theme]["contributing_files"].append(filename)

    # Drop empty themes and sort contributors for stable output.
    combined = {}
    for theme, data in themes.items():
        if not data["lines"]:
            continue
        data["contributing_files"] = sorted(data["contributing_files"])
        data["file_count"] = len(data["contributing_files"])
        data["line_count"] = len(data["lines"])
        combined[theme] = data

    return combined


def write_outputs(combined: dict) -> None:
    (DATA_DIR / "combined_workflows.json").write_text(
        json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = ["# Combined Workflows (Cross-Referenced Across Transcripts)", ""]
    for theme, data in sorted(combined.items(), key=lambda kv: -kv[1]["line_count"]):
        lines.append(f"## {theme}")
        lines.append(
            f"- spans {data['file_count']} file(s), {data['line_count']} matching line(s)"
        )
        lines.append(f"- contributing files: {', '.join(data['contributing_files'])}")
        lines.append("")
        for entry in data["lines"]:
            lines.append(f"  - [{entry['file']}] {entry['line']}")
        lines.append("")
    (DATA_DIR / "COMBINED_WORKFLOWS.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    records = load_transcripts()
    combined = cross_reference(records)
    write_outputs(combined)

    print(f"Cross-referenced {len(records)} transcripts into {len(combined)} combined workflow theme(s):")
    for theme, data in combined.items():
        print(f"  - {theme}: {data['file_count']} files, {data['line_count']} lines")
    print(f"\nOutputs: {DATA_DIR / 'combined_workflows.json'}, {DATA_DIR / 'COMBINED_WORKFLOWS.md'}")


if __name__ == "__main__":
    main()
