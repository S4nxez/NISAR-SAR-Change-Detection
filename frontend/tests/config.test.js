import assert from "node:assert/strict";
import { describe, test } from "node:test";

import { areaFromSearch, DEFAULT_AREA, LABEL, LINKED_STATUSES, ROUTE_STATUSES } from "../src/config.js";

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

  test("status names cover every route status and the linked ones", () => {
    assert.deepEqual(ROUTE_STATUSES, ["connected", "at_risk", "isolated"]);
    assert.ok(LINKED_STATUSES.every(s => ROUTE_STATUSES.includes(s)));
    for (const s of [...ROUTE_STATUSES, "no_data", "inland", "unresolved"]) assert.ok(LABEL[s], s);
  });
});
