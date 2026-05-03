# Yepis pipeline — 2026-05-03 manual-publish diagnosis

## Today's outcome (UTC)

- 07:06 — task fires; live site shows `<title>... · 2026-05-02</title>`. No GH Actions scheduled run for today.
- 07:09 — local fetch+infer pipeline started after PII sweep (clean).
- 07:13 — push as `5cfd431` ("Publish 2026-05-03 (manual: cron missed 04:17 UTC slot)"); 394 clusters across 8 regions, 0 carry-over needed.
- 07:25 — GH Pages live; title flips to 2026-05-03.
- 07:27 — `gh run list` confirms 0 scheduled runs today; 04:17 dropped, 07:17 dropped (now +10m past slot).
- 08:26 — re-verification after 1-hour wait: live page healthy, all 8 regions still populated, no regression.
- 08:26 — 10:17 UTC slot still pending at writing time.

## Manual intervention required: yes

The 04:17 and 07:17 UTC scheduled cron slots both dropped. The 10:17 UTC slot remains pending and may fire late (or drop, like 2026-05-02's 10:17).

## Four-day baseline of the triple-cron mitigation

Triple-cron (`17 4`, `17 7`, `17 10` UTC) shipped in `546061b` on 2026-04-30. Four full days of empirical data:

| Date | Slots fired | Drift relative to slot | Notes |
|---|---|---|---|
| 2026-04-30 | 2/3 | 04:17 → +6h13m, 07:17 → dropped, 10:17 → +5h43m | First day of triple cron. |
| 2026-05-01 | 3/3 | 04:17 → +5h53m, 07:17 → +4h19m, 10:17 → +4h17m | All slots fired but every one ≥4h late. |
| 2026-05-02 | 1/3 (cancelled) | 04:17 → dropped, 07:17 → dropped, 10:17 → +3h56m (cancelled mid-run) | Worst day for landing fresh content; manual publish required. |
| 2026-05-03 | 0/3 (so far, through 08:26 UTC) | 04:17 → dropped, 07:17 → dropped, 10:17 → pending | Extends the 05-02 pattern. |

Across 12 cron slots on 4 days: 6 fired (all 4-6h late, 1 cancelled mid-run), 5 dropped entirely, 1 still pending. Drop-or-cancel rate ≈ 50%. The 04:17 UTC slot has yet to land fresh content within an hour of its scheduled time on any of the four days observed.

This is the same root cause documented in `cron-drift-2026-05-01.md`, `cron-drift-2026-05-02.md`, and the inline `schedule:` comment in `.github/workflows/ingest.yml`: GitHub Actions free-tier scheduled cron is queue-dropped under platform load. Triple-cron mitigation reduces but does not eliminate the drop rate; latency is unchanged.

## What changed in framing today

Yesterday's recommendation flagged three external fixes — external trigger service, local launchd, self-hosted runner — and called them "out of scope for this run." Today's task fire makes the second one operational reality.

The Claude Code scheduled-tasks system on the operator's machine is now firing this exact pipeline daily. When GH cron drops a slot, the local fire-and-publish path picks it up. Today's `5cfd431` commit is the first day where that handoff has run end-to-end without hand-holding: cron dropped, scheduled-task fired, pipeline completed locally, push succeeded, Pages flipped, hour-check passed.

In effect, the genuine fix is already shipped. It does not live in this repo — it lives in `~/.claude/scheduled-tasks/yepis-pipeline/SKILL.md`. The in-repo workflow continues to provide best-effort GH-side coverage; the local task provides the floor.

## Confidence assessment for additional in-repo fix

**High confidence:** root cause continues to be GH-side queue scheduling, not workflow-side. Workflows that do fire still complete (the 2026-05-02 14:13 run was cancelled mid-infer because Job B is timing-tight, not because the cron was broken).

**Low confidence:** that an additional cron slot would help. All slots share the GH scheduling queue, and intra-day correlation (today 0/2 slots fired before fallback; 2026-05-02 0/2 likewise) suggests platform-load-driven drops, not independent draws. Adding `17 1` or `17 13` adds lottery tickets at the same odds.

**No fix shipped today.** The four-day pattern is consistent; the local fallback is now proven. Speculative cron changes risk masking signal in the data without changing outcomes.

## Recommendation: hold the line; observe the local fallback

- Keep the triple-cron as-is. It still produces some fresh GH-side runs and supports the trihourly-aggregation intent on days when slots do fire.
- Continue letting the scheduled-task fire daily; today is day 1 of provably-end-to-end local fallback.
- If a week of operation produces a day where both GH cron and the scheduled-task fail, escalate to option 1 (external trigger service hitting `workflow_dispatch` from a separate provider).

## Anonymity (task 2)

Clean. Whole-word regex sweep across working tree and full git history for the operator's personal identifiers (given name, surname, employer-domain), `/Users/<redacted>` paths, and personal email patterns returns zero matches. Authorship throughout history is `Yepisyeni Türkiye <yepisyeniturkiye@gmail.com>` only. Substring matches in news content (e.g. operator's given-name fragment inside the Turkish word for 'containing') are not personal. No history rewrite needed at the time of this entry.
## Hour-check (task 3)

Live page re-verified at 08:26 UTC: 2026-05-03 title, all 8 regions populated (MENA 8, LATAM 63, Africa 4, Asia 111, EU 17, UK 9, US 152, Global 43), convergent strip rendering, TR/EN toggle present, OSINT dashboard fully populated across Maritime / Aviation / Trade / Satellite / Sanctions / Conflict / Infrastructure categories. No partial rendering or stale content. No `cortex-generic` golden pathway invocation needed because nothing broke during the wait window.
