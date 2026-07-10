"""Launcher de compatibilidad: el monitor vive en solar-telemetry/."""

import runpy
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_TARGET = _ROOT / "solar-telemetry" / "bms_web_monitor.py"

sys.path.insert(0, str(_ROOT / "api-integrations"))
sys.path.insert(0, str(_TARGET.parent))

runpy.run_path(str(_TARGET), run_name="__main__")
