// Leaflet map of the monitor: basemap, the pass images, the area outline, the hub and one marker per community.

import { SEVERITY } from "./config.js";
import { esc } from "./format.js";

const PANES = { radar: 330, water: 340, change: 350 };
const ROUTE_GLYPH = new Set(["connected", "at_risk", "isolated"]);

export function glyphIcon(L, status, selected) {
  const size = ROUTE_GLYPH.has(status) ? 14 : 9;
  return L.divIcon({ className: "", iconSize: [size, size],
    html: `<div class="mk ${status}${selected ? " is-selected" : ""}"></div>` });
}

// Leaflet is passed in (window.L from the CDN) so this module can be loaded without it.
export function createMapView(L, { element, cat, onCommunityClick }) {
  const map = L.map(element, { zoomControl: true, scrollWheelZoom: true, attributionControl: true, zoomSnap: 0.25 });
  // OpenStreetMap standard tiles need no API key; monitor.css darkens them.
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap contributors · NISAR: NASA/ISRO, ASF DAAC", maxZoom: 18, className: "basemap-dark"
  }).addTo(map);
  for (const [pane, z] of Object.entries(PANES)) map.createPane(pane).style.zIndex = z;
  const otherLayer = L.layerGroup();
  const markerLayer = L.layerGroup().addTo(map);
  const markers = {};
  const overlays = {};
  const bounds = cat.grid.bounds;
  map.fitBounds(bounds);

  // the edge of the monitored area, drawn like a sensor footprint
  const circ = cat.area.circle;
  if (circ) {
    L.circle([circ.lat, circ.lon], { radius: circ.radius_km * 1000, color: "#b6c3ff", weight: 1, opacity: 0.55,
      dashArray: "2 6", fill: false, interactive: false }).addTo(map);
  }

  const { hub } = cat.area;
  const at = hub.access || hub;
  L.marker([at.lat, at.lon], { icon: L.divIcon({ className: "", html: '<div class="hub-mk"></div>', iconSize: [16, 16] }),
    zIndexOffset: 1000, keyboard: false })
    .bindTooltip(`<strong>${esc(hub.name)}</strong><br>Hub town: routes are traced to here`, { className: "tip" }).addTo(map);

  // Monitored communities on the main layer, the rest on the optional one. Classes come from the
  // whole record, so they can change when new passes arrive.
  function placeMarkers(communities) {
    markerLayer.clearLayers();
    otherLayer.clearLayers();
    for (const c of communities) {
      let m = markers[c.id];
      if (!m) {
        m = L.marker([c.lat, c.lon], { icon: glyphIcon(L, "no_data"), keyboard: false })
          .bindTooltip("", { className: "tip" })
          .on("click", () => onCommunityClick(c.id));
        markers[c.id] = m;
      }
      (c.class === "monitored" ? markerLayer : otherLayer).addLayer(m);
    }
  }

  // Show an image over the grid; the same image only gets its opacity updated.
  function setOverlay(key, url, opacity, on) {
    const current = overlays[key];
    if (current && on && current.url === url) {
      if (current.opacity !== opacity) { current.layer.setOpacity(opacity); current.opacity = opacity; }
      return;
    }
    if (current) { current.layer.remove(); delete overlays[key]; }
    if (on && url) {
      const layer = L.imageOverlay(url, bounds, { pane: key, opacity, interactive: false }).addTo(map);
      overlays[key] = { layer, url, opacity };
    }
  }

  // images: {radar, water, change} urls (or null); options: which layers are on and the water opacity.
  function showLayers(images, { radar, water, change, other, opacity }) {
    setOverlay("radar", images.radar, 1, radar);
    setOverlay("water", images.water, opacity, water);
    setOverlay("change", images.change, 1, change);
    if (other) otherLayer.addTo(map); else otherLayer.remove();
  }

  // markerState(c) -> {status, tooltip, selected}
  function updateMarkers(communities, markerState) {
    for (const c of communities) {
      const { status, tooltip, selected } = markerState(c);
      const m = markers[c.id];
      m.setIcon(glyphIcon(L, status, selected));
      m.setZIndexOffset(SEVERITY[status] ? SEVERITY[status] * 100 : 0);
      m.setTooltipContent(tooltip);
    }
  }

  return {
    placeMarkers,
    showLayers,
    updateMarkers,
    flyTo(c, animate) { map.flyTo([c.lat, c.lon], Math.max(map.getZoom(), 12), { duration: animate ? 0.6 : 0 }); },
  };
}
