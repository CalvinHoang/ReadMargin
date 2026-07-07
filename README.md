# AI Australia Radar

A **reading digest of the AI industry** — energy, infrastructure, chips, models and the application layer — in economic and investment detail, through an Australian lens.

The purpose: read it daily and come away understanding *how the industry works*, not just what happened. Deep analysis is ranked above wire news.

## The value chain

Every article is tagged with a **layer** of the stack, and the briefing walks the stack in order:

| Layer | The economic question |
|---|---|
| **Energy** | Can the grid supply the load, at what price? (AEMO, PPAs, renewables) |
| **Infrastructure** | Who is building data centres, at what capex? (NEXTDC, AirTrunk, CDC, hyperscalers) |
| **Chips** | Who gets silicon, at what price? (NVIDIA, TSMC, export controls) |
| **Models** | What does intelligence cost to train and serve? (frontier labs, API pricing) |
| **Applications** | Where does AI actually earn revenue? (enterprise adoption, productivity, startups) |

Articles are also tagged with a **scope** (Australia / Global — global items are kept only when they matter to the Australian picture) and cross-tags (economics, investment, policy).

## Screens

- **Briefing** — the front page: top reads ranked by depth + recency, then each layer of the stack in order. Filter by layer or scope, search everything. The Infrastructure layer includes the hand-maintained build-out register.
- **Markets & Deals** — investment flows: raises, M&A, procurement, market moves.
- **Pulse** — the key numbers end to end, every figure sourced and dated.
- **Foundations** — evergreen reading per layer that explains the economics. Start here.

## Running it

It's a static site — no build step.

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

Or enable **GitHub Pages** on this repo (Settings → Pages → deploy from branch, root folder) and it's live.

## How the feed stays fresh

`scripts/fetch_feeds.py` (standard library only) refreshes `data/news.json` from two tiers of sources:

1. **Deep-analysis publishers** via direct RSS — SemiAnalysis, Epoch AI, Construction Physics, Uptime Institute, The Next Platform, Data Center Dynamics, plus Australian outlets (InnovationAus, iTnews, RenewEconomy, The Conversation). These carry a depth weight that ranks them above wire news.
2. **Targeted Google News queries per layer**, written for economic substance (capex, pricing, supply) rather than headline volume.

Each item is classified into a layer, scoped Australia/Global, cross-tagged, and scored for depth. `.github/workflows/refresh-feed.yml` runs it every 6 hours and commits changes.

Run a refresh manually:

```bash
python3 scripts/fetch_feeds.py
```

## Curated data (hand-maintained)

- `data/foundations.json` — the evergreen library: what to read to understand each layer, and what each piece teaches.
- `data/buildouts.json` — the infrastructure register: who is building what, where, how many MW, at what stage.
- `data/stats.json` — the Pulse figures, each with source and as-of date.

All three are meant to be edited by hand (or by asking Claude) as the landscape moves — pull requests welcome.
