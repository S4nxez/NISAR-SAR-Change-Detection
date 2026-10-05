let routes = [
  {
    id: 1,
    name: "China → España (Directo)",
    coords: [
      [31.23, 121.47],
      [40.41, -3.7],
    ],
    cost: 1200,
    time: 25,
    risk: "medium",
  },
  {
    id: 2,
    name: "China → Países Bajos → España",
    coords: [
      [31.23, 121.47],
      [52.36, 4.9],
      [40.41, -3.7],
    ],
    cost: 1050,
    time: 30,
    risk: "low",
  },
  {
    id: 3,
    name: "China → Panamá → España",
    coords: [
      [31.23, 121.47],
      [8.98, -79.52],
      [40.41, -3.7],
    ],
    cost: 1140,
    time: 35,
    risk: "medium",
  },
  {
    id: 4,
    name: "China → Francia → España",
    coords: [
      [31.23, 121.47],
      [48.85, 2.35],
      [40.41, -3.7],
    ],
    cost: 1080,
    time: 28,
    risk: "medium",
  },
  {
    id: 5,
    name: "China → Alemania → España",
    coords: [
      [31.23, 121.47],
      [52.52, 13.4],
      [40.41, -3.7],
    ],
    cost: 1020,
    time: 29,
    risk: "low",
  },
  {
    id: 6,
    name: "China → Emiratos Árabes Unidos → España",
    coords: [
      [31.23, 121.47],
      [25.2, 55.27],
      [40.41, -3.7],
    ],
    cost: 980,
    time: 33,
    risk: "high",
  },
  {
    id: 7,
    name: "China → México → España",
    coords: [
      [31.23, 121.47],
      [19.43, -99.13],
      [40.41, -3.7],
    ],
    cost: 1170,
    time: 36,
    risk: "medium",
  },
];

const routesContainer = document.getElementById("routes");
const originInput = document.getElementById("originInput");
const destinationInput = document.getElementById("destinationInput");
const bestRouteEl = document.getElementById("best-route");

let isLoading = false;

function getRiskClass(risk) {
  return risk === "low" ? "good" : risk === "medium" ? "medium" : "bad";
}

function renderRoutesLoading() {
  routesContainer.innerHTML = "";

  for (let i = 0; i < 5; i++) {
    const card = document.createElement("div");
    card.className = "route-card route-card-loading";
    card.innerHTML = `
      <div class="route-cell route-name-cell">
        <div class="skeleton skeleton-title"></div>
      </div>
      <div class="route-separator"></div>
      <div class="route-cell route-metric-cell">
        <div class="skeleton skeleton-text"></div>
      </div>
      <div class="route-separator"></div>
      <div class="route-cell route-metric-cell">
        <div class="skeleton skeleton-text"></div>
      </div>
      <div class="route-separator"></div>
      <div class="route-cell route-metric-cell">
        <div class="skeleton skeleton-text"></div>
      </div>
    `;
    routesContainer.appendChild(card);
  }
}

function renderRoutes() {
  routesContainer.innerHTML = "";

  routes.forEach((route) => {
    const card = document.createElement("div");
    card.className = "route-card";

    card.innerHTML = `
      <div class="route-cell route-name-cell">
        <div class="route-title">${route.name}</div>
      </div>

      <div class="route-separator"></div>

      <div class="route-cell route-metric-cell">
        <div class="metric">${route.cost}€</div>
      </div>

      <div class="route-separator"></div>

      <div class="route-cell route-metric-cell">
        <div class="metric">⏱ ${route.time} días</div>
      </div>

      <div class="route-separator"></div>

      <div class="route-cell route-metric-cell">
        <div class="metric ${getRiskClass(route.risk)}">⚠ ${route.risk}</div>
      </div>
    `;

    card.addEventListener("click", () => drawRoute(route));
    routesContainer.appendChild(card);
  });
}

function calculateBestRoute() {
  return routes.reduce((best, current) => {
    const score =
      current.cost * 0.5 +
      current.time * 10 +
      (current.risk === "low" ? 0 : current.risk === "medium" ? 200 : 500);

    const bestScore =
      best.cost * 0.5 +
      best.time * 10 +
      (best.risk === "low" ? 0 : best.risk === "medium" ? 200 : 500);

    return score < bestScore ? current : best;
  });
}

function renderBestRoute() {
  if (isLoading) {
    bestRouteEl.innerText = "Cargando...";
    return;
  }

  const best = calculateBestRoute();
  bestRouteEl.innerText = best?.name ?? "Sin rutas";
}

async function fetchRoutes() {
  const origin = originInput.value.trim();
  const destination = destinationInput.value.trim();

  if (!origin || !destination) return;

  isLoading = true;
  renderBestRoute();
  renderRoutesLoading();
  try {
    const response = await fetch(
      `/api/routes?origin=${encodeURIComponent(origin)}&destination=${encodeURIComponent(destination)}`,
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();

    if (Array.isArray(data.routes) && data.routes.length > 0) {
      routes = data.routes;
    }

    isLoading = false;
    renderRoutes();
    renderBestRoute();
  } catch (error) {
    console.error("Error cargando rutas:", error);
    isLoading = false;
    renderRoutes();
    renderBestRoute();
  }
}

function handleOriginComplete() {
  if (originInput.value.trim()) {
    destinationInput.focus();
  }
}

function handleDestinationComplete() {
  if (!destinationInput.value.trim()) return;

  destinationInput.blur(); // baja el teclado en móvil
  fetchRoutes();
}

originInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    handleOriginComplete();
  }
});

originInput.addEventListener("blur", handleOriginComplete);

destinationInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    handleDestinationComplete();
  }
});

destinationInput.addEventListener("blur", () => {
  if (destinationInput.value.trim() && !isLoading) {
    fetchRoutes();
  }
});

renderRoutes();
renderBestRoute();
