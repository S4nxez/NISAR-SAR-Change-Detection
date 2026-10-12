const colors = { high: "#e47759", medium: "#e4b65c", low: "#68b6a3" };
let map;
let markerLayer;
const markers = new Map();

export async function createMap(sites, onSelect) {
  map = L.map("map", { zoomControl: true, scrollWheelZoom: false, worldCopyJump: true }).setView([20, 5], 2);
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png?key=cb1_4hx7_1_b016ecf4f001497ebf19ce2d", {
    attribution: '&copy; OpenStreetMap &copy; CARTO', subdomains: "abcd", maxZoom: 18
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
  return { selectSite };
}
function selectSite(id) {
  const marker = markers.get(id);
  if (!marker) return;
  map.flyTo(marker.getLatLng(), Math.max(map.getZoom(), 4), { duration: 0.5 });
  marker.openTooltip();
}
