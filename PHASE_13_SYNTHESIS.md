# Contrapolation: The Missing Backlog Tier
*Type:* `bug` · *Solved:* 2026-07-01

## Thesis
`CLAUDE.md`'s SESSION STARTUP SEQUENCE documents three fallback tiers,
explicitly ordered: (7) loop `tasks/queue.json` until empty, (8) if empty,
run BACKGROUND priority tasks from `tasks/backlog.json`, (9) only if
*that's* also empty, fall back to self-generated creative tasks.

## Antithesis
Steps 7 and 9 exist in `orchestrator.py`. Step 8 never did. The moment
`read_queue()` comes back empty, the main loop calls `gen_auto()` — pulling
from the hardcoded four-item `AUTONOMOUS` list — directly. `backlog.json`
was never read, never referenced, never even had a documented schema
outside of `CLAUDE.md`'s prose description. The middle tier — a
human-curated set of standing BACKGROUND-priority tasks distinct from the
code's own small hardcoded fallback — was documented but not implemented,
the same shape of gap Phase 4 found for `save_canon()`.

## Synthesis
`read_backlog()` loads `tasks/backlog.json` (same task schema as
`queue.json`), filters to `status: "pending"`, and — reusing Phase 7's
idempotency mechanism — excludes anything whose `task_id` already has a
completion record in `tasks/completed/`, so a backlog task runs once and
stays done even though `backlog.json` itself is never rewritten. The main
loop's "queue empty" branch now checks `read_backlog()` before falling
through to `gen_auto()`, matching CLAUDE.md's documented ordering exactly.
Backlog tasks flow through the same `mark_running`/`complete_task`
lifecycle as GitHub-issue-sourced tasks already do (structurally identical:
present only transiently in the in-memory task list, never written into
`queue.json`).

No `tasks/backlog.json` is seeded by this phase — `read_backlog()` handles
a missing file gracefully, so the system behaves exactly as before until an
operator actually populates it.
