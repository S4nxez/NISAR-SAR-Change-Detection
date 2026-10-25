const colors = { high: "#e47759", medium: "#e4b65c", low: "#68b6a3" };
let map;
let markerLayer;
const markers = new Map();

export async function createMap(sites, onSelect) {
  const worldBounds = L.latLngBounds([-85, -180], [85, 180]);
  map = L.map("map", {
    zoomControl: true, scrollWheelZoom: false,
    maxBounds: worldBounds, maxBoundsViscosity: 1
  }).setView([20, 5], 2);
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png?key=cb1_4hx7_1_b016ecf4f001497ebf19ce2d", {
    attribution: '&copy; OpenStreetMap &copy; CARTO', subdomains: "abcd", maxZoom: 18, noWrap: true, bounds: worldBounds
  }).addTo(map);
  markerLayer = L.layerGroup().addTo(map);
  sites.forEach(site => {
    const marker = L.circleMarker([site.lat, site.lng], {
      radius: 8, color: "#101b25", weight: 2, fillColor: colors[site.level], fillOpacity: 1
    }).bindTooltip(`${site.name} · ${site.change}`, { direction: "top", offset: [0, -7] });
    marker.on("click", () => onSelect(site.id));
    marker.addTo(markerLayer);
    markers.set(site.id, marker);
  });
  await new Promise(resolve => setTimeout(resolve, 80));
  map.invalidateSize();
  fitMinZoom();
  // The map grows with its panel (flex), so keep Leaflet's size and min zoom in sync.
  new ResizeObserver(() => {
    map.invalidateSize();
    fitMinZoom();
  }).observe(map.getContainer());
  return { selectSite };
}

// Lowest zoom at which a single world copy still fills the map width.
function fitMinZoom() {
  const minZoom = Math.max(1, Math.ceil(Math.log2(map.getSize().x / 256)));
  map.setMinZoom(minZoom);
  if (map.getZoom() < minZoom) map.setZoom(minZoom);
}
function selectSite(id) {
  const marker = markers.get(id);
  if (!marker) return;
  map.flyTo(marker.getLatLng(), Math.max(map.getZoom(), 4), { duration: 0.5 });
  marker.openTooltip();
}
