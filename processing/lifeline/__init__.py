"""
River lifeline monitor: tracks, pass by pass, whether riverside communities keep a water
connection to their hub town, using NISAR L2 GCOV radar backscatter.

Modules, from the raw data to the published record:
  config    paths, remote services and the status codes shared by every module
  geo       distances and place-name folding
  area      area files, the lon/lat grid and the area mask
  remote    Earthdata token and ranged reads of remote products
  asf       search of NISAR GCOV passes at the ASF DAAC
  radar     backscatter helpers and the read of one pass onto the area grid
  water     water mask, channel widths and route connectivity
  layers    images of a pass (radar, water, change) and the stored water mask
  places    communities from OpenStreetMap and their water access
  gauge     official river level (ANA telemetry)
  catalog   catalog.json: evaluation of a pass and whole-record classification
  pipeline  the commands: update, reevaluate, watch, communities

The command line is processing/river_monitor.py.
"""
