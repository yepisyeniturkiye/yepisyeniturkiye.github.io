# Phase 0 — Source Audit for Yepisint

## Context (self-contained, no prior session needed)

Yepisint is a public-benefit news aggregator being built as a static site on GitHub Pages.
It will run a trihourly cron that ingests a fixed set of anti-imperialist / left / Global South
news sources, then publishes structured data + rendered markdown to the repo. No customers,
no login, just visitors. Commit history doubles as a timeline artifact.

Before any code is written, the source list needs to be audited. The curated list below
comes from the Yepisyeni Türkiye X account and enumerates the actual sources the project
will aggregate. Each entry needs to be checked for a machine-ingestable feed.

**Legal constraint:** only ingest content from RSS/Atom feeds, public YouTube channel feeds,
or similar public syndication formats. No auth bypass. No scraping behind paywalls.
Fair-use headline + link aggregation only.

## Your task

Produce `sources.yaml` at the repository root.

For each source in the list below:
1. Resolve its public website (use web search if needed; most have known domains).
2. Find an RSS/Atom feed URL on that site. Check the usual places:
   - `/feed`, `/rss`, `/feed/atom`, `/rss.xml`, `/atom.xml`
   - `<link rel="alternate" type="application/rss+xml">` in the HTML head
   - `/feeds/posts/default` (Blogger)
   - `/feed/` (WordPress default)
   - For Substack: `<host>/feed`
3. For YouTube-only sources, resolve the channel and emit the YouTube channel RSS URL
   in the form `https://www.youtube.com/feeds/videos.xml?channel_id=UCxxxxxxxx`.
   You can find the channel ID via View Source on the channel page.
4. Verify the feed is live by fetching it (curl, check HTTP 200 and valid XML).
5. Record the result.

**Do not include sources whose feeds you could not verify. Mark them `status: dead`
or `status: no_feed` and leave the `feed_url` field empty.**

## Output schema

```yaml
# sources.yaml
# Generated <date>. Regenerate by rerunning Phase 0 brief.
sources:
  - id: alternet                        # stable slug, lowercase, hyphens allowed
    name: AlterNet                      # canonical display name
    homepage: https://www.alternet.org  # canonical https URL
    feed_url: https://www.alternet.org/feeds/feed.rss
    feed_type: rss                      # rss | atom | youtube
    category: general_left              # see buckets below
    region: us                          # us | uk | eu | latam | africa | mena | asia | global
    language: en                        # ISO 639-1
    status: live                        # live | no_feed | dead | auth_required
    notes: ""                           # optional short note; only non-obvious gotchas
    last_verified: 2026-04-20           # ISO date you verified the feed returned 200 + valid XML
```

### Category buckets (use these exact values, match the Turkish source list)

- `general_left` — AlterNet, Common Dreams, Democracy Now!, The Nation, Jacobin, In These Times, Truthout, The Real News Network, Monthly Review
- `anti_imperialism` — Geopolitical Economy Report, MintPress News, World Socialist Web Site, Tricontinental, The Grayzone, CounterPunch, Investig'Action, Alborada
- `movements_labor` — Liberation News, People's Dispatch, Fight Racism! Fight Imperialism!, ROAR Magazine
- `video` — BreakThrough News, People's World, Novara Media, Gravel Institute, Empire Files, Redfish
- `regional` — everything under "Bölgesel Haber Kaynakları" below

## The sources (verbatim from Yepisyeni Türkiye)

### General left
- AlterNet
- Common Dreams
- Democracy Now!
- The Nation
- Jacobin
- In These Times
- Truthout
- The Real News Network
- Monthly Review

### Anti-imperialism-centered
- Geopolitical Economy Report (Ben Norton, substack + youtube)
- MintPress News
- World Socialist Web Site
- Tricontinental: Institute for Social Research
- The Grayzone

### People's movements and labor
- Liberation News
- People's Dispatch
- Fight Racism! Fight Imperialism!

### Video-first platforms
- BreakThrough News
- People's World
- Novara Media
- Gravel Institute
- Empire Files (Abby Martin)

### Regional
- Mondoweiss (Israel/Palestine from anti-imperialist angle)
- Resumen Latinoamericano (Latin America social movements)
- Brasil de Fato (Brazil)
- Pan African TV (Africa)
- NewsClick (India)
- Dongsheng (China from left perspective)
- New Frame (South Africa)
- Madaar (MENA social movements)
- Palestinian People's Party
- ArgMedios (Argentina video)
- Landless Workers' Movement (MST, Brazil)
- Workers' Central Union of Cuba (CTC)
- National Union of Metal Workers of South Africa (NUMSA)

### Addendum (posted Dec 9, 2024)
- CounterPunch
- ROAR Magazine
- Alborada
- Investig'Action
- Redfish

## Approach guidance

- Batch your work. For each source: curl the homepage, grep for `alternate` link tags,
  try the conventional feed paths, stop as soon as one returns valid XML.
- Many of these sites are WordPress; `/feed/` is the default and will work.
- Substack sites: `/feed` (no trailing slash) returns RSS.
- YouTube channels need the channel ID (UC...). View-source on the channel page and search
  for `"browseId":"UC` or `"channelId":"UC`.
- Do not worry about perfection. The goal is a correct, verified list of what's ingestable
  right now. If Redfish is defunct (it had issues around the RT disruption), mark it dead
  and move on.
- If a source has multiple feeds (e.g. a "news" feed and an "opinion" feed), pick the
  comprehensive one or pick news. Note in `notes` if you had to choose.
- Do not invent feed URLs. If you can't verify, mark `no_feed`.

## When you're done

- Write `sources.yaml` at the path above.
- Also write a short `PHASE0_REPORT.md` in the same directory:
  - How many sources are live vs. no_feed vs. dead.
  - Any surprises (defunct orgs, renamed sites, changed domains).
  - Sources that need manual follow-up (e.g. YouTube-only with unclear channel).
- Do not commit anything. Do not create GitHub accounts. Do not write the fetcher.
  Phase 0 ends at the audit.
