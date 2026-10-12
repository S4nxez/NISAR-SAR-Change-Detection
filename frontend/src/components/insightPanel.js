const interpretations = {
  high: { title: "Significant signal variation", tag: "PRIORITY REVIEW", copy: "The latest readings differ from the earlier baseline. Review the paired acquisitions and local context to determine what changed." },
  medium: { title: "Moderate signal variation", tag: "COMPARE BASELINE", copy: "The signal has shifted, but seasonal and moisture effects may explain part or all of the difference." },
  low: { title: "Small signal variation", tag: "ROUTINE MONITORING", copy: "The observed difference is relatively small. Keep this site in view and reassess when another acquisition is available." }
};
export function renderInsight(container, site) {
  const item = interpretations[site.level];
  container.innerHTML = `<div class="insight-status"><span class="level-indicator level-bg-${site.level}"></span><span>${item.tag}</span></div>
    <h3>${item.title}</h3><p class="insight-copy">${item.copy}</p>
    <div class="insight-metrics"><div><span>CHANGE SIGNAL</span><strong class="level-${site.level}">${site.change}</strong></div><div><span>DEMO CONFIDENCE*</span><strong>${Math.round(site.confidence * 100)}%</strong></div></div>`;
}
