// Guards for every page of the frontend. The app is served under a path prefix (/terra-pulse/, /terra-pulse-dev/ and
// /terra-pulse-dev/pr-<N>/ for pull request previews), so a local URL starting with "/" escapes the app and 404s.
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { describe, test } from "node:test";
import { fileURLToPath } from "node:url";

const FRONTEND = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function files(dir, exts) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap(e => {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) return ["node_modules", "tests", "public"].includes(e.name) ? [] : files(p, exts);
    return exts.includes(path.extname(e.name)) ? [p] : [];
  });
}

const pages = fs.readdirSync(FRONTEND).filter(f => f.endsWith(".html"));
const ROOT_ABSOLUTE = [
  /\b(?:href|src|action)\s*=\s*["']\/(?!\/)/g,           // href="/x" (but not protocol-relative //cdn)
  /\bfetch\(\s*["'`]\/(?!\/)/g,                           // fetch("/api/...")
  /\burl\(\s*["']?\/(?!\/)/g,                             // CSS url(/img.png)
  /\bnew URL\(\s*["'`]\/(?!\/)/g,                         // new URL("/x", ...)
];

describe("pages", () => {
  test("there are pages to check", () => assert.ok(pages.includes("index.html")));

  for (const page of pages) {
    test(`${page} declares its icon, so browsers do not ask for /favicon.ico at the site root`, () => {
      const html = fs.readFileSync(path.join(FRONTEND, page), "utf8");
      const icons = [...html.matchAll(/<link\b[^>]*\brel=["'](?:shortcut )?icon["'][^>]*>/g)].map(m => m[0]);
      assert.ok(icons.length, "no <link rel=\"icon\">");
      for (const link of icons) {
        const href = link.match(/href=["']([^"']+)["']/)?.[1];
        assert.ok(href && !href.startsWith("/"), `${link} must use a relative href`);
        assert.ok(fs.existsSync(path.join(FRONTEND, href)), `${href} does not exist`);
      }
    });
  }

  test("no local URL is absolute from the site root", () => {
    const offenders = [];
    for (const file of [...pages.map(p => path.join(FRONTEND, p)), ...files(path.join(FRONTEND, "src"), [".js", ".css", ".html"])]) {
      const lines = fs.readFileSync(file, "utf8").split("\n");
      lines.forEach((line, i) => {
        for (const re of ROOT_ABSOLUTE) {
          if (line.match(re)) offenders.push(`${path.relative(FRONTEND, file)}:${i + 1}: ${line.trim()}`);
        }
      });
    }
    assert.deepEqual(offenders, []);
  });

  test("the patterns catch what they are meant to catch", () => {
    const hits = s => ROOT_ABSOLUTE.some(re => s.match(re));
    assert.ok(hits('<link rel="icon" href="/favicon.ico">'));
    assert.ok(hits('fetch("/api/sites")'));
    assert.ok(hits("background: url(/img/a.png)"));
    assert.ok(!hits('<script src="https://unpkg.com/x.js"></script>'));
    assert.ok(!hits('<script src="//cdn.example/x.js"></script>'));
    assert.ok(!hits('fetch(new URL("../api/sites", import.meta.url))'));
    assert.ok(!hits('href="./favicon.svg"'));
  });
});
