import assert from "node:assert/strict";
import { describe, test } from "node:test";

import { buildRecord, communityRows, gaugeOn, hasRoute, isUnconfirmed, lastLinked, nextPasses, passForDay,
  previousEvaluated, routeHistory, statusOf, stepPass, visibleRows } from "../../src/models/record.js";
import { catalog } from "../helpers/fixtures.js";

const setup = () => {
  const record = buildRecord(catalog());
  const byId = Object.fromEntries(record.cat.passes.map(p => [p.id, p]));
  const com = Object.fromEntries(record.cat.communities.map(c => [c.id, c]));
  return { record, byId, com };
};
const ids = passes => passes.map(p => p?.id ?? null);

describe("buildRecord", () => {
  test("keeps shown passes, evaluated ones, the gauge by day and the monitored communities", () => {
    const { record } = setup();
    assert.deepEqual(ids(record.passes), ["2026-07-07_t161A", "2026-07-19_t161A", "2026-08-12_t169D",
      "2026-08-19_t097D", "2026-08-31_t097D"]);
    assert.deepEqual(ids(record.evaluated), ["2026-07-07_t161A", "2026-07-19_t161A", "2026-08-19_t097D", "2026-08-31_t097D"]);
    assert.equal(record.gauge.get("2026-08-19"), 1300);
    assert.deepEqual(record.monitored.map(c => c.id), ["a", "b"]);
  });

  test("a catalog without gauge gives an empty series", () => {
    const cat = catalog();
    delete cat.gauge;
    assert.equal(buildRecord(cat).gauge.size, 0);
  });
});

describe("status of a community", () => {
  test("not monitored communities show their class", () => {
    const { record, byId, com } = setup();
    assert.equal(statusOf(record, byId["2026-07-07_t161A"], com.c), "inland");
    assert.equal(statusOf(record, byId["2026-07-07_t161A"], com.d), "unresolved");
  });

  test("codes, missing results and unconfirmed isolation", () => {
    const { record, byId, com } = setup();
    assert.equal(statusOf(record, byId["2026-07-07_t161A"], com.a), "connected");
    assert.equal(statusOf(record, byId["2026-07-19_t161A"], com.b), "at_risk");
    assert.equal(statusOf(record, byId["2026-08-19_t097D"], com.b), "at_risk");      // isolated once: to confirm
    assert.ok(isUnconfirmed(byId["2026-08-19_t097D"], com.b));
    assert.equal(statusOf(record, byId["2026-08-31_t097D"], com.b), "isolated");
    assert.equal(statusOf(record, byId["2026-08-12_t169D"], com.a), "no_data");
    assert.equal(statusOf(record, null, com.a), "no_data");
  });

  test("hasRoute is about the water route, not the confirmation", () => {
    const { record, byId, com } = setup();
    assert.ok(hasRoute(record, byId["2026-07-19_t161A"], com.b));
    assert.ok(!hasRoute(record, byId["2026-08-19_t097D"], com.b));
    assert.ok(!hasRoute(record, byId["2026-08-12_t169D"], com.a));
  });
});

describe("status codes", () => {
  test("are named by the catalog's own table, not by the page", () => {
    const cat = catalog();
    cat.status_codes = { 0: "no_data", 1: "isolated", 2: "at_risk", 3: "connected" };
    cat.passes[1].unconfirmed = [];
    const record = buildRecord(cat);
    const pass = record.cat.passes[1], a = record.cat.communities[0];
    assert.equal(statusOf(record, pass, a), "isolated");       // code 1 in this catalog
    assert.ok(!hasRoute(record, pass, a));
    assert.equal(record.statusName(3), "connected");
  });

  test("an unknown code or a catalog without the table reads as no data", () => {
    const cat = catalog();
    delete cat.status_codes;
    const record = buildRecord(cat);
    assert.equal(record.statusName(1), "no_data");
    assert.equal(statusOf(record, record.cat.passes[1], record.cat.communities[0]), "no_data");
    assert.equal(buildRecord(catalog()).statusName(9), "no_data");
  });
});

describe("moving through the record", () => {
  test("previous evaluated pass", () => {
    const { record, byId } = setup();
    assert.equal(previousEvaluated(record, byId["2026-08-19_t097D"]).id, "2026-07-19_t161A");
    assert.equal(previousEvaluated(record, byId["2026-07-07_t161A"]), null);
    assert.equal(previousEvaluated(record, byId["2026-08-12_t169D"]), null);
  });

  test("pass for a day: latest evaluated on or before it, else the first one", () => {
    const { record } = setup();
    assert.equal(passForDay(record, "2026-08-18").id, "2026-07-19_t161A");   // skips the partial 12 Aug pass
    assert.equal(passForDay(record, "2026-08-19").id, "2026-08-19_t097D");
    assert.equal(passForDay(record, "2027-01-01").id, "2026-08-31_t097D");
    assert.equal(passForDay(record, "2026-01-01").id, "2026-07-07_t161A");
  });

  test("pass for a day without evaluated passes is the latest pass", () => {
    const cat = catalog();
    cat.passes = cat.passes.filter(p => !p.counts);
    assert.equal(passForDay(buildRecord(cat), "2026-09-01").id, "2026-08-12_t169D");
  });

  test("step between evaluated passes and stay at the ends", () => {
    const { record, byId } = setup();
    assert.equal(stepPass(record, byId["2026-07-19_t161A"], 1).id, "2026-08-19_t097D");   // over the partial pass
    assert.equal(stepPass(record, byId["2026-08-19_t097D"], -1).id, "2026-07-19_t161A");
    assert.equal(stepPass(record, byId["2026-07-07_t161A"], -1).id, "2026-07-07_t161A");
    assert.equal(stepPass(record, byId["2026-08-31_t097D"], 1).id, "2026-08-31_t097D");
  });

  test("step from a partial pass goes to the nearest evaluated pass on that side", () => {
    const { record, byId } = setup();
    assert.equal(stepPass(record, byId["2026-08-12_t169D"], -1).id, "2026-07-19_t161A");
    assert.equal(stepPass(record, byId["2026-08-12_t169D"], 1).id, "2026-08-19_t097D");
  });

  test("step without evaluated passes does nothing", () => {
    const cat = catalog();
    cat.passes = cat.passes.filter(p => !p.counts);
    const record = buildRecord(cat);
    assert.equal(stepPass(record, record.passes[0], 1), null);
  });
});

describe("next passes", () => {
  test("12 days after the last pass of each evaluated track, on or after today, soonest first", () => {
    const { record } = setup();
    assert.deepEqual(nextPasses(record, "2026-09-01"), [
      { date: "2026-09-05", track: 161, direction: "ascending" },   // 19 Jul + 4 x 12 days
      { date: "2026-09-12", track: 97, direction: "descending" },
    ]);
  });

  test("a pass due today is listed, tracks never evaluated are not", () => {
    const { record } = setup();
    const next = nextPasses(record, "2026-09-12");
    assert.equal(next[0].date, "2026-09-12");
    assert.ok(!next.some(g => g.track === 169));
  });
});

describe("river gauge", () => {
  test("reading of the day or the nearest one within 3 days, the earlier day first", () => {
    const gauge = new Map([["2026-07-06", 1800], ["2026-07-08", 1790]]);
    assert.equal(gaugeOn(gauge, "2026-07-06"), 1800);
    assert.equal(gaugeOn(gauge, "2026-07-07"), 1800);
    assert.equal(gaugeOn(gauge, "2026-07-11"), 1790);
    assert.equal(gaugeOn(gauge, "2026-07-12"), null);
  });
});

describe("roster rows", () => {
  test("one row per monitored community, with the previous status when it changed", () => {
    const { record, byId } = setup();
    const rows = communityRows(record, byId["2026-07-19_t161A"], byId["2026-07-07_t161A"]);
    assert.deepEqual(rows.map(r => [r.c.id, r.s, r.was]), [["a", "connected", null], ["b", "at_risk", "connected"]]);
    assert.deepEqual(rows[1].r, [2, 0, 30]);
  });

  test("no previous status without a previous pass or across no data", () => {
    const { record, byId } = setup();
    assert.ok(communityRows(record, byId["2026-07-07_t161A"], null).every(r => r.was === null));
    const rows = communityRows(record, byId["2026-08-12_t169D"], byId["2026-07-19_t161A"]);
    assert.ok(rows.every(r => r.s === "no_data" && r.was === null));
  });

  test("filter, search and order: most severe and narrowest first", () => {
    const { record, byId } = setup();
    const rows = communityRows(record, byId["2026-08-31_t097D"], byId["2026-08-19_t097D"]);
    assert.deepEqual(visibleRows(rows).map(r => r.c.id), ["b", "a"]);
    assert.deepEqual(visibleRows(rows, { filter: "isolated" }).map(r => r.c.id), ["b"]);
    assert.deepEqual(visibleRows(rows, { filter: "changed" }).map(r => r.c.id), ["b", "a"]);
    assert.deepEqual(visibleRows(rows, { query: "  ALP " }).map(r => r.c.id), ["a"]);
    assert.deepEqual(visibleRows(rows, { query: "zulu" }), []);
  });

  test("equal status sorts by route width, then by name", () => {
    const row = (name, w) => ({ c: { name }, s: "at_risk", r: [2, w, 10], was: null });
    assert.deepEqual(visibleRows([row("b", 40), row("c", 0), row("a", 40)]).map(r => r.c.name), ["c", "a", "b"]);
  });
});

describe("history of a community", () => {
  test("result on every evaluated pass", () => {
    const { record, com } = setup();
    assert.deepEqual(routeHistory(record, com.b).map(h => h.s), ["connected", "at_risk", "at_risk", "isolated"]);
  });

  test("last link to the hub ignores passes with no route, even unconfirmed ones", () => {
    const { record, com } = setup();
    assert.equal(lastLinked(record, com.b, "2026-08-31").id, "2026-07-19_t161A");
    assert.equal(lastLinked(record, com.b, "2026-07-10").id, "2026-07-07_t161A");
    assert.equal(lastLinked(record, com.b, "2026-01-01"), null);
    assert.equal(lastLinked(record, com.a, "2026-08-31").id, "2026-08-31_t097D");
  });
});
