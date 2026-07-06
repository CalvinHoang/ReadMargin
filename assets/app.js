/* AI Australia Radar — front-end. No dependencies. */

const STATES = ["National", "NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"];

const SCREEN_INTROS = {
  current: "What is happening right now in Australian AI — the live feed across investment, procurement, infrastructure and policy.",
  markets: "The serious end of the market: bids, tenders, purchase orders, government procurement, capital raises, investments and M&A.",
  buildouts: "Who is building what, where — AI and data-centre infrastructure state by state, from operational campuses to the announced pipeline.",
  papers: "White papers, roadmaps and reports that are still worth reading — the long-term context behind the daily feed."
};

const MARKET_CATS = new Set(["markets", "bids", "investments"]);

const state = {
  screen: "current",
  geo: "all",
  horizon: "all",
  query: "",
  news: [],
  buildouts: [],
  papers: [],
  updated: null
};

/* ---------- data loading ---------- */

async function loadData() {
  const [news, builds, papers] = await Promise.all([
    fetch("data/news.json").then(r => r.json()),
    fetch("data/buildouts.json").then(r => r.json()),
    fetch("data/whitepapers.json").then(r => r.json())
  ]);
  state.news = (news.items || []).slice().sort((a, b) => (b.date || "").localeCompare(a.date || ""));
  state.buildouts = builds.projects || [];
  state.papers = (papers.papers || []).slice().sort((a, b) => b.year - a.year);
  state.updated = news.updated;
  const updatedEl = document.getElementById("last-updated");
  if (state.updated) {
    updatedEl.textContent = "Feed updated " + new Date(state.updated).toLocaleString("en-AU", {
      day: "numeric", month: "short", year: "numeric"
    });
  }
}

/* ---------- filtering ---------- */

function itemGeos(item) {
  if (Array.isArray(item.geography)) return item.geography;
  const geos = [item.state || "National"];
  if (Array.isArray(item.also_states)) geos.push(...item.also_states);
  return geos;
}

function paperHorizon(paper) {
  return paper.year >= 2025 ? "now" : "past";
}

function matchesFilters(item, { horizon }) {
  if (state.geo !== "all" && !itemGeos(item).includes(state.geo)) return false;
  if (state.horizon !== "all" && horizon !== state.horizon) return false;
  if (state.query) {
    const hay = [item.title, item.summary, item.notes, item.why_relevant, item.source,
      item.publisher, item.operator, item.location, ...(item.categories || []), ...(item.topics || [])]
      .filter(Boolean).join(" ").toLowerCase();
    if (!hay.includes(state.query)) return false;
  }
  return true;
}

function visibleItems() {
  switch (state.screen) {
    case "current":
      return state.news.filter(n => matchesFilters(n, { horizon: n.horizon }));
    case "markets":
      return state.news
        .filter(n => (n.categories || []).some(c => MARKET_CATS.has(c)))
        .filter(n => matchesFilters(n, { horizon: n.horizon }));
    case "buildouts":
      return state.buildouts.filter(p => matchesFilters(p, { horizon: p.horizon }));
    case "papers":
      return state.papers.filter(p => matchesFilters(p, { horizon: paperHorizon(p) }));
  }
  return [];
}

/* ---------- rendering ---------- */

function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text != null) node.textContent = text;
  return node;
}

function badge(text, cls) {
  return el("span", "badge" + (cls ? " " + cls : ""), text);
}

function horizonBadge(h) {
  if (h === "past") return badge("◂ past", "h-past");
  if (h === "future") return badge("future ▸", "h-future");
  return badge("● now", "h-now");
}

function fmtDate(iso) {
  if (!iso) return "";
  return new Date(iso + "T00:00:00").toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric" });
}

function newsCard(item) {
  const card = el("article", "card");
  const badges = el("div", "badges");
  badges.append(horizonBadge(item.horizon));
  itemGeos(item).forEach(g => badges.append(badge(g, "geo")));
  (item.categories || []).forEach(c => badges.append(badge(c)));
  card.append(badges);

  const h3 = el("h3");
  const a = el("a", null, item.title);
  a.href = item.url; a.target = "_blank"; a.rel = "noopener";
  h3.append(a);
  card.append(h3);

  card.append(el("p", "summary", item.summary || ""));

  const byline = el("p", "byline");
  byline.innerHTML = `<strong>${item.source || ""}</strong> · ${fmtDate(item.date)}`;
  card.append(byline);
  return card;
}

function buildoutCard(p) {
  const card = el("article", "card");
  const badges = el("div", "badges");
  badges.append(badge(p.status, "status-" + p.status));
  badges.append(horizonBadge(p.horizon));
  if (p.capacity_mw) badges.append(el("span", "mw", p.capacity_mw.toLocaleString() + " MW"));
  card.append(badges);

  const h3 = el("h3");
  const a = el("a", null, p.name);
  a.href = p.url; a.target = "_blank"; a.rel = "noopener";
  h3.append(a);
  card.append(h3);

  const byline = el("p", "byline");
  byline.innerHTML = `<strong>${p.operator}</strong> · ${p.location}`;
  card.append(byline);
  if (p.notes) card.append(el("p", "summary", p.notes));
  return card;
}

function paperCard(p) {
  const card = el("article", "card");
  const badges = el("div", "badges");
  badges.append(badge(String(p.year)));
  badges.append(horizonBadge(paperHorizon(p)));
  (p.geography || []).forEach(g => badges.append(badge(g, "geo")));
  (p.topics || []).forEach(t => badges.append(badge(t)));
  card.append(badges);

  const h3 = el("h3");
  const a = el("a", null, p.title);
  a.href = p.url; a.target = "_blank"; a.rel = "noopener";
  h3.append(a);
  card.append(h3);

  const byline = el("p", "byline");
  byline.innerHTML = `<strong>${p.publisher}</strong>`;
  card.append(byline);
  if (p.why_relevant) card.append(el("p", "why", "Still relevant because: " + p.why_relevant));
  return card;
}

function render() {
  const root = document.getElementById("screen-root");
  root.innerHTML = "";
  root.append(el("p", "screen-intro", SCREEN_INTROS[state.screen]));

  const items = visibleItems();
  if (!items.length) {
    root.append(el("div", "empty-state", "Nothing on the radar for this slice — widen the filters."));
    updateGeoChipCounts();
    return;
  }

  if (state.screen === "buildouts") {
    // Group by state, in fixed order, with MW subtotals.
    const order = state.geo === "all" ? STATES : [state.geo];
    for (const st of order) {
      const projects = items.filter(p => itemGeos(p)[0] === st || (state.geo !== "all" && itemGeos(p).includes(st)));
      if (!projects.length) continue;
      const section = el("section", "state-section");
      const header = el("div", "state-header");
      header.append(el("h2", null, st));
      const mw = projects.reduce((sum, p) => sum + (p.capacity_mw || 0), 0);
      header.append(el("span", "sub",
        projects.length + (projects.length === 1 ? " project" : " projects") + (mw ? " · " + mw.toLocaleString() + "+ MW tracked" : "")));
      section.append(header);
      const list = el("div", "card-list two-col");
      projects.forEach(p => list.append(buildoutCard(p)));
      section.append(list);
      root.append(section);
    }
  } else {
    const list = el("div", "card-list" + (state.screen === "papers" ? " two-col" : ""));
    const maker = state.screen === "papers" ? paperCard : newsCard;
    items.forEach(i => list.append(maker(i)));
    root.append(list);
  }
  updateGeoChipCounts();
}

/* ---------- controls ---------- */

function countForGeo(geo) {
  const saved = state.geo;
  state.geo = geo;
  const n = visibleItems().length;
  state.geo = saved;
  return n;
}

function buildGeoChips() {
  const wrap = document.getElementById("geo-chips");
  wrap.innerHTML = "";
  const all = el("button", "chip active", "All Australia");
  all.dataset.geo = "all";
  wrap.append(all);
  STATES.forEach(s => {
    const chip = el("button", "chip");
    chip.dataset.geo = s;
    chip.append(document.createTextNode(s));
    chip.append(el("span", "count"));
    wrap.append(chip);
  });
  wrap.addEventListener("click", e => {
    const chip = e.target.closest(".chip");
    if (!chip) return;
    state.geo = chip.dataset.geo;
    wrap.querySelectorAll(".chip").forEach(c => c.classList.toggle("active", c === chip));
    render();
  });
}

function updateGeoChipCounts() {
  document.querySelectorAll("#geo-chips .chip").forEach(chip => {
    const span = chip.querySelector(".count");
    if (span) span.textContent = countForGeo(chip.dataset.geo);
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

  document.getElementById("horizon-lens").addEventListener("click", e => {
    const chip = e.target.closest(".lens-chip");
    if (!chip) return;
    state.horizon = chip.dataset.horizon;
    document.querySelectorAll(".lens-chip").forEach(c => c.classList.toggle("active", c === chip));
    render();
  });

  document.getElementById("search-box").addEventListener("input", e => {
    state.query = e.target.value.trim().toLowerCase();
    render();
  });
}

/* ---------- boot ---------- */

loadData().then(() => {
  buildGeoChips();
  wireControls();
  render();
}).catch(err => {
  document.getElementById("screen-root").innerHTML =
    '<div class="empty-state">Could not load the radar data (' + err.message +
    "). If you opened index.html directly from disk, serve it instead: <code>python3 -m http.server</code></div>";
});
