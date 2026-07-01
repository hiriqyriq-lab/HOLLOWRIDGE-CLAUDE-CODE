# Contrapolation: Metricool Draft-by-Default
*Type:* `safety` · *Solved:* 2026-07-01

## Thesis
`distribute_content()` exists so `CONTENT_AGENT` output reaches an actual
audience without a human copy-pasting it into Instagram/TikTok — that's the
entire point of Phase 2's Metricool integration.

## Antithesis
It reaches that audience with zero review. Every cycle, whatever the LLM
wrote gets scheduled straight to real social accounts the moment
`METRICOOL_TOKEN`/`METRICOOL_BLOG_ID` are set — no draft state, no approval
step, no human ever sees it before it's live. `CLAUDE.md`'s own operating
rule #3 ("No hallucinated facts about real people — factual-critical
journalistic framing") is a *content* instruction to the model; nothing
enforces it before publish. An unreviewed LLM output going live under a real
brand's name on every autonomous cycle is exactly the kind of action that
should require a human in the loop by default.

## Synthesis
`schedule_post()` now sends `"draft": true` unless
`NIL_AGENCY_AUTO_PUBLISH=1` is explicitly set. `distribute_content()` reports
each result's status clearly (`draft` vs `scheduled`) and prints a one-line
reminder when nothing went live. Publishing is now something you turn on,
not something that happens by having a token configured. Metricool token
scoping is unchanged — this is a code-level default, not a permissions fix,
so it doesn't replace actually reviewing what gets published.
