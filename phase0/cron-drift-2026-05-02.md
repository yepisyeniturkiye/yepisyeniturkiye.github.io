# Yepis pipeline — 2026-05-02 manual-publish diagnosis

## Today's outcome (UTC)

- 07:07 — task fires; live site shows `<title>... · 2026-05-01</title>`. No GH Actions scheduled run for today.
- 07:10 — local fetch + infer started after PII history rewrite (see below).
- 07:33 — local infer completed (30 batches, 552 clusters across 8 regions). Push as `c2f7bcf`.
- 07:35 — GH Pages live; title flips to 2026-05-02. All 8 regions populated, 0 carry-over needed.
- 07:40 — OSINT distillation refreshed (yesterday's snapshot was 17h stale); push as `e80c686`.
- 08:35 — re-verification after 1-hour wait: live page healthy, 210 OSINT cards, 552 clusters, no regression.
- 08:36 — `gh run list` confirms still 0 scheduled runs today; the 04:17 and 07:17 UTC slots both dropped (now +4h19m and +1h19m past respectively). 10:17 UTC slot pending at writing time.

## Manual intervention required: yes

The 04:17 and 07:17 UTC scheduled cron slots both dropped silently. The 10:17 UTC slot is still pending and may fire late (yesterday's 10:17 fired at 14:34, +4h17m).

## Three-day baseline of the triple-cron mitigation

Triple-cron (`17 4`, `17 7`, `17 10` UTC) shipped in `546061b` on 2026-04-30. Three full days of empirical data:

| Date | Slots fired | Drift relative to slot | Notes |
|---|---|---|---|
| 2026-04-30 | 2/3 | 04:17 → +6h13m, 07:17 → dropped, 10:17 → +5h43m | First day of triple cron. |
| 2026-05-01 | 3/3 | 04:17 → +5h53m, 07:17 → +4h19m, 10:17 → +4h17m | All slots fired but every one ≥4h late. |
| 2026-05-02 | 0/3 (so far, through 08:36 UTC) | 04:17 → dropped, 07:17 → dropped, 10:17 → pending | Worst day so far; manual local publish required. |

Across 9 cron slots on 3 days: 5 fired (all 4-6h late), 3 dropped entirely, 1 still pending. Drop rate ≈ 33%. Even when slots do fire, the live site does not get today's title flip until ~14-16 UTC under the trihourly intent; the 04:17 slot has yet to land within an hour of its scheduled time on any of the three days observed.

This is the same root cause documented in [cron-drift-2026-05-01.md](cron-drift-2026-05-01.md) and the inline `schedule:` comment in `.github/workflows/ingest.yml`: GitHub Actions free-tier scheduled cron is queue-dropped under platform load. The triple-cron mitigation reduces but does not eliminate the drop rate; latency is unchanged.

## Confidence assessment for in-repo fix

**High confidence:** the failure mode is GitHub-side queue scheduling, not workflow-side. Workflows that *do* fire complete successfully; runs that don't start are simply never dispatched.

**Low confidence:** that an additional cron slot would help. All slots share the same scheduling queue, so adding `17 1` or `17 13` does not address the upstream drop rate; it only adds more lottery tickets at the same odds. Yesterday all three slots fired and today none have, which suggests the drop rate is correlated across slots within a day (platform-load-driven), not independently random.

The genuine fix lives outside this repo:

1. **External trigger** (cron-job.org, EasyCron, Cloudflare Cron Triggers, or a small VPS calling `POST /repos/:owner/:repo/actions/workflows/ingest.yml/dispatches`). Removes dependency on GH-internal scheduling. Requires a fine-grained PAT stored in the external service.
2. **Local scheduler.** A `launchd` plist on the operator's machine running the same pipeline as `HANDOVER.md`'s quickstart, pushing via the SSH deploy alias. Same effective behavior as today's manual publish, automated.
3. **Self-hosted runner** with its own `launchd`/systemd schedule. Heaviest lift; only justified if 1 and 2 are insufficient.

## Recommendation: defer in-repo fix; escalate externally

No in-repo cron change is shipped today. The evidence supports the diagnosis but not a code-side remediation. Yesterday's recommendation ("do not ship a speculative cron change") still holds — today's data extends the same pattern rather than introducing new evidence that points at a workflow-level fix.

Concrete next step (out of scope for this run): set up option 2 (local launchd) or option 1 (external trigger). Either delivers the trihourly intent without GH-internal scheduling dependency.

## Anonymity (task 2)

A literal PII string was found in `phase0/cron-drift-2026-05-01.md` from yesterday's session — a regex pattern containing the operator's name and employer was committed verbatim as part of the audit log. This was caught and rewritten:

- The offending commit `669e71f` was soft-reset, the file sanitized to remove the literal pattern, and a replacement commit `ab6f619` produced.
- Six subsequent CI commits from yesterday afternoon (`f849a10` through `88d2fcb`) were cherry-picked onto the rewritten history.
- A force-push with lease overwrote `origin/main`. Post-push history scan: clean. Working tree scan: clean.

Residual exposure: the original `669e71f` SHA is no longer reachable from `main`, but the blob remains in GitHub's storage until their internal gc runs (opaque timing, typically days). Direct-SHA URLs for that commit may still resolve in the meantime. If complete erasure is needed sooner, file a GitHub Support request for expedited reflog gc.

## Live verification — what was and was not checked

- **Static markup:** verified via curl + regex parse. All required structural elements present:
  - `<title>` shows 2026-05-02
  - 8/8 region columns rendered
  - 7 OSINT band tracks (`band-viewport`/`band-track`) with TR/EN labels populated
  - 210 OSINT cards (190 distilled item cards + 20 static reference cards) across the bands
  - Language toggle markup present: `data-lang` attribute, `lang-toggle` class, `t-tr`/`t-en` per-language siblings, body classes `s-tr`/`s-en`
  - Convergent strip rendered with 16 articles
  - All 552 clusters present in source HTML

- **Interactive behavior NOT verified:** TR/EN toggle click, OSINT band horizontal scroll, and any JS hydration paths were not exercised because the cortex-generic browser tool failed with a path bug (`ENOENT: mkdir '/.playwright-mcp'`) and the Playwright MCP profile was locked by a parallel session. Markup is structurally correct so behavior should follow, but visual/interaction confirmation is owed.

## What changed in the working tree today

```
ab6f619  phase0: log cron drift observations from 2026-05-01 manual publish (sanitized rewrite of 669e71f)
96175b3  fetch+render: 2026-05-01T10:15Z (cherry-picked)
4c63771  infer: 2026-05-01T11:33Z (cherry-picked)
4ae7cf0  fetch+render: 2026-05-01T11:42Z (cherry-picked)
f57efa1  infer: 2026-05-01T13:04Z (cherry-picked)
4628a35  fetch+render: 2026-05-01T14:43Z (cherry-picked)
e7275f9  infer: 2026-05-01T16:10Z (cherry-picked)
c2f7bcf  Publish 2026-05-02 (manual: scheduled cron missed 04:17 UTC slot)
e80c686  osint: distill platform content + re-render 2026-05-02T07:40Z
```
