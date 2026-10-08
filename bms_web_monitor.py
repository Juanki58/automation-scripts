"""Launcher de compatibilidad: el monitor vive en el repo hermano solar-telemetry."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_CANDIDATES = [
    _ROOT.parent / "solar-telemetry" / "bms_web_monitor.py",
    Path(r"C:\Users\juanc\projects\solar-telemetry\bms_web_monitor.py"),
]

_TARGET = next((p for p in _CANDIDATES if p.is_file()), None)
if _TARGET is None:
    raise SystemExit(
        "No se encontro solar-telemetry/bms_web_monitor.py.\n"
        "Clona https://github.com/Juanki58/solar-telemetry junto a este repo "
        "(esperado: ..\\solar-telemetry)."
    )

sys.path.insert(0, str(_ROOT / "api-integrations"))
sys.path.insert(0, str(_TARGET.parent))
runpy.run_path(str(_TARGET), run_name="__main__")
