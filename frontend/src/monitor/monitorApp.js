// River Lifeline: page state, user interface events and boot. Reads the static files written by processing/lifeline:
//   public/data/monitor/<area>/catalog.json              area, communities, river gauge, one entry per pass
//   public/data/monitor/<area>/passes/<id>/radar.webp    HH backscatter preview
//   public/data/monitor/<area>/passes/<id>/water.png     water mask (narrow channels in amber)
//   public/data/monitor/<area>/passes/<id>/change.png    water lost / gained since the previous pass of the same track

import { areaFromSearch, dataUrl, PLAY_STEP_MS, REFRESH_MS } from "./config.js";
import { isIsoDay, todayIso } from "./dates.js";
import { download, exportName, toCsv, toGeojson } from "./exporters.js";
import { createMapView } from "./mapView.js";
import * as panels from "./panels.js";
import { markSelectedStrip, renderPassLog } from "./passLog.js";
import { buildRecord, communityRows, nextPasses, passForDay, previousEvaluated, statusOf, stepPass,
  visibleRows } from "./record.js";

const AREA = areaFromSearch(location.search);
const DATA = dataUrl(AREA);
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
const $ = sel => document.querySelector(sel);

const state = { record: null, pass: null, prev: null, selected: null, day: null, filter: "all", query: "",
  base: "radar", playing: null, drawn: false };
let mapView;

const passUrl = (p, file) => (file ? `${DATA}passes/${p.id}/${file}` : null);
const findCommunity = id => state.record.cat.communities.find(c => c.id === id);
const latestEvaluated = () => state.record.evaluated[state.record.evaluated.length - 1];

// ---------------------------------------------------------------- rendering
function refreshLayers() {
  const p = state.pass;
  const water = $("#toggle-water").checked, change = $("#toggle-change").checked;
  mapView.showLayers({ radar: passUrl(p, p.files.radar), water: passUrl(p, p.files.water), change: passUrl(p, p.files.change) },
    { radar: state.base === "radar", water, change, other: $("#toggle-other").checked, opacity: Number($("#opacity").value) / 100 });
  $("#map-key").innerHTML = panels.mapKey(state.record, { water, change });
}

function refreshMarkers() {
  const { record, pass, selected } = state;
  mapView.updateMarkers(record.cat.communities, c => ({ status: statusOf(pass, c), selected: c.id === selected,
    tooltip: panels.markerTooltip(record, pass, c) }));
}

function renderHeadline() {
  const h = panels.headline(state.record, state.pass, state.day);
  $("#headline-meta").textContent = h.meta;
  $("#headline-text").innerHTML = h.title;
  $("#headline-sub").textContent = h.sub;
}

function renderRoster() {
  const all = communityRows(state.record, state.pass, state.prev);
  const list = visibleRows(all, { query: state.query, filter: state.filter });
  $("#community-list").innerHTML = list.length
    ? list.map(row => `<li>${panels.rosterItem(state.record, state.pass, row, state.selected)}</li>`).join("")
    : panels.rosterEmpty(state.pass);
  $("#roster-count").textContent = `${list.length} of ${all.length}`;
}

function renderDossier() {
  const c = findCommunity(state.selected);
  if (!c) return;
  $("#dossier-title").textContent = "Community";
  $("#dossier").innerHTML = panels.dossier(state.record, state.pass, c);
}

function renderPassLogNow() {
  const today = todayIso();
  const ghosts = nextPasses(state.record, today);
  // one-off "downlink" reveal on first draw; skipped when motion is reduced or the page is hidden
  // (hidden pages pause animations, which would leave the strips invisible)
  const animate = !state.drawn && !reducedMotion && document.visibilityState === "visible";
  renderPassLog($("#swath"), { record: state.record, current: state.pass, today, ghosts, animate,
    onSelect: id => selectPass(id, true) });
  state.drawn = true;
  $("#next-pass-note").innerHTML = panels.nextPassNote(ghosts[0], today);
}

// ---------------------------------------------------------------- selection
function selectPass(id, fromUser) {
  const p = state.record.passes.find(q => q.id === id);
  if (!p) return;
  state.pass = p;
  state.prev = p.evaluated ? previousEvaluated(state.record, p) : null;
  if (fromUser) { state.day = p.date; $("#date-input").value = p.date; }
  refreshLayers();
  refreshMarkers();
  renderHeadline();
  $("#plate").innerHTML = panels.plate(state.record, p);
  renderRoster();
  $("#ledger").innerHTML = panels.ledger(state.record, p, state.prev);
  renderDossier();
  markSelectedStrip($("#swath"), p);
  writeHash();
}

function selectCommunity(id, fly) {
  state.selected = id;
  const c = findCommunity(id);
  if (c && fly) mapView.flyTo(c, !reducedMotion);
  refreshMarkers();
  renderRoster();
  renderDossier();
  writeHash();
}

function writeHash() {
  const h = new URLSearchParams();
  if (state.day) h.set("d", state.day);
  if (state.selected) h.set("c", state.selected);
  history.replaceState(null, "", "#" + h.toString());
}

function step(dir) {
  const p = stepPass(state.record, state.pass, dir);
  if (p) selectPass(p.id, true);
}

function stopPlaying() {
  clearInterval(state.playing);
  state.playing = null;
  $("#play").setAttribute("aria-pressed", "false");
  $("#play").textContent = "Play record";
}

function togglePlay() {
  if (state.playing) return stopPlaying();
  const { evaluated } = state.record;
  if (!evaluated.length) return;
  if (state.pass === latestEvaluated()) selectPass(evaluated[0].id, true);
  $("#play").setAttribute("aria-pressed", "true");
  $("#play").textContent = "Pause";
  state.playing = setInterval(() => {
    if (state.pass === latestEvaluated()) return stopPlaying();
    step(1);
  }, PLAY_STEP_MS);
}

// ---------------------------------------------------------------- exports
function exportDay(format) {
  const rows = communityRows(state.record, state.pass, state.prev);
  const widths = state.record.cat.area.widths_m;
  if (format === "csv") download(exportName(AREA, state.pass, "csv"), toCsv(rows, state.pass, widths), "text/csv");
  else download(exportName(AREA, state.pass, "geojson"), toGeojson(rows, state.pass, widths), "application/geo+json");
}

// ---------------------------------------------------------------- boot
async function loadCatalog() {
  const res = await fetch(DATA + "catalog.json", { cache: "no-cache" });
  if (!res.ok) throw new Error("catalog.json not found");
  return res.json();
}

function applyCatalog(cat) {
  state.record = buildRecord(cat);
  $("#mast-mission").textContent = `NISAR L-band radar · ${cat.area.name}`;
  $("#gauge-name").textContent = cat.gauge?.name || "the town gauge";
  $("#foot-sources").textContent = `Radar: ${cat.sources.radar} · Places: ${cat.sources.places}` +
    (cat.gauge ? ` · River level: ${cat.gauge.source}` : "");
  $("#foot-search").textContent = cat.last_search ? `Last check for new passes: ${cat.last_search.replace("T", " ").replace("Z", " UTC")}` : "";
  const di = $("#date-input");
  di.min = state.record.passes[0].date;
  di.max = todayIso();
}

function bindUi() {
  $("#date-input").addEventListener("change", e => {
    if (!isIsoDay(e.target.value)) return;
    state.day = e.target.value;
    const p = passForDay(state.record, state.day);
    if (p) selectPass(p.id, false);
  });
  $("#prev-pass").addEventListener("click", () => step(-1));
  $("#next-pass").addEventListener("click", () => step(1));
  $("#play").addEventListener("click", togglePlay);
  document.querySelectorAll(".layers-base button").forEach(b => b.addEventListener("click", () => {
    state.base = b.dataset.base;
    document.querySelectorAll(".layers-base button").forEach(x => x.classList.toggle("is-on", x === b));
    refreshLayers();
  }));
  ["#toggle-water", "#toggle-change", "#toggle-other", "#opacity"].forEach(s => $(s).addEventListener("input", refreshLayers));
  $("#search").addEventListener("input", e => { state.query = e.target.value; renderRoster(); });
  document.querySelectorAll(".filter").forEach(b => b.addEventListener("click", () => {
    state.filter = b.dataset.filter;
    document.querySelectorAll(".filter").forEach(x => x.classList.toggle("is-on", x === b));
    renderRoster();
  }));
  $("#community-list").addEventListener("click", e => {
    const button = e.target.closest("button[data-id]");
    if (button) selectCommunity(button.dataset.id, true);
  });
  $("#export-csv").addEventListener("click", () => exportDay("csv"));
  $("#export-geojson").addEventListener("click", () => exportDay("geojson"));
  let t;
  addEventListener("resize", () => { clearTimeout(t); t = setTimeout(renderPassLogNow, 150); });
}

function showNotice(title, html) {
  $("#headline-meta").textContent = "No record yet";
  $("#headline-text").textContent = title;
  const n = document.createElement("div");
  n.className = "notice";
  n.innerHTML = html;
  document.querySelector(".map-frame").appendChild(n);
}

// The watcher (river_monitor.py watch) keeps adding passes; pick them up without a reload.
async function refreshCatalog() {
  try {
    const fresh = await loadCatalog();
    const { cat } = state.record;
    if (!fresh.passes?.length || (fresh.passes.length === cat.passes.length && fresh.last_search === cat.last_search)) return;
    const atLatest = state.pass === latestEvaluated();
    const keep = state.pass.id;
    applyCatalog(fresh);
    mapView.placeMarkers(fresh.communities);
    renderPassLogNow();
    const latest = latestEvaluated();
    selectPass(atLatest && latest ? latest.id : keep, atLatest);
  } catch { /* keep the current view if the refresh fails */ }
}

async function boot() {
  let cat;
  try {
    cat = await loadCatalog();
  } catch {
    showNotice("The pass record has not been built.",
      `Run <code>python processing/river_monitor.py communities</code> and <code>python processing/river_monitor.py update</code>, then reload this page.`);
    return;
  }
  if (!cat.passes?.some(p => p.shown !== false)) {
    showNotice("No NISAR pass over the area yet.",
      `The record has no pass to show. Run <code>python processing/river_monitor.py update</code> again after the next pass is published.`);
    return;
  }
  applyCatalog(cat);
  mapView = createMapView(window.L, { element: "map", cat, onCommunityClick: id => selectCommunity(id, false) });
  mapView.placeMarkers(cat.communities);
  bindUi();
  const h = new URLSearchParams(location.hash.slice(1));
  state.selected = h.get("c");
  const fromHash = h.get("d");
  state.day = isIsoDay(fromHash) ? fromHash : latestEvaluated()?.date || state.record.passes[state.record.passes.length - 1].date;
  $("#date-input").value = state.day;
  state.pass = passForDay(state.record, state.day);
  renderPassLogNow();
  selectPass(state.pass.id, false);
  setInterval(refreshCatalog, REFRESH_MS);
}

window.addEventListener("load", boot);
