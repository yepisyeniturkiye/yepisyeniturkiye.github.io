# Phase 4 — Visual Dashboard

## Decisions

- **No Jekyll.** `.nojekyll` at repo root. Python pipeline emits HTML directly.
- **Single dense dashboard.** Not a narrative site. "Monitor the world at a glance."
- **No branding.** No logo, no mission statement, no "about this site." Date bar, content, done.
- **Dark first.** `#0e0e10` bg, `#d4d4d4` text, one amber accent for convergence.
- **4-column regional grid, 2 rows** (MENA, LATAM, AFRICA, ASIA / EU, UK, US, GLOBAL).
- **TR/EN toggle.** Data attribute on `<html>`, CSS hides the other language. Preference persists in localStorage. Default TR.
- **OSINT rail at the bottom.** Thin pill row, platforms grouped by category, click-through to homepage.
- **Convergence as border accent.** Cluster cards get a left border colored by `data-diversity` (source count). 2-3 subtle, 4-5 medium, 6+ amber.
- **Top strip of convergent clusters.** Horizontal scroll of top-5 multi-source clusters above the regional grid.
- **Per-region pages** (`regions/*.html`) share the same chrome but show full region content, single column.
- **OSINT dashboard** (`dashboard.html`) gets its own grid layout for the 30 monitors.
- **Markdown archives stay** under `enriched/` and `feed/` as audit + machine-readable, not user-facing.

## Rendering split

- `fetch.py` — unchanged
- `infer.py` — unchanged; still produces `enriched/YYYY-MM-DD.{json,md}` and `index.md` (archive)
- `region_slice.py` — unchanged; still produces `regions/<region>.md` (archive)
- `dashboard.py` — unchanged; still produces `dashboard.md` (archive)
- **`render_html.py` (new)** — reads `enriched/*.json` + `sources.yaml`, emits:
  - `index.html` — top-5 convergent strip + 4×2 regional grid + OSINT rail
  - `regions/<region>.html` — single-column regional detail, same chrome
  - `dashboard.html` — OSINT monitor grid, same chrome

`assets/dash.css` is the single stylesheet. Minimal inline JS for the TR/EN toggle and localStorage.

## Column behaviour

Each region column on `index.html` shows top 4 clusters for that region. Region header is a link to `regions/<region>.html` for the full list. This keeps the at-a-glance view dense without forcing long columns.

## What's intentionally out

- No search bar (Ctrl+F is fine for now)
- No filtering UI beyond the language toggle
- No image thumbnails or favicons (dense text > decoration)
- No mobile-specific layout; the grid collapses to 2 columns below ~900px
- No client-side JS framework; vanilla only
