# Yepis pipeline — 2026-05-04 manual-publish diagnosis

## Today's outcome (UTC)

- 09:29 — scheduled-task fires; live site shows `<title>... · 2026-05-03</title>`. `gh run list` confirms zero scheduled runs today: 04:17 dropped, 07:17 dropped.
- 09:30 — local fetch starts; 90 new items written to `feed/2026/05/04/09.json`.
- 09:31–09:38 — local infer pass; 148 items in lookback, 8 batches, 134 clusters produced. (See "Operator note" below for an orchestration false-alarm during this stretch.)
- 09:38–09:42 — osint distill (30 platforms), dashboard, region_slice, render_html. `[html] carry-over for empty regions: {'africa': '2026-05-03'}` — africa had no qualifying clusters today; render carried yesterday's bucket forward, consistent with the supplement-from-prior-day rule.
- 09:42 — push as `5cd55e4` ("Publish 2026-05-04 (manual: cron missed 04:17 + 07:17 UTC slots)").
- 09:43 — GH Pages flips; live title shows 2026-05-04, all 8 regions linked, TR/EN toggle present, OSINT footer populated.
- 09:45 — 10:17 UTC slot still pending at writing time.

## Manual intervention required: yes

The 04:17 and 07:17 UTC scheduled cron slots both dropped (zero scheduled runs in the GH Actions list for today before the local publish). The 10:17 UTC slot remains pending and may fire late or drop, consistent with the four-day pattern catalogued in `cron-drift-2026-05-03.md`.

## Five-day baseline of the triple-cron mitigation

| Date | Slots fired | Drift relative to slot | Notes |
|---|---|---|---|
| 2026-04-30 | 2/3 | 04:17 → +6h13m, 07:17 → dropped, 10:17 → +5h43m | First day of triple cron. |
| 2026-05-01 | 3/3 | 04:17 → +5h53m, 07:17 → +4h19m, 10:17 → +4h17m | All slots fired but every one ≥4h late. |
| 2026-05-02 | 1/3 (cancelled) | 04:17 → dropped, 07:17 → dropped, 10:17 → +3h56m (cancelled mid-run) | Worst day for landing fresh content; manual publish required. |
| 2026-05-03 | 0/3 + 3 cancelled-late | 04:17 → dropped, 07:17 → dropped, 10:17 → dropped; three runs at 09:09 / 10:36 / 12:09 UTC all cancelled mid-run by the concurrency group after manual publish landed | Manual publish required. |
| 2026-05-04 | 0/2 (so far, through 09:45 UTC) | 04:17 → dropped, 07:17 → dropped, 10:17 → pending | Manual publish required. |

Across 15 cron slots on 5 days: 6 fired (all 4-6h late, 1 cancelled mid-run, plus 3 more cancelled by concurrency-group preemption on 05-03), 8 dropped entirely, 1 still pending. The 04:17 UTC slot has yet to land fresh content within an hour of its scheduled time on any of the five days observed.

This is the same root cause documented in `cron-drift-2026-05-01.md` through `2026-05-03.md` and the inline `schedule:` comment in `.github/workflows/ingest.yml`: GitHub Actions free-tier scheduled cron is queue-dropped under platform load. Triple-cron mitigation reduces but does not eliminate the drop rate; latency is unchanged.

## What changed in framing today

Day 2 of provably-end-to-end local fallback. Yesterday's run (2026-05-03) was the first day where the scheduled-task → local pipeline → push handoff worked without hand-holding. Today extends that streak: cron dropped, scheduled-task fired, pipeline completed locally, push succeeded, Pages flipped, region populations match prior-day shapes, and the carry-over policy correctly handled the empty `africa` bucket.

In effect, the genuine fix is already shipped. It does not live in this repo — it lives in `~/.claude/scheduled-tasks/yepis-pipeline/SKILL.md`. The in-repo workflow continues to provide best-effort GH-side coverage; the local task provides the floor.

## Confidence assessment for additional in-repo fix

**High confidence:** root cause continues to be GH-side queue scheduling, not workflow-side. No in-repo workflow change shipped on 2026-05-04 would have changed today's outcome — all three slots before 09:45 UTC were dropped at the GH-scheduling layer before any workflow code could run.

**Low confidence:** that an additional cron slot would help. All slots share the GH scheduling queue, and intra-day correlation (today 0/2 slots fired before fallback; 2026-05-03 0/3 likewise; 2026-05-02 0/2 before the late-cancelled run) suggests platform-load-driven correlated drops, not independent draws. Adding `17 1` or `17 13` adds lottery tickets at the same odds.

**No fix shipped today.** The five-day pattern is consistent; the local fallback is now proven for two consecutive days. Speculative cron changes risk masking signal in the data without changing outcomes.

## Operator note: Claude background-task orchestration false alarm

During today's manual run, three early background-task invocations of the pipeline reported `exit code 0` to the orchestrator within seconds of launch despite the actual subshell still running for ~10 minutes afterward and ultimately producing the correct enriched output. This is an orchestrator-side artifact — backgrounding via `cmd &` from within a wrapper script causes the parent to exit immediately while the `&` subshell continues independently — not a pipeline bug. The eventual output is correct. The lesson for future runs of the manual fallback: prefer foreground execution with `python -u … > log 2>&1; echo "exit=$?"` and a generous `timeout` on the Bash call over `cmd &` patterns. The HANDOVER.md quick-start (foreground `{ … } > /tmp/yepis.log 2>&1`) is already correct for this; it's the bg-with-`&` adaptation that misled diagnostics.

A second-order lesson: redirect ordering matters. `python -u … 2>&1 > /tmp/log` discards stderr to the original stdout (terminal) instead of merging into the log; correct order is `> /tmp/log 2>&1`. The wrong order made early `infer.py` runs look as if they died at "batch 1: 20 items -> DeepSeek" — the rest of the output was going to a now-detached terminal. Foreground re-runs with the correct order showed the full successful trace.

Neither artifact affected today's published content. Calling it out so the next operator (or the next scheduled-task fire) doesn't waste time on the same red herring.

## Anonymity (task 2)

Clean. Whole-word regex sweep across working tree for the operator's personal identifiers (given-name, given-name-surname compound, surname, employer-domain) and `/Users/<redacted>` paths returns zero matches. The substring `dev5` appears in `HANDOVER.md` only as the path component `~/dev5/yepisyeniturkiye.github.io`, which is generic and does not identify the operator. Substring matches of the operator's given-name fragment in news content (Turkish word for 'containing'; unrelated English/Spanish vocabulary; names of public figures) are not personal. Authorship throughout history is `Yepisyeni Türkiye <yepisyeniturkiye@gmail.com>` only. No history rewrite needed at the time of this entry.
## Hour-check (task 3)

Live page re-verified at 10:45 UTC (+1h03m after push at 09:42 UTC): title `2026-05-04`, body size 110,978 bytes (unchanged from immediate post-push snapshot), all 8 regions still linked (mena, latam, africa, asia, eu, uk, us, global), TR/EN toggle present, OSINT footer populated. No partial rendering, no regression, no stale content. No `cortex-generic` golden pathway invocation needed because nothing broke during the wait window.

The 10:17 UTC scheduled cron slot for today produced no GH Actions run by 10:45 UTC, extending the day's drop count to 3/3 — same shape as 2026-05-03. No follow-up push required; the manually published 5cd55e4 is the day's content of record.
