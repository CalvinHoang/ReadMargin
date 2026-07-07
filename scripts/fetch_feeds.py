#!/usr/bin/env python3
"""Refresh data/news.json — a reading digest of the AI industry, Australia-first.

Two source tiers, standard library only:

  Tier 1  Direct RSS/Atom feeds from deep-analysis publishers (the economics of
          energy, data centres, chips, models and the application layer).
  Tier 2  Targeted Google News queries per value-chain layer, written for
          economic substance rather than headline volume.

Every item is tagged with a value-chain layer (energy / infrastructure / chips /
models / applications), cross-tags (economics, investment, policy), a scope
(au / global) and a depth score used by the front-end to rank the briefing.
Global items are kept only when they plausibly matter to the Australian picture
(deep-analysis sources always do; wire news must mention majors or supply-chain
terms that reach Australia).
"""

import hashlib
import html
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
USER_AGENT = "Mozilla/5.0 (compatible; AIAustraliaRadar/2.0; +https://github.com/CalvinHoang/Aiautra)"
MAX_ITEMS = 400
MAX_PER_FEED = 25

LAYERS = ["energy", "infrastructure", "chips", "models", "applications"]

# ---------------------------------------------------------------------------
# Tier 1 — deep-analysis publishers, fetched directly.
# layer: default layer when keywords are inconclusive. weight: depth prior.
# ---------------------------------------------------------------------------
FEEDS = [
    {"url": "https://semianalysis.com/feed/", "source": "SemiAnalysis", "layer": "chips", "weight": 3},
    {"url": "https://epoch.ai/feed.xml", "source": "Epoch AI", "layer": "models", "weight": 3},
    {"url": "https://www.interconnects.ai/feed", "source": "Interconnects", "layer": "models", "weight": 3},
    {"url": "https://stratechery.com/feed/", "source": "Stratechery", "layer": "applications", "weight": 3},
    {"url": "https://www.construction-physics.com/feed", "source": "Construction Physics", "layer": "infrastructure", "weight": 3},
    {"url": "https://www.latent.space/feed", "source": "Latent Space", "layer": "applications", "weight": 2},
    {"url": "https://www.nextplatform.com/feed/", "source": "The Next Platform", "layer": "chips", "weight": 2},
    {"url": "https://www.datacenterdynamics.com/rss/", "source": "Data Center Dynamics", "layer": "infrastructure", "weight": 2},
    {"url": "https://journal.uptimeinstitute.com/feed/", "source": "Uptime Institute", "layer": "infrastructure", "weight": 3},
    {"url": "https://semiengineering.com/feed/", "source": "Semiconductor Engineering", "layer": "chips", "weight": 2},
    {"url": "https://www.theregister.com/software/ai_ml/headlines.atom", "source": "The Register", "layer": "models", "weight": 1},
    # Australian outlets — everything from these defaults to AU scope.
    {"url": "https://www.innovationaus.com/feed/", "source": "InnovationAus", "layer": "applications", "weight": 2, "scope": "au"},
    {"url": "https://www.itnews.com.au/rss/rss.ashx", "source": "iTnews", "layer": "applications", "weight": 1, "scope": "au"},
    {"url": "https://reneweconomy.com.au/feed/", "source": "RenewEconomy", "layer": "energy", "weight": 2, "scope": "au"},
    {"url": "https://theconversation.com/au/technology/articles.atom", "source": "The Conversation", "layer": "applications", "weight": 2, "scope": "au"},
]

# Tier-1 feeds cover many topics; keep only items that are about AI / compute.
AI_RELEVANCE = [
    "ai", "artificial intelligence", "machine learning", "llm", "gpu", "data centre",
    "data center", "datacenter", "chip", "semiconductor", "nvidia", "tsmc", "compute",
    "model", "inference", "training", "accelerator", "hyperscale", "openai", "anthropic",
    "foundry", "hbm", "cuda", "neural", "genai", "generative", "copilot", "agent",
]

# ---------------------------------------------------------------------------
# Tier 2 — Google News queries, per layer.
# ---------------------------------------------------------------------------
QUERIES = [
    # Energy — the grid economics of AI load in Australia, plus the global picture.
    {"q": '"data centre" Australia (electricity OR grid OR AEMO OR megawatt OR power)', "layer": "energy", "scope": "au"},
    {"q": 'data centre Australia (PPA OR renewable OR solar OR "power purchase")', "layer": "energy", "scope": "au"},
    {"q": 'AI "data center" (gigawatt OR "power demand" OR grid OR nuclear OR electricity price)', "layer": "energy", "scope": "global"},
    # Infrastructure — who is building what, at what cost.
    {"q": 'data centre Australia (capex OR investment OR construction OR campus OR approval)', "layer": "infrastructure", "scope": "au"},
    {"q": '(NEXTDC OR AirTrunk OR "CDC Data Centres" OR Goodman OR Macquarie) data centre', "layer": "infrastructure", "scope": "au"},
    {"q": '(Microsoft OR Google OR Amazon OR Meta OR Oracle) capex "data center" (billion OR spending)', "layer": "infrastructure", "scope": "global"},
    # Chips — supply, pricing, allocation, and where Australia sits.
    {"q": '(Nvidia OR TSMC OR AMD) (supply OR pricing OR capacity OR export controls) AI chips', "layer": "chips", "scope": "global"},
    {"q": 'AI chips (HBM OR foundry OR wafer OR packaging) (shortage OR capacity OR price)', "layer": "chips", "scope": "global"},
    {"q": 'Australia (GPU OR "AI chips" OR Nvidia) (access OR sovereign OR supply OR allocation)', "layer": "chips", "scope": "au"},
    # Models — the economics of building and serving frontier models.
    {"q": '(OpenAI OR Anthropic OR "Google DeepMind" OR Meta AI) (revenue OR pricing OR "training cost" OR economics)', "layer": "models", "scope": "global"},
    {"q": 'AI model ("inference cost" OR "API pricing" OR "cost per token" OR "training run")', "layer": "models", "scope": "global"},
    {"q": 'sovereign AI model Australia (Kangaroo OR CSIRO OR local OR onshore)', "layer": "models", "scope": "au"},
    # Applications — where AI actually earns revenue, especially in Australia.
    {"q": 'AI adoption Australia (enterprise OR productivity OR ROI OR revenue)', "layer": "applications", "scope": "au"},
    {"q": 'AI (startup OR software) Australia (raise OR funding OR ASX OR valuation)', "layer": "applications", "scope": "au"},
    {"q": 'AI application (ARR OR revenue OR monetisation OR "unit economics")', "layer": "applications", "scope": "global"},
]

# ---------------------------------------------------------------------------
# Classification keywords.
# ---------------------------------------------------------------------------
LAYER_KEYWORDS = {
    "energy": ["electricity", "grid", "megawatt", " mw", "gigawatt", " gw", "power purchase",
               "ppa", "aemo", "renewable", "solar", "wind farm", "nuclear", "gas turbine",
               "energy demand", "power demand", "substation", "transmission", "kwh", "mwh",
               "energy market", "power plant", "battery storage", "electricity price"],
    "infrastructure": ["data centre", "data center", "datacenter", "datacentre", "hyperscale",
                       "colocation", "capex", "campus", "construction", "cooling", "rack",
                       "facility", "build-out", "buildout", "nextdc", "airtrunk", "cdc data",
                       "equinix", "digital realty", "land acquisition", "planning approval",
                       "fibre", "fiber", "subsea cable", "cloud region"],
    "chips": ["chip", "semiconductor", "gpu", "nvidia", "tsmc", "amd ", "foundry", "wafer",
              "hbm", "accelerator", "cuda", "lithography", "asml", "packaging", "export control",
              "h100", "h200", "b200", "gb200", "blackwell", "tpu", "silicon", "fab ", "fabs",
              "node", "tape-out", "arm ", "broadcom"],
    "models": ["model", "llm", "training run", "inference", "frontier", "openai", "anthropic",
               "deepmind", "gemini", "claude", "gpt", "llama", "benchmark", "fine-tun",
               "parameters", "token", "context window", "reasoning", "open source model",
               "open-weight", "alignment", "scaling law", "pretraining", "rlhf"],
    "applications": ["adoption", "enterprise", "productivity", "copilot", "chatbot", "agent",
                     "saas", "software", "workflow", "automation", "customer", "startup",
                     "app ", "apps ", "deployment", "use case", "roi", "arr", "revenue",
                     "healthcare", "legal tech", "fintech", "mining", "agriculture", "education"],
}

TAG_KEYWORDS = {
    "economics": ["cost", "economics", "margin", "pricing", "price", "capex", "opex", "revenue",
                  "unit economics", "tco", "depreciation", "utilisation", "utilization",
                  "billion", "million", "cash flow", "profit", "demand", "supply", "$"],
    "investment": ["invest", "funding", "raise", "raised", "capital", "ipo", "acquisition",
                   "acquire", "stake", "venture", "valuation", "m&a", "merger", "fund ",
                   "asx", "shares", "stock", "backed"],
    "policy": ["policy", "regulation", "regulatory", "legislation", "government", "minister",
               "guardrail", "framework", "inquiry", "tender", "procurement", "sovereign",
               "national ai", "export control", "subsidy", "grant"],
}

# Signals that a piece explains something rather than just reports it.
DEPTH_KEYWORDS = ["economics", "cost of", "unit economics", "margins", "capex", "cost curve",
                  "supply chain", "explained", "deep dive", "analysis", "why ", "how ",
                  "the state of", "breakdown", "anatomy", "per token", "per gpu", "tco",
                  "payback", "depreciation", "utilisation", "utilization", "bottleneck"]

AU_KEYWORDS = ["australia", "australian", "sydney", "melbourne", "brisbane", "perth", "adelaide",
               "canberra", "nsw", "queensland", "victoria", "tasmania", "aemo", "csiro", "asx",
               "nextdc", "airtrunk", "cdc data centres", "telstra", "atlassian", "canva",
               "macquarie", "hobart", "darwin", "new south wales", "western australia"]

# A global wire-news item earns its place only if it touches the parts of the
# value chain that reach Australia: hyperscalers, chip supply, model economics.
GLOBAL_RELEVANCE = ["nvidia", "tsmc", "microsoft", "google", "amazon", "aws", "meta", "openai",
                    "anthropic", "oracle", "capex", "export control", "gpu", "hbm", "data center",
                    "data centre", "hyperscale", "inference cost", "training cost", "gigawatt",
                    "supply chain", "asml", "amd", "chip", "frontier model"]


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def strip_html(text: str) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def polish(item: dict) -> dict:
    """Clean Google News artifacts: ' - Publisher' title suffixes and
    descriptions that merely repeat the headline."""
    title = strip_html(item.get("title") or "")
    summary = strip_html(item.get("summary") or "")
    source = strip_html(item.get("source") or "")

    if item.get("kind") == "news" and " - " in title:
        stem, suffix = title.rsplit(" - ", 1)
        if len(suffix) < 48 and stem:
            title = stem.strip()
            if not source:
                source = suffix.strip()

    if summary and (_norm(title) in _norm(summary) or _norm(summary) in _norm(title)):
        summary = ""

    item["title"] = title
    item["summary"] = summary
    item["source"] = source
    return item


def parse_date(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    try:
        return parsedate_to_datetime(raw).date().isoformat()
    except (TypeError, ValueError):
        pass
    m = re.match(r"(\d{4}-\d{2}-\d{2})", raw)
    return m.group(1) if m else None


def parse_feed(data: bytes) -> list[dict]:
    """Parse RSS 2.0 or Atom into {title, url, date, summary, source?}."""
    root = ET.fromstring(data)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    out = []
    for node in root.iter("item"):  # RSS 2.0
        title = strip_html(node.findtext("title") or "")
        link = (node.findtext("link") or "").strip()
        if not title or not link:
            continue
        out.append({
            "title": title,
            "url": link,
            "date": parse_date(node.findtext("pubDate")),
            "summary": strip_html(node.findtext("description") or "")[:300],
            "source": strip_html(node.findtext("source") or ""),
        })
    if not out:  # Atom
        for node in root.iter("{http://www.w3.org/2005/Atom}entry"):
            title = strip_html(node.findtext("atom:title", namespaces=ns) or "")
            link = ""
            for l in node.findall("atom:link", ns):
                if l.get("rel") in (None, "alternate"):
                    link = l.get("href", "")
                    break
            if not title or not link:
                continue
            out.append({
                "title": title,
                "url": link,
                "date": parse_date(node.findtext("atom:updated", namespaces=ns)
                                   or node.findtext("atom:published", namespaces=ns)),
                "summary": strip_html(node.findtext("atom:summary", namespaces=ns)
                                      or node.findtext("atom:content", namespaces=ns) or "")[:300],
                "source": "",
            })
    return out


def classify_layer(text: str, default: str | None) -> str | None:
    scores = {layer: sum(1 for w in words if w in text)
              for layer, words in LAYER_KEYWORDS.items()}
    best = max(scores, key=lambda l: scores[l])
    if scores[best] >= 2:
        return best
    if scores[best] == 1:
        return best if default is None else default
    return default


def classify(item: dict, *, default_layer: str | None, default_scope: str | None,
             weight: int, kind: str) -> dict | None:
    """Tag an item; return None if it doesn't belong in the digest."""
    text = (item["title"] + " " + item.get("summary", "")).lower()

    layer = classify_layer(text, default_layer)
    if layer is None:
        return None

    is_au = any(w in text for w in AU_KEYWORDS) or default_scope == "au"
    scope = "au" if is_au else "global"
    # Global wire news must clear a relevance bar; deep-analysis sources always pass.
    if scope == "global" and kind == "news" and not any(w in text for w in GLOBAL_RELEVANCE):
        return None

    tags = [t for t, words in TAG_KEYWORDS.items() if any(w in text for w in words)]

    depth = weight * 3 + min(4, sum(1 for w in DEPTH_KEYWORDS if w in text))

    item["layer"] = layer
    item["scope"] = scope
    item["tags"] = tags
    item["depth"] = depth
    item["kind"] = kind
    item["id"] = "a-" + hashlib.sha1(item["url"].encode()).hexdigest()[:12]
    return polish(item)


def google_news(query: str) -> list[dict]:
    url = ("https://news.google.com/rss/search?q=" + urllib.parse.quote(query)
           + "&hl=en-AU&gl=AU&ceid=AU:en")
    return parse_feed(fetch(url))


def collect() -> list[dict]:
    items = []
    for feed in FEEDS:
        try:
            for raw in parse_feed(fetch(feed["url"]))[:MAX_PER_FEED]:
                text = (raw["title"] + " " + raw.get("summary", "")).lower()
                if not any(w in text for w in AI_RELEVANCE):
                    continue
                raw["source"] = feed["source"]
                tagged = classify(raw, default_layer=feed["layer"],
                                  default_scope=feed.get("scope"),
                                  weight=feed["weight"], kind="analysis")
                if tagged:
                    items.append(tagged)
        except Exception as exc:
            print(f"warn: feed {feed['source']} failed: {exc}")
        time.sleep(1)

    for spec in QUERIES:
        try:
            for raw in google_news(spec["q"])[:MAX_PER_FEED]:
                tagged = classify(raw, default_layer=spec["layer"],
                                  default_scope=spec["scope"] if spec["scope"] == "au" else None,
                                  weight=0, kind="news")
                if tagged:
                    items.append(tagged)
        except Exception as exc:
            print(f"warn: query {spec['q']!r} failed: {exc}")
        time.sleep(1)
    return items


def migrate(old: dict) -> dict:
    """Re-tag a pre-2.0 item into the layer taxonomy; None drops it."""
    if "layer" in old:
        return polish(old)
    kind = "analysis" if old.get("curated") else "news"
    weight = 1 if old.get("curated") else 0
    keep_keys = {"title", "url", "source", "date", "summary", "curated"}
    slim = {k: v for k, v in old.items() if k in keep_keys}
    return classify(slim, default_layer="applications" if old.get("curated") else None,
                    default_scope="au", weight=weight, kind=kind)


def main() -> None:
    existing = json.loads(NEWS_PATH.read_text()) if NEWS_PATH.exists() else {"items": []}
    by_id: dict[str, dict] = {}
    seen_titles: set[str] = set()

    for old in existing.get("items", []):
        item = migrate(old)
        if item is None or item["title"].lower() in seen_titles:
            continue
        by_id[item["id"]] = item
        seen_titles.add(item["title"].lower())

    added = 0
    for item in collect():
        if item["id"] in by_id or item["title"].lower() in seen_titles:
            continue
        by_id[item["id"]] = item
        seen_titles.add(item["title"].lower())
        added += 1

    items = sorted(by_id.values(), key=lambda i: (i.get("date") or "0000"), reverse=True)
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
