# Contrapolation: GitHub Issue Task Idempotency
*Type:* `bug` · *Solved:* 2026-07-01

## Thesis
`GitHubQueue.close_task()` closes the issue and posts a completion comment
once an agent finishes it — the intended lifecycle is: issue opens
(`state=open`, labeled `nil-agency-task`) → `get_tasks()` picks it up →
agent runs → `close_task()` closes it → `get_tasks()`'s `state=open` filter
naturally excludes it from then on.

## Antithesis
That lifecycle only holds if `close_task()` succeeds. `complete_task()`
writes the local `tasks/completed/gh-<n>.json` record *unconditionally*, then
tries to close the issue, and swallows any failure (network blip, token
permissions, GitHub API hiccup) as a logged warning — the run continues as
if nothing happened. But `read_queue()`'s dedup only checked `task_id`s
currently in `queue.json`, which GitHub-sourced tasks never populate
(`write_queue()` filters `gh-*` ids out by design). So a close failure meant
the issue stayed open, `get_tasks()` fetched it again next cycle, and it got
reprocessed — a second paid API call, a second `CONTENT_AGENT` output,
potentially a second live social post — indefinitely, once per cycle,
forever, even though it already had a "completed" record sitting right there
in `tasks/completed/`.

## Synthesis
`completed_task_ids()` scans `tasks/completed/` for non-`FAILED_` records and
`read_queue()` now excludes those ids from `get_tasks()` results in addition
to whatever's in `queue.json`. Local completion is now the actual source of
truth for "don't redo this," independent of whether the GitHub API call to
close the issue happened to succeed. The close-failure warning now also
tells the operator explicitly that the issue itself is still open on GitHub
and needs manual closing — the local guard prevents re-billing, it doesn't
fix GitHub's state for you.
