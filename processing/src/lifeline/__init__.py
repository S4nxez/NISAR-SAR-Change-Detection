"""
River lifeline monitor: tracks, pass by pass, whether riverside communities keep a water
connection to their hub town, using NISAR L2 GCOV radar backscatter.

Packages and modules, from the raw data to the published record:
  config      paths, remote services, the catalog schema version and the status codes
  geometry/   geo (distances, place-name folding), area (area files, lon/lat grid, area mask)
  sources/    external data: remote (Earthdata token, ranged reads), asf (NISAR GCOV passes),
              places (communities from OpenStreetMap and their water access), gauge (ANA river level)
  analysis/   radar (backscatter and the read of one pass onto the area grid),
              water (water mask, channel widths and route connectivity)
  output/     layers (images of a pass and the stored water mask), catalog (catalog.json:
              evaluation of a pass and whole-record classification)
  pipeline    the commands: update, reevaluate, watch, communities
  cli         the command line (`river-monitor`, or `python -m lifeline`)
"""
