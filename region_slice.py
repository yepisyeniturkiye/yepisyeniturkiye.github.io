#!/usr/bin/env python3
"""Slice today's enriched clusters into per-region pages.

Reads enriched/<today>.json (produced by infer.py) and sources.yaml,
partitions clusters by member region, and writes regions/<region>.md for
each region that has at least one cluster today.

Clusters appear on every region page whose tag matches any member. A
cluster with a US AlterNet item and a Brazilian Brasil de Fato item
appears on both regions/us.md and regions/latam.md. This is intentional
— crossover coverage is a real signal.

Cheap: no API calls. Runs in-process after infer.py.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent
ENRICHED_ROOT = REPO_ROOT / "enriched"
REGIONS_ROOT = REPO_ROOT / "regions"
SOURCES_FILE = REPO_ROOT / "sources.yaml"

REGION_LABELS: dict[str, tuple[str, str]] = {
    "us": ("ABD", "United States"),
    "uk": ("Birleşik Krallık", "United Kingdom"),
    "eu": ("Avrupa", "Europe"),
    "mena": ("Ortadoğu ve Kuzey Afrika", "Middle East & North Africa"),
    "latam": ("Latin Amerika", "Latin America"),
    "africa": ("Afrika", "Africa"),
    "asia": ("Asya", "Asia"),
    "global": ("Küresel", "Global"),
}

REGION_ORDER = ["mena", "latam", "africa", "asia", "eu", "uk", "us", "global"]


def build_source_region_map() -> dict[str, str]:
    data = yaml.safe_load(SOURCES_FILE.read_text())
    return {s["id"]: s.get("region", "") for s in data["sources"]}


def latest_enriched_path() -> Path | None:
    if not ENRICHED_ROOT.exists():
        return None
    files = sorted(ENRICHED_ROOT.glob("*.json"))
    return files[-1] if files else None


def render_cluster(c: dict, idx: int) -> list[str]:
    obscure_marker = " — *neutral voice applied*" if c.get("all_obscured") else ""
    lines = [
        f"### {idx}. {c['title_tr']}{obscure_marker}",
        f"*{c['title_en']}*",
        "",
    ]
    if c.get("synthesis_tr"):
        lines.append(c["synthesis_tr"])
    if c.get("synthesis_en"):
        lines.append("")
        lines.append(f"*{c['synthesis_en']}*")
    lines.append("")
    lines.append("**Kaynaklar / Sources:**")
    for m in c["members"]:
        pub = (m.get("published") or "")[:16].replace("T", " ")
        lines.append(f"- [{m['source_name']}]({m['url']})  *{pub}* — {m['title']}")
    lines.append("")
    return lines


def write_region_page(region: str, clusters: list[dict], date: str) -> None:
    tr_label, en_label = REGION_LABELS.get(region, (region, region))
    REGIONS_ROOT.mkdir(parents=True, exist_ok=True)
    out_path = REGIONS_ROOT / f"{region}.md"

    lines = [
        "---",
        f"title: Yepisyeni Türkiye — {tr_label}",
        "---",
        "",
        f"# {tr_label} / {en_label}",
        "",
        f"**{date} — {len(clusters)} küme / cluster**",
        "",
        "Ana sayfa / home: [`index.md`](../index.md)  |  "
        "Gösterge paneli / dashboard: [`dashboard.md`](../dashboard.md)  |  "
        "Bölgeler / regions: "
        + " · ".join(
            f"[{REGION_LABELS.get(r, (r, r))[1]}](../regions/{r}.md)"
            for r in REGION_ORDER if r != region
        ),
        "",
        "---",
        "",
    ]
    for i, c in enumerate(clusters, 1):
        lines.extend(render_cluster(c, i))
        lines.append("---")
        lines.append("")

    out_path.write_text("\n".join(lines))


def main() -> int:
    src = latest_enriched_path()
    if not src:
        print("[region] no enriched/*.json found; skipping region slice")
        return 0
    data = json.loads(src.read_text())
    clusters = data.get("clusters", [])
    if not clusters:
        print("[region] enriched file has no clusters; nothing to slice")
        return 0

    src_region = build_source_region_map()

    # partition clusters by region (a cluster may appear in multiple regions)
    by_region: dict[str, list[dict]] = {}
    for c in clusters:
        regions_seen: set[str] = set()
        for m in c.get("members", []):
            r = m.get("region") or src_region.get(m.get("source_id", ""), "")
            if r:
                regions_seen.add(r)
        for r in regions_seen:
            by_region.setdefault(r, []).append(c)

    date = src.stem  # YYYY-MM-DD
    written = 0
    for region in REGION_ORDER:
        if region in by_region and by_region[region]:
            write_region_page(region, by_region[region], date)
            print(f"[region] {region}: {len(by_region[region])} clusters")
            written += 1

    # any regions we don't have in ORDER but data has
    for region, cl in by_region.items():
        if region not in REGION_ORDER and cl:
            write_region_page(region, cl, date)
            print(f"[region] {region}: {len(cl)} clusters (unlabelled)")
            written += 1

    print(f"[region] wrote {written} region pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
