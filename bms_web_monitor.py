"""
B-Intelligent — BMS Cloud Auditor (Web App)
Monitor visual en tiempo real con Streamlit.
"""

import json
import logging
import math
import sys
import time
from datetime import datetime
from pathlib import Path

import streamlit as st
from pyModbusTCP.client import ModbusClient

from whatsapp_alerts import send_whatsapp_alert

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [MODBUS] - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

CONFIG_PATH = "config.json"
MODE_SIM = "Modo Laboratorio (Simulado)"
MODE_REAL = "Modo Planta Real (Victron Modbus)"

COLOR_BG = "#060d18"
COLOR_BG_GRADIENT = "linear-gradient(145deg, #060d18 0%, #0a1a32 45%, #0d2847 100%)"
COLOR_SURFACE = "#0f1e35"
COLOR_SURFACE_GRADIENT = "linear-gradient(160deg, rgba(15, 30, 53, 0.95) 0%, rgba(18, 40, 72, 0.88) 100%)"
COLOR_BORDER = "#2a5a9a"
COLOR_TEXT = "#f5f8ff"
COLOR_TEXT_MUTED = "#9eb8d9"
COLOR_ACCENT = "#00f5d4"
COLOR_ACCENT_2 = "#7b61ff"
COLOR_GREEN = "#00ff88"
COLOR_YELLOW = "#ffd93d"
COLOR_RED = "#ff4757"
COLOR_ORANGE = "#ff9f1c"
COLOR_GREEN_DARK = "linear-gradient(135deg, #0a3d28 0%, #0d5c3a 100%)"
COLOR_SOC_ON = "#ff9f1c"
COLOR_SOC_ON_GLOW = "#ffd93d"
COLOR_SOC_OFF = "#12243d"
COLOR_SOLAR = "#ffd93d"
COLOR_LOAD = "#4fc3f7"
COLOR_BATTERY = "#00e676"
COLOR_GRID = "#b388ff"
SOC_BAR_SEGMENTS = 20

METRIC_ACCENTS = {
    "cells": "#00f5d4",
    "temperature": "#ff6b6b",
    "consumption": "#4fc3f7",
    "solar": "#ffd93d",
    "battery": "#00e676",
    "grid": "#b388ff",
}


def load_configuration(config_path: str = CONFIG_PATH) -> dict:
    defaults = {
        "victron_ip": "192.168.1.100",
        "modbus_port": 502,
        "victron_unit_id": 100,
        "v_cell_critical_high": 3.60,
        "v_cell_warning_high": 3.45,
        "v_cell_critical_low": 2.60,
        "t_critical_high": 55.0,
        "t_charge_low": 0.0,
        "default_mode": "simulated",
        "sample_interval_s": 5,
        "soc_sim_min": 75,
        "soc_sim_max": 85,
        "cell_count": 16,
        "cell_spread_v": 0.04,
        "modbus_reg_system_voltage": 840,
        "modbus_reg_system_soc": 820,
        "modbus_reg_system_voltage_scale": 10,
        "modbus_reg_system_soc_scale": 10,
        "modbus_reg_system_soc_fallback": 843,
        "modbus_reg_system_soc_fallback_scale": 1,
        "modbus_reg_ac_consumption_l1": 817,
        "modbus_reg_ac_consumption_l2": 818,
        "modbus_reg_ac_consumption_l3": 819,
        "modbus_reg_pv_power": 850,
        "modbus_reg_grid_power": 820,
        "modbus_reg_battery_power": 842,
        "battery_capacity_kwh": 10.0,
        "soc_alert_warning": 20.0,
        "soc_alert_critical": 10.0,
        "whatsapp_alerts_enabled": False,
        "whatsapp_alert_cooldown_s": 3600,
        "whatsapp_recipient": "",
        "whatsapp_template_name": "alerta_bintelligent",
        "whatsapp_template_language": "es",
        "plant_name": "B-Intelligent Plant",
        "inverter_unit_id": 225,
        "battery_unit_id": None,
        "modbus_reg_battery_temperature": 282,
        "modbus_reg_battery_temperature_scale": 10,
    }
    path = Path(config_path)
    if not path.exists():
        return defaults
    with open(path, encoding="utf-8") as f:
        loaded = json.load(f)
    merged = {**defaults, **loaded}
    if "whatsapp_alerts_enabled" not in loaded and loaded.get("telegram_alerts_enabled") is not None:
        merged["whatsapp_alerts_enabled"] = loaded["telegram_alerts_enabled"]
    if "whatsapp_alert_cooldown_s" not in loaded and loaded.get("telegram_alert_cooldown_s") is not None:
        merged["whatsapp_alert_cooldown_s"] = loaded["telegram_alert_cooldown_s"]
    return merged


def _to_signed_int16(value: int) -> int:
    return value - 65536 if value >= 32768 else value


def format_house_power(watts: float) -> tuple[str, str]:
    """Formatea potencia de consumo para la tarjeta principal."""
    watts = max(watts, 0.0)
    if watts >= 1000:
        return f"{watts / 1000:.2f} kW", f"{watts:.0f} W instantáneos"
    return f"{watts:.0f} W", "Consumo AC instantáneo de la vivienda"


def format_power_watts(watts: float) -> str:
    watts = abs(watts)
    if watts >= 1000:
        return f"{watts / 1000:.2f} kW"
    return f"{watts:.0f} W"


def format_grid_power(watts: float) -> tuple[str, str]:
    if watts > 50:
        return format_power_watts(watts), "Importando de la red eléctrica"
    if watts < -50:
        return format_power_watts(watts), "Exportando excedente a la red"
    return "0 W", "Red en equilibrio"


def format_battery_power(watts: float) -> tuple[str, str]:
    if watts > 50:
        return format_power_watts(watts), "Batería cargando"
    if watts < -50:
        return format_power_watts(watts), "Batería descargando"
    return "0 W", "Batería en reposo"


def estimate_autonomy_hours(soc_percent: float, capacity_kwh: float, consumption_w: float) -> float | None:
    """Estima autonomía: energía usable / consumo instantáneo."""
    if consumption_w <= 50 or capacity_kwh <= 0:
        return None
    available_wh = capacity_kwh * 1000.0 * (soc_percent / 100.0)
    return available_wh / consumption_w


def format_autonomy(hours: float | None) -> str:
    if hours is None:
        return "— (consumo muy bajo)"
    if hours >= 24:
        return f"{hours / 24:.1f} días"
    return f"{hours:.1f} h"


def analizar_salud_celdas(voltajes_celdas: list[float]) -> dict:
    n = len(voltajes_celdas)
    if n == 0:
        return {
            "drift_mv": 0,
            "desviacion_estandar_mv": 0,
            "estado": "Sin datos",
            "tipo_alerta": "info",
            "media_v": 0,
        }

    v_max = max(voltajes_celdas)
    v_min = min(voltajes_celdas)
    drift_mv = (v_max - v_min) * 1000

    media = sum(voltajes_celdas) / n
    varianza = sum((x - media) ** 2 for x in voltajes_celdas) / n
    desviacion_estandar_mv = math.sqrt(varianza) * 1000

    if desviacion_estandar_mv < 10:
        estado = "Excelente 🟢"
        tipo_alerta = "success"
    elif desviacion_estandar_mv < 25:
        estado = "Normal / Bueno 🟡"
        tipo_alerta = "info"
    elif desviacion_estandar_mv < 50:
        estado = "Desequilibrio detectado 🟠"
        tipo_alerta = "warning"
    else:
        estado = "CRÍTICO (Revisar celdas/busbars) 🔴"
        tipo_alerta = "error"

    return {
        "drift_mv": round(drift_mv, 1),
        "desviacion_estandar_mv": round(desviacion_estandar_mv, 1),
        "estado": estado,
        "tipo_alerta": tipo_alerta,
        "media_v": round(media, 3),
    }


def build_simulated_cell_voltages(cell_count: int, t: float | None = None) -> list[float]:
    t = t or time.time()
    base = 3.322 + 0.003 * math.sin(t / 30)
    return [
        round(base + 0.002 * math.sin(t / 7 + i * 0.9) + 0.001 * math.sin(i * 1.7), 3)
        for i in range(cell_count)
    ]


def build_estimated_cell_voltages(v_min: float, v_max: float, cell_count: int) -> list[float]:
    if cell_count <= 0:
        return []
    if cell_count == 1:
        return [round(v_min, 3)]
    step = (v_max - v_min) / (cell_count - 1)
    return [round(v_min + i * step, 3) for i in range(cell_count)]


def render_cell_health_sidebar(telemetry: dict, cfg: dict):
    voltajes = telemetry.get("cell_voltages") or []
    salud = analizar_salud_celdas(voltajes)
    source = telemetry.get("cell_voltage_source", "desconocido")
    health_class = {
        "success": "health-success",
        "info": "health-info",
        "warning": "health-warning",
        "error": "health-error",
    }.get(salud["tipo_alerta"], "health-info")

    st.markdown("---")
    st.markdown("#### 🏥 Salud del Banco LiFePO4")
    st.caption(f"Fuente: {source} · {len(voltajes)} celdas · media {salud['media_v']:.3f} V")
    st.markdown(
        f'<div class="health-badge {health_class}">Estado: {salud["estado"]}</div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            label="Desviación Est.",
            value=f"{salud['desviacion_estandar_mv']} mV",
            help="Dispersión media entre celdas. Lo ideal es mantenerla por debajo de 15 mV en operación.",
        )
    with col2:
        st.metric(
            label="Dispersión (Drift)",
            value=f"{salud['drift_mv']} mV",
            help="Diferencia entre la celda con voltaje más alto y la más baja (Vmax − Vmin).",
        )

    with st.expander("ℹ️ ¿Por qué importa la Desviación Estándar?"):
        st.write(
            "A diferencia del drift clásico, la desviación estándar evalúa el comportamiento "
            "del bloque completo de celdas. Si sube de forma persistente al mismo SoC, avisa de "
            "envejecimiento prematuro o resistencia anómala en bornes (busbars) antes de que "
            "salte la protección del JK BMS."
        )


def read_modbus_register_w(client: ModbusClient, reg: int, signed: bool = False, label: str = "") -> float:
    try:
        regs = client.read_holding_registers(reg, 1)
        if not regs:
            logger.warning("Reg %s (%s): lectura vacía", reg, label)
            return 0.0
        value = _to_signed_int16(regs[0]) if signed else regs[0]
        logger.info("Potencia %s — reg %s: %s W", label, reg, value)
        return float(value)
    except Exception as exc:
        logger.error("ERROR reg %s (%s): %s: %s", reg, label, type(exc).__name__, exc)
        return 0.0


def process_whatsapp_alerts(telemetry: dict, cfg: dict, plant_status: str):
    if not cfg.get("whatsapp_alerts_enabled"):
        return

    soc = telemetry["soc"]
    plant = cfg.get("plant_name", "Planta")
    now = time.time()
    cooldown = cfg.get("whatsapp_alert_cooldown_s", 3600)
    recipient = cfg.get("whatsapp_recipient") or None
    template_name = cfg.get("whatsapp_template_name")
    template_language = cfg.get("whatsapp_template_language")

    alerts = []
    if soc <= cfg.get("soc_alert_critical", 10):
        alerts.append(("critical", f"SoC crítico: {soc:.1f}%"))
    elif soc <= cfg.get("soc_alert_warning", 20):
        alerts.append(("warning", f"SoC bajo: {soc:.1f}%"))
    if plant_status == "CRITICAL":
        alerts.append(("critical_status", "Estado de planta: CRÍTICO"))

    if "whatsapp_cooldown" not in st.session_state:
        st.session_state.whatsapp_cooldown = {}

    for key, message_text in alerts:
        last = st.session_state.whatsapp_cooldown.get(key, 0)
        if now - last >= cooldown:
            ok, detail = send_whatsapp_alert(
                message_text,
                plant_name=plant,
                recipient=recipient,
                template_name=template_name,
                template_language=template_language,
            )
            if ok:
                st.session_state.whatsapp_cooldown[key] = now
                logger.info("Alerta WhatsApp enviada: %s", key)
            else:
                logger.warning("WhatsApp no enviado (%s): %s", key, detail)


def read_ac_consumption_w(client: ModbusClient, cfg: dict) -> float:
    """Suma consumo AC L1+L2+L3 (registros 817-819, escala 1 W)."""
    total_w = 0.0
    phases = [
        ("L1", cfg["modbus_reg_ac_consumption_l1"]),
        ("L2", cfg.get("modbus_reg_ac_consumption_l2")),
        ("L3", cfg.get("modbus_reg_ac_consumption_l3")),
    ]
    for phase_name, reg in phases:
        if reg is None:
            continue
        try:
            regs = client.read_holding_registers(reg, 1)
            if not regs:
                logger.warning("Consumo AC %s — reg %s: lectura vacía", phase_name, reg)
                continue
            watts = _to_signed_int16(regs[0])
            if watts < 0:
                watts = 0
            total_w += watts
            logger.info("Consumo AC %s — reg %s: %s W", phase_name, reg, watts)
        except Exception as exc:
            logger.error("ERROR consumo AC %s reg %s: %s: %s", phase_name, reg, type(exc).__name__, exc)
    return total_w


def read_simulated_telemetry(cfg: dict) -> dict:
    phase = time.time() / 20
    soc_min = cfg["soc_sim_min"]
    soc_max = cfg["soc_sim_max"]
    soc = soc_min + (soc_max - soc_min) * (0.5 + 0.5 * math.sin(phase))

    house_w = 780 + 120 * math.sin(time.time() / 15)
    pv_w = max(0, 1200 + 400 * math.sin(time.time() / 25))
    battery_w = -350 + 200 * math.sin(time.time() / 18)
    grid_w = house_w - pv_w - battery_w
    autonomy = estimate_autonomy_hours(soc, cfg.get("battery_capacity_kwh", 10.0), house_w)
    cell_voltages = build_simulated_cell_voltages(cfg["cell_count"])

    return {
        "highest_cell_voltage": max(cell_voltages),
        "lowest_cell_voltage": min(cell_voltages),
        "max_pack_temperature": 28.5,
        "min_pack_temperature": 27.0,
        "soc": round(soc, 1),
        "pack_voltage": round(sum(cell_voltages), 2),
        "house_consumption_w": round(house_w, 0),
        "pv_power_w": round(pv_w, 0),
        "battery_power_w": round(battery_w, 0),
        "grid_power_w": round(grid_w, 0),
        "autonomy_hours": autonomy,
        "cell_voltages": cell_voltages,
        "cell_voltage_source": "Simulación laboratorio (JK)",
        "source": "simulated",
        "error": None,
    }


def read_victron_modbus_telemetry(cfg: dict) -> dict:
    """
    Lee telemetría Victron vía Modbus TCP (com.victronenergy.system, unit ID 100).
    SoC: registro 820, uint16, factor de escala 0.1 (raw 460 -> 46.0 %).
    Voltaje pack: registro 840, escala 0.1 V.
    """
    host = cfg["victron_ip"]
    port = cfg["modbus_port"]
    unit_id = cfg["victron_unit_id"]
    client = ModbusClient(host=host, port=port, unit_id=unit_id, auto_open=True, timeout=5)

    try:
        if not client.open():
            raise ConnectionError(f"No se pudo abrir conexión Modbus TCP con {host}:{port} (unit {unit_id})")

        # --- SoC: registro 820, uint16, escala 0.1 (estándar Victron) ---
        raw_soc = None
        soc = None
        try:
            soc_regs = client.read_holding_registers(cfg["modbus_reg_system_soc"], 1)
            if not soc_regs:
                raise ConnectionError(
                    f"Lectura SoC vacía en registro {cfg['modbus_reg_system_soc']} "
                    f"(unit {unit_id}, host {host})"
                )
            raw_soc = soc_regs[0]
            soc = raw_soc / cfg["modbus_reg_system_soc_scale"]
            logger.info(
                "SoC reg %s — raw=%s, escala=0.1, calculado=%.1f%%",
                cfg["modbus_reg_system_soc"],
                raw_soc,
                soc,
            )
        except Exception as exc:
            logger.error(
                "ERROR lectura SoC reg %s — unit %s, host %s: %s: %s",
                cfg["modbus_reg_system_soc"],
                unit_id,
                host,
                type(exc).__name__,
                exc,
            )
            soc = None

        # Fallback: registro 843 (SOC directo 0-100 en muchos Cerbo GX)
        fallback_reg = cfg.get("modbus_reg_system_soc_fallback")
        if fallback_reg is not None:
            try:
                fb_regs = client.read_holding_registers(fallback_reg, 1)
                if fb_regs:
                    raw_fb = fb_regs[0]
                    soc_fb = raw_fb / cfg.get("modbus_reg_system_soc_fallback_scale", 1)
                    logger.info(
                        "SoC fallback reg %s — raw=%s, calculado=%.1f%%",
                        fallback_reg,
                        raw_fb,
                        soc_fb,
                    )
                    if soc is None or not (0 <= soc <= 100):
                        raw_soc, soc = raw_fb, soc_fb
                        logger.warning("Usando SoC fallback reg %s (primario inválido)", fallback_reg)
                    elif abs(soc - soc_fb) > 10:
                        logger.warning(
                            "Reg %s (%.1f%%) difiere de fallback %s (%.1f%%) — usando fallback",
                            cfg["modbus_reg_system_soc"],
                            soc,
                            fallback_reg,
                            soc_fb,
                        )
                        raw_soc, soc = raw_fb, soc_fb
            except Exception as exc:
                logger.error(
                    "ERROR lectura SoC fallback reg %s: %s: %s",
                    fallback_reg,
                    type(exc).__name__,
                    exc,
                )

        if soc is None:
            raise ConnectionError("No se pudo leer SoC ni desde registro primario ni fallback")

        # --- Voltaje de batería: registro 840 ---
        try:
            voltage_regs = client.read_holding_registers(cfg["modbus_reg_system_voltage"], 1)
            if not voltage_regs:
                raise ConnectionError(
                    f"Lectura voltaje vacía en registro {cfg['modbus_reg_system_voltage']}"
                )
            raw_voltage = voltage_regs[0]
            pack_voltage = raw_voltage / cfg["modbus_reg_system_voltage_scale"]
            logger.info(
                "Voltaje pack OK — reg %s, raw=%s, pack=%.2f V",
                cfg["modbus_reg_system_voltage"],
                raw_voltage,
                pack_voltage,
            )
        except Exception as exc:
            logger.error(
                "ERROR lectura voltaje — reg %s: %s: %s",
                cfg["modbus_reg_system_voltage"],
                type(exc).__name__,
                exc,
            )
            raise

        if not (0 <= soc <= 100):
            raise ValueError(
                f"SoC fuera de rango tras escala 0.1: raw={raw_soc}, calculado={soc:.1f}% "
                f"(registro {cfg['modbus_reg_system_soc']})"
            )

        temperature = None
        battery_unit_id = cfg.get("battery_unit_id")
        if battery_unit_id:
            try:
                client.unit_id = battery_unit_id
                temp_regs = client.read_holding_registers(cfg["modbus_reg_battery_temperature"], 1)
                if temp_regs:
                    temperature = _to_signed_int16(temp_regs[0]) / cfg["modbus_reg_battery_temperature_scale"]
                    logger.info("Temperatura OK — unit %s, temp=%.1f C", battery_unit_id, temperature)
            except Exception as exc:
                logger.error(
                    "ERROR lectura temperatura — unit %s, reg %s: %s: %s",
                    battery_unit_id,
                    cfg["modbus_reg_battery_temperature"],
                    type(exc).__name__,
                    exc,
                )

        if temperature is None:
            temperature = 28.0

        try:
            house_consumption_w = read_ac_consumption_w(client, cfg)
        except Exception as exc:
            logger.error("ERROR lectura consumo casa: %s: %s", type(exc).__name__, exc)
            house_consumption_w = 0.0

        pv_power_w = read_modbus_register_w(client, cfg["modbus_reg_pv_power"], signed=False, label="PV")
        battery_power_w = read_modbus_register_w(
            client, cfg["modbus_reg_battery_power"], signed=True, label="Batería"
        )
        grid_power_w = read_modbus_register_w(
            client, cfg["modbus_reg_grid_power"], signed=True, label="Red"
        )
        autonomy_hours = estimate_autonomy_hours(
            soc, cfg.get("battery_capacity_kwh", 10.0), house_consumption_w
        )

        cell_count = cfg["cell_count"]
        spread = cfg["cell_spread_v"]
        v_avg = pack_voltage / cell_count
        v_max = round(v_avg + spread / 2, 3)
        v_min = round(v_avg - spread / 2, 3)
        cell_voltages = build_estimated_cell_voltages(v_min, v_max, cell_count)

        return {
            "highest_cell_voltage": max(cell_voltages),
            "lowest_cell_voltage": min(cell_voltages),
            "max_pack_temperature": round(temperature, 1),
            "min_pack_temperature": round(temperature - 1.0, 1),
            "soc": round(soc, 1),
            "pack_voltage": round(pack_voltage, 2),
            "house_consumption_w": round(house_consumption_w, 0),
            "pv_power_w": round(pv_power_w, 0),
            "battery_power_w": round(battery_power_w, 0),
            "grid_power_w": round(grid_power_w, 0),
            "autonomy_hours": autonomy_hours,
            "cell_voltages": cell_voltages,
            "cell_voltage_source": "Estimado desde pack Victron",
            "raw_soc": raw_soc,
            "source": "modbus",
            "error": None,
        }
    except Exception as exc:
        logger.error("FALLO Modbus TCP global: %s: %s", type(exc).__name__, exc)
        raise
    finally:
        client.close()


def fetch_telemetry(mode: str, cfg: dict) -> dict:
    if mode == MODE_REAL:
        try:
            return read_victron_modbus_telemetry(cfg)
        except Exception as exc:
            logger.error("Modo Real con fallback simulado: %s: %s", type(exc).__name__, exc)
            fallback = read_simulated_telemetry(cfg)
            fallback["source"] = "modbus_error"
            fallback["error"] = f"{type(exc).__name__}: {exc}"
            return fallback
    return read_simulated_telemetry(cfg)


def evaluate_plant_status(telemetry: dict, cfg: dict) -> tuple[str, str, str]:
    v_max = telemetry["highest_cell_voltage"]
    v_min = telemetry["lowest_cell_voltage"]
    t_max = telemetry["max_pack_temperature"]
    t_min = telemetry["min_pack_temperature"]

    if t_max >= cfg["t_critical_high"]:
        return "CRITICAL", "APAGADO DE EMERGENCIA — SOBRETEMPERATURA", COLOR_RED
    if t_min <= cfg["t_charge_low"]:
        return "CRITICAL", "CARGA BLOQUEADA — TEMPERATURA BAJO CERO", COLOR_RED
    if v_max >= cfg["v_cell_critical_high"]:
        return "CRITICAL", "CARGA A 0A — VOLTAJE CRÍTICO DE CELDA", COLOR_RED
    if v_min <= cfg["v_cell_critical_low"]:
        return "CRITICAL", "DESCARGA A 0A — SOBREDESCARGA DE CELDA", COLOR_RED
    if v_max >= cfg["v_cell_warning_high"]:
        return "WARNING", "REDUCCIÓN DE CARGA PREVENTIVA — CELDA ALTA", COLOR_YELLOW
    return "STABLE", "SISTEMA ESTABLE", COLOR_GREEN


def build_soc_segment_bar(soc: float, total_segments: int = SOC_BAR_SEGMENTS) -> str:
    """Genera barritas encendidas/apagadas de 0 a 100 %."""
    lit = int(round(min(max(soc, 0.0), 100.0) / 100.0 * total_segments))
    parts = []
    for index in range(total_segments):
        state = "on" if index < lit else "off"
        parts.append(f'<div class="soc-seg soc-seg-{state}"></div>')
    return f'<div class="soc-segments">{"".join(parts)}</div>'


def soc_glow_color(soc: float) -> str:
    if soc <= 15:
        return COLOR_RED
    if soc <= 35:
        return COLOR_ORANGE
    if soc <= 60:
        return COLOR_YELLOW
    return COLOR_GREEN


def inject_corporate_theme():
    st.markdown(
        f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

            .stApp {{
                background: {COLOR_BG_GRADIENT};
                color: {COLOR_TEXT};
                font-family: 'Inter', Helvetica, Arial, sans-serif;
            }}
            [data-testid="stHeader"], [data-testid="stToolbar"] {{
                background: rgba(6, 13, 24, 0.92);
            }}
            [data-testid="stSidebar"] {{
                background: linear-gradient(180deg, #0c1830 0%, #0a1428 100%);
                border-right: 1px solid rgba(0, 245, 212, 0.15);
            }}
            [data-testid="stSidebar"] * {{ color: {COLOR_TEXT} !important; }}
            [data-testid="stSidebar"] .stMetric {{
                background: rgba(0, 245, 212, 0.06);
                border: 1px solid rgba(0, 245, 212, 0.2);
                border-radius: 10px;
                padding: 0.5rem;
            }}
            .block-container {{ padding-top: 1.2rem; max-width: 1100px; }}

            .brand-tag {{
                display: inline-block;
                color: {COLOR_ACCENT};
                font-size: 0.8rem;
                font-weight: 800;
                letter-spacing: 0.14em;
                text-transform: uppercase;
                padding: 0.25rem 0.65rem;
                border-radius: 999px;
                border: 1px solid rgba(0, 245, 212, 0.45);
                background: rgba(0, 245, 212, 0.08);
                box-shadow: 0 0 18px rgba(0, 245, 212, 0.15);
            }}
            .brand-title {{
                background: linear-gradient(90deg, {COLOR_TEXT} 0%, {COLOR_ACCENT} 55%, {COLOR_ACCENT_2} 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                font-size: 2.45rem;
                font-weight: 800;
                margin: 0.6rem 0 0.35rem 0;
                letter-spacing: -0.02em;
            }}
            .brand-subtitle {{ color: {COLOR_TEXT_MUTED}; font-size: 0.98rem; margin-bottom: 1.1rem; }}

            .soc-card {{
                background: {COLOR_SURFACE_GRADIENT};
                border: 1px solid rgba(0, 245, 212, 0.25);
                border-radius: 18px;
                padding: 1.3rem 1.6rem;
                margin-bottom: 1rem;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255,255,255,0.06);
            }}
            .soc-label {{
                color: {COLOR_ACCENT};
                font-size: 0.78rem;
                font-weight: 800;
                letter-spacing: 0.1em;
                text-transform: uppercase;
            }}
            .soc-value {{
                font-size: 2.65rem;
                font-weight: 800;
                margin: 0.35rem 0 0.65rem 0;
                text-shadow: 0 0 24px currentColor;
            }}
            .soc-segments {{
                display: flex;
                gap: 4px;
                width: 100%;
                height: 38px;
                margin: 0.65rem 0 0.35rem 0;
            }}
            .soc-seg {{
                flex: 1;
                border-radius: 6px;
                min-height: 38px;
                transition: all 0.35s ease;
            }}
            .soc-seg-on {{
                background: linear-gradient(180deg, {COLOR_SOC_ON_GLOW} 0%, {COLOR_SOC_ON} 100%);
                box-shadow: 0 0 10px rgba(255, 159, 28, 0.55), 0 2px 4px rgba(0,0,0,0.3);
            }}
            .soc-seg-off {{
                background: {COLOR_SOC_OFF};
                border: 1px solid rgba(42, 90, 154, 0.5);
            }}
            .soc-scale {{
                display: flex;
                justify-content: space-between;
                color: {COLOR_TEXT_MUTED};
                font-size: 0.75rem;
            }}
            .autonomy-line {{
                color: {COLOR_ACCENT};
                font-size: 1.05rem;
                font-weight: 700;
                margin-top: 0.85rem;
                padding-top: 0.65rem;
                border-top: 1px dashed rgba(0, 245, 212, 0.25);
            }}

            .flow-strip {{
                display: flex;
                justify-content: space-between;
                gap: 0.65rem;
                margin-bottom: 1rem;
            }}
            .flow-item {{
                flex: 1;
                text-align: center;
                border-radius: 14px;
                padding: 0.85rem 0.6rem;
                font-size: 0.82rem;
                color: {COLOR_TEXT_MUTED};
                border: 1px solid transparent;
                box-shadow: 0 6px 20px rgba(0,0,0,0.25);
            }}
            .flow-item strong {{
                display: block;
                font-size: 1.15rem;
                font-weight: 800;
                margin-top: 0.25rem;
                color: {COLOR_TEXT};
            }}
            .flow-solar {{
                background: linear-gradient(160deg, rgba(255, 217, 61, 0.18) 0%, rgba(255, 159, 28, 0.08) 100%);
                border-color: rgba(255, 217, 61, 0.35);
            }}
            .flow-load {{
                background: linear-gradient(160deg, rgba(79, 195, 247, 0.18) 0%, rgba(41, 121, 255, 0.08) 100%);
                border-color: rgba(79, 195, 247, 0.35);
            }}
            .flow-battery {{
                background: linear-gradient(160deg, rgba(0, 230, 118, 0.18) 0%, rgba(0, 200, 83, 0.08) 100%);
                border-color: rgba(0, 230, 118, 0.35);
            }}
            .flow-grid {{
                background: linear-gradient(160deg, rgba(179, 136, 255, 0.18) 0%, rgba(123, 97, 255, 0.08) 100%);
                border-color: rgba(179, 136, 255, 0.35);
            }}

            .metric-card {{
                background: {COLOR_SURFACE_GRADIENT};
                border: 1px solid rgba(42, 90, 154, 0.45);
                border-radius: 16px;
                padding: 1.35rem 1.5rem;
                min-height: 168px;
                box-shadow: 0 8px 28px rgba(0, 0, 0, 0.28);
                border-top: 3px solid var(--accent, {COLOR_ACCENT});
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }}
            .metric-card:hover {{
                transform: translateY(-2px);
                box-shadow: 0 12px 32px rgba(0, 0, 0, 0.38);
            }}
            .metric-label {{
                color: var(--accent, {COLOR_ACCENT});
                font-size: 0.72rem;
                font-weight: 800;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                margin-bottom: 0.75rem;
            }}
            .metric-value {{
                color: {COLOR_TEXT};
                font-size: 2.55rem;
                font-weight: 800;
                line-height: 1;
                margin-bottom: 0.55rem;
                text-shadow: 0 0 20px rgba(255,255,255,0.08);
            }}
            .metric-detail {{ color: {COLOR_TEXT_MUTED}; font-size: 0.88rem; line-height: 1.35; }}

            .status-panel {{
                border-radius: 18px;
                padding: 2rem 1.5rem;
                text-align: center;
                margin-top: 0.6rem;
                box-shadow: 0 10px 40px rgba(0,0,0,0.35);
            }}
            .status-stable {{
                background: linear-gradient(135deg, #0a3d28 0%, #0f5a3a 50%, #0a3d28 100%);
                border: 2px solid {COLOR_GREEN};
                box-shadow: 0 0 30px rgba(0, 255, 136, 0.25);
            }}
            .status-warning {{
                background: linear-gradient(135deg, #4a3a00 0%, #6b5200 50%, #4a3a00 100%);
                border: 2px solid {COLOR_YELLOW};
                box-shadow: 0 0 30px rgba(255, 217, 61, 0.25);
            }}
            .status-critical {{
                background: linear-gradient(135deg, #4a0f14 0%, #7a1820 50%, #4a0f14 100%);
                border: 2px solid {COLOR_RED};
                box-shadow: 0 0 30px rgba(255, 71, 87, 0.3);
                animation: pulse-critical 2s ease-in-out infinite;
            }}
            @keyframes pulse-critical {{
                0%, 100% {{ box-shadow: 0 0 20px rgba(255, 71, 87, 0.25); }}
                50% {{ box-shadow: 0 0 40px rgba(255, 71, 87, 0.45); }}
            }}
            .status-title {{ font-size: 2rem; font-weight: 800; margin: 0; color: {COLOR_TEXT}; }}
            .status-subtitle {{ font-size: 0.95rem; margin-top: 0.55rem; opacity: 0.92; color: {COLOR_TEXT}; }}

            .health-badge {{
                border-radius: 12px;
                padding: 0.75rem 1rem;
                font-weight: 700;
                margin-bottom: 0.75rem;
                border: 1px solid transparent;
            }}
            .health-success {{
                background: linear-gradient(135deg, rgba(0,255,136,0.15), rgba(0,200,83,0.08));
                border-color: rgba(0,255,136,0.4);
                color: #b8ffda;
            }}
            .health-info {{
                background: linear-gradient(135deg, rgba(255,217,61,0.15), rgba(255,159,28,0.08));
                border-color: rgba(255,217,61,0.4);
                color: #ffeaa7;
            }}
            .health-warning {{
                background: linear-gradient(135deg, rgba(255,159,28,0.18), rgba(255,107,0,0.08));
                border-color: rgba(255,159,28,0.45);
                color: #ffd8a8;
            }}
            .health-error {{
                background: linear-gradient(135deg, rgba(255,71,87,0.2), rgba(200,30,50,0.1));
                border-color: rgba(255,71,87,0.5);
                color: #ffb3bc;
            }}

            .footer-bar {{
                background: rgba(15, 30, 53, 0.85);
                border: 1px solid rgba(0, 245, 212, 0.15);
                border-radius: 12px;
                padding: 0.8rem 1rem;
                color: {COLOR_TEXT_MUTED};
                font-size: 0.82rem;
                margin-top: 1rem;
            }}
            .alert-bar {{
                background: linear-gradient(90deg, rgba(255,71,87,0.2), rgba(255,159,28,0.12));
                border: 1px solid {COLOR_RED};
                border-radius: 12px;
                padding: 0.7rem 1rem;
                color: {COLOR_TEXT};
                font-size: 0.88rem;
                margin-bottom: 0.9rem;
                box-shadow: 0 0 20px rgba(255, 71, 87, 0.15);
            }}
            #MainMenu, footer, header {{ visibility: hidden; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_soc_card(soc: float, autonomy_hours: float | None, capacity_kwh: float):
    segment_bar = build_soc_segment_bar(soc)
    autonomy_text = format_autonomy(autonomy_hours)
    soc_color = soc_glow_color(soc)
    st.markdown(
        f"""
        <div class="soc-card">
            <div class="soc-label">Estado de Carga</div>
            <div class="soc-value" style="color:{soc_color};">⚡ SoC: {soc:.1f}%</div>
            {segment_bar}
            <div class="soc-scale"><span>0%</span><span>100%</span></div>
            <div class="autonomy-line">⏱ Autonomía estimada: {autonomy_text} · Banco {capacity_kwh:.1f} kWh</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_energy_flow_strip(telemetry: dict):
    pv = telemetry.get("pv_power_w", 0)
    load = telemetry.get("house_consumption_w", 0)
    bat = telemetry.get("battery_power_w", 0)
    grid = telemetry.get("grid_power_w", 0)
    st.markdown(
        f"""
        <div class="flow-strip">
            <div class="flow-item flow-solar">☀️ Solar<strong style="color:{COLOR_SOLAR};">{format_power_watts(pv)}</strong></div>
            <div class="flow-item flow-load">🏠 Consumo<strong style="color:{COLOR_LOAD};">{format_power_watts(load)}</strong></div>
            <div class="flow-item flow-battery">🔋 Batería<strong style="color:{COLOR_BATTERY};">{format_power_watts(bat)}</strong></div>
            <div class="flow-item flow-grid">🔌 Red<strong style="color:{COLOR_GRID};">{format_power_watts(grid)}</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(label: str, value: str, detail: str, accent: str = COLOR_ACCENT):
    st.markdown(
        f"""
        <div class="metric-card" style="--accent: {accent};">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-detail">{detail}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_panel(level: str, message: str):
    if level == "STABLE":
        css_class, subtitle = "status-stable", "Sin alertas activas en la planta"
    elif level == "WARNING":
        css_class, subtitle = "status-warning", "Acción preventiva recomendada"
    else:
        css_class, subtitle = "status-critical", "Contramedida Modbus activada o requerida"

    st.markdown(
        f"""
        <div class="status-panel {css_class}">
            <p class="status-title">{message}</p>
            <p class="status-subtitle">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_dashboard(cfg: dict, mode: str, telemetry: dict):
    level, message, _ = evaluate_plant_status(telemetry, cfg)
    process_whatsapp_alerts(telemetry, cfg, level)
    soc = telemetry["soc"]
    inject_corporate_theme()

    v_max = telemetry["highest_cell_voltage"]
    v_min = telemetry["lowest_cell_voltage"]
    t_max = telemetry["max_pack_temperature"]
    t_min = telemetry["min_pack_temperature"]
    now = datetime.now().strftime("%H:%M:%S")

    if telemetry.get("error"):
        st.markdown(
            f'<div class="alert-bar">⚠ Modbus: {telemetry["error"]} — mostrando respaldo simulado.</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<p class="brand-tag">B-Intelligent</p>', unsafe_allow_html=True)
    st.markdown('<h1 class="brand-title">BMS Cloud Auditor</h1>', unsafe_allow_html=True)
    st.markdown(
        f'<p class="brand-subtitle">{cfg.get("plant_name", "B-Intelligent")} · Color Control GX · {cfg["victron_ip"]}:{cfg["modbus_port"]}</p>',
        unsafe_allow_html=True,
    )

    render_soc_card(soc, telemetry.get("autonomy_hours"), cfg.get("battery_capacity_kwh", 10.0))
    render_energy_flow_strip(telemetry)

    power_value, power_detail = format_house_power(telemetry.get("house_consumption_w", 0.0))
    pv_value = format_power_watts(telemetry.get("pv_power_w", 0))
    bat_value, bat_detail = format_battery_power(telemetry.get("battery_power_w", 0))
    grid_value, grid_detail = format_grid_power(telemetry.get("grid_power_w", 0))
    modbus_note = "Victron Modbus" if telemetry["source"] == "modbus" else "Simulación"

    col1, col2, col3 = st.columns(3, gap="medium")
    with col1:
        render_metric_card(
            "Voltaje de Celdas",
            f"{v_max:.2f} V",
            f"Mínima: {v_min:.2f} V · Δ celda: {(v_max - v_min) * 1000:.0f} mV · {modbus_note}",
            accent=METRIC_ACCENTS["cells"],
        )
    with col2:
        render_metric_card(
            "Temperatura del Pack",
            f"{t_max:.1f} °C",
            f"Mínima: {t_min:.1f} °C · Rango: {t_max - t_min:.1f} °C",
            accent=METRIC_ACCENTS["temperature"],
        )
    with col3:
        render_metric_card(
            "Consumo de la Casa",
            power_value,
            f"{power_detail} · reg 817",
            accent=METRIC_ACCENTS["consumption"],
        )

    col4, col5, col6 = st.columns(3, gap="medium")
    with col4:
        render_metric_card(
            "Producción Solar",
            pv_value,
            f"Potencia PV instantánea · reg 850 · {modbus_note}",
            accent=METRIC_ACCENTS["solar"],
        )
    with col5:
        render_metric_card(
            "Potencia Batería",
            bat_value,
            f"{bat_detail} · reg 842 · {modbus_note}",
            accent=METRIC_ACCENTS["battery"],
        )
    with col6:
        render_metric_card(
            "Potencia de Red",
            grid_value,
            f"{grid_detail} · reg 820 · {modbus_note}",
            accent=METRIC_ACCENTS["grid"],
        )

    render_status_panel(level, message)

    source_label = {
        "simulated": "telemetría simulada",
        "modbus": "Victron Modbus TCP en vivo",
        "modbus_error": "Modbus con fallback simulado",
    }.get(telemetry["source"], telemetry["source"])

    st.markdown(
        f"""
        <div class="footer-bar">
            Última actualización: {now} · Muestreo cada {cfg["sample_interval_s"]}s · Modo: {mode} · Fuente: {source_label}
        </div>
        """,
        unsafe_allow_html=True,
    )


def main():
    st.set_page_config(
        page_title="B-Intelligent — BMS Cloud Auditor",
        page_icon="🔋",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    cfg = load_configuration()
    default_index = 0 if cfg.get("default_mode", "simulated") == "simulated" else 1

    with st.sidebar:
        st.markdown(
            '<p style="font-size:0.72rem;font-weight:800;letter-spacing:0.12em;'
            f'color:{COLOR_ACCENT};text-transform:uppercase;margin-bottom:0.2rem;">Panel de Control</p>',
            unsafe_allow_html=True,
        )
        mode = st.selectbox(
            "Modo operativo",
            [MODE_SIM, MODE_REAL],
            index=default_index,
            key="bintelligent_mode",
        )
        st.caption("Recarga la página (F5) tras cambiar de modo.")
        st.markdown("---")
        st.markdown(f"**Gateway:** `{cfg['victron_ip']}`")
        st.markdown(f"**Intervalo:** `{cfg['sample_interval_s']} s`")
        st.markdown(f"**Batería:** `{cfg.get('battery_capacity_kwh', 10)} kWh`")
        wa = "✅ Activas" if cfg.get("whatsapp_alerts_enabled") else "❌ Off"
        wa_color = "#00ff88" if cfg.get("whatsapp_alerts_enabled") else "#ff6b6b"
        st.markdown(
            f'**WhatsApp:** <span style="color:{wa_color};font-weight:700;">{wa}</span>',
            unsafe_allow_html=True,
        )

    cell_health_panel = st.sidebar.empty()
    dashboard = st.empty()
    interval = cfg["sample_interval_s"]

    while True:
        telemetry = fetch_telemetry(mode, cfg)
        with cell_health_panel.container():
            render_cell_health_sidebar(telemetry, cfg)
        with dashboard.container():
            render_dashboard(cfg, mode, telemetry)
        time.sleep(interval)


if __name__ == "__main__":
    main()
