import json
from datetime import timedelta
from pathlib import Path

from homeassistant.const import Platform


DOMAIN = "aucorsa"
PLATFORMS = [Platform.SENSOR, Platform.BUTTON]

CONF_LINE = "line"
CONF_STOP_ID = "stop_id"
CONF_INTERNAL_LINE_ID = "internal_line_id"
CONF_SCAN_INTERVAL_SECONDS = "scan_interval_seconds"

DEFAULT_SCAN_INTERVAL_SECONDS = 60
MIN_SCAN_INTERVAL_SECONDS = 30
MAX_SCAN_INTERVAL_SECONDS = 300
DEFAULT_SCAN_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL_SECONDS)

REQUEST_GAP_SECONDS = 5.0

DATA_API = "api"

ATTRIBUTION = "Data provided by AUCORSA"
API_CONFIGURATION_URL = "https://aucorsa.es/tiempos-de-paso/"
MANUFACTURER = "AUCORSA"


def _load_integration_version() -> str:
    manifest_path = Path(__file__).with_name("manifest.json")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        version = str(manifest["version"]).strip()
        if version:
            return version
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return "0.0.0"


INTEGRATION_VERSION = _load_integration_version()
