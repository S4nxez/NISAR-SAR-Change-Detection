// jsdom set-up for the page's DOM tests: the browser globals the modules read, the SVG features jsdom lacks,
// a recording stand-in for Leaflet and a fetch that serves a catalog.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { JSDOM } from "jsdom";

const FRONTEND = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const GLOBALS = ["window", "document", "location", "history", "matchMedia", "fetch", "L", "addEventListener",
  "setInterval", "Event"];

// jsdom has no SVG layout: give <svg> a size and a viewBox, and strips a bounding box from their polygons.
function patchSvg(window) {
  Object.defineProperty(window.SVGSVGElement.prototype, "viewBox", { configurable: true, get() {
    const [x, y, width, height] = (this.getAttribute("viewBox") || "0 0 0 0").split(" ").map(Number);
    return { baseVal: { x, y, width, height } };
  } });
  Object.defineProperty(window.SVGElement.prototype, "clientWidth", { configurable: true, get: () => 900 });
  Object.defineProperty(window.SVGElement.prototype, "clientHeight", { configurable: true, get: () => 240 });
  window.SVGElement.prototype.getBBox = function () {
    const pts = (this.querySelector("polygon")?.getAttribute("points") || "0,0").split(/[ ,]/).map(Number);
    const xs = pts.filter((_, i) => i % 2 === 0), ys = pts.filter((_, i) => i % 2 === 1);
    return { x: Math.min(...xs), y: Math.min(...ys), width: Math.max(...xs) - Math.min(...xs),
      height: Math.max(...ys) - Math.min(...ys) };
  };
}

export function fakeLeaflet() {
  const overlays = [], markers = [];
  const layer = (kind, args) => {
    const o = { kind, args, children: [], handlers: {},
      addTo() { if (kind === "overlay") overlays.push(args[0]); return o; }, remove() { return o; },
      bindTooltip(t) { o.tooltip = t; return o; }, on(evt, fn) { o.handlers[evt] = fn; return o; },
      setIcon(i) { o.icon = i.html; return o; }, setZIndexOffset() { return o; },
      setTooltipContent(t) { o.tooltip = t; return o; }, setOpacity() { return o; },
      clearLayers() { o.children = []; return o; }, addLayer(m) { o.children.push(m); return o; } };
    if (kind === "marker") markers.push(o);
    return o;
  };
  return { overlays, markers, flown: [],
    map() { const self = this; return { createPane: () => ({ style: {} }), fitBounds() {}, getZoom: () => 9,
      flyTo(ll) { self.flown.push(ll); } }; },
    tileLayer: u => layer("tile", [u]), layerGroup: () => layer("group", []), circle: () => layer("circle", []),
    marker: ll => layer("marker", [ll]), divIcon: o => o, imageOverlay: url => layer("overlay", [url]) };
}

// A page from frontend/ (scripts removed: tests import the modules themselves) with the browser globals set.
// Returns the window and a restore() for the globals.
export function openPage(page, { url = "http://localhost/terra-pulse-dev/pr-15/", catalog = null, status = 404,
  leaflet = fakeLeaflet() } = {}) {
  const html = fs.readFileSync(path.join(FRONTEND, page), "utf8").replace(/<script[\s\S]*?<\/script>/g, "");
  const dom = new JSDOM(html, { url, pretendToBeVisual: true });
  const { window } = dom;
  // jsdom fires its own load event asynchronously: wait for it, so that it never boots the app a second time
  const loaded = window.document.readyState === "complete"
    ? Promise.resolve() : new Promise(resolve => window.addEventListener("load", resolve, { once: true }));
  patchSvg(window);
  const saved = Object.fromEntries(GLOBALS.map(k => [k, Object.getOwnPropertyDescriptor(globalThis, k)]));
  const timers = [];
  const values = {
    window, document: window.document, location: window.location, history: window.history, Event: window.Event,
    matchMedia: () => ({ matches: true }),   // reduced motion: no reveal animation in tests
    // the backend: the catalog, or `status` (404 by default: nothing published yet) without one
    fetch: async () => (catalog ? { ok: true, status: 200, json: async () => structuredClone(catalog) } : { ok: false, status }),
    L: leaflet, addEventListener: window.addEventListener.bind(window),
    setInterval: (fn, ms) => { timers.push({ fn, ms }); return timers.length; },
  };
  for (const [k, v] of Object.entries(values)) Object.defineProperty(globalThis, k, { value: v, configurable: true, writable: true });
  window.L = leaflet;
  return {
    window, leaflet, timers, loaded,
    $: sel => window.document.querySelector(sel),
    restore() {
      for (const [k, d] of Object.entries(saved)) {
        if (d) Object.defineProperty(globalThis, k, d); else delete globalThis[k];
      }
      window.close();
    },
  };
}

let instance = 0;

// Import main.js as a fresh module (it boots on the window load event) and wait for the first render.
export async function bootApp(page) {
  await page.loaded;
  await import(`../../src/main.js?instance=${++instance}`);
  page.window.dispatchEvent(new page.window.Event("load"));
  for (let i = 0; i < 50 && page.$("#headline-meta").textContent.startsWith("Loading"); i++) {
    await new Promise(r => setTimeout(r, 5));
  }
}

export const click = (page, el) => el.dispatchEvent(new page.window.Event("click", { bubbles: true }));
