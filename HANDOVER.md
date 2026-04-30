# HANDOVER — Yepisint Operations

If you're picking this up cold, everything you need is here.

## Quick Start: Manual Pipeline Run

From scratch on the machine this repo lives on (`~/dev5/yepisyeniturkiye.github.io`),
this publishes today's content to https://yepisyeniturkiye.github.io/:

```bash
cd ~/dev5/yepisyeniturkiye.github.io
source .venv/bin/activate
export DEEPSEEK_API_KEY=$(awk -F= '/^export DEEPSEEK_API_KEY/{gsub(/"/,""); print $2}' ~/.zshrc)
git pull -q origin main

# Full pipeline — fetch + cluster + render + commit + push.
# Takes 15-30 min. DO NOT KILL IT mid-run regardless of how quiet it looks.
# Progress streams to /tmp/yepis.log; tail it from a second terminal.
{
  python -u fetch.py
  python -u infer.py
  python -u region_slice.py
  python -u dashboard.py
  python -u render_html.py
  git add -A
  git commit -q -m "Publish $(date -u +%Y-%m-%d)"
  git push
} > /tmp/yepis.log 2>&1
```

**The `python -u` flag is critical.** Without it, stdout gets pipe-buffered
and per-batch progress is invisible, which caused us on 2026-04-22 and
2026-04-23 to kill runs we mistakenly thought had hung. They were
working. See Problem #3 below.

For real-time visibility during a run, in a second terminal:
```bash
tail -f /tmp/yepis.log
```

Expected total runtime on a good day: 15-25 min. Bad DeepSeek day: up
to 45 min. Either way, let it finish.

## GitHub Auth for Ops

The operator may have multiple `gh` CLI identities on the machine. The
Yepisint brand identity is `yepisyeniturkiye`. The repo's `origin`
remote uses an SSH alias that routes to the Yepis SSH key, so
`git push`/`pull` work without switching accounts.

For `gh` CLI operations (trigger workflow, cancel run, set secret)
switch to the brand account, do the thing, and switch back to
whichever account is your default:

```bash
gh auth switch --user yepisyeniturkiye
# do the thing
gh auth switch --user <your-default>
```

Manual CI trigger (useful when the scheduled cron doesn't fire — see Problem #1):
```bash
gh auth switch --user yepisyeniturkiye
gh workflow run ingest.yml --repo yepisyeniturkiye/yepisyeniturkiye.github.io
gh run list --repo yepisyeniturkiye/yepisyeniturkiye.github.io --workflow ingest.yml --limit 3
gh auth switch --user <your-default>
```

## Known Problems

### Problem 1: GitHub scheduled cron fires unreliably

**Symptom:** A single `cron:` slot in `.github/workflows/ingest.yml`
either runs 4+ hours late, or doesn't run at all some days. Workflow
shows `state=active` in `gh workflow list` — GitHub just doesn't
dispatch it. 2026-04-29 had no scheduled run at all; 2026-04-30 also
skipped its 04:17 UTC slot, requiring manual local publish.

**Cause:** documented limitation of GitHub's scheduled event system.
Under platform load, crons get delayed or dropped. Not our code.

**Current mitigation (applied 2026-04-30):** three cron expressions in
`ingest.yml` — `17 4`, `17 7`, `17 10` UTC — give us multiple firing
chances per day. The `concurrency: ingest` group with
`cancel-in-progress: false` ensures only one runs at a time; later
firings queue or get auto-dropped while an earlier run is active.
Idempotent: re-runs produce a few extra commits per day but never
break the site, and they align with the project's stated trihourly
aggregation intent.

**Untried fallback fixes if multi-cron still proves insufficient:**
1. External cron service (cron-job.org, easycron.com, Cloudflare Cron
   Triggers) pings `POST /repos/:owner/:repo/actions/workflows/ingest.yml/dispatches`
   at the desired time. Needs a fine-grained PAT stored in the external service.
2. Self-hosted runner with its own `launchd`/systemd schedule.

### Problem 2: infer.py step consistently times out in CI

**Symptom:** Job B (the infer job in the split workflow) regularly
hits its 35-min timeout cap and gets cancelled. The same code on the
same repo runs locally in 15-25 min.

**Cause:** DeepSeek's streaming response latency is much higher from
GitHub runner IPs than from residential connections. Each 20-item
batch produces ~2000 output tokens; at the runner's observed
~20-30 tokens/sec that's 60-100s per batch. 22 batches × 90s worst
case = 33 min, leaves no margin.

Job A (`fetch_render`) is **not** affected — it uses DeepSeek only
for `osint_content.py`, which sends smaller payloads and completes
reliably. So the site always gets fresh raw feed + OSINT bands, just
not today's clustered enriched view on bad days.

**Untried fixes, ranked by likely payoff:**
1. **Parallel batches** via `concurrent.futures.ThreadPoolExecutor`
   with 4 workers inside `infer.py`'s main loop. 22 batches / 4 ≈ 6
   min wall time even on a slow day. DeepSeek's rate limits should
   allow it (60 RPM on chat model). This is the prime candidate;
   single-file code change.
2. **Reduce `LOOKBACK_HOURS`** from 24 to 8 in `infer.py`. Halves
   batch count. Trade-off: items older than 8h won't get re-clustered
   if they missed a prior run. Compatible with fix 1.
3. **Switch provider for CI only:** Groq's `llama-3.1-70b-versatile`
   or similar. Same OpenAI-compatible client, just change `base_url`
   to `https://api.groq.com/openai/v1` and `model`. Free tier may
   suffice; fall back to paid if not. Local script stays on DeepSeek.
4. **Move infer off GitHub Actions:** cheap VPS (Hetzner / DigitalOcean
   $4-6/mo) in EU region with DeepSeek latency closer to local. Daily
   cron, pushes via SSH deploy key. Nuclear option.

### Problem 3: Pipe-buffered stdout masked healthy progress

**Symptom on 2026-04-22 and 2026-04-23:** after 15-30 min of apparent
silence, I repeatedly killed local `infer.py` runs thinking they had
hung. In reality, `python infer.py | tail -N` holds all stdout in
tail's buffer until the child exits — so no batch output emits until
the whole script finishes. Killing at that point was always wrong.

**Fix (already applied):** use `python -u` (unbuffered) or
`PYTHONUNBUFFERED=1` env var. Never pipe infer.py through `tail` or
`head` when you want to see progress; redirect to a file and use a
separate `tail -f` session.

For the CI pipeline: `PYTHONUNBUFFERED: "1"` is set at the workflow
`env:` level in `.github/workflows/ingest.yml`. Keep it there.

## The Job A / B Split (ingest.yml)

Workflow is deliberately split so infer hanging can't leave the site
without today's fresh data:

- **Job A — `fetch_render`** (20-min cap): fetcher → osint_content →
  dashboard → region_slice → render_html → commit + push. Always
  succeeds in practice. This job alone keeps the site alive, just
  without today's clustered enriched view if infer fails.

- **Job B — `infer`** (35-min cap, `needs: fetch_render`): checkout
  fresh main (pulls Job A's commit), run infer, re-render regions +
  HTML, commit + push. If this times out, Job A's output is already
  live — readers see fresh OSINT bands and raw fetch, plus yesterday's
  clusters until Job B succeeds next time.

Validated: Job A has succeeded on every recent run. Job B is the only
flake.

## File Map

```
yepisyeniturkiye.github.io/
├── fetch.py            # Step 1: RSS/Atom/YouTube + Playwright for OC Portal
├── infer.py            # Step 2: DeepSeek clustering + bilingual synthesis + obscuring
├── osint_content.py    # Step 3: Playwright + DeepSeek distill per OSINT platform
├── region_slice.py     # Step 4: partition enriched clusters by region tag
├── dashboard.py        # Step 5: render static OSINT dashboard (pure python)
├── render_html.py      # Step 6: emit index.html + regions/*.html + dashboard.html
├── sources.yaml        # Source of truth: 79 entries (news + OSINT monitors)
├── feed/YYYY/MM/DD/HH.{json,md}   # Raw fetched items, audit trail
├── enriched/YYYY-MM-DD.{json,md}  # Clustered bilingual output
├── osint_content/*.json           # Per-platform distilled items
├── regions/*.{html,md}            # Per-region pages (8 regions)
├── index.html                     # Home (owned by render_html.py)
├── latest_raw.md                  # Rolling 24h raw feed (owned by fetch.py)
├── dashboard.html                 # OSINT monitor grid (owned by render_html.py)
├── assets/dash.css                # Single stylesheet
├── phase0/ phase3/ phase4/        # Design docs + audit reports
└── .github/workflows/ingest.yml   # CI pipeline
```

## Secrets + Config

- `DEEPSEEK_API_KEY` — local: exported from `~/.zshrc`. CI: GitHub Actions
  repo secret. To rotate: update `~/.zshrc`, then
  `gh secret set DEEPSEEK_API_KEY --repo yepisyeniturkiye/yepisyeniturkiye.github.io`
  as the `yepisyeniturkiye` gh user.
- GitHub Pages serves from `main` branch root with `.nojekyll` present
  (no Jekyll processing; pipeline emits HTML directly).
- Public repo → **unlimited Actions minutes**. No runtime cost concern.
- DeepSeek cost: ~$0.02/day of real runs, ~$0.60/month. Negligible.

## Invariants Already Enforced — Don't Regress These

- **`max_retries=0`** on every OpenAI client. SDK default of 2 retries
  silently 3× the timeout budget. This bit us hard before the fix.
- **Timeouts**: 90s on infer's OpenAI client, 30s on osint_content's.
- **`BATCH_SIZE=20`** in `infer.py`. Was 40; smaller response = shorter
  stream = better CI reliability.
- **`MAX_ITEMS_PER_SOURCE=8`** in `fetch.py`. Prevents loud Anglo
  feeds (Truthout 100/day, OCCRP 60/day, AlterNet 30/day) from
  swamping clusters and drowning out Global South voices.
- **Diversity-first sort** in the convergent strip at top of `index.html`.
  **Recency-first sort** inside region columns. `render_html.py` has
  both `sort_clusters` and `sort_by_recency` for this.
- **`render_html.py` is the sole owner of `index.html`.** `fetch.py`
  writes `latest_raw.md` instead — ownership split prevents rebase
  tangles when both run in the same job.
- **No jurisdiction or personal identifiers in meta docs/configs.** Only
  news-content mentions of countries are kept (editorial neutrality).
  Git history was previously squashed to a single commit to wipe
  earlier drafts that had those leaks.
- **Obscuring flag** (`obscuring_required: true` in `sources.yaml`) on
  The Grayzone and MintPress News. Inference pass applies
  wire-service-voice neutralization for clusters whose members are all
  flagged. Flag gates framing, not content — source links always stay.
- **Zero doxxing.** Hard rule, no exceptions. TrackANaziMerc and
  similar are rejected regardless of legal status.

## What a "Healthy" Daily Output Looks Like

- 100-400 enriched clusters (range varies by news day)
- All 8 regions populated (mena, latam, africa, asia, eu, uk, us, global)
- 30 OSINT monitor cards rendered (some with distilled items, some static)
- `index.html` last-modified today
- Convergent strip shows 5 multi-source clusters, diversity >= 3
- Per-region cards sorted most-recent first
- TR/EN toggle visible top-right, amber pill
