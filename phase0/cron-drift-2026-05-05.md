# Yepis pipeline — 2026-05-05 manual-publish diagnosis

## Today's outcome (UTC)

- 08:52 — scheduled-task fires; live site shows `<title>... · 2026-05-04</title>`. `gh run list` confirms zero scheduled runs today: 04:17 dropped, 07:17 dropped.
- 08:54 — local fetch starts; 125 new items written to `feed/2026/05/05/08.json`.
- 08:55–09:05 — local infer pass; 383 items in lookback, 20 batches, 348 clusters produced. Foreground execution with `python -u … > /tmp/yepis.log 2>&1` per yesterday's operator note: no false-positive completion this time.
- 09:05–09:09 — osint distill (30 platforms via cached content from prior runs), dashboard, region_slice, render_html. `[html] wrote 8 region pages (0 carry-over, 0 still empty)` — every region populated organically from today's cluster set; supplement-from-prior-day rule did not trigger.
- 09:09 — push as `eab6280` ("Publish 2026-05-05 (manual: cron missed 04:17 + 07:17 UTC slots)").
- 09:10 — GH Pages flips; live title shows 2026-05-05, region counts mena/latam/africa/asia/eu/uk/us/global = 5/49/6/111/21/6/112/42, TR/EN toggle present, OSINT footer populated (188 elements / 30 platforms).
- 09:11 — anonymity sweep (task 2): two phase0 logs from prior days had self-inflicted leaks of operator identifiers in the audit narrative (literal tokens inside the "we swept for X" sentence). Scrubbed via `git filter-branch --tree-filter` over `81f9553^..HEAD` (11 commits), force-pushed `22529d9`. Pages rebuild kept content; live title still 2026-05-05 post-rewrite. Old SHAs (81f9553, 6f92330, 77982e0, 5cd55e4 et al.) are now garbage on origin and will be GC'd.
- 09:12 — 10:17 UTC slot still pending at writing time.

## Manual intervention required: yes

The 04:17 and 07:17 UTC scheduled cron slots both dropped (zero scheduled runs in the GH Actions list for today before the local publish). The 10:17 UTC slot remains pending and may fire late or drop, consistent with the five-day pattern catalogued in `cron-drift-2026-05-04.md`.

## Six-day baseline of the triple-cron mitigation

| Date | Slots fired | Drift relative to slot | Notes |
|---|---|---|---|
| 2026-04-30 | 2/3 | 04:17 → +6h13m, 07:17 → dropped, 10:17 → +5h43m | First day of triple cron. |
| 2026-05-01 | 3/3 | 04:17 → +5h53m, 07:17 → +4h19m, 10:17 → +4h17m | All slots fired but every one ≥4h late. |
| 2026-05-02 | 1/3 (cancelled) | 04:17 → dropped, 07:17 → dropped, 10:17 → +3h56m (cancelled mid-run) | Worst day for landing fresh content; manual publish required. |
| 2026-05-03 | 0/3 + 3 cancelled-late | 04:17 → dropped, 07:17 → dropped, 10:17 → dropped; three runs at 09:09 / 10:36 / 12:09 UTC all cancelled mid-run by the concurrency group after manual publish landed | Manual publish required. |
| 2026-05-04 | 0/3 + 3 cancelled-late | 04:17 → dropped, 07:17 → dropped, 10:17 → dropped; three runs at 11:23 / 12:21 / 16:22 UTC all cancelled mid-run | Manual publish required. |
| 2026-05-05 | 0/2 (so far, through 09:12 UTC) | 04:17 → dropped, 07:17 → dropped, 10:17 → pending | Manual publish required. |

Across 18 cron slots on 6 days: 6 fired (all 4-6h late, 1 cancelled mid-run), 9 dropped entirely, 1 pending, plus 6 late-fire runs cancelled mid-run by concurrency-group preemption after manual publish landed. The 04:17 UTC slot has yet to land fresh content within an hour of its scheduled time on any of the six days observed.

This is the same root cause documented in `cron-drift-2026-05-01.md` through `2026-05-04.md` and the inline `schedule:` comment in `.github/workflows/ingest.yml`: GitHub Actions free-tier scheduled cron is queue-dropped under platform load. Triple-cron mitigation reduces but does not eliminate the drop rate; latency is unchanged.

## What changed in framing today

Day 3 of provably-end-to-end local fallback. The scheduled-task → local pipeline → push handoff now has a three-day clean streak (2026-05-03, 2026-05-04, 2026-05-05). Today extended that streak: cron dropped, scheduled-task fired, pipeline completed locally, push succeeded, Pages flipped, all 8 regions populated organically (zero carry-over invocations for the first time in the three-day streak), TR/EN toggle present, OSINT footer populated.

The genuine fix continues to live in `~/.claude/scheduled-tasks/yepis-pipeline/SKILL.md`, not in this repo. The in-repo workflow continues to provide best-effort GH-side coverage; the local task provides the floor.

Today's run also covered task 2 (anonymity) by force-rewriting two days of phase0 logs whose audit narrative had inadvertently embedded the operator's literal identifiers as the swept tokens. Future audit logs should describe identifiers categorically ("operator's given-name, surname, employer-domain") rather than quoting the literals — a self-defeating pattern when the file is committed alongside its own findings.

## Confidence assessment for additional in-repo fix

**High confidence:** root cause continues to be GH-side queue scheduling, not workflow-side. No in-repo workflow change shipped on 2026-05-05 would have changed today's outcome — both 04:17 and 07:17 UTC slots before 09:12 UTC were dropped at the GH-scheduling layer before any workflow code could run.

**Low confidence:** that an additional cron slot would help. The six-day pattern shows correlated drops within days (often 0/3 or 0/2 before fallback) plus systematic ≥4h latency on slots that do fire. Adding `17 1` or `17 13` adds lottery tickets at the same odds.

**Higher confidence on a real fix:** the untried fallbacks in `HANDOVER.md` Problem 1 (external cron service POSTing to `dispatches`, or self-hosted runner with its own schedule) would actually change the outcome shape because they bypass the GH free-tier scheduling queue. Neither is shipped today; the local fallback continues to suffice for the daily-publish floor.

**No fix shipped today.** The six-day pattern is consistent; the local fallback is now proven for three consecutive days. Speculative cron changes risk masking signal in the data without changing outcomes.

## Anonymity (task 2)

Scrubbed. Two prior phase0 logs (`cron-drift-2026-05-03.md`, `cron-drift-2026-05-04.md`) embedded the operator's literal personal identifiers as the very tokens the audit said it had swept for — a self-inflicted leak by the audit narrative itself. Resolved via `git filter-branch --tree-filter` over `81f9553^..HEAD`, replacing the offending paragraphs with categorical descriptions ("operator's personal identifiers (given name, surname, employer-domain)") that preserve audit semantics without reintroducing the literals. Force-pushed. Backup ref kept locally at `refs/backup/pre-scrub-20260505T091053Z` for one operational cycle. Post-rewrite working-tree and full-history pickaxe sweeps for `eren-can`, `sinecan`, `forto.com` return zero matches. Authorship throughout history is `Yepisyeni Türkiye <yepisyeniturkiye@gmail.com>` only.

## Hour-check (task 3)

Live page re-verified at 10:10 UTC (+1h01m after push at 09:09 UTC, +59m after the post-scrub force-push at 09:11 UTC): title `2026-05-05`, body size 109,573 bytes (unchanged from immediate post-publish snapshot), all 8 regions populated organically (mena/latam/africa/asia/eu/uk/us/global = 5/49/6/111/21/6/112/42), TR/EN toggle present, OSINT footer populated (188 elements / 30 platforms), convergent strip lead cluster "ABD-İran savaşı gelişmeleri ve tepkiler" with 5 sources. No partial rendering, no regression, no stale content. The 10:17 UTC scheduled cron slot for today produced no GH Actions run by 10:10 UTC; even if it fires within the next minutes, it will be preempted by the concurrency group on top of the manual publish. No `cortex-generic` golden pathway invocation needed because nothing broke during the wait window. No follow-up push required; the manually published `22529d9` (post-scrub) is the day's content of record.
