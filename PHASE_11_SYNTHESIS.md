# Contrapolation: Heartbeat + Staleness Detection
*Type:* `observability` · *Solved:* 2026-07-01

## Thesis
`CLAUDE.md`: "You are always working. There is no idle state." The whole
system — `pm2`'s `max_restarts: 999`, the hourly Actions cron — is built on
the assumption that it just keeps running.

## Antithesis
Nothing verifies that assumption from the outside. The main loop's
exception handling swallows every failure internally (`except Exception as
e: log_error(...); time.sleep(10)`) and keeps looping — so a GitHub Actions
run "succeeding" (exit 0) tells you nothing about whether a cycle actually
did anything. An expired `ANTHROPIC_API_KEY`, a persistent Phase 5
budget-cap trip, or a crash before the loop even starts would all look
identical from outside: green checkmarks, silence, and nobody notices until
someone happens to check `outputs/` and realizes nothing's been added in
days.

## Synthesis
`write_heartbeat(mode, cycle)` records `memory/heartbeat.json`
(`last_cycle_at`, `mode`, `holder`, `cycle`) in the loop's `finally` block —
so it fires whether the cycle succeeded, failed, or hit a rate limit, as
long as the lock was actually acquired and a cycle was attempted.
`check_heartbeat()` (`--check-heartbeat`) compares its age against
`NIL_AGENCY_HEARTBEAT_STALE_SECONDS` (default 7200s — generous slack over
the hourly cron) and reports `STALE`/`OK`/`INFO` accordingly.

`.github/workflows/nil_agency.yml` now runs this check as its last step.
If heartbeat is stale or missing, the step exits non-zero — a red X in the
Actions tab, the first externally-visible signal this system has ever had
that it stopped actually working, independent of the main loop's own
internal exception swallowing.
