#!/usr/bin/env python3
"""Yepisint trihourly ingest.

Reads sources.yaml, fetches live feeds, normalizes items, dedups by
canonical URL against the last 7 days of committed output, and writes
feed/YYYY/MM/DD/HH.{json,md} plus a rolled-up index.md (last 24 hours).

Sources with feed_type in {rss, atom, youtube} are pulled via feedparser.
Sources with feed_type == inoreader_html_playwright are scraped via
headless Chromium. Everything else (link_only, needs_verification, dead,
no_feed, auth_required) is skipped at the fetch layer.
"""

from __future__ import annotations

import html
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import feedparser
import yaml
from dateutil import parser as dateparser

REPO_ROOT = Path(__file__).resolve().parent
SOURCES_FILE = REPO_ROOT / "sources.yaml"
FEED_ROOT = REPO_ROOT / "feed"
INDEX_FILE = REPO_ROOT / "latest_raw.md"  # raw rolling view; infer.py owns index.md

DEDUP_WINDOW_DAYS = 7
ROLLUP_WINDOW_HOURS = 24
MAX_ITEMS_PER_SOURCE = 8  # per-run cap; equalizes loud Anglo feeds vs. smaller-voice sources

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "mc_cid", "mc_eid", "ref", "_ga", "hsa_cam", "hsa_grp",
    "cmpid", "CMP",
}

INGEST_FEED_TYPES = {"rss", "atom", "youtube", "inoreader_html_playwright"}
INGEST_CATEGORY_PREFIXES = (
    "general_left", "anti_imperialism", "movements_labor", "video",
    "regional", "curator", "investigative",
)


# ---------- canonicalization ----------

def canonicalize_url(url: str) -> str:
    if not url:
        return ""
    p = urlparse(url.strip())
    host = p.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    params = parse_qs(p.query, keep_blank_values=True)
    params = {k: v for k, v in params.items() if k.lower() not in TRACKING_PARAMS}
    query = urlencode(sorted(params.items()), doseq=True)
    path = p.path.rstrip("/") or "/"
    return urlunparse((p.scheme, host, path, "", query, ""))


def strip_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_time(raw: Any) -> str | None:
    if not raw:
        return None
    try:
        if isinstance(raw, (list, tuple)) and len(raw) >= 6:
            return datetime(*raw[:6], tzinfo=timezone.utc).isoformat()
        dt = dateparser.parse(str(raw))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        return None


# ---------- fetchers ----------

def fetch_feedparser(source: dict, now_iso: str) -> list[dict]:
    url = source["feed_url"]
    parsed = feedparser.parse(url, request_headers={
        "User-Agent": "Mozilla/5.0 (YepisintFetcher/0.1; +https://yepisyeniturkiye.github.io)"
    })
    items: list[dict] = []
    for entry in parsed.entries:
        link = entry.get("link") or (entry.get("links") or [{}])[0].get("href", "")
        if not link:
            continue
        title = entry.get("title", "").strip()
        summary = strip_html(entry.get("summary", "") or entry.get("description", ""))[:400]
        published = (
            parse_time(entry.get("published_parsed"))
            or parse_time(entry.get("published"))
            or parse_time(entry.get("updated_parsed"))
            or parse_time(entry.get("updated"))
        )
        items.append({
            "source_id": source["id"],
            "source_name": source["name"],
            "title": title,
            "url": link,
            "canonical_url": canonicalize_url(link),
            "published": published,
            "fetched": now_iso,
            "summary": summary,
            "category": source.get("category", ""),
            "region": source.get("region", ""),
            "language": source.get("language", ""),
            "feed_type": source.get("feed_type", ""),
        })
    return items


_REL_DATE_RE = re.compile(r"^(\d+)\s*([smhdw])$", re.IGNORECASE)


def parse_relative_time(rel: str, anchor: datetime) -> str | None:
    """Inoreader emits short relatives like '4m', '34m', '2h', '1d'. Convert to absolute ISO."""
    if not rel:
        return None
    m = _REL_DATE_RE.match(rel.strip())
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2).lower()
    delta = {"s": timedelta(seconds=n), "m": timedelta(minutes=n),
             "h": timedelta(hours=n), "d": timedelta(days=n),
             "w": timedelta(weeks=n)}.get(unit)
    if delta is None:
        return None
    return (anchor - delta).isoformat()


def fetch_inoreader_playwright(source: dict, now_iso: str) -> list[dict]:
    from playwright.sync_api import sync_playwright

    url = source["feed_url"]
    items: list[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (YepisintFetcher/0.1; +https://yepisyeniturkiye.github.io)"
            )
            page = ctx.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_selector(".article_magazine_content_wraper, .article_magazine_content_wraper_no_picture", timeout=10000)
            # scroll to load more
            for _ in range(3):
                page.mouse.wheel(0, 4000)
                page.wait_for_timeout(1200)
            raw = page.evaluate(
                """() => {
                  const nodes = document.querySelectorAll(
                    '.article_magazine_content_wraper, .article_magazine_content_wraper_no_picture'
                  );
                  return Array.from(nodes).map(el => {
                    const titleEl = el.querySelector('.article_magazine_title_content, .article_magazine_title');
                    const anyLink = el.querySelector('a[href^="http"]:not([href*="inoreader"])');
                    const dateEl = el.querySelector('.article_date_short');
                    const authorEl = el.querySelector('.article_author');
                    return {
                      title: titleEl ? titleEl.innerText.trim() : '',
                      url: anyLink ? anyLink.href : '',
                      date_relative: dateEl ? dateEl.innerText.trim() : '',
                      source_text: authorEl ? authorEl.innerText.trim() : '',
                    };
                  });
                }"""
            )
        finally:
            browser.close()

    anchor = datetime.fromisoformat(now_iso)
    seen_in_page = set()
    for r in raw:
        if not r.get("url"):
            continue
        canon = canonicalize_url(r["url"])
        if canon in seen_in_page:
            continue
        seen_in_page.add(canon)
        # Inoreader titles often stack "title\nauthor\ndescription" — take first line
        title_line = (r.get("title") or "").split("\n", 1)[0].strip()
        published = parse_relative_time(r.get("date_relative", ""), anchor)
        items.append({
            "source_id": source["id"],
            "source_name": source["name"],
            "title": title_line,
            "url": r["url"],
            "canonical_url": canon,
            "published": published,
            "fetched": now_iso,
            "summary": "",
            "category": source.get("category", ""),
            "region": source.get("region", ""),
            "language": source.get("language", ""),
            "feed_type": source.get("feed_type", ""),
            "via_source": r.get("source_text", ""),
        })
    return items


# ---------- dedup ----------

def load_seen_urls(days: int) -> set[str]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    seen: set[str] = set()
    if not FEED_ROOT.exists():
        return seen
    for json_file in FEED_ROOT.rglob("*.json"):
        try:
            mtime = datetime.fromtimestamp(json_file.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff:
                continue
            data = json.loads(json_file.read_text())
            for item in data.get("items", []):
                if item.get("canonical_url"):
                    seen.add(item["canonical_url"])
        except Exception as exc:
            print(f"  [warn] could not read {json_file}: {exc}", file=sys.stderr)
    return seen


# ---------- output ----------

def render_items_md(items: list[dict]) -> str:
    lines = []
    for item in items:
        title = item["title"] or "(untitled)"
        url = item["url"]
        src = item["source_name"]
        pub = item.get("published") or item.get("fetched", "")
        # short date
        pub_short = pub[:16].replace("T", " ") if pub else ""
        lines.append(f"- [{title}]({url}) — *{src}* — {pub_short}")
        summary = item.get("summary", "").strip()
        if summary:
            lines.append(f"  > {summary[:240]}")
    return "\n".join(lines) + "\n"


def write_hour_output(items: list[dict], run_time: datetime) -> Path:
    dir_path = FEED_ROOT / f"{run_time.year:04d}" / f"{run_time.month:02d}" / f"{run_time.day:02d}"
    dir_path.mkdir(parents=True, exist_ok=True)
    hour_slug = f"{run_time.hour:02d}"
    json_path = dir_path / f"{hour_slug}.json"
    md_path = dir_path / f"{hour_slug}.md"

    payload = {
        "generated_at": run_time.isoformat(),
        "item_count": len(items),
        "items": items,
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    md = [
        f"# Yepisint — {run_time.strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        f"{len(items)} new items this run.",
        "",
    ]
    md.append(render_items_md(items))
    md_path.write_text("\n".join(md))
    return json_path


def rebuild_index(hours: int) -> None:
    """Roll up the last N hours of new items into index.md."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    recent: list[dict] = []
    if FEED_ROOT.exists():
        for json_file in sorted(FEED_ROOT.rglob("*.json"), reverse=True):
            try:
                mtime = datetime.fromtimestamp(json_file.stat().st_mtime, tz=timezone.utc)
                if mtime < cutoff:
                    continue
                data = json.loads(json_file.read_text())
                recent.extend(data.get("items", []))
            except Exception:
                continue
    # sort by published (or fetched) desc
    recent.sort(key=lambda it: (it.get("published") or it.get("fetched") or ""), reverse=True)

    md = [
        "---",
        "title: Yepisyeni Türkiye — Raw Feed",
        "---",
        "",
        "# Yepisyeni Türkiye — Raw Feed",
        "",
        "Untransformed rolling view of the last 24 hours, straight from the sources.",
        "For the clustered bilingual view, see [index.md](index.md).",
        "",
        f"**Last {hours} hours — {len(recent)} items**",
        f"*Updated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*",
        "",
        "---",
        "",
    ]
    md.append(render_items_md(recent))
    md.append("")
    md.append("---")
    md.append("")
    md.append("Archive: [`feed/`](feed/) for per-run output.  ")
    md.append("Source list: [`sources.yaml`](sources.yaml).  ")
    md.append("Audit: [`phase0/PHASE0_REPORT.md`](phase0/PHASE0_REPORT.md).")
    INDEX_FILE.write_text("\n".join(md))


# ---------- main ----------

def main() -> int:
    run_time = datetime.now(timezone.utc)
    now_iso = run_time.isoformat()
    sources = yaml.safe_load(SOURCES_FILE.read_text())["sources"]

    ingestable = [
        s for s in sources
        if s.get("status") == "live"
        and s.get("feed_type") in INGEST_FEED_TYPES
        and any(s.get("category", "").startswith(p) for p in INGEST_CATEGORY_PREFIXES)
    ]

    print(f"[fetch] {len(ingestable)} ingestable sources at {now_iso}")

    seen_urls = load_seen_urls(DEDUP_WINDOW_DAYS)
    print(f"[fetch] {len(seen_urls)} URLs seen in last {DEDUP_WINDOW_DAYS} days")

    new_items: list[dict] = []
    per_source_counts: list[tuple[str, int, int, str]] = []

    for source in ingestable:
        ft = source.get("feed_type")
        try:
            if ft in ("rss", "atom", "youtube"):
                fetched = fetch_feedparser(source, now_iso)
            elif ft == "inoreader_html_playwright":
                fetched = fetch_inoreader_playwright(source, now_iso)
            else:
                continue
            # newest first so the per-source cap keeps the freshest items
            fetched.sort(
                key=lambda it: (it.get("published") or it.get("fetched") or ""),
                reverse=True,
            )
            added = 0
            for item in fetched:
                if added >= MAX_ITEMS_PER_SOURCE:
                    break
                canon = item["canonical_url"]
                if not canon or canon in seen_urls:
                    continue
                seen_urls.add(canon)
                new_items.append(item)
                added += 1
            per_source_counts.append((source["id"], len(fetched), added, ""))
            cap_note = " (capped)" if added == MAX_ITEMS_PER_SOURCE and len(fetched) > MAX_ITEMS_PER_SOURCE else ""
            print(f"  {source['id']}: {len(fetched)} raw / {added} new{cap_note}")
        except Exception as exc:
            per_source_counts.append((source["id"], 0, 0, f"ERROR: {exc}"))
            print(f"  {source['id']}: ERROR {exc}", file=sys.stderr)

    # sort new items by published desc
    new_items.sort(key=lambda it: (it.get("published") or it.get("fetched") or ""), reverse=True)

    if new_items:
        out = write_hour_output(new_items, run_time)
        print(f"[fetch] wrote {len(new_items)} new items -> {out.relative_to(REPO_ROOT)}")
    else:
        print("[fetch] no new items this run")

    rebuild_index(ROLLUP_WINDOW_HOURS)
    print(f"[fetch] rebuilt {INDEX_FILE.name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
