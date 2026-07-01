# NIL AGENCY — Phase Index

Every phase after Phase 2 was found the same way: audit `orchestrator.py`
and its supporting modules against what `CLAUDE.md` (or the code's own
prior phase) actually promised, treat the gap as a contrapolation (thesis =
what was promised, antithesis = what the code actually does, synthesis =
the fix), and ship it as its own stacked PR with tests.

## Phases

| Phase | What it did | Doc | PR |
|---|---|---|---|
| 1 | Original scaffold: `CLAUDE.md`, six agent prompts, `orchestrator.py` v1, `task.py`, local `pm2` deployment | — | — |
| 2 | Multi-mode orchestrator v2, GitHub Issues task queue, Metricool distributor, Docker deploy, hourly Actions workflow | — | #2 |
| 3 | Cross-environment lock (`tasks/.lock.json`) + `--git-sync`, so local and cloud runs stop racing | `PHASE_3_SYNTHESIS.md` | #3 |
| 4 | Fixed `save_canon()` never being called — canon had been permanently empty since Phase 2 | `PHASE_4_SYNTHESIS.md` | #4 |
| 5 | Daily spend cap circuit breaker (`memory/spend.json`) | `PHASE_5_SYNTHESIS.md` | #5 |
| 6 | Metricool defaults to draft, not auto-publish | `PHASE_6_SYNTHESIS.md` | #6 |
| 7 | Fixed GitHub Issue tasks reprocessing forever if `close_task()` failed | `PHASE_7_SYNTHESIS.md` | #7 |
| 8 | pytest suite (28→51 tests across phases) + CI (`.github/workflows/tests.yml`) | `PHASE_8_SYNTHESIS.md` | #8 |
| 9 | `.env.example` (referenced since Phase 2, never existed) + `--check` config validation | `PHASE_9_SYNTHESIS.md` | #9 |
| 10 | Exponential backoff with jitter for rate limits, replacing a flat 60s sleep | `PHASE_10_SYNTHESIS.md` | #10 |
| 11 | `memory/heartbeat.json` + `--check-heartbeat`, since the loop swallows exceptions internally | `PHASE_11_SYNTHESIS.md` | #11 |
| 12 | Structured `canon.worldbuilding.houses` + contradiction flags (both promised by `CLAUDE.md`, neither implemented) | `PHASE_12_SYNTHESIS.md` | #12 |
| 13 | Implemented the documented-but-missing `tasks/backlog.json` fallback tier | `PHASE_13_SYNTHESIS.md` | #13 |
| 14 | This index | — | #14 |

## Architecture, as of Phase 13

```
orchestrator.py main loop, per cycle:
  1. acquire_lock(mode)              — Phase 3, yield if another env holds it
  2. load_spend() / over_budget()    — Phase 5, skip cycle if daily cap hit
  3. read_queue(gh)                  — tasks/queue.json + GitHub Issues
                                        (Phase 7: skips already-completed gh-* issues)
     read_backlog()  if queue empty  — Phase 13, tasks/backlog.json
     gen_auto()       if that's empty too — hardcoded AUTONOMOUS list
  4. run_agent()                     — calls Anthropic, writes outputs/
  5. record_spend() / save_spend()   — Phase 5
  6. complete_task()                 — tasks/completed/, closes GitHub issue
  7. update_canon()                  — Phase 4, memory/canon.json
     update_worldbuilding_structure() if WORLDBUILDING_AGENT — Phase 12
  8. distribute_content()  if CONTENT_AGENT and Metricool configured
                                        — Phase 6, drafts unless AUTO_PUBLISH=1
  9. git_sync()  if --git-sync        — Phase 3, local runs commit like cloud does
  10. write_heartbeat() / release_lock() — Phase 11, in finally: always runs
```

Deployment: local `pm2` (Phase 1) and/or hourly GitHub Actions (Phase 2) —
`.github/workflows/nil_agency.yml` also now runs `--check-heartbeat` as its
last step (Phase 11) and `.github/workflows/tests.yml` runs the suite on
every PR (Phase 8).

## Running the checks

```bash
python3 -m pytest tests/ -v          # Phase 8
python3 orchestrator.py --check      # Phase 9 — config, no API calls
python3 orchestrator.py --check-heartbeat   # Phase 11 — staleness
```
