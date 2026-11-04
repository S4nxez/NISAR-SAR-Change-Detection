// River lifeline monitor. Reads the static files written by processing/river_monitor.py:
//   public/data/monitor/<area>/catalog.json              area, communities and one entry per pass
//   public/data/monitor/<area>/passes/<id>/radar.webp    HH backscatter preview
//   public/data/monitor/<area>/passes/<id>/water.png     water mask (narrow channels in amber)
//   public/data/monitor/<area>/passes/<id>/change.png    water lost / gained since the previous pass of the same track

const AREA = new URLSearchParams(location.search).get("area") || "tefe";
const DATA = `./public/data/monitor/${AREA}/`;
const REFRESH_MS = 10 * 60 * 1000;
const CODE = { 0: "no_data", 1: "connected", 2: "at_risk", 3: "isolated" };
const LABEL = { connected: "Connected", at_risk: "At risk", isolated: "Isolated", no_data: "No data",
  inland: "Inland", unresolved: "Not resolved" };
const COLOR = { connected: "#68b6a3", at_risk: "#e4b65c", isolated: "#e47759", no_data: "#6d8491",
  inland: "#4b5d68", unresolved: "#6d8491" };
const SEVERITY = { isolated: 3, at_risk: 2, connected: 1, no_data: 0 };
const fmt = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 1 });
const dayFmt = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
const $ = sel => document.querySelector(sel);
const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

const state = { cat: null, passes: [], evaluated: [], pass: null, prev: null, selected: null, filter: "all",
  query: "", base: "radar", layers: {}, markers: {}, chart: null, playing: null, day: null };
let map, markerLayer, otherLayer;

// ---------------------------------------------------------------- helpers
const day = iso => new Date(iso + "T00:00:00Z");
const fmtDay = iso => dayFmt.format(day(iso));
const daysBetween = (a, b) => Math.round((day(b) - day(a)) / 86400000);
const passUrl = (p, f) => `${DATA}passes/${p.id}/${f}`;

// Isolation seen on a single pass is not confirmed yet (wind or rain can spoil one image):
// it is shown and counted as at risk until the next pass with data agrees.
const unconfirmed = (pass, c) => !!pass?.unconfirmed?.includes(c.id);

function statusOf(pass, c) {
  if (c.class && c.class !== "monitored") return c.class;
  const r = pass?.status?.[c.id];
  if (!r) return "no_data";
  return unconfirmed(pass, c) ? "at_risk" : CODE[r[0]];
}

function widthLabel(b) {
  if (b === null || b === undefined) return "no route";
  const w = state.cat.area.widths_m;
  if (b === 0) return `< ${w[0]} m`;
  const next = w[w.indexOf(b) + 1];
  return next ? `${b}–${next} m` : `≥ ${b} m`;
}

function previousEvaluated(pass) {
  const i = state.evaluated.indexOf(pass);
  return i > 0 ? state.evaluated[i - 1] : null;
}

function passForDay(iso) {
  const ev = state.evaluated.filter(p => p.date <= iso);
  return ev.length ? ev[ev.length - 1] : state.evaluated[0] || state.passes[state.passes.length - 1];
}

// ---------------------------------------------------------------- map
function initMap() {
  map = L.map("map", { zoomControl: true, scrollWheelZoom: true, preferCanvas: true });
  // OpenStreetMap standard tiles need no API key (CARTO's now do); monitor.css darkens them.
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors · NISAR: NASA/ISRO, ASF DAAC", maxZoom: 18, className: "basemap-dark"
  }).addTo(map);
  map.createPane("radar").style.zIndex = 330;
  map.createPane("water").style.zIndex = 340;
  map.createPane("change").style.zIndex = 350;
  otherLayer = L.layerGroup();
  markerLayer = L.layerGroup().addTo(map);
  map.fitBounds(state.cat.grid.bounds);

  const { hub, river } = state.cat.area;
  const hubAt = hub.access || hub;
  L.marker([hubAt.lat, hubAt.lon], { icon: L.divIcon({ className: "", html: '<div class="hub-icon"></div>', iconSize: [16, 16] }), zIndexOffset: 1000 })
    .bindTooltip(`<strong>${esc(hub.name)}</strong> · hub town`, { className: "community-tip" }).addTo(map);
  L.circleMarker([river.lat, river.lon], { radius: 5, color: "#fff", weight: 2, fillColor: "#72b8d0", fillOpacity: 1 })
    .bindTooltip(esc(river.name), { className: "community-tip" }).addTo(map);

  placeMarkers();
}

// Monitored communities on the main layer, the rest on the optional one. Classes come from the
// whole record, so they can change when new passes arrive.
function placeMarkers() {
  markerLayer.clearLayers();
  otherLayer.clearLayers();
  for (const c of state.cat.communities) {
    let m = state.markers[c.id];
    if (!m) {
      m = L.circleMarker([c.lat, c.lon], { radius: 6, weight: 1.5, color: "#101b25", fillOpacity: 0.95 })
        .bindTooltip("", { className: "community-tip" })
        .on("click", () => selectCommunity(c.id, false));
      state.markers[c.id] = m;
    }
    (c.class === "monitored" ? markerLayer : otherLayer).addLayer(m);
  }
}

function setOverlay(key, url, pane, opacity, on) {
  const bounds = state.cat.grid.bounds;
  if (state.layers[key]) { state.layers[key].remove(); state.layers[key] = null; }
  if (on && url) state.layers[key] = L.imageOverlay(url, bounds, { pane, opacity, interactive: false }).addTo(map);
}

function refreshLayers() {
  const p = state.pass;
  const op = Number($("#opacity").value) / 100;
  setOverlay("radar", passUrl(p, p.files.radar), "radar", 1, state.base === "radar");
  setOverlay("water", passUrl(p, p.files.water), "water", op, $("#toggle-water").checked);
  setOverlay("change", p.files.change && passUrl(p, p.files.change), "change", 1, $("#toggle-change").checked);
  if ($("#toggle-other").checked) otherLayer.addTo(map); else otherLayer.remove();
  const key = [`<span><i class="key-swatch" style="background:#3d8bff"></i>Water, channel ≥ ${state.cat.area.safe_width_m} m</span>`,
    `<span><i class="key-swatch" style="background:#ffb020"></i>Narrower channel</span>`];
  if ($("#toggle-change").checked) key.push('<span><i class="key-swatch" style="background:#e47759"></i>Water lost</span>',
    '<span><i class="key-swatch" style="background:#68d6e6"></i>Water gained</span>');
  key.push(...["connected", "at_risk", "isolated"].map(s => `<span><i class="key-swatch round" style="background:${COLOR[s]}"></i>${LABEL[s]}</span>`));
  $("#map-key").innerHTML = key.join("");
}

function refreshMarkers() {
  for (const c of state.cat.communities) {
    const s = statusOf(state.pass, c);
    const m = state.markers[c.id];
    const r = state.pass.status?.[c.id];
    m.setStyle({ fillColor: COLOR[s], radius: c.id === state.selected ? 9 : c.class === "monitored" ? 6 : 4,
      color: c.id === state.selected ? "#fff" : "#101b25" });
    m.setTooltipContent(`<strong>${esc(c.name)}</strong> · ${LABEL[s]}` +
      (c.class === "monitored" && r && r[0] ? `<br>route: ${widthLabel(r[1])} · water ${fmt.format(r[2])} m away` : ""));
  }
}

// ---------------------------------------------------------------- timeline
function renderTimeline() {
  const el = $("#timeline");
  const ps = state.passes;
  if (!ps.length) return;
  const t0 = day(ps[0].date).getTime(), t1 = Math.max(day(ps[ps.length - 1].date).getTime(), t0 + 86400000);
  const x = iso => 1 + 98 * (day(iso).getTime() - t0) / (t1 - t0);
  const parts = ['<div class="tl-axis"></div>'];
  const m = new Date(t0); m.setUTCDate(1);
  while (m.getTime() <= t1) {
    if (m.getTime() >= t0) parts.push(`<span class="tl-month" style="left:${x(m.toISOString().slice(0, 10))}%">${m.toLocaleString("en-GB", { month: "short", timeZone: "UTC" })} ${String(m.getUTCFullYear()).slice(2)}</span>`);
    m.setUTCMonth(m.getUTCMonth() + 1);
  }
  const worst = Math.max(1, ...state.evaluated.map(p => p.counts.isolated));
  for (const p of ps) {
    const ev = p.evaluated && p.counts;
    let color = "";
    if (ev) {
      const t = p.counts.isolated / worst;
      color = p.counts.isolated === 0 ? COLOR.connected : t < 0.67 ? COLOR.at_risk : COLOR.isolated;
    }
    parts.push(`<button type="button" role="option" class="tl-pass ${ev ? "ev" : "partial"} ${p === state.pass ? "is-selected" : ""}"
      style="left:${x(p.date)}%;${ev ? `background:${color}` : ""}" data-id="${p.id}"
      aria-label="${fmtDay(p.date)}, track ${p.track} ${p.direction}${ev ? "" : ", partial coverage"}"
      title="${fmtDay(p.date)} · track ${p.track} ${p.direction}${ev ? ` · isolated ${p.counts.isolated}` : " · partial coverage"}"></button>`);
  }
  el.innerHTML = parts.join("");
  el.querySelectorAll(".tl-pass").forEach(b => b.addEventListener("click", () => selectPass(b.dataset.id, true)));
  $("#pass-count").textContent = `${state.evaluated.length} evaluated / ${ps.length} passes`;
}

// ---------------------------------------------------------------- stats, list, detail
function renderStats() {
  const p = state.pass, prev = state.prev;
  const total = state.cat.communities.filter(c => c.class === "monitored").length;
  for (const s of ["connected", "at_risk", "isolated"]) {
    const n = p.counts ? p.counts[s] : null;
    $(`#stat-${s}`).innerHTML = n === null ? "—" : `${n}<small>/ ${total}</small>`;
    const d = p.counts && prev?.counts ? n - prev.counts[s] : null;
    const base = { connected: `water route ≥ ${state.cat.area.safe_width_m} m wide`, at_risk: `route narrower than ${state.cat.area.safe_width_m} m`, isolated: "no water route to the hub" }[s];
    $(`#stat-${s}-foot`).innerHTML = d ? `<b>${d > 0 ? "+" : ""}${d}</b> since ${fmtDay(prev.date)}` : base;
  }
  const { hub, river } = state.cat.area;
  $("#link-label").textContent = `${hub.name.toUpperCase()} ↔ MAIN RIVER`;
  const link = p.hub_link;
  const ls = link ? CODE[link[0]] : "no_data";
  $("#stat-link").innerHTML = link ? `<span style="color:${COLOR[ls]}">${widthLabel(link[1])}</span>` : "—";
  $("#stat-link-foot").textContent = link ? `${LABEL[ls]} · narrowest point to the ${river.name}` : "not evaluated on this pass";
}

function rows() {
  const p = state.pass, prev = state.prev;
  return state.cat.communities.filter(c => c.class === "monitored").map(c => {
    const s = statusOf(p, c), was = prev ? statusOf(prev, c) : null;
    return { c, s, r: p.status?.[c.id], was: was && was !== s && s !== "no_data" && was !== "no_data" ? was : null };
  });
}

function renderList() {
  const q = state.query.trim().toLowerCase();
  let list = rows().filter(x => (!q || x.c.name.toLowerCase().includes(q)) &&
    (state.filter === "all" || (state.filter === "changed" ? x.was : x.s === state.filter)));
  list.sort((a, b) => SEVERITY[b.s] - SEVERITY[a.s] || (a.r?.[1] ?? -1) - (b.r?.[1] ?? -1) || a.c.name.localeCompare(b.c.name));
  const el = $("#community-list");
  el.innerHTML = list.length ? "" : '<p class="section-copy">No community matches.</p>';
  for (const { c, s, r, was } of list) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = `site-item ${state.selected === c.id ? "is-selected" : ""}`;
    b.dataset.id = c.id;
    b.innerHTML = `<span class="status-dot-s st-${s}"></span>
      <span class="site-main"><strong>${esc(c.name)}</strong><small>${esc(c.place)}${c.population ? " · " + c.population.toLocaleString("en-GB") + " people" : ""}</small></span>
      <span class="site-change"><b>${r && r[0] ? widthLabel(r[1]) : "—"}</b>${unconfirmed(state.pass, c) ? '<span class="was">route lost, to confirm</span>' :
        was ? `<span class="was">was ${LABEL[was].toLowerCase()}</span>` : ""}</span>`;
    b.addEventListener("click", () => selectCommunity(c.id, true));
    el.appendChild(b);
  }
  const cls = state.cat.community_classes || {};
  $("#community-count").textContent = `${list.length} shown`;
  $("#community-count").title = `${cls.monitored || 0} monitored · ${cls.unresolved || 0} not resolved · ${cls.inland || 0} inland`;
}

function renderDetail() {
  const c = state.cat.communities.find(x => x.id === state.selected);
  if (!c) return;
  const p = state.pass, s = statusOf(p, c), r = p.status?.[c.id];
  $("#detail-title").textContent = c.name;
  if (c.class !== "monitored") {
    $("#detail").innerHTML = `<p class="section-copy"><span class="badge" style="background:${COLOR[c.class]};color:#edf4f7">${LABEL[c.class]}</span></p>
      <p class="section-copy">${c.class === "inland" ? "No water within " + state.cat.area.access_radius_m + " m on any pass: this place does not depend on the river, so it is not monitored." :
        "There is water nearby, but no pass shows a water route to the hub that the radar can resolve at 20 m (very narrow streams). Its status would be a guess, so it is left out of the counts."}</p>`;
    return;
  }
  const hist = state.evaluated.map(q => ({ q, s: statusOf(q, c), r: q.status?.[c.id] }));
  const levels = [null, 0, ...state.cat.area.widths_m];
  const bars = hist.map(({ q, s, r }) => {
    const h = r && r[0] ? 12 + 88 * Math.max(0, levels.indexOf(r[1])) / (levels.length - 1) : 8;
    return `<i class="${q === p ? "is-current" : ""}" style="height:${h}%;background:${COLOR[s]}" title="${fmtDay(q.date)} · ${LABEL[s]} · ${r && r[0] ? widthLabel(r[1]) : "—"}"></i>`;
  }).join("");
  const lastOk = [...hist].reverse().find(h => h.q.date <= p.date && (h.s === "connected" || h.s === "at_risk"));
  $("#detail").innerHTML = `
    <p class="section-copy"><span class="badge" style="background:${COLOR[s]}">${LABEL[s].toUpperCase()}</span> on ${fmtDay(p.date)}${unconfirmed(p, c) ?
      " · no water route on this pass; isolation is confirmed if the next pass agrees" : ""}</p>
    <div class="detail-facts">
      <div><span>NARROWEST POINT OF THE ROUTE</span><strong>${r && r[0] ? widthLabel(r[1]) : "—"}</strong></div>
      <div><span>NEAREST WATER</span><strong>${r && r[0] ? fmt.format(r[2]) + " m" : "—"}</strong></div>
      <div><span>TYPE</span><strong>${esc(c.place)}</strong></div>
      <div><span>MEASURED FROM</span><strong>${c.access ? esc(c.access_source) : "the place itself"}</strong></div>
      <div><span>LAST LINKED TO ${esc(state.cat.area.hub.name.toUpperCase())}</span><strong>${lastOk ? fmtDay(lastOk.q.date) : "—"}</strong></div>
    </div>
    <span class="stat-label">ROUTE WIDTH ON EVERY EVALUATED PASS</span>
    <div class="history">${bars}</div>
    <div class="history-axis"><span>${hist.length ? fmtDay(hist[0].q.date) : ""}</span><span>${hist.length ? fmtDay(hist[hist.length - 1].q.date) : ""}</span></div>`;
}

function renderNote() {
  const p = state.pass;
  const bits = [`<strong>${fmtDay(p.date)}</strong> · NISAR track ${p.track} ${p.direction} · ${p.time_utc} UTC`];
  if (state.day && state.day !== p.date) bits.push(`latest observation before ${fmtDay(state.day)} (${daysBetween(p.date, state.day)} days earlier)`);
  if (!p.evaluated) bits.push(`only ${Math.round(p.coverage * 100)} % of the area is covered: water image only, communities not evaluated`);
  if (p.beta) bits.push("beta product");
  const note = $("#pass-note");
  note.innerHTML = bits.join(" · ");
  note.hidden = false;
  $("#date-help").textContent = `${state.passes.length} passes from ${fmtDay(state.passes[0].date)} to ${fmtDay(state.passes[state.passes.length - 1].date)}`;
  $("#map-title").textContent = `River map · ${fmtDay(p.date)}`;
  const ch = p.change ? ` · since ${fmtDay(state.passes.find(q => q.id === p.change.since)?.date || p.date)}: −${fmt.format(p.change.lost_km2)} / +${fmt.format(p.change.gained_km2)} km² water` : "";
  $("#map-foot").textContent = `Water ${fmt.format(p.water_km2)} km² · narrow channels ${fmt.format(p.narrow_km2)} km²${ch}`;
}

// ---------------------------------------------------------------- chart
function renderChart() {
  const ev = state.evaluated;
  const data = {
    labels: ev.map(p => fmtDay(p.date)),
    datasets: [
      ...["isolated", "at_risk", "connected"].map(s => ({ type: "bar", label: LABEL[s], data: ev.map(p => p.counts[s]),
        backgroundColor: COLOR[s], stack: "c", yAxisID: "y", borderRadius: 3 })),
      { type: "line", label: "Water (km²)", data: ev.map(p => p.water_km2), borderColor: "#72b8d0", backgroundColor: "#72b8d0",
        yAxisID: "y2", tension: 0.25, pointRadius: 2 }
    ]
  };
  const opts = {
    responsive: true, maintainAspectRatio: false, animation: false,
    plugins: { legend: { labels: { color: "#93a7b3", boxWidth: 10, font: { size: 11 } } } },
    scales: {
      x: { stacked: true, ticks: { color: "#6d8491", maxRotation: 0, autoSkipPadding: 12, font: { size: 10 } }, grid: { display: false } },
      y: { stacked: true, ticks: { color: "#6d8491", font: { size: 10 } }, grid: { color: "#2a3c48" }, title: { display: true, text: "communities", color: "#6d8491" } },
      y2: { position: "right", ticks: { color: "#72b8d0", font: { size: 10 } }, grid: { display: false }, title: { display: true, text: "water km²", color: "#72b8d0" } }
    },
    onClick: (_, els) => { if (els.length) selectPass(ev[els[0].index].id, true); }
  };
  if (state.chart) state.chart.destroy();
  if (window.Chart) state.chart = new Chart($("#trend-chart"), { data, options: opts });
}

// ---------------------------------------------------------------- selection
function selectPass(id, fromUser) {
  const p = state.passes.find(q => q.id === id);
  if (!p) return;
  state.pass = p;
  state.prev = p.evaluated ? previousEvaluated(p) : null;
  if (fromUser) { state.day = p.date; $("#date-input").value = p.date; }
  refreshLayers();
  refreshMarkers();
  renderStats();
  renderNote();
  renderList();
  renderDetail();
  document.querySelectorAll(".tl-pass").forEach(b => b.classList.toggle("is-selected", b.dataset.id === id));
  writeHash();
}

function selectCommunity(id, fly) {
  state.selected = id;
  const c = state.cat.communities.find(x => x.id === id);
  if (c && fly) map.flyTo([c.lat, c.lon], Math.max(map.getZoom(), 12), { duration: 0.6 });
  refreshMarkers();
  renderList();
  renderDetail();
  writeHash();
}

function writeHash() {
  const h = new URLSearchParams();
  if (state.day) h.set("d", state.day);
  if (state.selected) h.set("c", state.selected);
  history.replaceState(null, "", "#" + h.toString());
}

function step(dir) {
  const ev = state.evaluated;
  const i = ev.indexOf(state.pass);
  const j = i < 0 ? ev.length - 1 : Math.min(ev.length - 1, Math.max(0, i + dir));
  if (ev[j]) selectPass(ev[j].id, true);
}

function togglePlay() {
  const btn = $("#play");
  if (state.playing) { clearInterval(state.playing); state.playing = null; btn.classList.remove("is-on"); btn.textContent = "▶"; return; }
  if (state.evaluated.indexOf(state.pass) === state.evaluated.length - 1) selectPass(state.evaluated[0].id, true);
  btn.classList.add("is-on"); btn.textContent = "❚❚";
  state.playing = setInterval(() => {
    if (state.evaluated.indexOf(state.pass) >= state.evaluated.length - 1) return togglePlay();
    step(1);
  }, 1300);
}

// ---------------------------------------------------------------- exports
function download(name, text, type) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], { type }));
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

function exportCsv() {
  const head = ["community", "place", "lat", "lon", "status", "route_narrowest_m", "nearest_water_m", "pass_date", "track"];
  const lines = [head.join(",")];
  for (const { c, s, r } of rows()) {
    lines.push([`"${c.name.replace(/"/g, '""')}"`, c.place, c.lat, c.lon, s, r && r[0] ? widthLabel(r[1]) : "", r && r[0] ? r[2] : "",
      state.pass.date, state.pass.track].join(","));
  }
  download(`communities_${AREA}_${state.pass.date}.csv`, lines.join("\n"), "text/csv");
}

function exportGeojson() {
  const features = rows().map(({ c, s, r }) => ({ type: "Feature", geometry: { type: "Point", coordinates: [c.lon, c.lat] },
    properties: { name: c.name, place: c.place, status: s, route_narrowest: r && r[0] ? widthLabel(r[1]) : null,
      nearest_water_m: r && r[0] ? r[2] : null, pass_date: state.pass.date, track: state.pass.track } }));
  download(`communities_${AREA}_${state.pass.date}.geojson`, JSON.stringify({ type: "FeatureCollection", features }, null, 1), "application/geo+json");
}

// ---------------------------------------------------------------- boot
async function loadCatalog() {
  const res = await fetch(DATA + "catalog.json", { cache: "no-cache" });
  if (!res.ok) throw new Error("catalog.json not found");
  return res.json();
}

function applyCatalog(cat) {
  state.cat = cat;
  state.passes = cat.passes.filter(p => p.shown !== false);
  state.evaluated = cat.passes.filter(p => p.evaluated && p.counts);
  $("#area-eyebrow").textContent = `${cat.area.name.toUpperCase()} · ${cat.area.country.toUpperCase()}`;
  $("#footer-sources").textContent = `Radar: ${cat.sources.radar} · Places: ${cat.sources.places} · last search for new passes ${cat.last_search ? cat.last_search.replace("T", " ").replace("Z", " UTC") : "—"} · prototype, not an official alert system`;
  const di = $("#date-input");
  di.min = cat.passes[0].date;
  di.max = new Date().toISOString().slice(0, 10);
}

function bindUi() {
  $("#date-input").addEventListener("change", e => {
    if (!e.target.value) return;
    state.day = e.target.value;
    const p = passForDay(state.day);
    if (p) selectPass(p.id, false);
  });
  $("#prev-pass").addEventListener("click", () => step(-1));
  $("#next-pass").addEventListener("click", () => step(1));
  $("#play").addEventListener("click", togglePlay);
  document.querySelectorAll(".seg button").forEach(b => b.addEventListener("click", () => {
    state.base = b.dataset.base;
    document.querySelectorAll(".seg button").forEach(x => x.classList.toggle("is-on", x === b));
    refreshLayers();
  }));
  ["#toggle-water", "#toggle-change", "#toggle-other", "#opacity"].forEach(s => $(s).addEventListener("input", refreshLayers));
  $("#search").addEventListener("input", e => { state.query = e.target.value; renderList(); });
  document.querySelectorAll(".chip").forEach(b => b.addEventListener("click", () => {
    state.filter = b.dataset.filter;
    document.querySelectorAll(".chip").forEach(x => x.classList.toggle("is-on", x === b));
    renderList();
  }));
  $("#export-csv").addEventListener("click", exportCsv);
  $("#export-geojson").addEventListener("click", exportGeojson);
}

async function boot() {
  let cat;
  try {
    cat = await loadCatalog();
  } catch {
    const note = $("#pass-note");
    note.innerHTML = `<strong>NO DATA YET</strong> Run <code>python processing/river_monitor.py communities</code> and <code>python processing/river_monitor.py update</code> to build public/data/monitor/${esc(AREA)}/catalog.json.`;
    note.hidden = false;
    return;
  }
  if (!cat.passes?.length) return;
  applyCatalog(cat);
  initMap();
  bindUi();
  renderTimeline();
  renderChart();
  const h = new URLSearchParams(location.hash.slice(1));
  state.selected = h.get("c");
  state.day = h.get("d") || state.evaluated[state.evaluated.length - 1]?.date || cat.passes[cat.passes.length - 1].date;
  $("#date-input").value = state.day;
  selectPass(passForDay(state.day).id, false);

  // The watcher (river_monitor.py watch) keeps adding passes; pick them up without a reload.
  setInterval(async () => {
    try {
      const fresh = await loadCatalog();
      if (fresh.passes.length === state.passes.length && fresh.last_search === state.cat.last_search) return;
      const atLatest = state.pass === state.evaluated[state.evaluated.length - 1];
      const keep = state.pass.id;
      applyCatalog(fresh);
      placeMarkers();
      renderTimeline();
      renderChart();
      const latest = state.evaluated[state.evaluated.length - 1];
      selectPass(atLatest && latest ? latest.id : keep, atLatest);
    } catch { /* keep the current view if the refresh fails */ }
  }, REFRESH_MS);
}

window.addEventListener("load", boot);
