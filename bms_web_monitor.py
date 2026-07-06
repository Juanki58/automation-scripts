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

COLOR_BG = "#0a1628"
COLOR_SURFACE = "#132238"
COLOR_BORDER = "#2a4a72"
COLOR_TEXT = "#f0f4f8"
COLOR_TEXT_MUTED = "#8fa3bf"
COLOR_ACCENT = "#00d4aa"
COLOR_GREEN = "#00e676"
COLOR_YELLOW = "#ffc107"
COLOR_RED = "#ff5252"
COLOR_GREEN_DARK = "#0d4d2a"
COLOR_SOC_ON = "#ff8c00"
COLOR_SOC_ON_GLOW = "#ffb347"
COLOR_SOC_OFF = "#152238"
SOC_BAR_SEGMENTS = 20


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

    st.markdown("---")
    st.subheader("🏥 Salud del Banco LiFePO4")
    st.caption(f"Fuente: {source} · {len(voltajes)} celdas · media {salud['media_v']:.3f} V")

    if salud["tipo_alerta"] == "success":
        st.success(f"Estado: {salud['estado']}")
    elif salud["tipo_alerta"] == "info":
        st.info(f"Estado: {salud['estado']}")
    elif salud["tipo_alerta"] == "warning":
        st.warning(f"Estado: {salud['estado']}")
    else:
        st.error(f"Estado: {salud['estado']}")

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


def inject_corporate_theme():
    st.markdown(
        f"""
        <style>
            .stApp {{ background-color: {COLOR_BG}; color: {COLOR_TEXT}; font-family: Helvetica, Arial, sans-serif; }}
            [data-testid="stHeader"], [data-testid="stToolbar"] {{ background: rgba(10, 22, 40, 0.95); }}
            [data-testid="stSidebar"] {{ background-color: {COLOR_SURFACE}; }}
            [data-testid="stSidebar"] * {{ color: {COLOR_TEXT} !important; }}
            .block-container {{ padding-top: 1.5rem; max-width: 960px; }}
            .brand-tag {{ color: {COLOR_ACCENT}; font-size: 0.85rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; }}
            .brand-title {{ color: {COLOR_TEXT}; font-size: 2.2rem; font-weight: 700; margin: 0 0 0.4rem 0; }}
            .brand-subtitle {{ color: {COLOR_TEXT_MUTED}; font-size: 0.95rem; margin-bottom: 1rem; }}
            .soc-card {{ background: {COLOR_SURFACE}; border: 1px solid {COLOR_BORDER}; border-radius: 14px; padding: 1.2rem 1.5rem; margin-bottom: 1rem; }}
            .soc-label {{ color: {COLOR_ACCENT}; font-size: 0.8rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; }}
            .soc-value {{ color: {COLOR_TEXT}; font-size: 2.4rem; font-weight: 700; margin: 0.3rem 0 0.6rem 0; }}
            .soc-segments {{
                display: flex;
                gap: 5px;
                width: 100%;
                height: 36px;
                margin: 0.6rem 0 0.35rem 0;
            }}
            .soc-seg {{
                flex: 1;
                border-radius: 5px;
                min-height: 36px;
                transition: background 0.3s ease;
            }}
            .soc-seg-on {{
                background: linear-gradient(180deg, {COLOR_SOC_ON_GLOW} 0%, {COLOR_SOC_ON} 100%);
                box-shadow: 0 0 8px rgba(255, 140, 0, 0.45);
            }}
            .soc-seg-off {{
                background: {COLOR_SOC_OFF};
                border: 1px solid {COLOR_BORDER};
                opacity: 0.85;
            }}
            .soc-scale {{
                display: flex;
                justify-content: space-between;
                color: {COLOR_TEXT_MUTED};
                font-size: 0.75rem;
                margin-top: 0.15rem;
            }}
            .autonomy-line {{
                color: {COLOR_ACCENT};
                font-size: 1.05rem;
                font-weight: 600;
                margin-top: 0.75rem;
            }}
            .flow-strip {{
                display: flex;
                justify-content: space-between;
                gap: 0.5rem;
                background: {COLOR_SURFACE};
                border: 1px solid {COLOR_BORDER};
                border-radius: 12px;
                padding: 0.9rem 1.2rem;
                margin-bottom: 1rem;
                font-size: 0.88rem;
                color: {COLOR_TEXT_MUTED};
            }}
            .flow-item {{ text-align: center; flex: 1; }}
            .flow-item strong {{ color: {COLOR_TEXT}; display: block; font-size: 1rem; margin-top: 0.2rem; }}
            .metric-card {{ background: {COLOR_SURFACE}; border: 1px solid {COLOR_BORDER}; border-radius: 14px; padding: 1.4rem 1.6rem; min-height: 170px; }}
            .metric-label {{ color: {COLOR_ACCENT}; font-size: 0.75rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; margin-bottom: 0.8rem; }}
            .metric-value {{ color: {COLOR_TEXT}; font-size: 2.6rem; font-weight: 700; line-height: 1; margin-bottom: 0.5rem; }}
            .metric-detail {{ color: {COLOR_TEXT_MUTED}; font-size: 0.92rem; }}
            .status-panel {{ border-radius: 16px; padding: 2rem 1.5rem; text-align: center; margin-top: 0.5rem; }}
            .status-title {{ font-size: 2rem; font-weight: 700; margin: 0; }}
            .status-subtitle {{ font-size: 0.95rem; margin-top: 0.6rem; opacity: 0.92; }}
            .footer-bar {{ background: {COLOR_SURFACE}; border: 1px solid {COLOR_BORDER}; border-radius: 10px; padding: 0.75rem 1rem; color: {COLOR_TEXT_MUTED}; font-size: 0.82rem; margin-top: 1rem; }}
            .alert-bar {{ background: #4a1212; border: 1px solid {COLOR_RED}; border-radius: 10px; padding: 0.6rem 1rem; color: {COLOR_TEXT}; font-size: 0.85rem; margin-bottom: 0.8rem; }}
            #MainMenu, footer, header {{ visibility: hidden; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_soc_card(soc: float, autonomy_hours: float | None, capacity_kwh: float):
    segment_bar = build_soc_segment_bar(soc)
    autonomy_text = format_autonomy(autonomy_hours)
    st.markdown(
        f"""
        <div class="soc-card">
            <div class="soc-label">Estado de Carga</div>
            <div class="soc-value">⚡ SoC: {soc:.1f}%</div>
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
            <div class="flow-item">☀️ Solar<strong>{format_power_watts(pv)}</strong></div>
            <div class="flow-item">🏠 Consumo<strong>{format_power_watts(load)}</strong></div>
            <div class="flow-item">🔋 Batería<strong>{format_power_watts(bat)}</strong></div>
            <div class="flow-item">🔌 Red<strong>{format_power_watts(grid)}</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(label: str, value: str, detail: str):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-detail">{detail}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_panel(level: str, message: str):
    if level == "STABLE":
        bg, border, subtitle = COLOR_GREEN_DARK, COLOR_GREEN, "Sin alertas activas en la planta"
    elif level == "WARNING":
        bg, border, subtitle = "#4a3f00", COLOR_YELLOW, "Acción preventiva recomendada"
    else:
        bg, border, subtitle = "#4a1212", COLOR_RED, "Contramedida Modbus activada o requerida"

    st.markdown(
        f"""
        <div class="status-panel" style="background:{bg}; border:2px solid {border};">
            <p class="status-title" style="color:{COLOR_TEXT};">{message}</p>
            <p class="status-subtitle" style="color:{COLOR_TEXT};">{subtitle}</p>
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
        cell_note = modbus_note
        render_metric_card(
            "Voltaje de Celdas",
            f"{v_max:.2f} V",
            f"Mínima: {v_min:.2f} V · Δ celda: {(v_max - v_min) * 1000:.0f} mV · {cell_note}",
        )
    with col2:
        render_metric_card(
            "Temperatura del Pack",
            f"{t_max:.1f} °C",
            f"Mínima: {t_min:.1f} °C · Rango: {t_max - t_min:.1f} °C",
        )
    with col3:
        render_metric_card("Consumo de la Casa", power_value, f"{power_detail} · reg 817")

    col4, col5, col6 = st.columns(3, gap="medium")
    with col4:
        render_metric_card("Producción Solar", pv_value, f"Potencia PV instantánea · reg 850 · {modbus_note}")
    with col5:
        render_metric_card("Potencia Batería", bat_value, f"{bat_detail} · reg 842 · {modbus_note}")
    with col6:
        render_metric_card("Potencia de Red", grid_value, f"{grid_detail} · reg 820 · {modbus_note}")

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
        st.markdown("### ⚙ Panel de Control")
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
        st.markdown(f"**WhatsApp:** {wa}")

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
