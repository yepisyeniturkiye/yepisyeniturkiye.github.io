# Phase 3 — Inference Pipeline

Daily pass that turns the raw trihourly (currently daily) feed into a
clustered, bilingual, optionally-obscured published view.

## Shape

```
cron (daily 06:00 UTC)
  │
  ├─ fetch.py  ── pulls live feeds → feed/YYYY/MM/DD/HH.{json,md}
  │
  └─ infer.py  ── reads last 24h of feed/
                  tags items with obscuring flag from sources.yaml
                  batches into groups of 40
                  per-batch DeepSeek call (clustering + bilingual synthesis)
                  writes enriched/YYYY-MM-DD.{json,md}
                  rebuilds index.md as the enriched view
```

Both scripts run in one Actions job. Commit author is `Yepisyeni Türkiye
<yepisyeniturkiye@gmail.com>`. Secrets needed in repo settings:
`DEEPSEEK_API_KEY`.

## Cadence

Starting **daily** (06:00 UTC). One
Actions run per day. At ~5–10 min per run, that's 150–300 min/month against
the 2000 min free tier — comfortable headroom.

If the first week shows the budget is ample, bump fetch.py to trihourly
(cron `0 */3 * * *`) while keeping infer.py daily. Run fetch in its own
workflow with no Playwright cache dependency on infer.

## Balancing loud vs. smaller-voice sources

Well-funded Anglo and Brazilian outlets emit 5–10× the item volume of
smaller regional / Global South voices. Without mitigation the clustering
pipeline amplifies this: a 30-item AlterNet feed forms a dominant cluster
at the top of the page every day while a 10-item +972 or Tricontinental
or Dongsheng post sinks to the bottom.

Two mechanisms, applied at different layers:

**Fetch-layer cap** (`fetch.py`, `MAX_ITEMS_PER_SOURCE = 8`). After
canonical-URL dedup against the 7-day history, each source contributes at
most 8 newest items per run. Small-voice sources (≤8/run) are untouched.
High-volume sources (Truthout 100, OCCRP 60, Brasil de Fato 99, AlterNet
30) get capped to their 8 newest. The long-tail volume we lose is mostly
variations-on-a-theme; the top-of-funnel signal survives. This is the
single most important fairness knob.

**Display-layer diversity sort** (`infer.py`, `sort_clusters`). Clusters
are ranked by count of distinct source IDs first, latest publish time
second. A 5-source convergent cluster ("five outlets covering the same
Lebanon ceasefire shift") beats a 1-source repetitive cluster. Convergence
is treated as signal, volume as noise.

Open to revisit if observation shows the cap is too sharp for a specific
high-quality investigative source (OCCRP is the most likely candidate).
Per-source overrides can live as a `max_items: N` field in `sources.yaml`
when needed.

## Obscuring discipline

Some sources publish heat-attracting framing that creates legal and
reputational exposure risk if surfaced verbatim under the Yepisint brand.
These sources are flagged `obscuring_required: true` in `sources.yaml`:

- `the-grayzone`
- `mintpress-news`

The inference pass checks each cluster's members. If **all** members are
obscuring-flagged, the EN/TR synthesis uses wire-service voice and
attributes factual claims to the source by name. If any member is from an
unflagged source, normal neutral voice is used. The flag is NOT a censor —
it gates framing, not facts. An obscured cluster still appears, with its
sources fully linked.

This is a publisher-side editorial choice, not an opinion on the source.
Direct links remain in the sources block of each cluster.

## Clustering model

Single DeepSeek call per 40-item batch. Prompt returns JSON with
`{clusters: [{member_ids, title_en, title_tr, synthesis_en, synthesis_tr}]}`.
Combined clustering + synthesis minimizes call count.

Cost estimate at 500 items/day:
- ~13 batches × ~3K input + ~4K output tokens = ~40K in + 52K out per day
- DeepSeek: $0.14/M in, $0.28/M out → roughly **$0.02/day**, **~$0.60/month**

## Cross-batch clustering gaps

Items in different batches never cluster together. With 40-item batches
and ~500 items/day this means occasional duplicates across clusters.
Accepted for MVP. Fix-later options:
1. Increase batch size to 80-100 (DeepSeek handles 128K context easily).
2. Two-pass: local TF-IDF rough-cluster first, then DeepSeek on rough clusters.
3. Post-process: find near-duplicate cluster titles and merge.

## Rendering

`enriched/YYYY-MM-DD.md` is the daily artifact. `index.md` is overwritten
on each run to be the latest enriched view. Raw per-hour output stays
under `feed/` for audit trail and timeline artifact use.

Turkish leads each cluster card, English in italic underneath. This is the
Yepis audience default.

## What Phase 3 does NOT do

- OSINT monitor dashboard cards (deferred — will render `link_only`
  entries in a separate `dashboard.md` in Phase 3.5)
- Per-region and per-category index pages (deferred)
- Inference-result rotation beyond daily (the design supports it but we
  start at once-per-day)
- Convergence-based story surfacing (currently all clusters render; a
  future pass could sort by member count to elevate stories with N+ source
  coverage)
