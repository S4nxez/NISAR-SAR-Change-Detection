import assert from "node:assert/strict";
import { describe, test } from "node:test";

import * as panels from "../../src/components/panels.js";
import { buildRecord, communityRows } from "../../src/models/record.js";
import { catalog } from "../helpers/fixtures.js";

const setup = () => {
  const record = buildRecord(catalog());
  const byId = Object.fromEntries(record.cat.passes.map(p => [p.id, p]));
  const com = Object.fromEntries(record.cat.communities.map(c => [c.id, c]));
  return { record, byId, com };
};
const strip = html => html.replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();

describe("headline", () => {
  test("isolated communities on a full pass", () => {
    const { record, byId } = setup();
    const h = panels.headline(record, byId["2026-08-31_t097D"], "2026-08-31");
    assert.equal(h.meta, "31 Aug 2026 · 2 communities watched");
    assert.equal(strip(h.title), "1 community has lost the water route to Tefé.");
    assert.match(h.title, /class="count" style="color:#ff6b5b"/);
    assert.equal(h.sub, "1 more can only reach it through channels narrower than 60 m.");
  });

  test("no isolated community, and routes lost for the first time", () => {
    const { record, byId } = setup();
    assert.equal(strip(panels.headline(record, byId["2026-07-07_t161A"]).title),
      "0 communities have lost their water route to Tefé.");
    assert.equal(panels.headline(record, byId["2026-07-07_t161A"]).sub,
      "Every other watched community has a route at least 60 m wide.");
    assert.equal(panels.headline(record, byId["2026-08-19_t097D"]).sub,
      "1 more can only reach it through channels narrower than 60 m, 1 of them with no route on this pass for the first time.");
  });

  test("days between the chosen day and the pass shown, both ways and singular", () => {
    const { record, byId } = setup();
    assert.match(panels.headline(record, byId["2026-07-19_t161A"], "2026-08-01").meta,
      /latest pass before 1 Aug, 13 days earlier$/);
    assert.match(panels.headline(record, byId["2026-07-19_t161A"], "2026-07-20").meta, /, 1 day earlier$/);
    assert.match(panels.headline(record, byId["2026-07-07_t161A"], "2026-07-01").meta,
      /no full pass before 1 Jul: first one 6 days later$/);
  });

  test("a partial pass is shown but not evaluated", () => {
    const { record, byId } = setup();
    const h = panels.headline(record, byId["2026-08-12_t169D"], "2026-08-12");
    assert.equal(h.title, "This pass covers only part of the area.");
    assert.match(h.sub, /\(25 % covered\)/);
  });

  test("hub names are escaped", () => {
    const cat = catalog();
    cat.area.hub.name = "<img src=x>";
    const record = buildRecord(cat);
    assert.ok(!panels.headline(record, record.evaluated[0]).title.includes("<img"));
  });
});

describe("plate, map key and tooltips", () => {
  test("plate", () => {
    const { record, byId } = setup();
    assert.equal(strip(panels.plate(record, byId["2026-08-31_t097D"])),
      "NISAR · L-band HH · Track 97 ↓ descending · 31 Aug 2026 10:02 UTC · 19.9 m grid · 99 % of the area · beta product");
  });

  test("map key follows the layers that are on", () => {
    const { record } = setup();
    assert.equal(strip(panels.mapKey(record, { water: false, change: false })), "ConnectedAt riskIsolated");
    const all = strip(panels.mapKey(record, { water: true, change: true }));
    assert.equal(all, "WaterChannel &lt; 60 mWater lostWater gainedConnectedAt riskIsolated");
  });

  test("map key explains water under vegetation when the area maps it", () => {
    const { record } = setup();
    record.cat.area.vegetated_water = { hh_min_db: -4, ratio_min_db: 7, near_water_m: 1000 };
    assert.equal(strip(panels.mapKey(record, { water: true, change: false })),
      "WaterChannel &lt; 60 mWater under vegetation · not a routeConnectedAt riskIsolated");
    assert.equal(strip(panels.mapKey(record, { water: false, change: false })), "ConnectedAt riskIsolated");
  });

  test("marker tooltips", () => {
    const { record, byId, com } = setup();
    assert.equal(panels.markerTooltip(record, byId["2026-07-19_t161A"], com.a),
      "<strong>Alpha</strong> · Connected<br>Narrowest point 100–200 m · water 20 m away");
    assert.equal(panels.markerTooltip(record, byId["2026-07-19_t161A"], com.c), "<strong>Charlie</strong> · Not river-dependent");
    assert.equal(panels.markerTooltip(record, byId["2026-08-12_t169D"], com.a), "<strong>Alpha</strong> · No data");
    assert.match(panels.markerTooltip(record, byId["2026-07-19_t161A"], com.b), /Bravo &lt;b&gt;/);
  });
});

describe("roster", () => {
  test("a row with route, population and the previous status", () => {
    const { record, byId } = setup();
    const [a, b] = communityRows(record, byId["2026-07-19_t161A"], byId["2026-07-07_t161A"]);
    const html = panels.rosterItem(record, byId["2026-07-19_t161A"], a, "a");
    assert.match(html, /class="is-selected" data-id="a"/);
    assert.equal(strip(html), "Alphavillage · 1,200 people 100–200 m");
    assert.equal(strip(panels.rosterItem(record, byId["2026-07-19_t161A"], b, null)), "Bravo &lt;b&gt;hamlet &lt; 40 mwas connected");
  });

  test("a route lost on this pass only is to confirm", () => {
    const { record, byId } = setup();
    const b = communityRows(record, byId["2026-08-19_t097D"], null)[1];
    assert.match(panels.rosterItem(record, byId["2026-08-19_t097D"], b, null), /<b>no route<\/b><em>route lost, to confirm<\/em>/);
  });

  test("empty list", () => {
    const { byId } = setup();
    assert.equal(panels.rosterEmpty(byId["2026-07-07_t161A"]), '<li class="empty">No community matches this filter on 7 Jul.</li>');
  });
});

describe("ledger", () => {
  test("counts with changes since the previous pass, hub route, water change and river level", () => {
    const { record, byId } = setup();
    const text = strip(panels.ledger(record, byId["2026-07-19_t161A"], byId["2026-07-07_t161A"]));
    assert.match(text, /Isolated0 \/ 2no change since 7 Jul/);
    assert.match(text, /At risk1 \/ 2\+1 since 7 Jul/);
    assert.match(text, /Connected1 \/ 2−1 since 7 Jul/);
    assert.match(text, /Route Tefé ↔ Solimões≥ 400 mnarrowest point of the town's own route/);
    assert.match(text, /Water in view800 km²12.3 km² lost, 0 km² gained since the last pass of this track/);
    assert.match(text, /River at Tefé gauge1700 cm−1[0,]*00 cm since 7 Jul/);
  });

  test("partial pass without gauge readings nearby", () => {
    const { record, byId } = setup();
    const text = strip(panels.ledger(record, byId["2026-08-12_t169D"], null));
    assert.match(text, /^Communities—pass covers part of the area: not evaluated/);
    assert.ok(!text.includes("River at"));
  });
});

describe("dossier", () => {
  test("communities that are not monitored explain why", () => {
    const { record, byId, com } = setup();
    assert.match(panels.dossier(record, byId["2026-07-07_t161A"], com.c), /No water within 1000 m on any pass/);
    assert.match(panels.dossier(record, byId["2026-07-07_t161A"], com.d), /streams here are too narrow/);
  });

  test("monitored community: facts, confirmation note and route history", () => {
    const { record, byId, com } = setup();
    const html = panels.dossier(record, byId["2026-08-19_t097D"], com.b);
    const text = strip(html);
    assert.match(text, /At risk on 19 Aug 2026/);
    assert.match(text, /No water route on this pass\. It counts as isolated if the next pass agrees\./);
    assert.match(text, /Last linked to Tefé19 Jul 2026/);     // not 19 Aug: that pass has no route
    assert.match(text, /Measured frompier/);
    assert.equal((html.match(/<i class="/g) || []).length, 1 + 4);   // status glyph + one bar per evaluated pass
    assert.match(html, /is-current" style="height:16%"/);   // no route: the lowest bar with a result
    assert.match(text, /7 Jul 202631 Aug 2026$/);
  });
});

describe("next pass note", () => {
  test("next pass, and one due today", () => {
    const ghost = { date: "2026-11-08", track: 161, direction: "ascending" };
    assert.equal(panels.nextPassNote(undefined, "2026-11-08"), "");
    assert.equal(panels.nextPassNote(ghost, "2026-11-01"), "Next pass over the area<br><b>8 Nov 2026</b> · track 161 ↑");
    assert.match(panels.nextPassNote(ghost, "2026-11-08"), /acquired today, published within days$/);
  });
});
