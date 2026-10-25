const levelLabels = { high: "High", medium: "Moderate", low: "Low" };
const levelRank = { high: 3, medium: 2, low: 1 };
const openCountries = new Set();

export function groupByCountry(sites) {
  const groups = new Map();
  sites.forEach(site => {
    if (!groups.has(site.country)) groups.set(site.country, []);
    groups.get(site.country).push(site);
  });
  return [...groups.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([country, items]) => ({ country, sites: items.sort((a, b) => a.name.localeCompare(b.name)) }));
}

export function renderSiteList(container, countries, selectedId, onSelect, { reveal = false } = {}) {
  const selectedCountry = countries.find(group => group.sites.some(site => site.id === selectedId))?.country;
  if (reveal && selectedCountry) openCountries.add(selectedCountry);

  container.replaceChildren();
  let index = 0;
  countries.forEach(({ country, sites }) => {
    const group = document.createElement("details");
    group.className = "country-group";
    group.open = openCountries.has(country);
    group.addEventListener("toggle", () => {
      if (group.open) openCountries.add(country);
      else openCountries.delete(country);
    });

    const topLevel = sites.reduce((top, site) => (levelRank[site.level] > levelRank[top] ? site.level : top), "low");
    const summary = document.createElement("summary");
    summary.className = `country-summary ${country === selectedCountry ? "has-selected" : ""}`;
    summary.innerHTML = `
      <span class="country-name"><i class="key-dot key-${topLevel}"></i>${country}</span>
      <span class="country-count">${String(sites.length).padStart(2, "0")}</span>
      <span class="country-chevron" aria-hidden="true"></span>`;
    group.append(summary);

    const items = document.createElement("div");
    items.className = "country-sites";
    sites.forEach(site => {
      index += 1;
      const button = document.createElement("button");
      button.type = "button";
      button.className = `site-item ${site.id === selectedId ? "is-selected" : ""}`;
      button.setAttribute("aria-pressed", String(site.id === selectedId));
      button.innerHTML = `
        <span class="site-index">${String(index).padStart(2, "0")}</span>
        <span class="site-main"><strong>${site.name}</strong><small>${site.category}</small></span>
        <span class="site-change"><b class="level-${site.level}">${site.change}</b><small>${levelLabels[site.level]}</small></span>`;
      button.addEventListener("click", () => onSelect(site.id));
      items.append(button);
    });
    group.append(items);
    container.append(group);
  });

  const selected = container.querySelector(".site-item.is-selected");
  if (reveal && selected && selected.offsetParent) {
    const top = selected.offsetTop;
    const bottom = top + selected.offsetHeight;
    if (top < container.scrollTop || bottom > container.scrollTop + container.clientHeight) {
      container.scrollTo({ top: top - 8, behavior: "smooth" });
    }
  }
}

export function renderSelectedSummary(container, site) {
  container.innerHTML = `<div class="summary-top"><span>SELECTED SITE</span><span class="confidence">${Math.round(site.confidence * 100)}% confidence*</span></div>
    <h3>${site.name}</h3><p>${site.description}</p>`;
}
