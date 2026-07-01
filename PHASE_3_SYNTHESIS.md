# Contrapolation: NIL AGENCY Phase 1 × Phase 2 → Phase 3
*Type:* `system` · *Solved:* 2026-07-01

## Thesis (Phase 1 — local)
The original orchestrator is a single perpetual loop: `pm2` keeps `orchestrator.py`
alive on one machine, polling `tasks/queue.json` every 60s forever, restarting on
crash, restarting daily by cron. All state — the queue, `memory/canon.json`,
`memory/session_log.md`, `outputs/` — lives on that one machine's disk. Nothing
about it assumes another copy of itself might be running anywhere else.

## Antithesis (Phase 2 — cloud)
Phase 2 adds a second, independent execution path: `.github/workflows/nil_agency.yml`
runs the same `orchestrator.py` on an hourly cron inside GitHub Actions, reading
task from GitHub Issues as well as `queue.json`, and — critically — commits its
state (`outputs/`, `memory/`, `tasks/completed/`) back to git after every run.
This inverts Phase 1's assumption: state is no longer local-machine-only, it's
git-authoritative. But Phase 2 never learned about Phase 1: if someone runs
`pm2 start ecosystem.config.js` locally *and* merges the Actions workflow, both
loops read the same `tasks/queue.json`, can both grab the same pending task in
the same few seconds, and only one of their outputs survives — the other's local
`memory/canon.json` silently diverges from what's in git, forever out of sync
with what the cloud run actually published.

## Synthesis (Phase 3 — this PR)
Two mechanisms resolve the contradiction instead of picking a side:

1. **`tasks/.lock.json` cross-environment lock.** Before claiming a cycle, an
   orchestrator instance writes `{holder, mode, acquired_at}` and checks whether
   a *different* holder's lock is still fresh (`NIL_AGENCY_LOCK_TTL`, default
   900s). If so, it yields the cycle instead of racing. Thesis (continuous local
   loop) and antithesis (scheduled cloud loop) can now coexist — whichever
   claims first, finishes first; the TTL means a crashed holder's lock expires
   and doesn't permanently starve the other side.
2. **`--git-sync` / `NIL_AGENCY_GIT_SYNC=1` for local mode.** Local runs can now
   opt into the same commit-and-push behavior Phase 2's workflow already does,
   so a task solved on someone's laptop lands in `memory/canon.json` in git just
   as reliably as one solved by the scheduled Action. Local-only state stops
   being a second, unsynchronized truth.

Neither mechanism requires choosing local *or* cloud as canonical — the
synthesis is that both are legitimate execution environments for the same
orchestrator, and the thing that was actually missing was coordination, not a
winner.
