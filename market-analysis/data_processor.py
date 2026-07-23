"""
Procesador de series de precios de mercado.

Limpia feeds crudos y calcula métricas básicas (media, volatilidad, extremos).
"""

from __future__ import annotations

import logging
import math
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
)
logger = logging.getLogger(__name__)


def calculate_market_metrics(prices: list[Any]) -> dict[str, float | int] | None:
    """
    Analiza precios crudos y calcula métricas de mercado.

    Descarta valores no numéricos del feed de entrada.
    """
    if not prices:
        logger.warning("Feed de precios vacío.")
        return None

    clean_prices = [float(p) for p in prices if isinstance(p, (int, float))]
    total_days = len(clean_prices)
    if total_days == 0:
        logger.warning("Ningún valor numérico válido tras la limpieza.")
        return None

    average_price = sum(clean_prices) / total_days
    variance = sum((x - average_price) ** 2 for x in clean_prices) / total_days
    volatility = math.sqrt(variance)

    return {
        "total_records": total_days,
        "average_price": round(average_price, 2),
        "volatility": round(volatility, 2),
        "highest_price": max(clean_prices),
        "lowest_price": min(clean_prices),
    }


if __name__ == "__main__":
    # Feed simulado de una API de mercado (incluye un valor inválido a propósito)
    raw_feed: list[Any] = [105.4, 106.2, 104.8, 107.5, 109.1, "error_string", 108.3]

    logger.info("Iniciando limpieza y cálculo de métricas de mercado")
    results = calculate_market_metrics(raw_feed)

    if results:
        logger.info("Procesados %s registros válidos.", results["total_records"])
        print(f"Precio medio: ${results['average_price']}")
        print(f"Volatilidad: {results['volatility']}")
        print(
            f"Máximo: ${results['highest_price']} | Mínimo: ${results['lowest_price']}"
        )
    else:
        logger.error("Falló el procesamiento. Revisa la estructura del feed.")
