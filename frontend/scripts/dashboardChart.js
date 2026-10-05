// ======================
// DASHBOARD MOCK MEJORADO
// ======================
const ctx = document.getElementById("dashboardChart").getContext("2d");

// Función de normalización (0–100)
function normalize(data) {
  const min = Math.min(...data);
  const max = Math.max(...data);
  return data.map((v) => ((v - min) / (max - min)) * 100);
}

// Datos base (mock coherente)
const coste = [1100, 1250, 1180, 1350];
const tiempo = [22, 26, 24, 29];
const riesgo = [35, 50, 45, 60];

// Normalizados
const costeNorm = normalize(coste);
const tiempoNorm = normalize(tiempo);
const riesgoNorm = normalize(riesgo);

const dashboardChart = new Chart(ctx, {
  type: "line",
  data: {
    labels: ["Semana 1", "Semana 2", "Semana 3", "Semana 4"],
    datasets: [
      {
        label: "Coste (Índice)",
        data: costeNorm,
        borderColor: "#22c55e",
        backgroundColor: "rgba(34,197,94,0.15)",
        tension: 0.4,
        fill: true,
        pointRadius: 4,
      },
      {
        label: "Tiempo (Índice)",
        data: tiempoNorm,
        borderColor: "#f59e0b",
        backgroundColor: "rgba(245,158,11,0.15)",
        tension: 0.4,
        fill: true,
        pointRadius: 4,
      },
      {
        label: "Riesgo (Índice)",
        data: riesgoNorm,
        borderColor: "#ef4444",
        backgroundColor: "rgba(239,68,68,0.15)",
        tension: 0.4,
        fill: true,
        pointRadius: 4,
      },
    ],
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: "index",
      intersect: false,
    },
    plugins: {
      legend: {
        labels: {
          color: "white",
          font: {
            size: 15,
          },
        },
      },
      tooltip: {
        backgroundColor: "#111",
        titleColor: "#fff",
        bodyColor: "#ddd",
        callbacks: {
          label: function (context) {
            return `${context.dataset.label}: ${context.parsed.y.toFixed(0)}`;
          },
        },
      },
    },
    scales: {
      x: {
        ticks: {
          color: "white",
          font: {
            size: 15,
          },
        },
        grid: { color: "rgba(255,255,255,0.05)" },
      },
      y: {
        min: 0,
        max: 100,
        ticks: {
          font: {
            size: 15,
          },
          callback: (value) => value + "",
        },
        grid: { color: "rgba(255,255,255,0.05)" },
      },
    },
  },
});
