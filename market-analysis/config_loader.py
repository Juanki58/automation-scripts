"""Configuración aislada de market-analysis (sin dependencias de solar-telemetry)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

DEFAULTS: dict[str, Any] = {
    "bind_host": "127.0.0.1",
    "bind_port": 8502,
    "ticker": "AMBQ",
    "company_name": "Ambiq Micro",
    "history_period": "3mo",
    "refresh_seconds": 60,
    "watchlist": ["AMBQ"],
}


def load_configuration(config_path: Path | str | None = None) -> dict[str, Any]:
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    cfg = dict(DEFAULTS)

    if not path.exists():
        logger.warning("No existe %s — usando defaults (127.0.0.1:8502).", path)
        return cfg

    with open(path, encoding="utf-8-sig") as f:
        loaded = json.load(f)

    if not isinstance(loaded, dict):
        raise ValueError(f"Config inválida en {path}")

    cfg.update(loaded)
    return cfg
