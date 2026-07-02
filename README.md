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
