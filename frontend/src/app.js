import { sites as demoSites, observationDates as demoObservationDates } from "./data/sites.js";
import { renderSiteList, renderSelectedSummary } from "./components/siteList.js";
import { renderInsight } from "./components/insightPanel.js";
import { renderTrendChart } from "./components/trendChart.js";
import { createMap } from "./services/mapService.js";

const elements = {
  list: document.querySelector("#site-list"),
  summary: document.querySelector("#selected-summary"),
  insight: document.querySelector("#insight-content"),
  chart: document.querySelector("#trend-chart"),
  topbar: document.querySelector(".topbar")
};
let sites = demoSites;
let observationDates = demoObservationDates;
let selectedId = sites[0].id;
let mapControls;

function selectSite(id) {
  selectedId = id;
  const site = sites.find(item => item.id === id);
  if (!site) return;
  renderSiteList(elements.list, sites, selectedId, selectSite);
  renderSelectedSummary(elements.summary, site);
  renderInsight(elements.insight, site);
  renderTrendChart(elements.chart, site, observationDates);
  mapControls?.selectSite(id);
}

function bindScrollEffects() {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  let compact = false;
  let ticking = false;

  function update() {
    ticking = false;
    const y = window.scrollY;
    // Hysteresis: shrinking the bar shifts the layout, so expand/compact at different offsets to avoid flicker.
    if (!compact && y > 40) compact = true;
    else if (compact && y < 4) compact = false;
    elements.topbar.classList.toggle("is-compact", compact);
    // Background follows the content at a fraction of its speed (parallax).
    const shift = reduceMotion.matches ? 0 : -Math.min(y * 0.12, window.innerHeight * 0.4);
    document.documentElement.style.setProperty("--bg-shift", `${shift}px`);
  }

  window.addEventListener("scroll", () => {
    if (!ticking) {
      ticking = true;
      requestAnimationFrame(update);
    }
  }, { passive: true });
  update();
}

async function init() {
  try {
    const response = await fetch(new URL("../api/sites", import.meta.url), { headers: { Accept: "application/json" } });
    if (response.ok) {
      const catalog = await response.json();
      if (Array.isArray(catalog.sites) && catalog.sites.length > 0) {
        sites = catalog.sites;
        observationDates = Array.isArray(catalog.observationDates) ? catalog.observationDates : demoObservationDates;
        selectedId = sites[0].id;
      }
    }
  } catch (error) {
    console.info("SAR API unavailable; using illustrative demo data.", error);
  }

  document.querySelector("#stat-areas").textContent = String(sites.length).padStart(2, "0");
  document.querySelector("#stat-signals").textContent = String(sites.reduce((total, site) => total + (site.level === "high" ? 5 : site.level === "medium" ? 3 : 1), 0)).padStart(2, "0");
  selectSite(selectedId);
  createMap(sites, selectSite).then(controls => {
    mapControls = controls;
    mapControls.selectSite(selectedId);
  }).catch(error => {
    document.querySelector("#map").innerHTML = '<p class="map-error">Map could not load. Check your connection and reload.</p>';
    console.error("Map initialisation failed:", error);
  });
}
bindScrollEffects();
init();
