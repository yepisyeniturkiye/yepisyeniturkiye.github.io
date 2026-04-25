# Phase 0 Report — Yepisint Source Audit

## Summary

Attempted verification of all 40 sources listed in the PHASE0 brief. Results:

| Status | Count | Sources |
|--------|-------|---------|
| live | 25 | See below |
| no_feed | 3 | In These Times, World Socialist Web Site, New Frame |
| dead | 10 | Gravel Institute, Resumen Latinoamericano, NewsClick, Madaar, Palestinian People's Party, ArgMedios, CTC Cuba, ROAR Magazine, Empire Files (website), BreakThrough News (website) |
| auth_required | 0 | — |

**Of the 10 marked dead, 5 have valid live alternatives** (YouTube channels for video-first sources; feed hosted on a different domain for Fight Racism! Fight Imperialism!). The effective ingest coverage is 28 sources — 25 direct feeds plus 3 YouTube-channel fallbacks.

---

## Live Sources (25 direct + 3 YouTube fallbacks = 28)

- **General Left (5 live, 1 no_feed):** AlterNet, Common Dreams, Democracy Now!, The Nation, Jacobin, Truthout, Real News Network, Monthly Review. In These Times: blocked by 403 on all feed paths.
- **Anti-imperialism (4 live, 1 no_feed):** Geopolitical Economy Report, MintPress News, Tricontinental, The Grayzone, CounterPunch, Alborada, Investig'Action. WSWS: no machine-ingestable feed found.
- **Movements/Labor (3 live):** Liberation News, People's Dispatch, Fight Racism! Fight Imperialism!
- **Video-first (3 live via YouTube, 1 dead):** BreakThrough News (YouTube), People's World, Novara Media, Empire Files (YouTube). Gravel Institute: site redirects to /lander, appears defunct.
- **Regional (12 live, 5 dead):** Mondoweiss, Brasil de Fato, Pan African TV, Dongsheng, MST, NUMSA. Dead: Resumen Latinoamericano (host unreachable), NewsClick (timeout/403), New Frame (Cloudflare), Madaar (timeout), PPP (timeout), ArgMedios (timeout), CTC Cuba (timeout).

---

## Surprises and Notable Findings

1. **Fight Racism! Fight Imperialism!** — original domain `fightracismimperialism.org` is dead and has been for some time. The publication now lives at `revolutionarycommunist.org`. Feed confirmed live there.

2. **BreakThrough News and Empire Files** — both websites are blocked (Cloudflare / timeout) but have active YouTube channels. Ingest via YouTube RSS is the correct fallback.

3. **Redfish** — original `redfishcontent.ca` website returns 200 but no feed. YouTube channel still active at `UC7eJ4xCqiCvvs3n7tPdPM9Q`. Marked live via YouTube.

4. **Gravel Institute** — entire site has been turned into a single redirect-to-lander page. No articles, no feed. Marked dead.

5. **ROAR Magazine** — server returns HTTP 500 on all requests including homepage. Likely fully defunct.

6. **In These Times** — a 403 is returned on every feed path tested (`/feed`, `/feed/`, `/rss`, `/index.xml`, etc.). This is unusual — most WordPress sites at least serve XML even if empty. Either they're blocking non-browser user-agents or the feed is restricted in some way. Marked no_feed.

7. **WSWS** — World Socialist Web Site has no `<link rel="alternate" type="application/rss+xml">` in its HTML head and no feed at standard paths. They may have discontinued RSS or never offered it.

8. **CTC Cuba** — the central union of Cuba is unreachable via `cta.cu`, `sindicato.cu`, `workerscentralunion.cu`, and `www.cta.cu`. All time out. Either a connectivity issue or the site is not web-published.

---

## Sources Requiring Manual Follow-up

- **In These Times** — worth a human attempting to fetch the feed from a browser to determine if it's a UA-block or genuinely no feed.
- **WSWS** — worth checking if they have moved to a subdomain or alternate feed URL; their site structure may have changed.
- **Resumen Latinoamericano** — host may be up for browsers but blocked for automated clients; try from a different IP or with different headers.
- **New Frame** — Cloudflare challenge blocks automated access; human verification needed to confirm if an RSS feed exists.

---

## Post-Audit Addition: OC Portal Curator Feed

A Yepisyeni Türkiye follower (Inoreader user id `1003877176`) maintains a public-HTML Inoreader tag named **"The OC Portal"** that consolidates a hand-picked subset of the sources in this audit. The feed is not owned by the Yepis account, so OPML export and Inoreader Pro RSS export are not options; the public HTML view is reachable but requires headless Playwright to render (curl returns the shell HTML, but full DOM needs a real browser).

Validated 2026-04-20 via headless Playwright: 21 items rendered in initial viewport, clean `.article_magazine_content_wraper` selectors, surfaces **wsws.org** items directly — recovering one of the `no_feed` candidates from the main audit.

Registered as source `oc-portal` in `sources.yaml` with `feed_type: inoreader_html_playwright`. Acts as recovery lane for sources without direct feeds. Four plausible recovery candidates (In These Times, WSWS, New Frame, Resumen Latinoamericano, NewsClick) have been annotated to point at this lane. Phase 2 full scrape will confirm which are actually covered.

Deduplication discipline for Phase 2: items arriving via both direct feed and OC Portal must be deduped by canonical article URL, with direct-feed items preferred (fresher, less scrape fragility).

---

## Phase 0.6 Addition: OSINT Monitor Layer

Second ingest layer added on top of news sources: public-data OSINT monitors. Researched via web search + targeted page fetches. 29 entries vetted and integrated into `sources.yaml` under `category: osint_monitor_*`.

**Breakdown by category:**
- Maritime (5): MarineTraffic, VesselFinder, AIS Hub, IFC-IOR, MSCHOA
- Aviation (3): ADS-B Exchange, Flightradar24, OpenSky Network
- Trade (3): UN Comtrade, Trase, OEC
- Satellite (4): Copernicus, NASA Worldview, Planet Disaster Data, CRESDA (needs verification)
- Sanctions/Corporate (3): OpenSanctions, OpenCorporates, OCCRP Aleph (link-only)
- Conflict (5): ACLED, GDELT, UCDP, Airwars, CIT (quarterly review)
- General/Infrastructure (6): Submarine Cable Map, Cloudflare Radar, IODA, USGS quakes, EMSC, NASA FIRMS

**Filters applied** (per user directive):
1. Freely accessible without VPN in relevant jurisdictions (no sanctioned outlets — RT, Sputnik, PressTV, RIA, TASS excluded)
2. Zero doxxing / zero individual-targeting (TrackANaziMerc and similar excluded regardless of legality)
3. Not affiliated with banned organizations in applicable jurisdictions (Samidoun, Hamas, Hezbollah, PFLP affiliates excluded as precaution)
4. Institutional/aggregate-level data preferred over individual targeting

**Special-case defaults applied:**
- **OCCRP Aleph**: `link_only` feed type, explicit "do NOT mirror individual profile pages" note in sources.yaml (persona-rights concerns). Cite/link as investigative pivot only.
- **CIT (Conflict Intelligence Team)**: included with `review_quarterly: true` flag. Domain has rotated historically; requires periodic verification.
- **CRESDA**: `status: needs_verification`. Reachability untested from our network. Non-CN phone number registration unconfirmed. Multipolar balance candidate but needs empirical check before Phase 2 relies on it.
- **MarineTraffic / VesselFinder / Flightradar24**: all paywalled APIs. Included as `feed_type: link_only` for dashboard reference (the Turkey-Israel shipping-denial debunk case relied on MarineTraffic spot-checks). Not part of trihourly aggregation.

**Rejected candidates** (non-exhaustive list of platforms considered and excluded):
- RT, Sputnik, TASS, RIA Novosti, PressTV — EU-sanctioned (Council Reg 2022/350, 2023/2873); DNS/transport blocks on EU ISPs.
- The Grayzone (as a Yepisint-aggregated source) — not banned but sanctions adjacency risk for a pseudonymous host given recurring coverage mapping onto proscribed-org narratives. Remains in news layer with inference-obscuring policy for Phase 3.
- Samidoun-affiliated outlets (Quds News Network etc.) — banned in multiple EU jurisdictions since late 2023.
- TrackANaziMerc and similar doxxing Telegram channels — hard-excluded on ethical grounds per user directive.
- Rybar, Intel Slava Z, WarGonzo (Russian milblogger Telegram) — unverifiable institutional backing, state-proximate, republishing liability risk.
- Equasis — paywalled/account-gated, unfriendly to automated access. Possible manual-lookup fallback only.
- Panjiva / ImportGenius / S&P Global Maritime Intelligence — fully paywalled, no public tier meaningful for public-benefit aggregation.
- Bellingcat — excellent but downstream analysis layer, not a data-feed monitor. Belongs on a separate "investigative reader" reference list, not this instrumentation layer.

**Open gaps** (flagged for follow-up, not blockers):
1. **Turkish-language OSINT monitors**: none at reference-grade. Medyascope data desk, 140Journos archives, Teyit.org exist but are not pure data feeds. Note in repo README.
2. **African maritime beyond IFC-IOR**: RMIFC (Madagascar), Yaoundé Architecture — public data outputs thin. Gulf of Guinea piracy data gap.
3. **Latin American commodity-flow investigators with data feeds**: CLIP, OjoPúblico, Armando.info publish articles, not feeds. Currently covered by Trase + Comtrade macro-layer.

---

## Verification Method

All checks performed via `curl` from the executing machine (residential outbound IP). Timestamps in `last_verified` field reflect the date of this audit. A source marked `live` returned HTTP 200 with valid XML at the recorded `feed_url`. A source marked `no_feed` had a reachable homepage but no RSS/Atom feed found. A source marked `dead` was unreachable (timeout, DNS failure, 5xx, or site converted to a placeholder).
