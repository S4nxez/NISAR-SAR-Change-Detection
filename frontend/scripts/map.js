let map;
let currentLayer = null;
let countriesLayer = null;

// ======================
// MAPA ESTILO PREMIUM
// ======================
async function initMap() {
  map = L.map("map", {
    worldCopyJump: false,
    maxBounds: [
      [-85, -180],
      [85, 180],
    ],
    minZoom: 2,
    maxZoom: 6,
    zoomControl: true,
    attributionControl: false,
  }).setView([25, 0], 2);

  map.getContainer().style.background = "transparent";

  const res = await fetch(
    "assets/geo/worldmap.geo.json",
  );
  const countries = await res.json();

  countriesLayer = L.geoJSON(countries, {
    style: {
      color: "rgba(34, 197, 94, 0.51)", // más tenue
      weight: 1,
      fillColor: "#228fc5",
      fillOpacity: 0.03, // relleno muy ligero
      opacity: 0.8,
    },
    interactive: false,
  }).addTo(map);
}

// ======================
// GENERAR CURVA SUAVE (Bezier simple)
// ======================
function createCurvedLine(coords) {
  if (coords.length < 2) return coords;

  const curved = [];
  for (let i = 0; i < coords.length - 1; i++) {
    const start = coords[i];
    const end = coords[i + 1];

    const midLat = (start[0] + end[0]) / 2;
    const midLng = (start[1] + end[1]) / 2;

    // desviación para curvatura (ajusta intensidad aquí)
    const offset = 10;

    const controlPoint = [
      midLat + offset * Math.sign(end[1] - start[1]),
      midLng,
    ];

    // interpolación cuadrática
    const steps = 30;
    for (let t = 0; t <= 1; t += 1 / steps) {
      const lat =
        (1 - t) * (1 - t) * start[0] +
        2 * (1 - t) * t * controlPoint[0] +
        t * t * end[0];

      const lng =
        (1 - t) * (1 - t) * start[1] +
        2 * (1 - t) * t * controlPoint[1] +
        t * t * end[1];

      curved.push([lat, lng]);
    }
  }

  return curved;
}

// ======================
// DIBUJAR RUTA (GLOW + LÍNEA)
// ======================
function drawRoute(route) {
  if (currentLayer) map.removeLayer(currentLayer);

  const curvedCoords = createCurvedLine(route.coords);

  const glow = L.polyline(curvedCoords, {
    color: "#22c55e",
    weight: 8,
    opacity: 0.15,
    lineCap: "round",
  });

  const mainLine = L.polyline(curvedCoords, {
    color: "#22c556",
    weight: 2,
    opacity: 1,
    lineCap: "round",
    lineJoin: "round",
    dashArray: "6 10", // efecto más moderno tipo flujo
  });

  currentLayer = L.layerGroup([glow, mainLine]).addTo(map);

  map.fitBounds(mainLine.getBounds(), {
    padding: [60, 60],
    animate: true,
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  await initMap();
  renderRoutes();
  renderBestRoute();
});
