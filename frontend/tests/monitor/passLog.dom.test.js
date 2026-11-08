import assert from "node:assert/strict";
import { afterEach, describe, test } from "node:test";

import { markSelectedStrip, renderPassLog } from "../../src/monitor/passLog.js";
import { buildRecord, nextPasses } from "../../src/monitor/record.js";
import { openPage } from "./dom.js";
import { catalog } from "./fixtures.js";

let page;
afterEach(() => page?.restore());

function draw(cat, options = {}) {
  page = openPage("index.html");
  const record = buildRecord(cat);
  const selected = [];
  const today = "2026-09-01";
  const svg = page.$("#swath");
  renderPassLog(svg, { record, current: record.evaluated[0], today, ghosts: nextPasses(record, today), animate: false,
    onSelect: id => selected.push(id), ...options });
  return { svg, record, selected, all: sel => [...svg.querySelectorAll(sel)] };
}

describe("pass log drawing", () => {
  test("one strip per shown pass, split by status, partial passes as outlines", () => {
    const { svg, all } = draw(catalog());
    assert.equal(svg.getAttribute("viewBox"), "0 0 900 240");
    assert.deepEqual(all(".strip").map(g => g.dataset.id), ["2026-07-07_t161A", "2026-07-19_t161A", "2026-08-12_t169D",
      "2026-08-19_t097D", "2026-08-31_t097D"]);
    assert.ok(svg.querySelector('[data-id="2026-08-12_t169D"]').classList.contains("partial"));
    assert.equal(svg.querySelector('[data-id="2026-08-12_t169D"]').querySelectorAll("polygon").length, 1);
    assert.deepEqual([...svg.querySelector('[data-id="2026-08-31_t097D"]').querySelectorAll("polygon")].map(p => p.getAttribute("class")),
      ["seg-isolated", "seg-at_risk", "shell"]);
    assert.match(svg.querySelector('[data-id="2026-07-19_t161A"]').getAttribute("aria-label"), /river 1700 cm$/);
  });

  test("axis, gauge, today line, expected passes and the selected label", () => {
    const { svg, all } = draw(catalog());
    const months = all(".axis text").map(t => t.textContent);
    assert.deepEqual(months.slice(0, 2), ["Jul", "Aug"]);
    assert.match(months[2], /^Sept?$/);   // ICU versions abbreviate September differently
    assert.match(svg.querySelector(".gauge-line").getAttribute("d"), /^M[\d.]+,[\d.]+(L[\d.]+,[\d.]+)*M/);  // broken by the gap
    assert.equal(all(".gauge-tick").map(t => t.textContent).at(-1), "today");
    assert.equal(all(".ghost").length, 2);
    assert.equal(svg.querySelector(".sel-label").textContent, "7 JUL");
  });

  test("click and keyboard select a pass", () => {
    const { svg, selected } = draw(catalog());
    const strip = svg.querySelector('[data-id="2026-08-19_t097D"]');
    strip.dispatchEvent(new page.window.Event("click"));
    strip.dispatchEvent(new page.window.KeyboardEvent("keydown", { key: " " }));
    strip.dispatchEvent(new page.window.KeyboardEvent("keydown", { key: "a" }));
    assert.deepEqual(selected, ["2026-08-19_t097D", "2026-08-19_t097D"]);
  });

  test("without a gauge series there is no river line", () => {
    const cat = catalog();
    delete cat.gauge;
    const { svg } = draw(cat);
    assert.equal(svg.querySelector(".gauge-line"), null);
    assert.equal(svg.querySelector(".gauge-label"), null);
  });

  test("the reveal animation is staggered and always cleaned up", async () => {
    const { all } = draw(catalog(), { animate: true });
    const strips = all(".strip");
    assert.ok(strips.every(g => g.classList.contains("strip-in")));
    assert.equal(strips[2].style.animationDelay, "80ms");
    strips[0].dispatchEvent(new page.window.Event("animationend"));
    assert.ok(!strips[0].classList.contains("strip-in"));
  });

  test("selection moves the label", () => {
    const { svg, record } = draw(catalog());
    markSelectedStrip(svg, record.evaluated[3]);
    assert.equal(svg.querySelectorAll(".strip.is-selected").length, 1);
    assert.equal(svg.querySelectorAll(".sel-label").length, 1);
    assert.equal(svg.querySelector(".sel-label").textContent, "31 AUG");
    markSelectedStrip(svg, null);
    assert.equal(svg.querySelector(".sel-label"), null);
  });
});
