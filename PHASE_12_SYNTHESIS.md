# Contrapolation: Structured Canon + Contradiction Flags
*Type:* `bug` · *Solved:* 2026-07-01

## Thesis
`CLAUDE.md`'s worldbuilding output standard, unchanged since Phase 1:
"Cross-reference existing lore entities" and "Flag any contradictions with
existing canon." `memory/canon.json`'s schema has had a `worldbuilding.houses`
dict since Phase 2, specifically for this.

## Antithesis
Phase 4's `update_canon()` only ever appends flat records to
`worldbuilding.confirmed_lore` — a list of `{task_id, instruction, summary,
output_path}` blobs with no structure per entity. `worldbuilding.houses`
has been an empty `{}` since Phase 2; nothing ever wrote to it. And nothing
ever compared a new output against prior canon — CLAUDE.md's own explicit
promise to flag contradictions was, like Phase 4's canon write-back before
it, unimplemented.

## Synthesis
`extract_worldbuilding_entities(text)` finds which of the five known Houses
(Aurveil, Morrval, Sylvorne, Vaelthorn, Veilwynn) a given output actually
discusses. `update_worldbuilding_structure()` upserts
`canon.worldbuilding.houses[<house>]` with mention count and a bounded
output history — the cross-referencing CLAUDE.md promised.

For contradiction detection, this doesn't attempt real semantic conflict
resolution (that would need another LLM call, or a much larger project) —
it's an honest, narrow heuristic: a canonical origin should be singular per
House (Phase 1's own seed task literally called House Aurveil's founding
myth "the canonical origin"). If a new output makes another
founding/origin-myth claim for a House that already has one recorded, it's
appended to `worldbuilding.contradiction_flags` and logged as a warning —
surfaced for human review, not silently resolved or silently ignored,
which is what CLAUDE.md's own "flag" (not "fix") instruction actually asks
for.
