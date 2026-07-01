# NIL AGENCY
Autonomous Creative-Technical Intelligence | Amalgamated Omnipresence

## Deploy (choose one)

### GitHub Actions (free, zero server)
1. Push repo to GitHub
2. Settings -> Secrets -> Actions -> ANTHROPIC_API_KEY
3. Enable Actions. Runs hourly, commits outputs to repo.

### Docker
```bash
cp .env.example .env && docker-compose up -d
```

### Local (pm2)
```bash
cp .env.example .env && ./setup.sh
```

## Add Tasks
```bash
python3 task.py add --agent CONTENT_AGENT --priority 1 "instruction"
python3 task.py add --agent WORLDBUILDING_AGENT --priority 2 "instruction"
python3 task.py list
python3 task.py status
```

Via GitHub: create Issue with title [AGENT_NAME] instruction, label nil-agency-task

## Running Local + Cloud Together (Phase 3)

Phase 1 (local `pm2`) and Phase 2 (hourly GitHub Actions) can both be active at
once. `orchestrator.py` coordinates them via `tasks/.lock.json` so only one
claims a given cycle (`NIL_AGENCY_LOCK_TTL`, default 900s). To keep a local
run's `memory/canon.json` in sync with what the cloud publishes, run local mode
with git-sync on:

```bash
python3 orchestrator.py --git-sync
# or: NIL_AGENCY_GIT_SYNC=1 python3 orchestrator.py
```

See `PHASE_3_SYNTHESIS.md` for the reasoning.

## Canon Accumulation (Phase 4)

Every completed task now writes a record back into `memory/canon.json` under
its agent's section (`worldbuilding.confirmed_lore`, `brand.confirmed_copy`,
`research.completed_syntheses`, `content.published_topics`,
`music.released_content`, `code.changes`), so future cycles' "ESTABLISHED
CANON" prompt context actually reflects prior output instead of staying
empty. See `PHASE_4_SYNTHESIS.md`.

## Budget Cap (Phase 5)

The loop checks `memory/spend.json` before every cycle and skips the cycle
once today's estimated cost hits `NIL_AGENCY_MAX_DAILY_SPEND_USD` (default
`$15`). Shared across local and cloud runs like canon. Estimate only — check
your actual Anthropic billing for real numbers. See `PHASE_5_SYNTHESIS.md`.

## Social Publishing Defaults to Draft (Phase 6)

Metricool distribution now saves posts as drafts by default — nothing goes
live automatically. Set `NIL_AGENCY_AUTO_PUBLISH=1` to actually publish. See
`PHASE_6_SYNTHESIS.md`.

## GitHub Issue Task Idempotency (Phase 7)

If closing a GitHub issue fails after a task completes, it no longer gets
reprocessed on the next cycle — local completion records in
`tasks/completed/` are now the source of truth, independent of the GitHub
API call succeeding. See `PHASE_7_SYNTHESIS.md`.

## Tests (Phase 8)

```bash
pip install -r requirements-dev.txt
python3 -m pytest tests/ -v
```

28 tests covering the lock, canon write-back, budget circuit breaker, and
GitHub Issue idempotency mechanisms. Runs automatically on every PR via
`.github/workflows/tests.yml`. See `PHASE_8_SYNTHESIS.md`.

## Config Check (Phase 9)

`.env.example` finally exists (README referenced it since Phase 2 without
it actually being there). Validate config without spending anything:

```bash
python3 orchestrator.py --check
```

See `PHASE_9_SYNTHESIS.md`.

## Rate-Limit Backoff (Phase 10)

Rate-limit retries now back off exponentially with jitter
(`NIL_AGENCY_RATE_LIMIT_BASE_SLEEP`/`_MAX_SLEEP`, defaults 30s/600s) instead
of a flat 60s sleep, so local and cloud runs sharing one API key don't retry
in lockstep. See `PHASE_10_SYNTHESIS.md`.

## Heartbeat (Phase 11)

`memory/heartbeat.json` is written every cycle. Check staleness (a
perpetual system otherwise has no way to notice it stopped):

```bash
python3 orchestrator.py --check-heartbeat
```

The GitHub Actions workflow now fails loudly (red X) if the last cycle is
older than `NIL_AGENCY_HEARTBEAT_STALE_SECONDS` (default 2h). See
`PHASE_11_SYNTHESIS.md`.
