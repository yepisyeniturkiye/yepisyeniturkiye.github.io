#!/usr/bin/env python3
"""Render the OSINT monitor dashboard.

Reads sources.yaml, filters entries in osint_monitor_* categories (plus
entries flagged needs_verification), and writes a bilingual (TR/EN)
dashboard page grouping them by domain. This is the instrumentation
reference — data platforms, registries, and public monitors that
complement the clustered news view in index.md.

Static; regenerated on every workflow run so any sources.yaml edits
propagate automatically. Does not call any external APIs.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent
SOURCES_FILE = REPO_ROOT / "sources.yaml"
OUT_FILE = REPO_ROOT / "dashboard.md"

# Category -> (TR label, EN label)
CATEGORY_LABELS: dict[str, tuple[str, str]] = {
    "osint_monitor_maritime": ("Denizcilik", "Maritime / Shipping"),
    "osint_monitor_aviation": ("Havacılık", "Aviation"),
    "osint_monitor_trade": ("Ticaret ve Emtia", "Trade / Commodity"),
    "osint_monitor_satellite": ("Uydu Verisi", "Satellite / Earth Observation"),
    "osint_monitor_sanctions": ("Yaptırımlar ve Şirketler", "Sanctions / Corporate"),
    "osint_monitor_conflict": ("Çatışma Verisi", "Conflict / Event Data"),
    "osint_monitor_general": ("Genel Altyapı", "General Infrastructure"),
}

CATEGORY_ORDER = list(CATEGORY_LABELS.keys())

REGION_FLAGS: dict[str, str] = {
    "global": "🌍",
    "us": "🇺🇸",
    "uk": "🇬🇧",
    "eu": "🇪🇺",
    "asia": "🌏",
    "mena": "🏜️",
    "latam": "🌎",
    "africa": "🌍",
}


def render_entry(s: dict) -> list[str]:
    name = s.get("name", s.get("id", "")).strip()
    homepage = s.get("homepage", "").strip()
    notes = (s.get("notes") or "").strip()
    # take only the first sentence of notes to keep the card compact
    if notes:
        first_sentence = notes.split(".")[0].strip()
        if first_sentence:
            notes = first_sentence + ("." if not first_sentence.endswith(".") else "")
    region = s.get("region", "").strip()
    flag = REGION_FLAGS.get(region, "")
    status = s.get("status", "live")
    status_marker = ""
    if status == "needs_verification":
        status_marker = " ⚠️ *needs verification / doğrulama gerekiyor*"
    access = s.get("feed_type", "")
    access_label = {
        "api": "API",
        "rss": "RSS",
        "atom": "Atom",
        "bulk_csv": "CSV bulk",
        "bulk_json": "JSON bulk",
        "link_only": "Link",
    }.get(access, access)

    lines = []
    if flag:
        lines.append(f"- **[{name}]({homepage})** {flag} *[{access_label}]*{status_marker}")
    else:
        lines.append(f"- **[{name}]({homepage})** *[{access_label}]*{status_marker}")
    if notes:
        lines.append(f"  {notes}")
    return lines


def main() -> int:
    sources = yaml.safe_load(SOURCES_FILE.read_text())["sources"]
    buckets: dict[str, list[dict]] = {cat: [] for cat in CATEGORY_ORDER}
    for s in sources:
        cat = s.get("category", "")
        if cat in buckets and s.get("status") != "dead":
            buckets[cat].append(s)

    out = [
        "---",
        "title: Yepisyeni Türkiye — OSINT Dashboard",
        "---",
        "",
        "# OSINT Gösterge Paneli / Dashboard",
        "",
        "Bu sayfa, kamu yararına erişilebilir OSINT izleme platformlarının dizinidir.",
        "Makale akışı değil — araçlar ve veri kaynakları. Türkiye-İsrail arasındaki "
        "ticaret inkârının AIS verisiyle çürütülmesi gibi kullanım durumları için "
        "gerekli olan enstrümantasyon katmanı.",
        "",
        "*This page indexes public-benefit OSINT monitoring platforms — tools and "
        "data sources, not an article feed. Instrumentation for factual debunks "
        "(e.g. shipping-denial refutations via AIS data).*",
        "",
        "**Filtreler / Filters:**",
        "",
        "- Kamu erişimine açık, VPN gerektirmez / publicly accessible, no VPN required",
        "- AB yaptırımlı yayıncılar dışlandı / no EU-sanctioned outlets",
        "- Doxxing yok / no individual-targeting platforms",
        "- Yaptırımlı/yasaklı örgütlerle bağlantılı değil / no sanctioned or banned affiliates",
        "",
        "Haber akışı / news stream: [`index.md`](index.md). "
        "Kaynak denetimi / source audit: [`phase0/PHASE0_REPORT.md`](phase0/PHASE0_REPORT.md).",
        "",
        "---",
        "",
    ]

    for cat in CATEGORY_ORDER:
        entries = buckets[cat]
        if not entries:
            continue
        tr_label, en_label = CATEGORY_LABELS[cat]
        out.append(f"## {tr_label} / {en_label}")
        out.append("")
        for s in entries:
            out.extend(render_entry(s))
        out.append("")
        out.append("---")
        out.append("")

    total_live = sum(
        1 for s in sources
        if s.get("category", "").startswith("osint_monitor_") and s.get("status") != "dead"
    )
    out.append(f"*{total_live} platform • Son güncelleme / last build: build-time*")
    out.append("")

    OUT_FILE.write_text("\n".join(out))
    print(f"[dashboard] wrote {OUT_FILE.name} with {total_live} entries across "
          f"{sum(1 for b in buckets.values() if b)} categories")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
