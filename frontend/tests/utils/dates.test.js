import assert from "node:assert/strict";
import { describe, test } from "node:test";

import { addDays, daysBetween, fmtDay, fmtShort, isIsoDay, todayIso, toIso } from "../../src/utils/dates.js";

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
