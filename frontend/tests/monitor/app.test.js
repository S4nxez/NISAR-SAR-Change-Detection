// The River Lifeline page end to end in jsdom: boot from a catalog, user actions and the error states.
import assert from "node:assert/strict";
import { afterEach, describe, test } from "node:test";

import { bootApp, click, openPage } from "./dom.js";
import { catalog } from "./fixtures.js";

let page;
afterEach(() => page?.restore());

async function open(options = {}) {
  page = openPage("index.html", { catalog: catalog(), ...options });
  await bootApp(page);
  return page;
}

const text = sel => page.$(sel).textContent.replace(/\s+/g, " ").trim();
const select = (sel, value, event = "change") => {
  const el = page.$(sel);
  el.value = value;
  el.dispatchEvent(new page.window.Event(event));
};

describe("boot", () => {
  test("shows the latest evaluated pass and the whole record", async () => {
    await open();
    assert.equal(text("#headline-meta"), "31 Aug 2026 · 2 communities watched");
    assert.equal(text("#headline-text"), "1 community has lost the water route to Tefé.");
    assert.equal(page.$("#date-input").value, "2026-08-31");
    assert.equal(page.window.location.hash, "#d=2026-08-31");
    assert.equal(page.window.document.querySelectorAll("#swath .strip").length, 5);
    assert.equal(page.window.document.querySelectorAll("#community-list li").length, 2);
    assert.equal(text("#roster-count"), "2 of 2");
    assert.match(text("#plate"), /Track 97 ↓ descending/);
    assert.equal(text("#mast-mission"), "NISAR L-band radar · Lake Tefé");
    assert.equal(page.leaflet.markers.length, 1 + 4);   // hub + communities
    assert.deepEqual(page.leaflet.overlays, ["./public/data/monitor/tefe/passes/2026-08-31_t097D/radar.webp",
      "./public/data/monitor/tefe/passes/2026-08-31_t097D/water.png"]);
    assert.equal(page.timers[0].ms, 10 * 60 * 1000);   // catalog refresh
  });

  test("restores the day and the community from the URL", async () => {
    await open({ url: "http://localhost/app/#d=2026-07-20&c=b" });
    assert.equal(text("#headline-meta"), "19 Jul 2026 · 2 communities watched · latest pass before 20 Jul, 1 day earlier");
    assert.match(text("#dossier"), /^Bravo <b> At risk on 19 Jul 2026/);
  });

  test("an invalid day in the URL falls back to the latest pass instead of breaking the page", async () => {
    await open({ url: "http://localhost/app/#d=garbage&c=a" });
    assert.equal(text("#headline-meta"), "31 Aug 2026 · 2 communities watched");
    assert.equal(page.window.location.hash, "#d=2026-08-31&c=a");
  });

  test("an area that is not a plain id reads the default area", async () => {
    let asked;
    page = openPage("index.html", { url: "http://localhost/app/?area=../../x", catalog: catalog() });
    const fetch = globalThis.fetch;
    globalThis.fetch = async u => { asked = u; return fetch(u); };
    await bootApp(page);
    assert.equal(asked, "./public/data/monitor/tefe/catalog.json");
  });

  test("without a catalog the page explains how to build it", async () => {
    page = openPage("index.html", { catalog: null });
    await bootApp(page);
    assert.equal(text("#headline-meta"), "No record yet");
    assert.equal(text("#headline-text"), "The pass record has not been built.");
    assert.match(text(".notice"), /river_monitor\.py communities/);
  });

  test("a catalog with no pass to show says so instead of loading forever", async () => {
    const cat = catalog();
    cat.passes = cat.passes.filter(p => p.shown === false);
    page = openPage("index.html", { catalog: cat });
    await bootApp(page);
    assert.equal(text("#headline-meta"), "No record yet");
    assert.equal(text("#headline-text"), "No NISAR pass over the area yet.");
  });
});

describe("user actions", () => {
  test("a strip of the pass log selects its pass", async () => {
    await open();
    click(page, page.$('#swath .strip[data-id="2026-07-19_t161A"]'));
    assert.equal(text("#headline-meta"), "19 Jul 2026 · 2 communities watched");
    assert.equal(page.$("#date-input").value, "2026-07-19");
    assert.equal(text("#swath .sel-label"), "19 JUL");
    assert.match(text("#ledger"), /At risk1 \/ 2\+1 since 7 Jul/);
  });

  test("keyboard on a strip, and a partial pass shows the image only", async () => {
    await open();
    const strip = page.$('#swath .strip[data-id="2026-08-12_t169D"]');
    strip.dispatchEvent(new page.window.KeyboardEvent("keydown", { key: "Enter" }));
    assert.equal(text("#headline-text"), "This pass covers only part of the area.");
    click(page, page.$("#prev-pass"));
    assert.equal(page.$("#date-input").value, "2026-07-19");   // nearest full pass before the partial one
  });

  test("previous and next pass, stopping at the ends", async () => {
    await open();
    click(page, page.$("#next-pass"));
    assert.equal(page.$("#date-input").value, "2026-08-31");
    click(page, page.$("#prev-pass"));
    assert.equal(page.$("#date-input").value, "2026-08-19");
  });

  test("a day picks the latest full pass before it", async () => {
    await open();
    select("#date-input", "2026-08-18");
    assert.match(text("#headline-meta"), /^19 Jul 2026 .* latest pass before 18 Aug, 30 days earlier$/);
    select("#date-input", "not a day");
    assert.match(text("#headline-meta"), /^19 Jul 2026/);
  });

  test("a community from the list opens its dossier and flies the map to it", async () => {
    await open();
    click(page, page.$('#community-list button[data-id="b"]'));
    assert.match(text("#dossier"), /Last linked to Tefé ?19 Jul 2026/);
    assert.deepEqual(page.leaflet.flown, [[-3.4, -64.7]]);
    assert.equal(page.window.location.hash, "#d=2026-08-31&c=b");
    assert.ok(page.$('#community-list button[data-id="b"]').classList.contains("is-selected"));
  });

  test("a community from the map opens its dossier without moving the map", async () => {
    await open();
    page.leaflet.markers[3].handlers.click();   // Charlie, inland
    assert.match(text("#dossier"), /Not river-dependent/);
    assert.deepEqual(page.leaflet.flown, []);
  });

  test("filters and search", async () => {
    await open();
    click(page, page.$('.filter[data-filter="isolated"]'));
    assert.equal(text("#roster-count"), "1 of 2");
    click(page, page.$('.filter[data-filter="all"]'));
    select("#search", "zzz", "input");
    assert.equal(text("#community-list"), "No community matches this filter on 31 Aug.");
  });

  test("layers and the map key", async () => {
    await open();
    const change = page.$("#toggle-change");
    change.checked = true;
    change.dispatchEvent(new page.window.Event("input"));
    assert.match(text("#map-key"), /Water lost/);
    click(page, page.$('.layers-base button[data-base="none"]'));
    assert.ok(page.$('.layers-base button[data-base="none"]').classList.contains("is-on"));
  });

  test("play the record from the start", async () => {
    await open();
    click(page, page.$("#play"));
    assert.equal(page.$("#date-input").value, "2026-07-07");
    assert.equal(page.$("#play").textContent, "Pause");
    click(page, page.$("#play"));
    assert.equal(page.$("#play").textContent, "Play record");
  });

  test("download the day as CSV", async () => {
    await open();
    const blobs = [];
    globalThis.URL.createObjectURL = blob => { blobs.push(blob); return "blob:test"; };
    page.window.HTMLAnchorElement.prototype.click = function () { blobs.push(this.download); };
    click(page, page.$("#export-csv"));
    assert.equal(blobs[1], "communities_tefe_2026-08-31.csv");
    assert.match(await blobs[0].text(), /"Bravo <b>","hamlet"/);
  });
});

describe("catalog refresh", () => {
  test("new passes are picked up and the view follows the latest one", async () => {
    await open();
    const fresh = catalog();
    const last = fresh.passes[fresh.passes.length - 1];
    fresh.passes.push({ ...structuredClone(last), id: "2026-09-12_t097D", date: "2026-09-12", unconfirmed: [] });
    globalThis.fetch = async () => ({ ok: true, json: async () => fresh });
    await page.timers[0].fn();
    assert.equal(page.$("#date-input").value, "2026-09-12");
    assert.equal(page.window.document.querySelectorAll("#swath .strip").length, 6);
  });

  test("an unchanged or failing catalog keeps the view", async () => {
    await open();
    click(page, page.$('#swath .strip[data-id="2026-07-19_t161A"]'));
    await page.timers[0].fn();
    globalThis.fetch = async () => { throw new Error("offline"); };
    await page.timers[0].fn();
    assert.equal(page.$("#date-input").value, "2026-07-19");
  });
});
