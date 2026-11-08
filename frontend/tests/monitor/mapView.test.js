import assert from "node:assert/strict";
import { beforeEach, describe, test } from "node:test";

import { createMapView, glyphIcon } from "../../src/monitor/mapView.js";
import { catalog } from "./fixtures.js";

// A recording stand-in for the parts of Leaflet the map view uses.
function fakeLeaflet() {
  const log = [];
  const layer = (kind, args) => {
    const o = { kind, args, on: true, children: [], handlers: {},
      addTo() { o.on = true; log.push(["add", kind, args[0]]); return o; },
      remove() { o.on = false; log.push(["remove", kind, args[0]]); return o; },
      bindTooltip(t) { o.tooltip = t; return o; },
      on(evt, fn) { o.handlers[evt] = fn; return o; },
      setIcon(i) { o.icon = i; return o; }, setZIndexOffset(z) { o.z = z; return o; },
      setTooltipContent(t) { o.tooltip = t; return o; }, setOpacity(v) { o.opacity = v; log.push(["opacity", kind, v]); return o; },
      clearLayers() { o.children = []; return o; }, addLayer(m) { o.children.push(m); return o; } };
    return o;
  };
  const map = { panes: {}, fitted: null, flown: null,
    createPane(name) { return (map.panes[name] = { style: {} }); }, fitBounds(b) { map.fitted = b; },
    flyTo(ll, zoom, opts) { map.flown = [ll, zoom, opts]; }, getZoom: () => 9 };
  const made = { markers: [], groups: [], circles: [] };
  const L = {
    log, map: () => map, made,
    tileLayer: url => layer("tile", [url]),
    layerGroup: () => { const g = layer("group", []); made.groups.push(g); return g; },
    circle: (ll, o) => { const c = layer("circle", [ll, o]); made.circles.push(c); return c; },
    marker: ll => { const m = layer("marker", [ll]); made.markers.push(m); return m; },
    divIcon: o => o,
    imageOverlay: (url, bounds, o) => layer("overlay", [url, bounds, o]),
  };
  return { L, map };
}

describe("map view", () => {
  let L, map, cat, clicked, view;
  beforeEach(() => {
    ({ L, map } = fakeLeaflet());
    cat = catalog();
    clicked = [];
    view = createMapView(L, { element: "map", cat, onCommunityClick: id => clicked.push(id) });
  });

  test("fits the grid, stacks the image panes and draws the area circle and the hub", () => {
    assert.deepEqual(map.fitted, cat.grid.bounds);
    assert.deepEqual(Object.fromEntries(Object.entries(map.panes).map(([k, v]) => [k, v.style.zIndex])),
      { radar: 330, water: 340, change: 350 });
    assert.equal(L.made.circles[0].args[1].radius, 55000);
    const hub = L.made.markers[0];
    assert.deepEqual(hub.args[0], [-3.35, -64.71]);
    assert.match(hub.tooltip, /<strong>Tefé<\/strong>/);
  });

  test("hub marker at its water access when it has one, no circle for a box area", () => {
    const f = fakeLeaflet();
    const c = catalog();
    delete c.area.circle;
    c.area.hub.access = { lon: -64.72, lat: -3.36 };
    createMapView(f.L, { element: "map", cat: c, onCommunityClick() {} });
    assert.equal(f.L.made.circles.length, 0);
    assert.deepEqual(f.L.made.markers[0].args[0], [-3.36, -64.72]);
  });

  test("monitored communities on the main layer, the rest on the optional one; markers are reused", () => {
    const [other, main] = L.made.groups;
    view.placeMarkers(cat.communities);
    assert.equal(main.children.length, 2);
    assert.equal(other.children.length, 2);
    const first = main.children[0];
    view.placeMarkers(cat.communities);
    assert.equal(main.children[0], first);
    first.handlers.click();
    assert.deepEqual(clicked, ["a"]);
  });

  test("layers: the same image only changes opacity, switched off images are removed", () => {
    const images = { radar: "r.webp", water: "w.png", change: null };
    view.showLayers(images, { radar: true, water: true, change: true, other: false, opacity: 0.7 });
    assert.deepEqual(L.log.filter(e => e[1] === "overlay").map(e => `${e[0]} ${e[2]}`), ["add r.webp", "add w.png"]);
    L.log.length = 0;
    view.showLayers(images, { radar: true, water: true, change: true, other: true, opacity: 0.4 });
    assert.deepEqual(L.log.filter(e => e[1] === "overlay"), [["opacity", "overlay", 0.4]]);
    assert.ok(L.log.some(e => e[0] === "add" && e[1] === "group"));
    L.log.length = 0;
    view.showLayers({ ...images, water: "w2.png" }, { radar: false, water: true, change: false, other: false, opacity: 0.4 });
    assert.deepEqual(L.log.filter(e => e[1] === "overlay").map(e => `${e[0]} ${e[2]}`),
      ["remove r.webp", "remove w.png", "add w2.png"]);
  });

  test("markers show the status, the selection and the tooltip; worse statuses on top", () => {
    view.placeMarkers(cat.communities);
    view.updateMarkers(cat.communities, c => ({ status: c.id === "a" ? "isolated" : "connected", selected: c.id === "b",
      tooltip: `tip ${c.id}` }));
    const byLatLon = Object.fromEntries(L.made.markers.slice(1).map((m, i) => [cat.communities[i].id, m]));
    assert.equal(byLatLon.a.z, 300);
    assert.equal(byLatLon.b.z, 100);
    assert.match(byLatLon.b.icon.html, /mk connected is-selected/);
    assert.equal(byLatLon.a.tooltip, "tip a");
  });

  test("fly to a community, never zooming out", () => {
    view.flyTo({ lat: -3.3, lon: -64.6 }, false);
    assert.deepEqual(map.flown, [[-3.3, -64.6], 12, { duration: 0 }]);
  });

  test("glyph size: route statuses are bigger", () => {
    assert.deepEqual(glyphIcon(L, "isolated").iconSize, [14, 14]);
    assert.deepEqual(glyphIcon(L, "inland").iconSize, [9, 9]);
  });
});
