/* AI Australia Radar — reading digest front-end. No dependencies. */

const LAYER_ORDER = ["energy", "infrastructure", "chips", "models", "applications"];

const LAYER_META = {
  energy: {
    name: "Energy",
    blurb: "The stack starts at the grid. Electricity supply, pricing and connection queues decide what can be built — in Australia that story runs through AEMO, PPAs and the renewables build-out."
  },
  infrastructure: {
    name: "Infrastructure",
    blurb: "Data centres turn power into rentable compute. Watch capex, megawatts and approvals — NEXTDC, AirTrunk, CDC and the hyperscalers building on Australian soil."
  },
  chips: {
    name: "Chips",
    blurb: "Silicon is the scarcest input. NVIDIA, TSMC and the memory makers set the price of compute worldwide — and export controls decide who gets allocation, Australia included."
  },
  models: {
    name: "Models",
    blurb: "Frontier labs convert chips and power into intelligence. Training costs, inference pricing and API economics determine who can afford to compete — and what Australia buys versus builds."
  },
  applications: {
    name: "Applications",
    blurb: "Where AI has to earn its keep. Enterprise adoption, productivity gains and real revenue — the layer where Australian businesses mostly live."
  }
};

const SCREEN_INTROS = {
  briefing: "Today's most significant reads across the AI value chain, then each layer of the stack in order — from the grid up to the application layer.",
  markets: "The money: raises, M&A, procurement and market moves across the stack, most recent first.",
  pulse: "The key numbers, end to end: power, capacity, compute, money and adoption. Every figure is sourced and dated.",
  foundations: "Evergreen reading that explains how each layer of the industry works economically. Start here; the briefing will make more sense."
};

const LEAD_COUNT = 5;
const SECTION_LIMIT = 8;

const state = {
  screen: "briefing",
  layer: "all",
  scope: "all",
  query: "",
  expanded: new Set(),
  news: [],
  buildouts: [],
  foundations: [],
  stats: [],
  statsUpdated: null,
  updated: null
};

/* ---------- data loading ---------- */

async function loadData() {
  const [news, builds, foundations, stats] = await Promise.all([
    fetch("data/news.json").then(r => r.json()),
    fetch("data/buildouts.json").then(r => r.json()),
    fetch("data/foundations.json").then(r => r.json()),
    fetch("data/stats.json").then(r => r.json())
  ]);
  state.news = (news.items || []).slice().sort((a, b) => (b.date || "").localeCompare(a.date || ""));
  state.buildouts = builds.projects || [];
  state.foundations = foundations.entries || [];
  state.stats = stats.sections || [];
  state.statsUpdated = stats.updated;
  state.updated = news.updated;

  const today = new Date().toLocaleDateString("en-AU", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
  const upd = state.updated
    ? " — feed updated " + new Date(state.updated).toLocaleDateString("en-AU", { day: "numeric", month: "short" })
    : "";
  document.getElementById("dateline").textContent = today + upd;
}

/* ---------- filtering & ranking ---------- */

function matchesFilters(item) {
  if (state.layer !== "all" && item.layer !== state.layer) return false;
  if (state.scope !== "all" && item.scope !== state.scope) return false;
  if (state.query) {
    const hay = [item.title, item.summary, item.source, item.layer, ...(item.tags || [])]
      .filter(Boolean).join(" ").toLowerCase();
    if (!hay.includes(state.query)) return false;
  }
  return true;
}

function daysAgo(iso) {
  if (!iso) return 999;
  return Math.floor((Date.now() - new Date(iso + "T00:00:00")) / 86400000);
}

function significance(item) {
  const age = daysAgo(item.date);
  const freshness = age <= 2 ? 4 : age <= 7 ? 2 : age <= 14 ? 1 : 0;
  return (item.depth || 0) * 2 + freshness;
}

/* ---------- rendering helpers ---------- */

function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text != null) node.textContent = text;
  return node;
}

function fmtDate(iso) {
  if (!iso) return "";
  return new Date(iso + "T00:00:00").toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric" });
}

function sectionHead(title, sub) {
  const head = el("div", "section-head");
  head.append(el("h2", null, title));
  if (sub) head.append(el("span", "sub", sub));
  return head;
}

function story(item, { showLayer = true } = {}) {
  const art = el("article", "story");

  const kicker = el("div", "kicker");
  if (showLayer) kicker.append(el("span", "layer", LAYER_META[item.layer]?.name || item.layer));
  kicker.append(el("span", "badge " + (item.scope === "au" ? "au" : ""), item.scope === "au" ? "Australia" : "Global"));
  if (item.kind === "analysis") kicker.append(el("span", "badge deep", "Deep read"));
  art.append(kicker);

  const h3 = el("h3");
  const a = el("a", null, item.title);
  a.href = item.url; a.target = "_blank"; a.rel = "noopener";
  h3.append(a);
  art.append(h3);

  if (item.summary) art.append(el("p", "summary", item.summary));

  const byline = el("p", "byline");
  const src = el("strong", null, item.source || "");
  byline.append(src);
  if (item.date) byline.append(document.createTextNode(" · " + fmtDate(item.date)));
  art.append(byline);
  return art;
}

/* ---------- briefing screen ---------- */

function renderBuildoutRegister(root) {
  const projects = state.buildouts
    .filter(p => !state.query || (p.name + " " + p.operator + " " + p.location).toLowerCase().includes(state.query))
    .slice().sort((a, b) => (b.capacity_mw || 0) - (a.capacity_mw || 0));
  if (!projects.length) return;
  const mw = projects.reduce((s, p) => s + (p.capacity_mw || 0), 0);
  root.append(sectionHead("Build-out register", projects.length + " projects · " + mw.toLocaleString() + "+ MW tracked"));
  root.append(el("p", "section-blurb", "AI and data-centre infrastructure across Australia, largest first."));
  const reg = el("div", "register");
  for (const p of projects) {
    const row = el("div", "project");
    row.append(el("span", "status " + p.status, p.status));
    const a = el("a", null, p.name);
    a.href = p.url; a.target = "_blank"; a.rel = "noopener";
    row.append(a);
    row.append(el("span", "where", p.operator + " · " + p.location));
    if (p.capacity_mw) row.append(el("span", "mw", p.capacity_mw.toLocaleString() + " MW"));
    reg.append(row);
  }
  root.append(reg);
}

function renderBriefing(root) {
  const visible = state.news.filter(matchesFilters);
  if (!visible.length && state.layer !== "infrastructure") {
    root.append(el("div", "empty-state", "Nothing in this slice — widen the filters."));
    return;
  }

  const leadIds = new Set();
  // Lead section only in the unfiltered layer view — a layer filter means "show me that layer".
  if (state.layer === "all") {
    const lead = visible
      .filter(i => daysAgo(i.date) <= 14)
      .sort((a, b) => significance(b) - significance(a))
      .slice(0, LEAD_COUNT);
    if (lead.length) {
      root.append(sectionHead("Top reads", "ranked by depth and recency"));
      const wrap = el("div", "lead");
      lead.forEach(i => { leadIds.add(i.id); wrap.append(story(i)); });
      root.append(wrap);
    }
  }

  const layers = state.layer === "all" ? LAYER_ORDER : [state.layer];
  for (const layer of layers) {
    const items = visible.filter(i => i.layer === layer && !leadIds.has(i.id))
      .sort((a, b) => significance(b) - significance(a));
    if (items.length || layer === "infrastructure") {
      const meta = LAYER_META[layer];
      root.append(sectionHead(meta.name, items.length ? items.length + (items.length === 1 ? " read" : " reads") : ""));
      root.append(el("p", "section-blurb", meta.blurb));
      const limit = (state.layer !== "all" || state.expanded.has(layer)) ? Infinity : SECTION_LIMIT;
      items.slice(0, limit).forEach(i => root.append(story(i, { showLayer: false })));
      if (items.length > limit) {
        const note = el("p", "more-note");
        const btn = el("button", null, "Show all " + items.length + " " + meta.name.toLowerCase() + " reads");
        btn.addEventListener("click", () => { state.expanded.add(layer); render(); });
        note.append(btn);
        root.append(note);
      }
    }
    if (layer === "infrastructure" && state.layer === "infrastructure" && state.scope !== "global") {
      renderBuildoutRegister(root);
    }
  }
}

/* ---------- markets screen ---------- */

function renderMarkets(root) {
  const items = state.news
    .filter(i => (i.tags || []).includes("investment"))
    .filter(matchesFilters);
  if (!items.length) {
    root.append(el("div", "empty-state", "No deals in this slice — widen the filters."));
    return;
  }
  items.forEach(i => root.append(story(i)));
}

/* ---------- foundations screen ---------- */

function renderFoundations(root) {
  const layers = state.layer === "all" ? LAYER_ORDER : [state.layer];
  let any = false;
  for (const layer of layers) {
    const entries = state.foundations.filter(f => {
      if (f.layer !== layer) return false;
      if (state.scope !== "all" && f.scope !== state.scope) return false;
      if (state.query && !(f.title + " " + f.publisher + " " + f.teaches).toLowerCase().includes(state.query)) return false;
      return true;
    });
    if (!entries.length) continue;
    any = true;
    const meta = LAYER_META[layer];
    root.append(sectionHead(meta.name, entries.length + (entries.length === 1 ? " read" : " reads")));
    for (const f of entries.slice().sort((a, b) => b.year - a.year)) {
      const card = el("article", "foundation");
      const kicker = el("div", "kicker");
      kicker.append(el("span", "badge " + (f.scope === "au" ? "au" : ""), f.scope === "au" ? "Australia" : "Global"));
      kicker.append(el("span", "badge", String(f.year)));
      card.append(kicker);
      const h3 = el("h3");
      const a = el("a", null, f.title);
      a.href = f.url; a.target = "_blank"; a.rel = "noopener";
      h3.append(a);
      card.append(h3);
      card.append(el("p", "byline"));
      card.lastChild.append(el("strong", null, f.publisher));
      card.append(el("p", "teaches", f.teaches));
      root.append(card);
    }
  }
  if (!any) root.append(el("div", "empty-state", "Nothing in this slice — widen the filters."));
}

/* ---------- pulse screen ---------- */

function statTile(t) {
  const tile = el("article", "stat-tile");
  tile.append(el("p", "stat-label", t.label));
  tile.append(el("p", "stat-value", t.value));
  if (t.delta) tile.append(el("p", "stat-delta", t.delta));
  if (t.context) tile.append(el("p", "stat-context", t.context));
  const src = el("p", "stat-source");
  const a = el("a", null, t.source);
  a.href = t.source_url; a.target = "_blank"; a.rel = "noopener";
  src.append(a);
  if (t.as_of) src.append(document.createTextNode(" · " + t.as_of));
  tile.append(src);
  return tile;
}

function renderPulse(root) {
  for (const section of state.stats) {
    root.append(sectionHead(section.title));
    if (section.blurb) root.append(el("p", "section-blurb", section.blurb));
    const grid = el("div", "stat-grid");
    (section.tiles || []).forEach(t => grid.append(statTile(t)));
    root.append(grid);
  }
  if (state.statsUpdated) {
    root.append(el("p", "section-blurb", "Figures last reviewed " + state.statsUpdated +
      ". Hand-maintained in data/stats.json — each tile keeps its source and as-of date."));
  }
}

/* ---------- render ---------- */

function render() {
  const root = document.getElementById("screen-root");
  root.innerHTML = "";
  root.append(el("p", "screen-intro", SCREEN_INTROS[state.screen]));

  document.getElementById("controls").style.display = state.screen === "pulse" ? "none" : "";

  switch (state.screen) {
    case "briefing": renderBriefing(root); break;
    case "markets": renderMarkets(root); break;
    case "foundations": renderFoundations(root); break;
    case "pulse": renderPulse(root); break;
  }
}

/* ---------- controls ---------- */

function buildLayerChips() {
  const wrap = document.getElementById("layer-chips");
  wrap.innerHTML = "";
  const all = el("button", "chip active", "The whole stack");
  all.dataset.layer = "all";
  wrap.append(all);
  LAYER_ORDER.forEach(l => {
    const chip = el("button", "chip", LAYER_META[l].name);
    chip.dataset.layer = l;
    wrap.append(chip);
  });
  wrap.addEventListener("click", e => {
    const chip = e.target.closest(".chip");
    if (!chip) return;
    state.layer = chip.dataset.layer;
    state.expanded.clear();
    wrap.querySelectorAll(".chip").forEach(c => c.classList.toggle("active", c === chip));
    render();
  });
}

function wireControls() {
  document.querySelector(".tabs").addEventListener("click", e => {
    const tab = e.target.closest(".tab");
    if (!tab) return;
    state.screen = tab.dataset.screen;
    document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t === tab));
    render();
  });

  document.getElementById("scope-toggle").addEventListener("click", e => {
    const chip = e.target.closest(".chip");
    if (!chip) return;
    state.scope = chip.dataset.scope;
    document.querySelectorAll("#scope-toggle .chip").forEach(c => c.classList.toggle("active", c === chip));
    render();
  });

  document.getElementById("search-box").addEventListener("input", e => {
    state.query = e.target.value.trim().toLowerCase();
    render();
  });
}

/* ---------- boot ---------- */

loadData().then(() => {
  buildLayerChips();
  wireControls();
  render();
}).catch(err => {
  document.getElementById("screen-root").innerHTML =
    '<div class="empty-state">Could not load the digest data (' + err.message +
    "). If you opened index.html directly from disk, serve it instead: <code>python3 -m http.server</code></div>";
});
