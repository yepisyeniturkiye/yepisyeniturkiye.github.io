#!/usr/bin/env python3
"""Phase 4 — render the dashboard HTML surface.

Reads the latest enriched clusters JSON plus sources.yaml and emits:
  - index.html              (top-5 convergent strip + 4x2 regional grid + OSINT rail)
  - regions/<region>.html   (single-column regional detail)
  - dashboard.html          (OSINT monitor grid)

All three pages share assets/dash.css and a minimal inline language-toggle
script. Markdown archives (enriched/*.md, regions/*.md, dashboard.md)
remain as audit + machine-readable artifacts but are no longer the
user-facing surface.

No external API calls. Pure local render after the rest of the pipeline.
"""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent
ENRICHED_ROOT = REPO_ROOT / "enriched"
REGIONS_HTML_ROOT = REPO_ROOT / "regions"
SOURCES_FILE = REPO_ROOT / "sources.yaml"
OSINT_CONTENT_ROOT = REPO_ROOT / "osint_content"

REGION_LABELS: dict[str, tuple[str, str]] = {
    "mena": ("Ortadoğu", "MENA"),
    "latam": ("Latin Amerika", "Latin America"),
    "africa": ("Afrika", "Africa"),
    "asia": ("Asya", "Asia"),
    "eu": ("Avrupa", "Europe"),
    "uk": ("Birleşik Krallık", "UK"),
    "us": ("ABD", "United States"),
    "global": ("Küresel", "Global"),
}
GRID_ROW_1 = ["mena", "latam", "africa", "asia"]
GRID_ROW_2 = ["eu", "uk", "us", "global"]
REGION_ORDER = GRID_ROW_1 + GRID_ROW_2

TOP_PER_REGION_ON_INDEX = 4
CONVERGENT_TOP_N = 5

OSINT_CAT_LABELS: dict[str, tuple[str, str]] = {
    "osint_monitor_maritime": ("Denizcilik", "Maritime"),
    "osint_monitor_aviation": ("Havacılık", "Aviation"),
    "osint_monitor_trade": ("Ticaret", "Trade"),
    "osint_monitor_satellite": ("Uydu", "Satellite"),
    "osint_monitor_sanctions": ("Yaptırımlar", "Sanctions"),
    "osint_monitor_conflict": ("Çatışma", "Conflict"),
    "osint_monitor_general": ("Altyapı", "Infrastructure"),
}
OSINT_CAT_ORDER = list(OSINT_CAT_LABELS.keys())


def esc(s: str | None) -> str:
    return html.escape(s or "", quote=True)


def latest_enriched_path() -> Path | None:
    if not ENRICHED_ROOT.exists():
        return None
    files = sorted(ENRICHED_ROOT.glob("*.json"))
    return files[-1] if files else None


def diversity_of(c: dict) -> int:
    return len({m.get("source_id") for m in c.get("members", []) if m.get("source_id")})


def latest_pub_of(c: dict) -> str:
    pubs = [m.get("published") or "" for m in c.get("members", [])]
    return max(pubs) if pubs else ""


def sort_clusters(clusters: list[dict]) -> list[dict]:
    """Diversity-first for the convergent strip (multi-source wins)."""
    return sorted(clusters, key=lambda c: (diversity_of(c), latest_pub_of(c)), reverse=True)


def sort_by_recency(clusters: list[dict]) -> list[dict]:
    """Recency-first for region cards (latest story wins, convergence is a chip)."""
    return sorted(clusters, key=lambda c: (latest_pub_of(c), diversity_of(c)), reverse=True)


def partition_by_region(clusters: list[dict], src_region: dict[str, str]) -> dict[str, list[dict]]:
    by_region: dict[str, list[dict]] = {}
    for c in clusters:
        regions_seen: set[str] = set()
        for m in c.get("members", []):
            r = m.get("region") or src_region.get(m.get("source_id", ""), "")
            if r:
                regions_seen.add(r)
        for r in regions_seen:
            by_region.setdefault(r, []).append(c)
    return by_region


REGION_LABELS_FULL: dict[str, tuple[str, str]] = {
    "mena": ("Ortadoğu", "MENA"),
    "latam": ("Latin Amerika", "Latin America"),
    "africa": ("Afrika", "Africa"),
    "asia": ("Asya", "Asia"),
    "eu": ("Avrupa", "Europe"),
    "uk": ("Birleşik Krallık", "United Kingdom"),
    "us": ("ABD", "United States"),
    "global": ("Küresel", "Global"),
}


THIN_REGION_THRESHOLD = 4


def carry_over_for_empty_regions(by_region: dict[str, list[dict]],
                                 today_date: str,
                                 src_region: dict[str, str]) -> dict[str, str]:
    """For each region in REGION_ORDER with no or too few clusters today, walk
    back through prior enriched/<date>.json files and pull additional clusters
    until the region either reaches THIN_REGION_THRESHOLD or runs out of prior
    content. Returns {region: source_date} for regions that were FULLY empty
    today (banner rendered), and the value is the freshest prior date that
    contributed. Regions that just topped up are filled silently."""
    carry_dates: dict[str, str] = {}
    thin = [r for r in REGION_ORDER
            if len(by_region.get(r, [])) < THIN_REGION_THRESHOLD]
    if not thin or not ENRICHED_ROOT.exists():
        return carry_dates
    files = sorted(ENRICHED_ROOT.glob("*.json"), reverse=True)
    for region in thin:
        existing = list(by_region.get(region, []))
        was_empty = not existing
        seen_urls: set[str] = set()
        for c in existing:
            for m in c.get("members", []):
                u = m.get("url", "")
                if u:
                    seen_urls.add(u)
        accumulated = list(existing)
        first_carry_date: str | None = None
        for fp in files:
            if fp.stem == today_date:
                continue
            if len(accumulated) >= THIN_REGION_THRESHOLD:
                break
            try:
                data = json.loads(fp.read_text())
            except Exception:
                continue
            added_from_this_file = False
            for c in data.get("clusters", []):
                regions_seen: set[str] = set()
                for m in c.get("members", []):
                    r = m.get("region") or src_region.get(m.get("source_id", ""), "")
                    if r:
                        regions_seen.add(r)
                if region not in regions_seen:
                    continue
                cluster_urls = {m.get("url", "") for m in c.get("members", [])}
                cluster_urls.discard("")
                if cluster_urls & seen_urls:
                    continue
                accumulated.append(c)
                seen_urls |= cluster_urls
                added_from_this_file = True
                if len(accumulated) >= THIN_REGION_THRESHOLD:
                    break
            if added_from_this_file and first_carry_date is None:
                first_carry_date = fp.stem
        if len(accumulated) > len(existing):
            by_region[region] = accumulated
            if was_empty and first_carry_date is not None:
                carry_dates[region] = first_carry_date
    return carry_dates


def _carry_over_banner(region: str, source_date: str) -> str:
    tr_label, en_label = REGION_LABELS_FULL.get(region, (region, region))
    return (
        '<div class="carryover-banner" style="padding:14px 18px;'
        'border-left:3px solid var(--accent);background:rgba(255,200,80,0.06);'
        'color:var(--fg-dim);font-size:12.5px;line-height:1.5;margin-bottom:18px;">'
        f'<p class="t-tr" style="margin:0 0 4px 0;color:var(--fg);"><strong>'
        f'{esc(tr_label)} · son taze döngüden taşındı</strong></p>'
        f'<p class="t-en" style="margin:0 0 4px 0;color:var(--fg);"><strong>'
        f'{esc(en_label)} · carried from last fresh cycle</strong></p>'
        '<p class="t-tr" style="margin:0;">Bu bölgeden bugünün döngüsünde yeni öğe '
        f'ulaşmadı. Aşağıda son taze döngünün ({esc(source_date)}) küme çıktısı '
        'tutulmuştur — kaynak yayınevleri yeni içerik gönderdiğinde otomatik '
        'olarak değişecektir.</p>'
        '<p class="t-en" style="margin:0;">No fresh items reached this region in '
        f'today&#x27;s cycle. The clusters below are carried over from the last '
        f'cycle that did produce new content ({esc(source_date)}). They will be '
        'replaced automatically as soon as the source publishers ship new material.</p>'
        '</div>'
    )


def _empty_state_block(region: str) -> str:
    other_regions = [r for r in REGION_ORDER if r != region]
    nav_links = ' · '.join(
        f'<a href="{r}.html" style="color:var(--link);">{r}</a>' for r in other_regions
    )
    return (
        '<div class="empty-state" style="padding:24px 18px;'
        'border:1px dashed var(--fg-dimmer);border-radius:6px;color:var(--fg-dim);'
        'font-size:13px;line-height:1.55;margin-bottom:18px;">'
        '<p class="t-tr" style="margin:0 0 8px 0;color:var(--fg);font-size:14px;">'
        '<strong>Bugün bu bölgeden zenginleştirilmiş küme yok ve önceki döngülerde '
        'de bulunamadı.</strong></p>'
        '<p class="t-en" style="margin:0 0 8px 0;color:var(--fg);font-size:14px;">'
        '<strong>No enriched clusters from this region today and none found in '
        'prior cycles.</strong></p>'
        '<p class="t-tr" style="margin:0 0 12px 0;">Aşağıdaki OSINT şeritleri her '
        'bölge için her zaman canlıdır.</p>'
        '<p class="t-en" style="margin:0 0 12px 0;">The OSINT bands below are '
        'always live for every region.</p>'
        f'<p style="margin:0;"><a href="../index.html" style="color:var(--link);">'
        '← <span class="t-tr">ana sayfa</span><span class="t-en">home</span></a>'
        f'&nbsp;·&nbsp;{nav_links}</p>'
        '</div>'
    )


# ---------- HTML fragments ----------

CHROME_HEAD = """<!doctype html>
<html data-lang="tr" lang="tr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <link rel="stylesheet" href="{css_href}">
  <meta name="description" content="">
  <meta name="robots" content="index,follow">
</head>
<body>
"""

TOPBAR_TEMPLATE = """<header class="topbar">
  <span class="date">{date}</span>
  <nav class="nav">
    <a href="{root}index.html"{a_home}>world</a>
    <a href="{root}dashboard.html"{a_dash}>osint</a>
    <a href="{root}regions/mena.html"{a_mena}>mena</a>
    <a href="{root}regions/latam.html"{a_latam}>latam</a>
    <a href="{root}regions/africa.html"{a_africa}>africa</a>
    <a href="{root}regions/asia.html"{a_asia}>asia</a>
    <a href="{root}regions/eu.html"{a_eu}>eu</a>
    <a href="{root}regions/us.html"{a_us}>us</a>
  </nav>
  <button id="lang-toggle" aria-label="Toggle language"><span class="t-tr">→ EN</span><span class="t-en">→ TR</span></button>
</header>"""

CHROME_TAIL = """<script>
(function(){
  var root = document.documentElement;
  var saved = localStorage.getItem('yy-lang') || 'tr';
  root.dataset.lang = saved;
  var btn = document.getElementById('lang-toggle');
  if (btn) {
    btn.addEventListener('click', function(){
      var next = root.dataset.lang === 'tr' ? 'en' : 'tr';
      root.dataset.lang = next;
      localStorage.setItem('yy-lang', next);
    });
  }
})();
</script>
</body>
</html>
"""


def render_topbar(date_str: str, active: str, root: str) -> str:
    active_map = {
        "home": "a_home",
        "dash": "a_dash",
        "mena": "a_mena",
        "latam": "a_latam",
        "africa": "a_africa",
        "asia": "a_asia",
        "eu": "a_eu",
        "us": "a_us",
    }
    kw = {v: "" for v in active_map.values()}
    if active in active_map:
        kw[active_map[active]] = ' class="active"'
    return TOPBAR_TEMPLATE.format(date=esc(date_str), root=root, **kw)


def render_cluster(c: dict, compact: bool = True) -> str:
    div = diversity_of(c)
    chip_class = "chip hot" if div >= 5 else "chip"
    pub = (latest_pub_of(c) or "")[:16].replace("T", " ")
    obscured_tag = '<span class="neutral">neutral</span>' if c.get("all_obscured") else ""
    # Sources rendered inline as compact attributed links (source names, not URLs).
    src_frags = []
    for m in c.get("members", []):
        src_frags.append(
            f'<a href="{esc(m.get("url",""))}" title="{esc(m.get("title",""))}">'
            f'{esc(m.get("source_name",""))}</a>'
        )
    sources_html = " · ".join(src_frags)
    title_block = (
        f'<div class="title t-tr">{esc(c.get("title_tr",""))}</div>'
        f'<div class="title t-en">{esc(c.get("title_en",""))}</div>'
    )
    meta = (
        f'<div class="meta">'
        f'<span class="{chip_class}">{div} src · {len(c.get("members", []))} it</span>'
        f'<span>{esc(pub)}</span>'
        f'{obscured_tag}'
        f'</div>'
    )
    synth_tr = c.get("synthesis_tr", "").strip()
    synth_en = c.get("synthesis_en", "").strip()
    synth_html = ""
    if synth_tr or synth_en:
        synth_html = (
            '<details class="synth">'
            '<summary>▸ sentez / synthesis</summary>'
            f'<div class="body s-tr">{esc(synth_tr)}</div>'
            f'<div class="body s-en">{esc(synth_en)}</div>'
            '</details>'
        )
    return (
        f'<article class="cluster" data-diversity="{div}">'
        f'{title_block}'
        f'{meta}'
        f'<div class="sources">{sources_html}</div>'
        f'{synth_html}'
        '</article>'
    )


# ---------- pages ----------

def render_index(clusters: list[dict], by_region: dict[str, list[dict]],
                 sources: list[dict], osint_content: dict[str, list[dict]],
                 date_str: str) -> str:
    parts: list[str] = []
    parts.append(CHROME_HEAD.format(
        title=f"Yepisyeni Türkiye · {date_str}",
        css_href="assets/dash.css",
    ))
    parts.append(render_topbar(date_str, active="home", root=""))

    # Convergent strip: top N by diversity across all clusters
    sorted_all = sort_clusters(clusters)
    top_convergent = [c for c in sorted_all if diversity_of(c) >= 3][:CONVERGENT_TOP_N]
    if top_convergent:
        parts.append('<section class="convergent">')
        parts.append('<h2>yakınsak / convergent</h2>')
        parts.append('<div class="row">')
        for c in top_convergent:
            parts.append(render_cluster(c))
        parts.append('</div>')
        parts.append('</section>')

    def render_row(regions: list[str]) -> str:
        row_parts = ['<section class="grid">']
        for r in regions:
            region_clusters = sort_by_recency(by_region.get(r, []))
            top = region_clusters[:TOP_PER_REGION_ON_INDEX]
            tr_label, en_label = REGION_LABELS[r]
            total = len(region_clusters)
            row_parts.append(f'<div class="col region-{r}">')
            row_parts.append(
                f'<h2><a href="regions/{r}.html">'
                f'<span class="t-tr">{esc(tr_label)}</span>'
                f'<span class="t-en">{esc(en_label)}</span>'
                f'</a><span class="count">{total}</span></h2>'
            )
            for c in top:
                row_parts.append(render_cluster(c))
            if total > TOP_PER_REGION_ON_INDEX:
                more = total - TOP_PER_REGION_ON_INDEX
                row_parts.append(
                    f'<a class="sources" style="display:block;margin-top:4px;" '
                    f'href="regions/{r}.html">'
                    f'<span class="t-tr">+{more} daha →</span>'
                    f'<span class="t-en">+{more} more →</span>'
                    f'</a>'
                )
            row_parts.append('</div>')
        row_parts.append('</section>')
        return "\n".join(row_parts)

    parts.append(render_row(GRID_ROW_1))
    parts.append(render_row(GRID_ROW_2))
    parts.append(render_osint_section(sources, osint_content))
    parts.append(CHROME_TAIL)
    return "\n".join(parts)


def render_region(region: str, region_clusters: list[dict],
                  sources: list[dict], osint_content: dict[str, list[dict]],
                  date_str: str, carry_over_from: str | None = None) -> str:
    parts: list[str] = []
    tr_label, en_label = REGION_LABELS.get(region, (region, region))
    parts.append(CHROME_HEAD.format(
        title=f"{en_label} · Yepisyeni Türkiye",
        css_href="../assets/dash.css",
    ))
    parts.append(render_topbar(date_str, active=region, root="../"))
    parts.append(f'<section class="region-detail region-{region}">')
    parts.append(
        f'<h2 style="color:var(--fg-dim);font-family:ui-monospace,Menlo,monospace;'
        f'font-size:11px;text-transform:uppercase;letter-spacing:0.14em;'
        f'border-bottom:2px solid var(--{region});padding-bottom:4px;margin-bottom:14px;">'
        f'<span class="t-tr">{esc(tr_label)}</span>'
        f'<span class="t-en">{esc(en_label)}</span>'
        f' <span class="count" style="color:var(--fg-dimmer);">· {len(region_clusters)} cluster</span>'
        f'</h2>'
    )
    if carry_over_from:
        parts.append(_carry_over_banner(region, carry_over_from))
    elif not region_clusters:
        parts.append(_empty_state_block(region))
    for c in sort_by_recency(region_clusters):
        parts.append(render_cluster(c, compact=False))
    parts.append('</section>')
    parts.append(render_osint_section(sources, osint_content))
    parts.append(CHROME_TAIL)
    return "\n".join(parts)


def render_dashboard(sources: list[dict], osint_content: dict[str, list[dict]],
                     date_str: str) -> str:
    parts: list[str] = []
    parts.append(CHROME_HEAD.format(
        title="OSINT · Yepisyeni Türkiye",
        css_href="assets/dash.css",
    ))
    parts.append(render_topbar(date_str, active="dash", root=""))

    buckets: dict[str, list[dict]] = {cat: [] for cat in OSINT_CAT_ORDER}
    for s in sources:
        cat = s.get("category", "")
        if cat in buckets and s.get("status") != "dead":
            buckets[cat].append(s)

    parts.append('<section class="dash-grid">')
    for cat in OSINT_CAT_ORDER:
        if not buckets[cat]:
            continue
        tr_label, en_label = OSINT_CAT_LABELS[cat]
        parts.append('<div class="dash-cat">')
        parts.append(
            f'<h3><span class="t-tr">{esc(tr_label)}</span>'
            f'<span class="t-en">{esc(en_label)}</span></h3>'
        )
        for s in buckets[cat]:
            access = {
                "api": "API", "rss": "RSS", "atom": "Atom",
                "bulk_csv": "CSV", "bulk_json": "JSON", "link_only": "↗",
            }.get(s.get("feed_type", ""), s.get("feed_type", ""))
            status_note = ""
            if s.get("status") == "needs_verification":
                status_note = ' <span class="access" style="color:var(--neutral);font-style:italic;">⚠ needs verification</span>'
            notes = (s.get("notes") or "").strip()
            if notes:
                first = notes.split(".")[0].strip()
                notes = first + ("." if first and not first.endswith(".") else "")
            parts.append('<div class="item">')
            parts.append(
                f'<a href="{esc(s.get("homepage",""))}" rel="noopener">'
                f'{esc(s.get("name",""))}</a>'
                f'<span class="access">[{access}]</span>'
                f'{status_note}'
            )
            if notes:
                parts.append(f'<div class="desc">{esc(notes)}</div>')
            parts.append('</div>')
        parts.append('</div>')
    parts.append('</section>')
    parts.append(CHROME_TAIL)
    return "\n".join(parts)


def load_osint_content() -> dict[str, list[dict]]:
    """Load per-platform distilled items keyed by platform_id."""
    out: dict[str, list[dict]] = {}
    if not OSINT_CONTENT_ROOT.exists():
        return out
    for f in OSINT_CONTENT_ROOT.glob("*.json"):
        try:
            d = json.loads(f.read_text())
            out[d["platform_id"]] = d.get("items", []) or []
        except Exception:
            continue
    return out


def render_osint_section(sources: list[dict], content: dict[str, list[dict]]) -> str:
    """Render the 7-domain OSINT section with infinite-scroll bands."""
    parts = ['<section class="osint-section">']
    parts.append('<h2 class="section-title">osint</h2>')

    for cat in OSINT_CAT_ORDER:
        platforms = [
            s for s in sources
            if s.get("category") == cat and s.get("status") != "dead"
        ]
        if not platforms:
            continue
        tr_label, en_label = OSINT_CAT_LABELS[cat]
        # collect cards for this band: distilled items first, static fallback for platforms with none
        cards: list[str] = []
        for p in platforms:
            items = content.get(p["id"], [])
            if items:
                for it in items:
                    title_tr = it.get("title_tr", "") or it.get("title_en", "")
                    title_en = it.get("title_en", "") or it.get("title_tr", "")
                    cards.append(
                        f'<a class="osint-card item" href="{esc(it["url"])}" '
                        f'rel="noopener" target="_blank">'
                        f'<span class="src">{esc(p["name"])}</span>'
                        f'<span class="ttl t-tr">{esc(title_tr)}</span>'
                        f'<span class="ttl t-en">{esc(title_en)}</span>'
                        f'</a>'
                    )
            else:
                # static fallback card: platform description + homepage link
                note = (p.get("notes") or "").strip()
                note_first = note.split(".")[0].strip() if note else ""
                cards.append(
                    f'<a class="osint-card static" href="{esc(p["homepage"])}" '
                    f'rel="noopener" target="_blank">'
                    f'<span class="src">{esc(p["name"])}</span>'
                    f'<span class="ttl t-tr">'
                    f'{esc(note_first or "platforma git →")}</span>'
                    f'<span class="ttl t-en">'
                    f'{esc(note_first or "visit platform →")}</span>'
                    f'</a>'
                )
        if not cards:
            continue
        # duplicate cards so the infinite-scroll animation loops seamlessly
        doubled = cards + cards
        duration = max(30, min(120, len(cards) * 6))  # scale speed with content
        parts.append('<div class="band">')
        parts.append(
            f'<div class="band-label">'
            f'<span class="t-tr">{esc(tr_label)}</span>'
            f'<span class="t-en">{esc(en_label)}</span>'
            f'</div>'
        )
        parts.append(
            f'<div class="band-viewport">'
            f'<div class="band-track" style="animation-duration:{duration}s;">'
        )
        parts.extend(doubled)
        parts.append('</div></div>')
        parts.append('</div>')

    parts.append('</section>')
    return "\n".join(parts)


# ---------- main ----------

def main() -> int:
    src = latest_enriched_path()
    if not src:
        print("[html] no enriched/*.json found")
        return 0
    data = json.loads(src.read_text())
    clusters = data.get("clusters", [])
    sources = yaml.safe_load(SOURCES_FILE.read_text())["sources"]
    src_region = {s["id"]: s.get("region", "") for s in sources}
    date_str = src.stem  # YYYY-MM-DD

    by_region = partition_by_region(clusters, src_region)

    carry_dates = carry_over_for_empty_regions(by_region, date_str, src_region)
    if carry_dates:
        print(f"[html] carry-over for empty regions: {carry_dates}")

    osint_content = load_osint_content()
    print(f"[html] loaded osint content for {len(osint_content)} platforms")

    (REPO_ROOT / "index.html").write_text(
        render_index(clusters, by_region, sources, osint_content, date_str)
    )
    print(f"[html] wrote index.html ({len(clusters)} clusters across "
          f"{sum(1 for r in REGION_ORDER if by_region.get(r))} populated regions)")

    REGIONS_HTML_ROOT.mkdir(parents=True, exist_ok=True)
    written = 0
    for r in REGION_ORDER:
        rc = by_region.get(r, [])
        carry_from = carry_dates.get(r)
        (REGIONS_HTML_ROOT / f"{r}.html").write_text(
            render_region(r, rc, sources, osint_content, date_str, carry_from)
        )
        written += 1
    print(f"[html] wrote {written} region pages "
          f"({len(carry_dates)} carry-over, "
          f"{sum(1 for r in REGION_ORDER if not by_region.get(r))} still empty)")

    (REPO_ROOT / "dashboard.html").write_text(
        render_dashboard(sources, osint_content, date_str)
    )
    print(f"[html] wrote dashboard.html")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
