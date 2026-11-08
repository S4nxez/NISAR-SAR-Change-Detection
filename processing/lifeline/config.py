"""Paths, remote services and the constants shared by every module."""
import os
import time

PROCESSING_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(PROCESSING_DIR)
AREAS_DIR = os.path.join(PROCESSING_DIR, "areas")
OUT_ROOT = os.path.join(ROOT, "frontend", "public", "data", "monitor")

ASF_SEARCH = "https://api.daac.asf.alaska.edu/services/search/param"
ANA_TELEMETRY = "http://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicos"
OVERPASS_MIRRORS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
USER_AGENT = "nisar-river-monitor/0.1 (NASA Space Apps 2026 prototype)"

# Status of a community on one pass, as stored in catalog.json (the frontend reads the same codes)
STATUS = {"no_data": 0, "connected": 1, "at_risk": 2, "isolated": 3}
STATUS_NAME = {code: name for name, code in STATUS.items()}


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)
