import assert from "node:assert/strict";
import { describe, test } from "node:test";

import { dayMs } from "../../src/utils/dates.js";
import { gaugePath, gaugeScale, monthTicks, passTitle, recordGaps, stripGeometry, stripPoints, stripSegments,
  timeScale } from "../../src/components/passLog.js";

describe("time axis", () => {
  test("days map linearly onto the axis", () => {
    const x = timeScale(dayMs("2026-01-01"), dayMs("2026-01-11"), 0, 100);
    assert.equal(x("2026-01-01"), 0);
    assert.equal(x("2026-01-06"), 50);
    assert.equal(x("2026-01-11"), 100);
  });

  test("one tick per month after the start, January with its year", () => {
    const ticks = monthTicks(dayMs("2026-11-15"), dayMs("2027-02-01"));
    assert.deepEqual(ticks.map(t => t.iso), ["2026-12-01", "2027-01-01", "2027-02-01"]);
    assert.deepEqual(ticks.map(t => t.label), ["Dec", "Jan 2027", "Feb"]);
  });

  test("gaps of more than 60 days between passes", () => {
    const passes = ["2025-11-04", "2026-01-08", "2026-06-25", "2026-07-07"].map(date => ({ date }));
    assert.deepEqual(recordGaps(passes).map(([a, b]) => [a.date, b.date]),
      [["2025-11-04", "2026-01-08"], ["2026-01-08", "2026-06-25"]]);
    assert.deepEqual(recordGaps(passes, 100).map(([a]) => a.date), ["2026-01-08"]);
  });
});

describe("river gauge line", () => {
  test("scale in whole metres with margin", () => {
    const s = gaugeScale([780, 1825], 26, 210);
    assert.deepEqual([s.lo, s.hi], [700, 1900]);
    assert.equal(s.y(700), 210);
    assert.equal(s.y(1900), 26);
  });

  test("path breaks where readings are more than 5 days apart", () => {
    const series = [["2026-01-01", 1], ["2026-01-02", 2], ["2026-01-10", 3]];
    const path = gaugePath(series, d => dayMs(d) / 86400000 % 100, v => v * 10);
    assert.equal(path.match(/M/g).length, 2);
    assert.equal(path.match(/L/g).length, 1);
    assert.equal(gaugePath([], () => 0, () => 0), "");
  });
});

describe("strips", () => {
  test("strip width follows the closest passes, within limits", () => {
    assert.equal(stripGeometry([0, 10, 100], 26, 210).w, 6.2);
    assert.equal(stripGeometry([0, 1], 26, 210).w, 4);
    assert.equal(stripGeometry([0, 500], 26, 210).w, 12);
    assert.equal(stripGeometry([0], 26, 210).w, 12);
    const geo = stripGeometry([0, 100], 26, 210);
    assert.deepEqual([geo.h, geo.yb, geo.yt], [130, 208, 78]);
  });

  test("ascending strips lean right, descending ones left", () => {
    const geo = { w: 10, lean: 9, h: 100, yb: 200, yt: 100 };
    assert.equal(stripPoints(geo, 50, "ascending", 200, 100), "45,200 55,200 64,100 54,100");
    assert.equal(stripPoints(geo, 50, "descending", 200, 100), "45,200 55,200 46,100 36,100");
  });

  test("slices from the baseline up: isolated, at risk, connected; empty slices skipped", () => {
    const segs = stripSegments({ isolated: 1, at_risk: 0, connected: 3 }, 200, 100);
    assert.deepEqual(segs, [["isolated", 200, 175], ["connected", 175, 100]]);
    assert.deepEqual(stripSegments({ isolated: 0, at_risk: 0, connected: 0 }, 200, 100), []);
  });

  test("titles", () => {
    const pass = { date: "2026-10-23", track: 161, direction: "ascending", evaluated: true,
      counts: { isolated: 9, at_risk: 19, connected: 104 } };
    assert.equal(passTitle(pass, 801.4), "23 Oct 2026 · track 161 ascending · isolated 9, at risk 19, connected 104 · river 801 cm");
    assert.equal(passTitle({ ...pass, evaluated: false }, null), "23 Oct 2026 · track 161 ascending · partial coverage, image only");
  });
});
