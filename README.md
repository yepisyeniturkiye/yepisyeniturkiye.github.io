# Yepisyeni Türkiye

Trihourly multipolar news and OSINT aggregation. Public benefit. No customers.

## Status

**Phase 0 — Source audit.** Complete. Artifacts in [`phase0/`](phase0/):
- [`sources.yaml`](phase0/sources.yaml) — 70 entries across three layers (news / curator / OSINT monitor)
- [`PHASE0_REPORT.md`](phase0/PHASE0_REPORT.md) — audit summary, rejections, gaps

## What this is

A static site that aggregates stories every three hours from a fixed set of:

- Anti-imperialist and left-leaning news publishers
- A follower-curated Inoreader feed covering the subset not otherwise ingestable
- Public OSINT monitors: shipping (AIS), aviation (ADS-B), trade flows, satellite imagery, sanctions/corporate registries, conflict event data, general infrastructure monitors

The commit history of this repo doubles as the timeline artifact — every trihourly run emits structured JSON + rendered markdown.

## What this is not

- Not a commentary platform
- Not a commercial service
- Not affiliated with any party, state, or organization

## Filters applied

- **Legal:** No sanctioned outlets. No affiliates of banned organizations in applicable jurisdictions.
- **Ethical:** No doxxing feeds. No individual-targeting regardless of legality.
- **Editorial:** Aggregator, not editor. Inference obscuring applied to heat-attracting sources via LLM pass (planned Phase 3).
