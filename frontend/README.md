# SAR Observatory — frontend starter

Mobile-first, componentised vanilla JavaScript interface for the NASA Space Apps Challenge 2026 **Dancing with the SARs** concept.

## Run locally
Because the app uses JavaScript modules and fetches a local GeoJSON file, serve the folder over HTTP (do not open `index.html` with `file://`).

```bash
python -m http.server 8080
```
Open `http://localhost:8080`.

## Structure
- `index.html` — semantic page shell and visible dashboard regions.
- `src/app.js` — app entry point and selected-site state.
- `src/data/sites.js` — centralised sample sites and chart series.
- `src/components/` — site list, interpretation panel, trend chart.
- `src/services/mapService.js` — Leaflet map and markers.
- `src/styles/main.css` — design tokens, layout, responsive styles.
- `public/data/world.geo.json` — retained source GeoJSON asset, available for future overlays.

## Important
- **All values and detections are illustrative UI demo data**, not live Sentinel-1 data and not scientific findings.
- The map uses CARTO basemap tiles and requires an internet connection. Chart.js, Leaflet and Google Fonts are loaded from CDNs.
- No framework/build step is required. When the project grows, a bundler such as Vite can be added without changing the component boundaries.

## Suggested next implementation steps
1. Replace `src/data/sites.js` with a validated API response from a processing pipeline.
2. Add paired SAR acquisition previews (before/after) and metadata: acquisition date, orbit direction, polarisation, and processing level.
3. Define change detection thresholds and explain uncertainty with validated domain-specific methodology.
4. Add accessible map/list synchronisation and a clear distinction between model confidence and physical event certainty.
