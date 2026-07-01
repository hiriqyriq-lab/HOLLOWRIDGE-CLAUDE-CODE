# Contrapolation: Budget Circuit Breaker
*Type:* `safety` · *Solved:* 2026-07-01

## Thesis
NIL AGENCY is designed to run forever — Phase 1's `pm2` config sets
`max_restarts: 999` and `autorestart: true`; Phase 2's GitHub Actions workflow
fires hourly with no end date; the operator's own `CLAUDE.md` says "You are
always working. There is no idle state." Every cycle calls the Anthropic API.

## Antithesis
"Forever" and "no spend ceiling" is an unbounded liability, not just an
uptime goal. A stuck queue that keeps regenerating autonomous tasks, a bug
that causes rapid cycling, or simply months of unattended hourly runs turns
directly into an unbounded bill — nothing in Phases 1-4 checks cost before
spending it.

## Synthesis
`memory/spend.json` tracks token usage and an estimated USD cost per day
(and all-time), shared across local and cloud runs the same way
`memory/canon.json` already is. Before each cycle spends anything,
`over_budget(spend)` checks today's estimated cost against
`NIL_AGENCY_MAX_DAILY_SPEND_USD` (default $15/day) and skips the cycle —
releasing the Phase 3 lock so the other environment can also see and respect
the cap — instead of calling the API. After a successful call,
`record_spend()` updates the running total from the response's actual
`input_tokens`/`output_tokens`.

The dollar figure is an estimate (a small $/Mtok table, not real billing
reconciliation) — a circuit breaker, not an invoice. Good enough to stop
runaway spend; not a substitute for checking your actual Anthropic billing
dashboard.
