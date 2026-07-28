"""Launcher: monitor Ambiq en market-analysis/ (puerto 8502, no mezclar con BMS)."""

import runpy
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_TARGET = _ROOT / "market-analysis" / "ambiq_monitor.py"

sys.path.insert(0, str(_TARGET.parent))
runpy.run_path(str(_TARGET), run_name="__main__")
