# Automation & System Scripts Portfolio

Welcome to my public repository. This space is dedicated to showcasing clean, production-ready automation scripts, data pipelines, and system configurations designed to optimize business workflows and system efficiency.

## Servicios separados (no mezclar)

| Qué | Carpeta | URL / puerto |
|-----|---------|----------------|
| **Monitor baterías / Victron / JK BMS** | `solar-telemetry/` | `http://0.0.0.0:8501` |
| **Ambiq / mercado (AMBQ)** | `market-analysis/` | `http://127.0.0.1:8502` |

Cada módulo tiene su propio `config.json`, README y puerto Streamlit.

---

## 📂 Repository Structure

```
automation-scripts/
├── solar-telemetry/        # Victron GX, BMS LiFePO4, monitorización industrial
├── api-integrations/       # WhatsApp Cloud API y alertas modulares
├── market-analysis/        # Seguimiento financiero y métricas de mercado
├── automation-utilities/   # Herramientas mecánicas (imagen → STL 3D)
├── business-tools/         # Generadores de documentación comercial (demo)
├── scripts/windows/        # Autostart y gestión de servicios Windows
├── requirements.txt
└── README.md
```

## 📊 Repository Contents

### 1. Solar Telemetry (`solar-telemetry/`)

Industrial monitoring, Victron inverter control, and LiFePO4 battery management.

| Script | Description |
|--------|-------------|
| `config_loader.py` | Shared config loader: unifies `victron_host` / `victron_ip` for all modules |
| `victron_industrial_bms_safety.py` | Closed-loop safety supervisor: JK BMS telemetry → Victron GX countermeasures over Modbus TCP |
| `bms_web_monitor.py` | Real-time Streamlit dashboard (Modbus live + simulation) |
| `bms_gui_monitor.py` | Desktop tkinter panel for BMS health monitoring |
| `jk_bms_client.py` | JK BMS TCP client with failure cache and simulation fallback |
| `config.example.json` | Template for plant IP (`victron_host`), thresholds, and alert settings |

**Victron BMS safety supervisor:**
```bash
# Copy config.example.json → config.json and edit your Cerbo GX IP (victron_host)
python solar-telemetry/victron_industrial_bms_safety.py
```

**BMS web monitor (Streamlit):**
```bash
streamlit run solar-telemetry/bms_web_monitor.py
```

### 2. API Integrations (`api-integrations/`)

WhatsApp Cloud API integration and modular alerting.

| Script | Description |
|--------|-------------|
| `whatsapp_alerts.py` | Sends approved WhatsApp template alerts via Meta Cloud API |
| `system_monitor_backup.py` | Disk health checks, tarball backups, WhatsApp alerts above 90% usage |

**System health monitor:**
```bash
python api-integrations/system_monitor_backup.py
```

**BMS web monitor (Streamlit):**
```bash
streamlit run solar-telemetry/bms_web_monitor.py
# → http://0.0.0.0:8501
```

Ver `solar-telemetry/README.md`.

### 3. Market Analysis (`market-analysis/`)

**Solo finanzas — Ambiq (AMBQ).** Puerto y host distintos al BMS.

| Script | Description |
|--------|-------------|
| `ambiq_monitor.py` | Dashboard Streamlit de cotización AMBQ (precio, histórico, volatilidad) |
| `ambiq_data.py` | Descarga datos vía yfinance |
| `data_processor.py` | Métricas de mercado (media, volatilidad, extremos) |
| `config.example.json` | Host `127.0.0.1`, puerto `8502` |

**Ambiq market monitor:**
```bash
streamlit run market-analysis/ambiq_monitor.py
# → http://127.0.0.1:8502  (local, no comparte IP/puerto con la planta)
```

Ver `market-analysis/README.md`.

**Market data CLI (genérico):**
```bash
python market-analysis/data_processor.py
```

### 4. Automation Utilities (`automation-utilities/`)

Mechanical / manufacturing helpers.

| Script | Description |
|--------|-------------|
| `convert_to_3d.py` | Downloads shield image (if missing) and converts to relief STL |
| `image_to_stl.py` | Image → 3D STL (color segmentation or B/W with white cutout) |

**Image to STL:**
```bash
cd automation-utilities
python image_to_stl.py escudo3.0.jpeg -o escudo3.0_3d.stl --mode bw
```

### 5. Business Tools (`business-tools/`)

Demo commercial documentation generators (portfolio sample). The generated PDF is gitignored.

| Script | Description |
|--------|-------------|
| `generar_dosier.py` | Builds an investment dossier PDF for B-Intelligent (seed-round narrative demo) |

```bash
python business-tools/generar_dosier.py
```

> **Note:** Treat market claims in this demo as illustrative unless backed by a cited source. Do not present placeholder figures to real investors.

### 6. Windows Autostart (`scripts/windows/`)

Scheduled-task-based autostart for all plant services on Windows login.

| Script | Description |
|--------|-------------|
| `start-plant-services.ps1` | Starts Docker/Home Assistant, BMS monitor (:8501), Ambiq monitor (:8502) |
| `stop-plant-services.ps1` | Stops BMS and Ambiq Streamlit processes (Docker untouched) |
| `register-autostart.ps1` | Creates a Windows scheduled task (`PlantServices-Autostart`) to run on login |

**Register autostart (run once as your user):**
```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\register-autostart.ps1
```

**Manual start/stop:**
```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\start-plant-services.ps1
powershell -ExecutionPolicy Bypass -File scripts\windows\stop-plant-services.ps1
```

Log: `%LOCALAPPDATA%\plant-services\startup.log`

## 🛠️ Tech Stack & Skills Demonstrated

*   **Languages:** Python (core logic, math operations, and data structures).
*   **Methodologies:** Data engineering pipelines, robust exception/error handling, closed-loop control, and algorithmic efficiency.
*   **Systems & Automation:** Modbus TCP industrial fieldbus, Victron Venus OS / Cerbo GX integration, BMS telemetry gateways, API data integrations, and headless server environments (Linux, Docker, Home Assistant ecosystems).

## 🚀 Setup

Clone the repository and install dependencies:

```bash
pip install -r requirements.txt
```
