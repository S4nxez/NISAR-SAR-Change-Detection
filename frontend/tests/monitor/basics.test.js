import assert from "node:assert/strict";
import { describe, test } from "node:test";

import { areaFromSearch, dataUrl, DEFAULT_AREA } from "../../src/monitor/config.js";
import { addDays, daysBetween, fmtDay, fmtShort, isIsoDay, todayIso, toIso } from "../../src/monitor/dates.js";
import { delta, esc, fmtNum, fmtPeople, percent, widthLabel } from "../../src/monitor/format.js";
import { WIDTHS } from "./fixtures.js";

describe("config", () => {
  test("area from the query string", () => {
    assert.equal(areaFromSearch("?area=manaus_2"), "manaus_2");
    assert.equal(areaFromSearch(""), DEFAULT_AREA);
    assert.equal(areaFromSearch("?area="), DEFAULT_AREA);
  });

  test("an area that is not a plain id cannot leave the data folder", () => {
    for (const bad of ["?area=../../etc", "?area=a/b", "?area=%2e%2e", "?area=<x>"]) {
      assert.equal(areaFromSearch(bad), DEFAULT_AREA, bad);
    }
  });

  test("data URL is relative to the page, so it works under any path prefix", () => {
    assert.equal(dataUrl("tefe"), "./public/data/monitor/tefe/");
  });
});

describe("dates", () => {
  test("days in UTC across months and years", () => {
    assert.equal(addDays("2026-12-25", 12), "2027-01-06");
    assert.equal(addDays("2026-03-01", -1), "2026-02-28");
    assert.equal(daysBetween("2026-07-19", "2026-08-01"), 13);
    assert.equal(daysBetween("2026-08-01", "2026-07-19"), -13);
    assert.equal(toIso(new Date(Date.UTC(2026, 9, 23, 23, 59))), "2026-10-23");
    assert.equal(todayIso(new Date(Date.UTC(2026, 10, 8, 1))), "2026-11-08");
  });

  test("only real days written as YYYY-MM-DD are days", () => {
    assert.ok(isIsoDay("2026-10-23"));
    assert.ok(isIsoDay("2028-02-29"));
    for (const bad of ["2026-02-30", "2026-13-01", "2026-1-5", "garbage", "", null, undefined, 20261023]) {
      assert.ok(!isIsoDay(bad), String(bad));
    }
  });

  test("display formats", () => {
    assert.equal(fmtDay("2026-10-23"), "23 Oct 2026");
    assert.equal(fmtShort("2026-10-23"), "23 Oct");
  });
});

describe("format", () => {
  test("escapes HTML", () => {
    assert.equal(esc(`<a href="x">Tom & 'Jerry'</a>`), "&lt;a href=&quot;x&quot;&gt;Tom &amp; &#39;Jerry&#39;&lt;/a&gt;");
    assert.equal(esc(42), "42");
  });

  test("route width classes", () => {
    assert.equal(widthLabel(null, WIDTHS), "no route");
    assert.equal(widthLabel(undefined, WIDTHS), "no route");
    assert.equal(widthLabel(0, WIDTHS), "< 40 m");
    assert.equal(widthLabel(60, WIDTHS), "60–100 m");
    assert.equal(widthLabel(400, WIDTHS), "≥ 400 m");
  });

  test("signed changes", () => {
    assert.equal(delta(2), "<b>+2</b>");
    assert.equal(delta(-1.25, " cm"), "<b>−1.3 cm</b>");
    assert.equal(delta(0.04), "no change");
    assert.equal(delta(null), "");
    assert.equal(delta(NaN), "");
  });

  test("numbers", () => {
    assert.equal(fmtNum(1521.44), "1,521.4");
    assert.equal(fmtPeople(12000), "12,000");
    assert.equal(percent(0.8896), 89);
  });
});
