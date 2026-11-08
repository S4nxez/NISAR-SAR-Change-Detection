"""Paths, remote services and the constants shared by every module."""
import os
import time

# processing/ in a source checkout (src/lifeline/config.py is three levels below it)
PROCESSING_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def areas_dir(environ=os.environ):
    """Folder of the area files: MONITOR_AREAS_DIR, else processing/areas of the source checkout."""
    return environ.get("MONITOR_AREAS_DIR") or os.path.join(PROCESSING_DIR, "areas")


def data_dir(environ=os.environ):
    """Folder the published record is written to: MONITOR_DATA_DIR (the monitor_data volume in the stack, which the
    backend serves under api/monitor), else processing/output of the source checkout (not tracked by git)."""
    return environ.get("MONITOR_DATA_DIR") or os.path.join(PROCESSING_DIR, "output")


AREAS_DIR = areas_dir()
OUT_ROOT = data_dir()

ASF_SEARCH = "https://api.daac.asf.alaska.edu/services/search/param"
ANA_TELEMETRY = "http://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicos"
OVERPASS_MIRRORS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
USER_AGENT = "nisar-river-monitor/0.1 (NASA Space Apps 2026 prototype)"

# Version of the catalog.json layout. The backend refuses to serve a catalog of another version
# (MonitorRecordService.SCHEMA_VERSION): bump both when the layout changes in a way readers notice.
SCHEMA_VERSION = 1

# Status of a community on one pass, as stored in catalog.json. The catalog carries this table
# ("status_codes"), so readers take the names from it instead of repeating the codes.
STATUS = {"no_data": 0, "connected": 1, "at_risk": 2, "isolated": 3}
STATUS_NAME = {code: name for name, code in STATUS.items()}


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)
