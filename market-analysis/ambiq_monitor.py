"""
Monitor de mercado — Ambiq (AMBQ).

Servicio independiente del BMS solar. Por defecto escucha en 127.0.0.1:8502
(solo este PC), separado del monitor de planta en :8501.
"""

from __future__ import annotations

import time
from datetime import datetime

import streamlit as st

from ambiq_data import fetch_quote
from config_loader import load_configuration

COLOR_BG = "#0b0f19"
COLOR_SURFACE = "#151b2e"
COLOR_BORDER = "#3d4f7c"
COLOR_TEXT = "#e8ecf4"
COLOR_MUTED = "#8b9bb8"
COLOR_UP = "#00c853"
COLOR_DOWN = "#ff5252"
COLOR_ACCENT = "#7c4dff"


def inject_theme():
    st.markdown(
        f"""
        <style>
            .stApp {{
                background: {COLOR_BG};
                color: {COLOR_TEXT};
            }}
            .market-header {{
                font-size: 0.72rem;
                font-weight: 800;
                letter-spacing: 0.14em;
                text-transform: uppercase;
                color: {COLOR_ACCENT};
                margin-bottom: 0.25rem;
            }}
            .market-title {{
                font-size: 2rem;
                font-weight: 800;
                margin: 0 0 0.35rem 0;
            }}
            .market-sub {{
                color: {COLOR_MUTED};
                font-size: 0.92rem;
                margin-bottom: 1.2rem;
            }}
            .metric-card {{
                background: {COLOR_SURFACE};
                border: 1px solid {COLOR_BORDER};
                border-radius: 14px;
                padding: 1rem 1.1rem;
                margin-bottom: 0.6rem;
            }}
            .metric-label {{
                color: {COLOR_MUTED};
                font-size: 0.78rem;
                text-transform: uppercase;
                letter-spacing: 0.08em;
            }}
            .metric-value {{
                font-size: 1.8rem;
                font-weight: 800;
                margin-top: 0.35rem;
            }}
            .isolation-banner {{
                background: #1a1433;
                border: 1px solid {COLOR_ACCENT};
                border-radius: 10px;
                padding: 0.65rem 0.9rem;
                font-size: 0.82rem;
                color: {COLOR_MUTED};
                margin-bottom: 1rem;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_metric(label: str, value: str, color: str = COLOR_TEXT):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value" style="color:{color};">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main():
    st.set_page_config(
        page_title="Ambiq — Market Monitor",
        page_icon="📈",
        layout="wide",
    )

    cfg = load_configuration()
    inject_theme()

    st.markdown('<p class="market-header">Market Analysis</p>', unsafe_allow_html=True)
    st.markdown('<h1 class="market-title">Ambiq Micro (AMBQ)</h1>', unsafe_allow_html=True)
    st.markdown(
        f'<p class="market-sub">Seguimiento bursátil · Puerto {cfg["bind_port"]} · '
        f'Host {cfg["bind_host"]} · Sin enlace al BMS solar</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="isolation-banner">'
        f'📌 Este panel es <strong>solo mercado</strong>. '
        f'El monitor de baterías LiFePO4 vive en <strong>otro servicio</strong> '
        f'(<code>0.0.0.0:8501</code> · solar-telemetry). '
        f'Ambiq usa <code>{cfg["bind_host"]}:{cfg["bind_port"]}</code>.</div>',
        unsafe_allow_html=True,
    )

    ticker = cfg.get("ticker", "AMBQ")
    try:
        quote = fetch_quote(ticker, cfg.get("history_period", "3mo"))
    except Exception as exc:
        st.error(f"No se pudo cargar {ticker}: {exc}")
        st.caption("Comprueba conexión a internet y que el ticker sea correcto.")
        return

    trend_color = COLOR_UP if quote["change"] >= 0 else COLOR_DOWN
    sign = "+" if quote["change"] >= 0 else ""

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric("Último precio", f"${quote['last_price']}", trend_color)
    with c2:
        render_metric("Variación", f"{sign}{quote['change_pct']}%", trend_color)
    with c3:
        render_metric("Máx / Mín día", f"${quote['day_high']} / ${quote['day_low']}")
    with c4:
        vol = quote["metrics"].get("volatility", 0)
        render_metric("Volatilidad σ", f"{vol}")

    st.markdown("#### Histórico de cierre")
    st.line_chart(quote["chart"], use_container_width=True)

    metrics = quote["metrics"]
    m1, m2, m3 = st.columns(3)
    m1.metric("Media período", f"${metrics.get('average_price', 0)}")
    m2.metric("Máximo período", f"${metrics.get('highest_price', 0)}")
    m3.metric("Mínimo período", f"${metrics.get('lowest_price', 0)}")

    now = datetime.now().strftime("%H:%M:%S")
    st.caption(
        f"Actualizado {now} · {quote['history_days']} sesiones · "
        f"Refresco cada {cfg.get('refresh_seconds', 60)}s"
    )

    time.sleep(cfg.get("refresh_seconds", 60))
    st.rerun()


if __name__ == "__main__":
    main()
