# Contrapolation: Canon Write-Back
*Type:* `bug` · *Solved:* 2026-07-01

## Thesis
`memory/canon.json` exists to give NIL AGENCY continuity across cycles.
`build_system_prompt()` injects each agent's `canon[section]` into its system
prompt as "ESTABLISHED CANON" so, in theory, the WORLDBUILDING_AGENT knows what
lore already exists before writing more, the BRAND_AGENT knows which notarikon
dissections are already canon, and so on. `save_canon()` was written in Phase 2
specifically to close this loop.

## Antithesis
It's never called. Every cycle calls `load_canon()` and reads from it, but
`orchestrator.py`'s main loop never calls `save_canon()` after a task completes.
The result: `memory/canon.json` is permanently whatever `{"worldbuilding":
{"houses":{},...}}` skeleton Phase 2's setup script wrote once, forever. Every
"ESTABLISHED CANON" block injected into every prompt across every cycle,
local or cloud, is empty. The continuity mechanism the whole memory/ directory
exists for has never actually operated.

## Synthesis
`update_canon(canon, task, summary, output_path)` maps each agent to a canon
section/key (`WORLDBUILDING_AGENT` → `worldbuilding.confirmed_lore`,
`BRAND_AGENT` → `brand.confirmed_copy`, `RESEARCH_AGENT` →
`research.completed_syntheses`, `CONTENT_AGENT` → `content.published_topics`,
plus new `music.released_content` and `code.changes` sections that didn't
exist in the Phase 2 schema), appends a compact record of what the task
produced, and the main loop now calls `save_canon(update_canon(...))`
immediately after `complete_task()`. New sections are created with
`setdefault`, so this doesn't require migrating the existing `canon.json` —
`music`/`code` sections simply appear the first time those agents run.

Canon now actually accumulates. The next cycle's "ESTABLISHED CANON" block
will contain something.
