#!/usr/bin/env python3
"""Phase 4.5 — scrape OSINT monitor homepages and distill notable items.

For each OSINT platform in sources.yaml (category starts with osint_monitor_,
status live or needs_verification), visit the homepage with headless
Chromium, convert the DOM to lightweight markdown, and ask DeepSeek to
extract 3–5 notable items with titles + URLs. Output goes to
osint_content/<platform_id>.json.

Platforms whose homepages are marketing / login walls / pure data APIs
return [] from DeepSeek. The renderer falls back to a static description
card in that case.

Playwright navigation has a 20s timeout and a short post-load wait; total
runtime ~5–8 min for 30 platforms. DeepSeek cost is ~$0.05–0.10 per full
run.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import yaml
from openai import OpenAI

REPO_ROOT = Path(__file__).resolve().parent
SOURCES_FILE = REPO_ROOT / "sources.yaml"
OUT_ROOT = REPO_ROOT / "osint_content"

MAX_HTML_CHARS = 8000   # trim DOM text before sending to DeepSeek
ITEMS_PER_PLATFORM = 5
NAV_TIMEOUT_MS = 20000

SYSTEM_PROMPT = (
    "You are an OSINT content distiller for a public-benefit dashboard. "
    "You read a platform's homepage markdown and extract the most notable, "
    "factual items — recent investigations, data releases, reports, "
    "incidents, dashboards. You never fabricate; if the page is marketing, "
    "a login wall, API docs, or has no substantive content, return an "
    "empty array. You always return valid JSON."
)


def _client() -> OpenAI | None:
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        print("[osint] DEEPSEEK_API_KEY not set — skipping distillation.", file=sys.stderr)
        return None
    return OpenAI(
        api_key=key,
        base_url="https://api.deepseek.com",
        timeout=30.0,
        max_retries=0,
    )


def dom_to_markdown(html: str, anchors: list[dict], base_url: str) -> str:
    """Produce a trimmed markdown-ish text. Prioritize link-bearing content."""
    # collapse whitespace in extracted text
    text = re.sub(r"\s+", " ", html or "").strip()
    # keep a compact list of anchors with their text (first 40 char text + href)
    anchor_lines: list[str] = []
    seen: set[str] = set()
    for a in anchors:
        href = (a.get("href") or "").strip()
        t = (a.get("text") or "").strip()
        if not href or not t or len(t) < 3:
            continue
        if href.startswith("#") or href.startswith("javascript:"):
            continue
        absolute = urljoin(base_url, href)
        if absolute in seen:
            continue
        seen.add(absolute)
        anchor_lines.append(f"- [{t[:140]}]({absolute})")
        if len(anchor_lines) >= 60:
            break
    md = f"PAGE TEXT:\n{text[:MAX_HTML_CHARS]}\n\nLINKS:\n" + "\n".join(anchor_lines)
    return md[:MAX_HTML_CHARS + 6000]


def scrape_platform(page, source: dict) -> tuple[str, list[dict]]:
    url = source["homepage"]
    page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
    # brief idle so JS-rendered content can paint; don't block on it
    try:
        page.wait_for_load_state("networkidle", timeout=4000)
    except Exception:
        pass
    page.wait_for_timeout(800)
    text = page.evaluate("() => document.body ? document.body.innerText : ''")
    anchors = page.evaluate(
        """() => Array.from(document.querySelectorAll('a[href]')).map(a => ({
             href: a.getAttribute('href'),
             text: (a.innerText || a.textContent || '').trim()
           }))"""
    )
    return text, anchors


def distill(client: OpenAI, source: dict, markdown: str) -> list[dict]:
    prompt = (
        f"Platform: {source['name']}\n"
        f"URL: {source['homepage']}\n"
        f"Category: {source.get('category', '')}\n"
        f"One-line description: {(source.get('notes') or '').split('.')[0]}\n\n"
        "CONTENT FROM HOMEPAGE (truncated):\n"
        f"{markdown}\n\n"
        "Extract up to 5 notable items visible on this page. Each item is "
        "ideally a specific report, incident, investigation, data release, "
        "dashboard widget, or similar substantive surface — not menu links, "
        "not marketing taglines, not navigation, not login prompts.\n\n"
        "RETURN JSON matching this schema exactly:\n"
        "{\n"
        '  "items": [\n'
        "    {\n"
        '      "title_en": "concise English title, <= 14 words",\n'
        '      "title_tr": "Turkish translation, <= 14 words",\n'
        '      "url": "absolute URL to the specific item (not the homepage)",\n'
        '      "date": "ISO date if visible on the page, otherwise empty string"\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Rules:\n"
        '- If the page is marketing, a login wall, pure API docs, an empty '
        'catalog, or has nothing substantive to extract, return {"items": []}.\n'
        "- Prefer items that are NEW (recent date, active incident, fresh "
        "dataset).\n"
        "- URL must be an absolute URL distinct from the homepage. If only "
        "the homepage is available, return empty.\n"
        "- Never fabricate. Only items visible in the provided content."
    )
    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=2400,
        )
        data = json.loads(resp.choices[0].message.content)
        items = data.get("items", []) or []
    except Exception as exc:
        print(f"  [{source['id']}] distill error: {exc}", file=sys.stderr)
        return []

    # normalize, clamp, dedupe by URL
    out: list[dict] = []
    seen: set[str] = set()
    for it in items[:ITEMS_PER_PLATFORM]:
        if not isinstance(it, dict):
            continue
        url = (it.get("url") or "").strip()
        if not url or url == source["homepage"]:
            continue
        if url in seen:
            continue
        seen.add(url)
        out.append({
            "title_en": (it.get("title_en") or "").strip()[:220],
            "title_tr": (it.get("title_tr") or "").strip()[:220],
            "url": url,
            "date": (it.get("date") or "").strip(),
        })
    return out


def main() -> int:
    client = _client()
    if client is None:
        return 0

    sources = yaml.safe_load(SOURCES_FILE.read_text())["sources"]
    targets = [
        s for s in sources
        if s.get("category", "").startswith("osint_monitor_")
        and s.get("status") in ("live", "needs_verification")
    ]

    print(f"[osint] distilling {len(targets)} platforms")
    OUT_ROOT.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import sync_playwright
    stamp = datetime.now(timezone.utc).isoformat()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)

        for s in targets:
            t0 = time.time()
            items: list[dict] = []
            err = ""
            # fresh context + page per platform — one platform's nav failure
            # must not cascade into the next platform's goto.
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (YepisintFetcher/0.1; +https://yepisyeniturkiye.github.io)",
                viewport={"width": 1280, "height": 900},
                locale="en-US",
            )
            # hard-cap every Playwright operation. one misbehaving homepage
            # cannot hang the entire daily run. 15s > the 4s networkidle
            # budget used in scrape_platform so it only bites on true hangs.
            ctx.set_default_timeout(15000)
            ctx.set_default_navigation_timeout(15000)
            page = ctx.new_page()
            try:
                text, anchors = scrape_platform(page, s)
                md = dom_to_markdown(text, anchors, s["homepage"])
                items = distill(client, s, md)
            except Exception as exc:
                err = str(exc)[:240]
                print(f"  [{s['id']}] scrape error: {err}", file=sys.stderr)
            finally:
                try:
                    ctx.close()
                except Exception:
                    pass

            out = {
                "platform_id": s["id"],
                "platform_name": s["name"],
                "homepage": s["homepage"],
                "category": s.get("category", ""),
                "fetched_at": stamp,
                "error": err,
                "items": items,
            }
            (OUT_ROOT / f"{s['id']}.json").write_text(
                json.dumps(out, indent=2, ensure_ascii=False)
            )
            took = int((time.time() - t0) * 1000)
            print(f"  {s['id']:30s} {len(items):2d} items  {took}ms"
                  f"{' (error)' if err else ''}")

        browser.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
