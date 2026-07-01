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
