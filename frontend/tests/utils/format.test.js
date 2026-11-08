import assert from "node:assert/strict";
import { describe, test } from "node:test";

import { delta, esc, fmtNum, fmtPeople, percent, widthLabel } from "../../src/utils/format.js";
import { WIDTHS } from "../helpers/fixtures.js";

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
