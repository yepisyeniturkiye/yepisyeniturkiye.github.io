# Yepis pipeline — 2026-05-01 manual-publish diagnosis

## Today's outcome (UTC)

- 08:33 — task fires; live site shows `<title>... · 2026-04-30</title>`. No GH Actions scheduled run for today yet.
- 08:42 — local fetch+render commit pushed (`03401c6`).
- 08:43–10:55 — local infer (16 batches, 289 clusters).
- 10:55 — re-render and push (`e45a769`, "Publish 2026-05-01: 289 clusters across 8 regions").
- 10:57 — GH Pages live; title flips to 2026-05-01.

## Manual intervention required: yes

The 04:17 and 07:17 UTC scheduled cron slots both failed to fire on time. By the time the live verification ran (UTC 09:21), neither slot had fired late either.

## Root cause: GH Actions free-tier scheduled cron unreliability

This is already documented in `.github/workflows/ingest.yml` (the comment block on `schedule:`). Historical pattern from `gh run list --workflow=ingest.yml --limit 30`:

| Date | Scheduled runs | Fire time vs. cron | Notes |
|---|---|---|---|
| 2026-04-30 | 2 (10:30, 16:00) | ~6h13m, ~5h43m late | First day of triple cron mitigation. 04:17 fired at 10:30; 10:17 fired at 16:00; 07:17 missed entirely. |
| 2026-04-29 | 0 | n/a — all skipped | Documented in workflow comment as the case that motivated triple cron. |
| 2026-04-28 | 1 (12:12) | n/a (single-cron era) | |
| 2026-04-27 | 1 cancelled (12:06) | superseded by dispatch | |
| 2026-04-26 | 1 cancelled (09:15) | superseded by dispatch | |
| 2026-04-25 | 1 cancelled (08:37) | superseded by dispatch | |
| 2026-04-24 | 1 cancelled (10:51) | superseded by dispatch | |
| 2026-04-23 | 1 (10:54) | success | |
| 2026-04-22 | 1 cancelled (10:47) | superseded | |
| 2026-04-21 | 1 failure (10:50) + manual workflow_dispatch | | |

So for the prior 9 days, only 4 days had a successful scheduled run land naturally; the rest required manual dispatch or cancellation/superseding. Today extends that pattern: 04:17 and 07:17 missed, manual fallback used.

## Existing mitigation

Commit `546061b` (yesterday, 2026-04-30) added the triple cron (`17 4`, `17 7`, `17 10` UTC). Today is its first full day in production, and the first two slots already missed. The 10:17 UTC slot may still fire late and produce additional content; that is harmless because:
- `fetch.py` writes `feed/YYYY/MM/DD/HH.json` per UTC hour, so a late run does not overwrite my manual `feed/2026/05/01/08.json`.
- `infer.py` writes `enriched/YYYY-MM-DD.json` once; a later run will append-and-overwrite with combined clusters, which is the intended cycle behavior.
- `concurrency: ingest` with `cancel-in-progress: false` means parallel firings queue rather than collide.

## Recommendation: report, do not patch

The mitigation is recent and the failure mode is GitHub-side, not workflow-side. Possible next steps if the triple cron continues to underperform after a longer observation window (say, 1 week):

1. **External webhook trigger** (cron-job.org, EasyCron, etc.) calling the `repos/.../actions/workflows/ingest.yml/dispatches` endpoint. Removes dependency on GH-internal scheduling.
2. **Add a 4th very-early slot** (e.g., `17 1 * * *`) for additional retry chances during the typical drift window.
3. **Self-hosted runner** (heaviest lift; only justified if external triggers also fail).

None of these are urgent today. Do not ship a speculative cron change without a longer baseline of triple-cron behavior, since today's published content (commit `e45a769`) is the stable known-good state and the current workflow risks nothing further.

## Anonymity (task 2)

Clean. PII regex sweep across working tree and full git history returns no matches. Commit author identity is `Yepisyeni Türkiye <yepisyeniturkiye@gmail.com>` only. No history reset needed.

## Cron drift quantification

From the last 100 workflow runs, only 10 were scheduled (the rest were `workflow_dispatch` or `pages-build-deployment`). Drift relative to the closest cron slot:

| UTC start | conclusion | drift |
|---|---|---|
| 2026-04-30 16:00 | success | +5h44m |
| 2026-04-30 10:30 | success | +14m |
| 2026-04-28 12:12 | success | +6h13m |
| 2026-04-27 12:06 | cancelled | +6h07m (superseded) |
| 2026-04-26 09:15 | cancelled | +3h16m (superseded) |
| 2026-04-25 08:37 | cancelled | +2h38m (superseded) |
| 2026-04-24 10:51 | cancelled | +4h52m (superseded) |
| 2026-04-23 10:54 | success | +4h54m |
| 2026-04-22 10:47 | cancelled | +4h48m (superseded) |
| 2026-04-21 10:50 | failure | +4h50m |

So in the past 10 days:
- 1 run (10%) fired within 15 min of its cron slot
- 8 runs (80%) were 2.5–6.2h late
- 2026-04-29 had zero scheduled runs (entirely skipped, separately documented)
- Today (2026-05-01) at 09:21 UTC: still no scheduled run (04:17 +5h04m late, 07:17 +2h04m late, 10:17 not yet due)

This empirically validates the documented "free-tier scheduled cron is unreliable — runs 4–6h late or skip entirely" comment. The triple-cron mitigation is too new (1 day) to evaluate.
