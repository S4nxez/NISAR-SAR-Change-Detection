let chart;
export function renderTrendChart(canvas, site, dates) {
  if (chart) chart.destroy();
  chart = new Chart(canvas, {
    type: "line",
    data: { labels: dates, datasets: [
      { label: "VV", data: site.vv, borderColor: "#e4b65c", backgroundColor: "#e4b65c18", borderWidth: 2, pointRadius: 2.5, tension: .32 },
      { label: "VH", data: site.vh, borderColor: "#72b8d0", backgroundColor: "#72b8d018", borderWidth: 2, pointRadius: 2.5, tension: .32 }
    ]},
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: { display: false }, tooltip: { backgroundColor: "#172530", titleColor: "#edf4f7", bodyColor: "#c1d0d8", padding: 10 } },
      scales: {
        x: { grid: { display: false }, ticks: { color: "#8fa2ae", maxRotation: 0, autoSkip: true, maxTicksLimit: 6 }, border: { display: false } },
        y: { grid: { color: "#263742" }, ticks: { color: "#8fa2ae", maxTicksLimit: 5 }, border: { display: false }, title: { display: true, text: "dB", color: "#8fa2ae" } }
      }
    }
  });
}
