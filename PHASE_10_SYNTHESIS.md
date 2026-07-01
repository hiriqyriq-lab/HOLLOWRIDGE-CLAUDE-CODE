# Contrapolation: Rate-Limit Backoff With Jitter
*Type:* `resilience` · *Solved:* 2026-07-01

## Thesis
`RateLimitError` was already handled: catch it, sleep 60s, try the next
cycle. Simple, and good enough for a single perpetual loop.

## Antithesis
Phase 3 made "single loop" no longer true — local `pm2` and GitHub Actions
can both hold the lock in turn, alternating cycles against the same
`ANTHROPIC_API_KEY`. A flat, unjittered 60s sleep means that if both
environments hit the account's rate limit around the same time, they retry
on the same fixed cadence — synchronized, not staggered — competing for the
same quota the moment it opens back up instead of spreading their retries
out. And a single fixed sleep doesn't distinguish a momentary blip from a
sustained rate-limit period; it retries at the same pace either way.

## Synthesis
`backoff_seconds(attempt)` grows exponentially
(`RATE_LIMIT_BASE_SLEEP * 2^attempt`, default base 30s) up to
`RATE_LIMIT_MAX_SLEEP` (default 600s), with up to 25% random jitter added on
top so concurrent holders don't retry in lockstep. The main loop tracks a
`rate_limit_streak` counter — incremented on each consecutive
`RateLimitError`, reset to zero the moment a cycle actually succeeds — so an
isolated blip still recovers in ~30-45s, while a sustained rate-limit period
backs off further each time instead of hammering the API on a fixed clock.
