import assert from "node:assert/strict";
import { describe, test } from "node:test";

import { areaUrl, CatalogError, fetchCatalog, layerUrl } from "../../src/services/monitorApi.js";

describe("URLs", () => {
  test("are relative to the page, so they work under any path prefix", () => {
    assert.equal(areaUrl("tefe"), "./api/monitor/areas/tefe");
    assert.equal(layerUrl("tefe", { id: "2026-10-23_t161A" }, "radar.webp"),
      "./api/monitor/areas/tefe/passes/2026-10-23_t161A/radar.webp");
  });

  test("a pass without the file has no URL", () => {
    assert.equal(layerUrl("tefe", { id: "2026-10-23_t161A" }, undefined), null);
  });

  test("names are encoded, so they can never add a path segment", () => {
    assert.equal(areaUrl("../x"), "./api/monitor/areas/..%2Fx");
    assert.equal(layerUrl("a", { id: "b/c" }, "d?e"), "./api/monitor/areas/a/passes/b%2Fc/d%3Fe");
  });
});

describe("fetchCatalog", () => {
  test("asks the backend for the area's catalog and revalidates it every time", async () => {
    const calls = [];
    const fetchFn = async (url, options) => {
      calls.push({ url, options });
      return { ok: true, status: 200, json: async () => ({ passes: [] }) };
    };
    assert.deepEqual(await fetchCatalog("tefe", fetchFn), { passes: [] });
    assert.deepEqual(calls, [{ url: "./api/monitor/areas/tefe",
      options: { cache: "no-cache", headers: { Accept: "application/json" } } }]);
  });

  for (const [status, reason] of [[404, "missing"], [503, "unsupported"], [500, "unavailable"], [502, "unavailable"]]) {
    test(`HTTP ${status} is a CatalogError with reason ${reason}`, async () => {
      const fetchFn = async () => ({ ok: false, status });
      await assert.rejects(fetchCatalog("tefe", fetchFn), e => e instanceof CatalogError && e.status === status &&
        e.reason === reason && e.message.includes(String(status)));
    });
  }

  test("a network failure is passed on as it is", async () => {
    await assert.rejects(fetchCatalog("tefe", async () => { throw new TypeError("offline"); }), /offline/);
  });

  test("uses the browser's fetch by default", async t => {
    t.mock.method(globalThis, "fetch", async () => ({ ok: true, json: async () => ({ id: 1 }) }));
    assert.deepEqual(await fetchCatalog("tefe"), { id: 1 });
    assert.equal(globalThis.fetch.mock.calls[0].arguments[0], "./api/monitor/areas/tefe");
  });
});
