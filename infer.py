#!/usr/bin/env python3
"""Daily inference pass: cluster + bilingual synthesis + obscuring.

Reads the last 24 hours of raw items from feed/, groups them into clusters
covering the same story, produces EN + TR title and synthesis for each
cluster, and writes enriched/YYYY-MM-DD.{json,md}. Also rebuilds index.md
to render the enriched view as the home page, with raw archive linked.

One DeepSeek call per batch (combined clustering + synthesis). Obscuring
discipline: clusters whose members are entirely from sources flagged with
obscuring_required in sources.yaml get neutralized wire-service voice.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from openai import OpenAI

REPO_ROOT = Path(__file__).resolve().parent
FEED_ROOT = REPO_ROOT / "feed"
ENRICHED_ROOT = REPO_ROOT / "enriched"
INDEX_FILE = REPO_ROOT / "index.md"
SOURCES_FILE = REPO_ROOT / "sources.yaml"

LOOKBACK_HOURS = 24
# Halved from 40. DeepSeek streams output at ~50-80 tok/sec; a 40-item batch
# produces ~4000 output tokens = 60-80s of streaming per call. From a CI
# runner's slower network path that regularly exceeded the 90s timeout.
# 20-item batches produce ~2000 tokens = 25-40s, fitting comfortably in the
# CI budget at the cost of ~2× more calls.
BATCH_SIZE = 20

SYSTEM_PROMPT = (
    "You are a multilingual news clustering and synthesis assistant for Yepisyeni "
    "Türkiye, a public-benefit news aggregator. You return valid JSON only, "
    "matching the schema the user specifies. You never fabricate facts. You prefer "
    "neutral wire-service voice over loaded framing. For clusters whose members "
    "are all from obscure=true sources, you strip inflammatory framing and attribute "
    "factual claims back to the source name."
)


def _client() -> OpenAI:
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        print("[infer] DEEPSEEK_API_KEY not set — skipping inference pass.", file=sys.stderr)
        sys.exit(0)
    # Hard bound per call. max_retries=0 disables the SDK's default 2-retry
    # behavior — otherwise 40s timeout silently becomes 120s per call on a
    # stalled response, blowing through the workflow budget.
    # 40-item batches need ~20-30s locally but can push past 40s from CI
    # (different network path). 90s covers p99 without letting the SDK retry
    # multiply it behind our back.
    return OpenAI(
        api_key=key,
        base_url="https://api.deepseek.com",
        timeout=90.0,
        max_retries=0,
    )


def load_recent_items(hours: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    items: list[dict] = []
    seen: set[str] = set()
    if not FEED_ROOT.exists():
        return items
    for json_file in sorted(FEED_ROOT.rglob("*.json"), reverse=True):
        try:
            mtime = datetime.fromtimestamp(json_file.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff:
                continue
            data = json.loads(json_file.read_text())
            for item in data.get("items", []):
                url = item.get("canonical_url")
                if url and url not in seen:
                    seen.add(url)
                    items.append(item)
        except Exception as exc:
            print(f"  [warn] could not read {json_file}: {exc}", file=sys.stderr)
    return items


def tag_obscuring(items: list[dict]) -> None:
    sources = yaml.safe_load(SOURCES_FILE.read_text())["sources"]
    flagged = {s["id"] for s in sources if s.get("obscuring_required")}
    for item in items:
        item["_obscure"] = item["source_id"] in flagged


def call_batch(client: OpenAI, batch: list[dict]) -> list[dict]:
    trimmed = [{
        "idx": i,
        "title": it["title"][:220],
        "summary": (it.get("summary") or "")[:320],
        "source": it["source_name"],
        "obscure": bool(it.get("_obscure")),
    } for i, it in enumerate(batch)]

    user_prompt = (
        "Group the following news items into clusters covering the same story. "
        "For each cluster, produce bilingual synthesis.\n\n"
        f"ITEMS:\n{json.dumps(trimmed, ensure_ascii=False)}\n\n"
        "OUTPUT SCHEMA (valid JSON):\n"
        "{\n"
        '  "clusters": [\n'
        "    {\n"
        '      "member_ids": [list of idx values from ITEMS],\n'
        '      "title_en": "~12-word headline, neutral, no loaded framing",\n'
        '      "title_tr": "~12-word Turkish translation of the headline",\n'
        '      "synthesis_en": "2-3 sentences factual synthesis in neutral wire-service voice",\n'
        '      "synthesis_tr": "2-3 sentences factual synthesis in Turkish neutral wire-service voice"\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Rules:\n"
        "- Every item must belong to exactly one cluster. Singletons allowed (cluster of one).\n"
        "- Two items cluster only if they cover the same discrete news event or claim.\n"
        "- If ALL members have obscure=true, strip loaded framing and attribute: "
        "  'X source reports that...' style. Stick to the factual kernel only.\n"
        "- If any member has obscure=false, use normal neutral voice.\n"
        "- Never invent facts beyond what the ITEMS say.\n"
        "- Turkish translations must be natural, not word-for-word. Target fluent TR reader."
    )

    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=8000,
    )
    try:
        data = json.loads(resp.choices[0].message.content)
    except json.JSONDecodeError as exc:
        print(f"  [warn] bad JSON from model: {exc}", file=sys.stderr)
        return []

    out: list[dict] = []
    for c in data.get("clusters", []):
        mids = c.get("member_ids") or []
        members = [batch[j] for j in mids if isinstance(j, int) and 0 <= j < len(batch)]
        if not members:
            continue
        out.append({
            "members": [{
                "title": m["title"],
                "url": m["url"],
                "source_name": m["source_name"],
                "source_id": m["source_id"],
                "region": m.get("region", ""),
                "published": m.get("published"),
                "obscured": bool(m.get("_obscure")),
            } for m in members],
            "title_en": (c.get("title_en") or "").strip(),
            "title_tr": (c.get("title_tr") or "").strip(),
            "synthesis_en": (c.get("synthesis_en") or "").strip(),
            "synthesis_tr": (c.get("synthesis_tr") or "").strip(),
            "all_obscured": all(m.get("_obscure") for m in members),
        })
    return out


def sort_clusters(clusters: list[dict]) -> list[dict]:
    """Sort by diversity first, recency second.

    A cluster with N distinct sources covering the same story is a stronger
    convergence signal than a cluster with N items from one prolific source.
    This prevents loud Anglo feeds from dominating the top of the page just
    by virtue of publishing volume.
    """
    def key(c):
        diversity = len({m.get("source_id") for m in c["members"] if m.get("source_id")})
        pubs = [m.get("published") or "" for m in c["members"]]
        latest = max(pubs) if pubs else ""
        return (diversity, latest)
    return sorted(clusters, key=key, reverse=True)


def render_enriched_md(clusters: list[dict], date: str) -> str:
    lines = [
        "---",
        "title: Yepisyeni Türkiye",
        "---",
        "",
        "# Yepisyeni Türkiye",
        "",
        "Multipolar haber ve OSINT agregasyonu. Kamu yararına. Müşteri yok.",
        "*Multipolar news and OSINT aggregation. Public benefit. No customers.*",
        "",
        f"**{date} — {len(clusters)} küme / cluster**",
        "",
        "---",
        "",
    ]
    for i, c in enumerate(clusters, 1):
        if c["all_obscured"]:
            obscure_marker = " — *neutral voice applied*"
        else:
            obscure_marker = ""
        lines.append(f"## {i}. {c['title_tr']}{obscure_marker}")
        lines.append(f"*{c['title_en']}*")
        lines.append("")
        if c["synthesis_tr"]:
            lines.append(c["synthesis_tr"])
        if c["synthesis_en"]:
            lines.append("")
            lines.append(f"*{c['synthesis_en']}*")
        lines.append("")
        lines.append("**Kaynaklar / Sources:**")
        for m in c["members"]:
            pub = (m.get("published") or "")[:16].replace("T", " ")
            lines.append(f"- [{m['source_name']}]({m['url']})  *{pub}* — {m['title']}")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.extend([
        "",
        "## Navigasyon / Navigation",
        "",
        "**OSINT Gösterge Paneli / Dashboard:** [`dashboard.md`](dashboard.md) — "
        "denizcilik, havacılık, ticaret, yaptırım, çatışma ve altyapı izleme platformları.",
        "",
        "**Bölgeler / Regions:** "
        "[Ortadoğu](regions/mena.md) · "
        "[Latin Amerika](regions/latam.md) · "
        "[Afrika](regions/africa.md) · "
        "[Asya](regions/asia.md) · "
        "[Avrupa](regions/eu.md) · "
        "[Birleşik Krallık](regions/uk.md) · "
        "[ABD](regions/us.md) · "
        "[Küresel](regions/global.md)",
        "",
        "**Ham akış / Raw feed:** [`latest_raw.md`](latest_raw.md) — gruplama ve sentez öncesi kaynak başlıkları.",
        "",
        "**Arşiv / Archive:** [`feed/`](feed/) (per-hour JSON+markdown) · "
        "[`enriched/`](enriched/) (daily clustered JSON+markdown).",
        "",
        "**Şeffaflık / Transparency:** "
        "[kaynak listesi / source list `sources.yaml`](sources.yaml) · "
        "[denetim / audit `phase0/PHASE0_REPORT.md`](phase0/PHASE0_REPORT.md) · "
        "[pipeline `phase3/PIPELINE.md`](phase3/PIPELINE.md).",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    client = _client()

    items = load_recent_items(LOOKBACK_HOURS)
    if not items:
        print("[infer] no raw items in lookback window — nothing to do.")
        return 0

    tag_obscuring(items)
    print(f"[infer] {len(items)} items across lookback window; batching into {BATCH_SIZE}")

    clusters: list[dict] = []
    for i in range(0, len(items), BATCH_SIZE):
        batch = items[i:i + BATCH_SIZE]
        print(f"  batch {i // BATCH_SIZE + 1}: {len(batch)} items -> DeepSeek")
        try:
            clusters.extend(call_batch(client, batch))
        except Exception as exc:
            print(f"  batch {i // BATCH_SIZE + 1} failed: {exc}", file=sys.stderr)

    clusters = sort_clusters(clusters)
    print(f"[infer] produced {len(clusters)} clusters")

    today = datetime.now(timezone.utc).date().isoformat()
    ENRICHED_ROOT.mkdir(parents=True, exist_ok=True)
    json_path = ENRICHED_ROOT / f"{today}.json"
    md_path = ENRICHED_ROOT / f"{today}.md"
    json_path.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cluster_count": len(clusters),
        "source_item_count": len(items),
        "clusters": clusters,
    }, indent=2, ensure_ascii=False))
    md_body = render_enriched_md(clusters, today)
    md_path.write_text(md_body)
    INDEX_FILE.write_text(md_body)
    print(f"[infer] wrote {json_path.relative_to(REPO_ROOT)} + {md_path.relative_to(REPO_ROOT)} + index.md")

    return 0


if __name__ == "__main__":
    sys.exit(main())
