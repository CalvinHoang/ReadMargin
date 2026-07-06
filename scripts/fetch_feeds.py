#!/usr/bin/env python3
"""Refresh data/news.json from Google News RSS queries scoped to Australian AI topics.

Standard library only. Tags each item with categories (markets/bids/investments/
buildouts/policy), geography (state/territory or National) and a time horizon,
then merges with existing items (curated seed items are never dropped).
"""

import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

NEWS_PATH = Path(__file__).resolve().parent.parent / "data" / "news.json"

# Query -> categories the results default to.
QUERIES = {
    'artificial intelligence Australia': ["current"],
    'AI investment Australia': ["investments"],
    'AI (tender OR procurement OR contract) Australia government': ["bids"],
    '"data centre" Australia (construction OR build OR megawatt)': ["buildouts"],
    'AI policy Australia government regulation': ["policy"],
    'AI startup Australia funding raise': ["investments", "markets"],
}

GEO_KEYWORDS = {
    "NSW": ["nsw", "new south wales", "sydney", "newcastle", "wollongong", "western sydney", "eastern creek", "kemps creek", "hunter valley"],
    "VIC": ["victoria", "melbourne", "geelong", "derrimut", "tullamarine"],
    "QLD": ["queensland", "brisbane", "gold coast", "townsville"],
    "WA": ["western australia", "perth", "pilbara"],
    "SA": ["south australia", "adelaide", "lot fourteen"],
    "TAS": ["tasmania", "hobart", "launceston"],
    "ACT": ["canberra", "act government", "australian capital territory"],
    "NT": ["northern territory", "darwin"],
}

CATEGORY_KEYWORDS = {
    "bids": ["tender", "procurement", "purchase order", "standing offer", "rfp", "rfq", "bid", "panel arrangement", "contract award"],
    "investments": ["invest", "funding", "raise", "raised", "capital", "billion", "million", "ipo", "acquisition", "acquire", "stake", "venture"],
    "buildouts": ["data centre", "data center", "datacentre", "megawatt", " mw", "gigawatt", "construction", "campus", "facility", "infrastructure", "build-out", "buildout"],
    "policy": ["policy", "regulation", "regulatory", "legislation", "guardrail", "framework", "government plan", "white paper", "inquiry"],
    "markets": ["asx", "shares", "stock", "market", "ipo", "merger", "acquisition", "valuation"],
}

FUTURE_WORDS = ["will ", "plans to", "planned", "to build", "pipeline", "by 2030", "by 2029", "by 2028", "forecast", "expected to", "announces", "proposal", "proposed"]

MAX_ITEMS = 250
USER_AGENT = "Mozilla/5.0 (compatible; AIAustraliaRadar/1.0; +https://github.com/CalvinHoang/ReadMargin)"


def fetch_rss(query: str) -> list[dict]:
    url = ("https://news.google.com/rss/search?q=" + urllib.parse.quote(query)
           + "&hl=en-AU&gl=AU&ceid=AU:en")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        root = ET.fromstring(resp.read())
    items = []
    for node in root.iter("item"):
        title = (node.findtext("title") or "").strip()
        link = (node.findtext("link") or "").strip()
        pub = node.findtext("pubDate")
        source = (node.findtext("source") or "").strip()
        desc = re.sub(r"<[^>]+>", " ", node.findtext("description") or "").strip()
        if not title or not link:
            continue
        try:
            date = parsedate_to_datetime(pub).date().isoformat() if pub else None
        except (TypeError, ValueError):
            date = None
        items.append({"title": title, "url": link, "source": source, "date": date, "summary": desc[:280]})
    return items


def tag(item: dict, default_cats: list[str]) -> dict:
    text = (item["title"] + " " + item.get("summary", "")).lower()

    cats = set(c for c in default_cats if c != "current")
    for cat, words in CATEGORY_KEYWORDS.items():
        if any(w in text for w in words):
            cats.add(cat)
    item["categories"] = sorted(cats) if cats else ["current"]

    geos = [st for st, words in GEO_KEYWORDS.items() if any(w in text for w in words)]
    item["geography"] = geos or ["National"]

    item["horizon"] = "future" if any(w in text for w in FUTURE_WORDS) else "now"
    item["id"] = "gn-" + re.sub(r"[^a-z0-9]+", "-", item["title"].lower())[:80].strip("-")
    return item


def main() -> None:
    existing = json.loads(NEWS_PATH.read_text()) if NEWS_PATH.exists() else {"items": []}
    by_id = {i["id"]: i for i in existing.get("items", [])}
    seen_titles = {i["title"].lower() for i in existing.get("items", [])}

    added = 0
    for query, cats in QUERIES.items():
        try:
            for raw in fetch_rss(query):
                item = tag(raw, cats)
                if item["id"] in by_id or item["title"].lower() in seen_titles:
                    continue
                by_id[item["id"]] = item
                seen_titles.add(item["title"].lower())
                added += 1
        except Exception as exc:  # keep going if one query fails
            print(f"warn: query {query!r} failed: {exc}")
        time.sleep(1)

    items = list(by_id.values())
    items.sort(key=lambda i: (i.get("date") or "0000"), reverse=True)
    # Trim oldest non-curated items beyond the cap; curated seeds are kept.
    kept, overflow = [], 0
    for item in items:
        if item.get("curated") or len(kept) < MAX_ITEMS:
            kept.append(item)
        else:
            overflow += 1

    out = {"updated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "items": kept}
    NEWS_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(f"added {added} new items, kept {len(kept)}, trimmed {overflow}")


if __name__ == "__main__":
    main()
