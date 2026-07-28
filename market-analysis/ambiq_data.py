"""Datos de mercado para Ambiq (AMBQ) — sin dependencias de solar-telemetry."""

from __future__ import annotations

import logging
from typing import Any

import yfinance as yf

from data_processor import calculate_market_metrics

logger = logging.getLogger(__name__)


def fetch_quote(ticker: str, history_period: str = "3mo") -> dict[str, Any]:
    """Obtiene cotización, histórico y métricas para un ticker."""
    symbol = yf.Ticker(ticker)
    history = symbol.history(period=history_period, auto_adjust=True)

    if history.empty:
        raise LookupError(f"Sin datos de mercado para {ticker}")

    closes = history["Close"].dropna().tolist()
    metrics = calculate_market_metrics(closes) or {}

    last_row = history.iloc[-1]
    prev_close = float(history["Close"].iloc[-2]) if len(history) > 1 else float(last_row["Close"])
    last_price = float(last_row["Close"])
    change = last_price - prev_close
    change_pct = (change / prev_close * 100) if prev_close else 0.0

    fast = getattr(symbol, "fast_info", None)
    currency = getattr(fast, "currency", None) or "USD"

    chart = history[["Close"]].rename(columns={"Close": ticker})
    chart.index = chart.index.strftime("%Y-%m-%d")

    return {
        "ticker": ticker,
        "currency": currency,
        "last_price": round(last_price, 2),
        "change": round(change, 2),
        "change_pct": round(change_pct, 2),
        "day_high": round(float(last_row["High"]), 2),
        "day_low": round(float(last_row["Low"]), 2),
        "volume": int(last_row["Volume"]) if last_row["Volume"] == last_row["Volume"] else 0,
        "metrics": metrics,
        "chart": chart,
        "history_days": len(closes),
    }
