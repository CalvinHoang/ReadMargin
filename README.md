# AI Australia Radar

A news feed and intelligence dashboard on the **state of the AI industry in Australia** — by geography, and across time (past · now · future).

## What it tracks

| Screen | What's on it |
|---|---|
| **Current Affairs** | The live feed: what is happening right now in Australian AI |
| **Markets & Deals** | Serious markets — bids, tenders, purchase orders, government procurement, investments, M&A |
| **Build-outs** | AI/data-centre infrastructure build-outs, state by state (NSW, VIC, QLD, WA, SA, TAS, ACT, NT) with status: operational, under construction, announced |
| **White Papers** | Older white papers, roadmaps and policy reports that are still relevant — the long-term context |

Every item is tagged with a **geography** (a state/territory or National) and a **time horizon**:

- **Past** — history and context that still matters
- **Now** — current affairs
- **Future** — announced pipeline, forecasts, things not yet built

Use the state chips and the Past / Now / Future lens at the top of any screen to slice the feed.

## Running it

It's a static site — no build step.

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

Or enable **GitHub Pages** on this repo (Settings → Pages → deploy from branch, root folder) and it's live.

## How the feed stays fresh

- `data/news.json` — the feed. Seeded with curated, sourced items; refreshed automatically.
- `scripts/fetch_feeds.py` — pulls Google News RSS queries scoped to Australian AI topics (investment, tenders/procurement, data-centre build-outs, policy), tags each item by category and state, dedupes, and merges into `data/news.json`. Standard library only — no dependencies.
- `.github/workflows/refresh-feed.yml` — runs the fetcher every 6 hours and commits changes.

Run a refresh manually:

```bash
python3 scripts/fetch_feeds.py
```

## Curated registers (hand-maintained)

- `data/buildouts.json` — the infrastructure register: who is building what, where, how many MW, and at what stage.
- `data/whitepapers.json` — the white-paper library: reports worth keeping even as they age.

Both are meant to be edited by hand (or by asking Claude) as the landscape moves — pull requests welcome.
