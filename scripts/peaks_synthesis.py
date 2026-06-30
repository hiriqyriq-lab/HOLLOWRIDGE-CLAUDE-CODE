#!/usr/bin/env python3
"""Synthesize 'Peak' content across transcripts.

Two outputs, re-invokable any time data/transcripts.json is refreshed:

1. data/combined_peaks.json / data/COMBINED_PEAKS.md
   Cross-references "peak"-related sentences from the FULL TEXT of every
   transcript (not just the workflow/automation lines used by
   cross_reference_workflows.py), capped per file to keep it readable.

2. data/PEAK_FILES_MERGED.md
   Dedicated merge of the transcripts whose filename itself contains
   "peak" (Peak Eternal, Peak Book Genome, Peak Energies, the 396-entry
   PEAK_ETERNAL_MOMENTS_MASTER_INDEX, etc.) into one combined document.

Usage:
  python3 scripts/peaks_synthesis.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
TRANSCRIPTS_JSON = DATA_DIR / "transcripts.json"

PEAK_WORD = re.compile(r"\bpeak\w*\b", re.IGNORECASE)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
MAX_SENTENCES_PER_FILE = 20


def load_transcripts() -> list[dict]:
    if not TRANSCRIPTS_JSON.exists():
        raise SystemExit(
            f"{TRANSCRIPTS_JSON} not found. Run scripts/extract_transcripts.py first."
        )
    return json.loads(TRANSCRIPTS_JSON.read_text(encoding="utf-8"))


def cross_reference_peaks(records: list[dict]) -> dict:
    """Scan full text of every transcript for peak-related sentences."""
    entries = []
    contributing_files = []

    for record in records:
        sentences = [s.strip() for s in SENTENCE_SPLIT.split(record["text"]) if s.strip()]
        peak_sentences = [s for s in sentences if PEAK_WORD.search(s)][:MAX_SENTENCES_PER_FILE]
        if peak_sentences:
            contributing_files.append(record["filename"])
            for sentence in peak_sentences:
                entries.append({"file": record["filename"], "sentence": sentence})

    return {
        "contributing_files": sorted(contributing_files),
        "file_count": len(contributing_files),
        "sentence_count": len(entries),
        "sentences": entries,
    }


def write_peaks_cross_reference(combined: dict) -> None:
    (DATA_DIR / "combined_peaks.json").write_text(
        json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = ["# Combined Peaks (Cross-Referenced Across All Transcripts)", ""]
    lines.append(
        f"Spans {combined['file_count']} file(s), {combined['sentence_count']} matching sentence(s) "
        f"(capped at {MAX_SENTENCES_PER_FILE} per file)."
    )
    lines.append("")
    by_file: dict[str, list[str]] = {}
    for entry in combined["sentences"]:
        by_file.setdefault(entry["file"], []).append(entry["sentence"])
    for filename in sorted(by_file):
        lines.append(f"## {filename}")
        for sentence in by_file[filename]:
            lines.append(f"- {sentence}")
        lines.append("")
    (DATA_DIR / "COMBINED_PEAKS.md").write_text("\n".join(lines), encoding="utf-8")


def merge_peak_named_files(records: list[dict]) -> None:
    peak_named = sorted(
        (r for r in records if "peak" in r["filename"].lower()),
        key=lambda r: r["filename"],
    )

    lines = ["# Peak-Named Files Merged", ""]
    lines.append(f"{len(peak_named)} file(s) with 'peak' in the filename, merged below.")
    lines.append("")
    for record in peak_named:
        lines.append(f"## {record['filename']}")
        lines.append(f"(words: {record['word_count']})")
        lines.append("")
        lines.append(record["text"])
        lines.append("")
        lines.append("---")
        lines.append("")
    (DATA_DIR / "PEAK_FILES_MERGED.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Merged {len(peak_named)} peak-named files -> {DATA_DIR / 'PEAK_FILES_MERGED.md'}")


def main() -> None:
    records = load_transcripts()

    combined = cross_reference_peaks(records)
    write_peaks_cross_reference(combined)
    print(
        f"Cross-referenced peak mentions across {combined['file_count']} file(s), "
        f"{combined['sentence_count']} sentence(s) -> "
        f"{DATA_DIR / 'combined_peaks.json'}, {DATA_DIR / 'COMBINED_PEAKS.md'}"
    )

    merge_peak_named_files(records)


if __name__ == "__main__":
    main()
