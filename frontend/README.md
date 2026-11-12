# River Lifeline — frontend

Mobile-first vanilla JavaScript page of the NASA Space Apps Challenge 2026 project: for every NISAR pass, which
riverside communities still have a water route to their hub town. No framework and no build step: nginx serves the
files as they are, under a path prefix, so every URL is relative.

## Data

The page only talks to the backend, on the same origin: `api/monitor/areas/<area>` (the pass record) and
`api/monitor/areas/<area>/passes/<pass>/<layer>` (its images). The record is written by the monitor worker
(`processing/`) and served by the backend; see `docs/river-monitor.md` for the API and the catalog contract.
`index.html?area=<id>` picks another area.

## Run locally

`make up` (the development environment, `tools/dev`) serves the folder with hot reload and forwards `/api` to the
backend; in the stack, Caddy does the same. Start the backend with `MONITOR_DATA_DIR` pointing at a record built by
`river-monitor update` (`processing/output` by default). Opening the pages with `file://` does not work: the app
uses JavaScript modules.

## Structure

```
index.html            page shell
src/
  main.js             entry point: page state, user interface events and boot (the only module that touches the whole page)
  config.js           constants: area id, refresh and replay timings, status labels and colours
  services/
    monitorApi.js     the backend's API: URLs, catalog request and its errors
    exporters.js      CSV and GeoJSON of the selected day
  models/
    record.js         questions asked to the pass record: status of a community, pass for a day, next passes, roster rows
  components/
    panels.js         HTML of the headline, plate, map key, roster, ledger and dossier (pure functions returning strings)
    passLog.js        the SVG pass log; its geometry helpers are pure
    mapView.js        the Leaflet map (Leaflet is passed in)
  utils/
    dates.js          UTC days
    format.js         escaping and text formatting
  styles/
    main.css          the page's styles
tests/                mirrors src/ (helpers/ holds the jsdom set-up and the catalog fixture)
```

## Tests

```bash
npm ci      # once: installs jsdom, the only (dev) dependency
npm test    # node --test "tests/**/*.test.js"
```

Unit tests use Node's built-in `node:test` (Node 22+); the page tests load `index.html` in `jsdom` with a stand-in
for Leaflet and for the backend. `tests/pages.test.js` checks every page: it must declare its icon and no local URL
may start with `/`, because the app is served under a path prefix (`/terra-pulse/`, `/terra-pulse-dev/`,
`/terra-pulse-dev/pr-<N>/`). The CI runs them before building the images; `tests/`, `package.json` and
`package-lock.json` are left out of the nginx image (`.dockerignore`).

## Notes

- The basemap uses OpenStreetMap tiles and Leaflet and Google Fonts load from CDNs: the page needs an internet
  connection.
- Thresholds are not validated against field data yet; see the limits in `docs/river-monitor.md`.
