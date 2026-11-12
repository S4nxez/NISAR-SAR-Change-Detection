// River Lifeline: page state, user interface events and boot (the only module that touches the whole page). Its data
// comes from the backend's API (services/monitorApi.js).

import { areaFromSearch, PLAY_STEP_MS, REFRESH_MS } from "./config.js";
import { createMapView } from "./components/mapView.js";
import * as panels from "./components/panels.js";
import { markSelectedStrip, renderPassLog } from "./components/passLog.js";
import { buildRecord, communityRows, nextPasses, passForDay, previousEvaluated, statusOf, stepPass,
  visibleRows } from "./models/record.js";
import { download, exportName, toCsv, toGeojson } from "./services/exporters.js";
import { fetchCatalog, layerUrl } from "./services/monitorApi.js";
import { isIsoDay, todayIso } from "./utils/dates.js";

const AREA = areaFromSearch(location.search);
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
const $ = sel => document.querySelector(sel);

const state = { record: null, pass: null, prev: null, selected: null, day: null, filter: "all", query: "",
  base: "radar", playing: null, drawn: false };
let mapView;

const passUrl = (p, file) => layerUrl(AREA, p, file);
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
  mapView.updateMarkers(record.cat.communities, c => ({ status: statusOf(record, pass, c), selected: c.id === selected,
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
const loadCatalog = () => fetchCatalog(AREA);

// What the page says when there is no record to show, by CatalogError reason
const NOTICES = {
  missing: ["The pass record has not been built.",
    "The monitor worker has not published this area yet. Run <code>river-monitor communities</code> and " +
    "<code>river-monitor update</code> (see docs/river-monitor.md), then reload this page."],
  unsupported: ["The pass record cannot be read by this version.",
    "The record was written by another version of the monitor worker: deploy matching versions of the backend and " +
    "the worker, then reload this page."],
  unavailable: ["The pass record could not be loaded.",
    "The server did not answer. Reload this page in a few minutes."],
};

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

// The worker (river-monitor watch) keeps adding passes; pick them up without a reload.
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
  } catch (e) {
    showNotice(...(NOTICES[e.reason] || NOTICES.unavailable));
    return;
  }
  if (!cat.passes?.some(p => p.shown !== false)) {
    showNotice("No NISAR pass over the area yet.",
      "The record has no pass to show yet: the monitor worker adds the next pass once NASA publishes it.");
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
