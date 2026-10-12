import { sites, observationDates } from "./data/sites.js";
import { renderSiteList, renderSelectedSummary } from "./components/siteList.js";
import { renderInsight } from "./components/insightPanel.js";
import { renderTrendChart } from "./components/trendChart.js";
import { createMap } from "./services/mapService.js";

const elements = {
  list: document.querySelector("#site-list"),
  summary: document.querySelector("#selected-summary"),
  insight: document.querySelector("#insight-content"),
  chart: document.querySelector("#trend-chart")
};
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

function init() {
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
init();
