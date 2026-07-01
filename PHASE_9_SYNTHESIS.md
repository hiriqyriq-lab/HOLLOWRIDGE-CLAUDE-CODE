# Contrapolation: Config Validation + `.env.example`
*Type:* `bug` · *Solved:* 2026-07-01

## Thesis
`README.md` has told operators to run `cp .env.example .env` since Phase 2's
"Docker" and "Local (pm2)" deploy sections. Config problems (missing key,
missing agent prompt) should be cheap and obvious to find before running
anything that costs money.

## Antithesis
`.env.example` never existed — the referenced file was never created in any
phase. And nothing validated config before the first paid API call: a
missing `agents/*.md` file, a bad `ANTHROPIC_API_KEY`, or Metricool
credentials that don't actually authenticate would only surface mid-run, as
a crash or a silently-skipped optional feature buried in log output.

## Synthesis
`.env.example` now exists, documenting every environment variable the
system reads (required and optional, all phases). `orchestrator.py --check`
(or `NIL_AGENCY_CHECK=1`... no — implemented as a CLI flag, not an env var,
so it can't be accidentally left on) runs `run_config_check()`: confirms
`ANTHROPIC_API_KEY` presence, `CLAUDE.md`/`agents/*.md` coverage, and
reports GitHub Issues / Metricool availability and current spend — all
without constructing an Anthropic client or spending anything. Exits
non-zero only if the one truly required piece (the API key) is missing;
everything else is informational, since GitHub/Metricool integrations are
optional by design.
