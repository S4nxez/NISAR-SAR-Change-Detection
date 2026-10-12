const levelLabels = { high: "High", medium: "Moderate", low: "Low" };

export function renderSiteList(container, sites, selectedId, onSelect) {
  container.replaceChildren();
  sites.forEach((site, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `site-item ${site.id === selectedId ? "is-selected" : ""}`;
    button.setAttribute("aria-pressed", String(site.id === selectedId));
    button.innerHTML = `
      <span class="site-index">${String(index + 1).padStart(2, "0")}</span>
      <span class="site-main"><strong>${site.name}</strong><small>${site.country} · ${site.category}</small></span>
      <span class="site-change"><b class="level-${site.level}">${site.change}</b><small>${levelLabels[site.level]}</small></span>`;
    button.addEventListener("click", () => onSelect(site.id));
    container.append(button);
  });
}

export function renderSelectedSummary(container, site) {
  container.innerHTML = `<div class="summary-top"><span>SELECTED SITE</span><span class="confidence">${Math.round(site.confidence * 100)}% confidence*</span></div>
    <h3>${site.name}</h3><p>${site.description}</p>`;
}
