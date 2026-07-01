# Contrapolation: Test Suite + CI
*Type:* `quality` · *Solved:* 2026-07-01

## Thesis
`CODE_AGENT`'s own operating standard, defined back in Phase 1's
`agents/code_agent.md`: "Tests must pass. Linters must clear." Every phase
since has claimed a "Test plan" checklist in its PR description.

## Antithesis
Every one of those checklists says "manual test" — a one-off script run in
conversation, never saved, never re-run. `orchestrator.py` has grown a lock
mechanism, canon write-back, a budget circuit breaker, and GitHub Issue
idempotency logic across Phases 3-7, and none of it has a single automated
test. Worse: every PR opened in this session (#2 through #7) has shown zero
CI check runs, because there was no `pull_request`-triggered workflow at
all — the "Test plan" checkboxes were unverifiable by anyone but whoever ran
them once by hand.

## Synthesis
`tests/test_orchestrator.py` — 28 pytest cases covering the lock (fresh
acquire, contention, release, stale-TTL reclaim, corrupt-file reclaim),
canon write-back (all six agent routes plus the unknown-agent fallback),
the budget circuit breaker (accumulation, cap trip, bounded history), Phase
7's GitHub Issue idempotency guard, and the core task lifecycle
(mark/complete/fail). `tests/conftest.py` + an autouse fixture isolate every
test into a `tmp_path`, so nothing touches the real repo's `tasks/`,
`outputs/`, or `memory/`.

`.github/workflows/tests.yml` runs this suite on every pull request and on
push to `main` — no secrets required, since none of these tests call the
real Anthropic API. This is also the first CI check any of these PRs will
actually show.
