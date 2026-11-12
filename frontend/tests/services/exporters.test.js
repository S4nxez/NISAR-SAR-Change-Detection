import assert from "node:assert/strict";
import { describe, test } from "node:test";

import { csvCell, exportName, toCsv, toGeojson } from "../../src/services/exporters.js";
import { buildRecord, communityRows } from "../../src/models/record.js";
import { catalog, WIDTHS } from "../helpers/fixtures.js";

const rowsOn = id => {
  const record = buildRecord(catalog());
  const pass = record.passes.find(p => p.id === id);
  return { pass, rows: communityRows(record, pass, null) };
};

describe("csv cells", () => {
  test("numbers raw, text quoted with doubled quotes, nothing for empty values", () => {
    assert.equal(csvCell(-3.25), "-3.25");
    assert.equal(csvCell('Vila "Nova", AM'), '"Vila ""Nova"", AM"');
    assert.equal(csvCell(null), "");
    assert.equal(csvCell(undefined), "");
  });

  test("text a spreadsheet would run as a formula is defused", () => {
    assert.equal(csvCell("=HYPERLINK(\"x\")"), '"\'=HYPERLINK(""x"")"');
    assert.equal(csvCell("+1"), '"\'+1"');
    assert.equal(csvCell("@cmd"), '"\'@cmd"');
  });
});

describe("exports of a day", () => {
  test("CSV with a BOM, a header and one row per monitored community", () => {
    const { pass, rows } = rowsOn("2026-08-31_t097D");
    const csv = toCsv(rows, pass, WIDTHS);
    assert.ok(csv.startsWith("\uFEFFcommunity,place,lat,lon,status,"));
    const lines = csv.slice(1).split("\n");
    assert.equal(lines.length, 3);
    assert.equal(lines[1], '"Alpha","village",-3.3,-64.6,"at_risk","40–60 m",25,"place","2026-08-31",97');
    assert.equal(lines[2], '"Bravo <b>","hamlet",-3.4,-64.7,"isolated","no route",160,"pier","2026-08-31",97');
  });

  test("GeoJSON with the same values", () => {
    const { pass, rows } = rowsOn("2026-07-19_t161A");
    const fc = JSON.parse(toGeojson(rows, pass, WIDTHS));
    assert.equal(fc.type, "FeatureCollection");
    assert.deepEqual(fc.features[1], { type: "Feature", geometry: { type: "Point", coordinates: [-64.7, -3.4] },
      properties: { name: "Bravo <b>", place: "hamlet", status: "at_risk", route_narrowest: "< 40 m", nearest_water_m: 30,
        measured_from: "pier", pass_date: "2026-07-19", track: 161 } });
  });

  test("file names", () => {
    assert.equal(exportName("tefe", { date: "2026-10-23" }, "csv"), "communities_tefe_2026-10-23.csv");
  });
});
