# Automation & System Scripts Portfolio

Welcome to my public repository. This space is dedicated to showcasing clean, production-ready automation scripts, data pipelines, and system configurations designed to optimize business workflows and system efficiency.

## 📂 Repository Structure

```
automation-scripts/
├── solar-telemetry/        # Victron GX, BMS LiFePO4, monitorización industrial
├── api-integrations/       # WhatsApp Cloud API y alertas modulares
├── market-analysis/        # Seguimiento financiero y métricas de mercado
├── automation-utilities/   # Herramientas mecánicas (imagen → STL 3D)
├── requirements.txt
└── README.md
```

## 📊 Repository Contents

### 1. Solar Telemetry (`solar-telemetry/`)

Industrial monitoring, Victron inverter control, and LiFePO4 battery management.

| Script | Description |
|--------|-------------|
| `victron_industrial_bms_safety.py` | Closed-loop safety supervisor: JK BMS telemetry → Victron GX countermeasures over Modbus TCP |
| `bms_web_monitor.py` | Real-time Streamlit dashboard (Modbus live + simulation) |
| `bms_gui_monitor.py` | Desktop tkinter panel for BMS health monitoring |
| `config.example.json` | Template for plant IP, thresholds, and alert settings |

**Victron BMS safety supervisor:**
```bash
# Copy config.example.json → config.json and edit your Cerbo GX IP
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

### 3. Market Analysis (`market-analysis/`)

Financial tracking tools and market data automation.

| Script | Description |
|--------|-------------|
| `data_processor.py` | Cleans raw price feeds and calculates volatility, averages, peaks, and drops |

**Market data automation:**
```bash
python market-analysis/data_processor.py
```

### 4. Automation Utilities (`automation-utilities/`)

Mechanical / manufacturing helpers.

| Script | Description |
|--------|-------------|
| `convert_to_3d.py` | Downloads shield PNG (if missing) and converts to relief STL |
| `image_to_stl.py` | Color-segmented image → 3D STL converter (OpenCV) |
| `image_8ff221.png` | Input image for the El Vendrell shield (place in this folder) |

**Image to STL:**
```bash
cd automation-utilities
python convert_to_3d.py
# or
python image_to_stl.py image_8ff221.png -o escudo_vendrell_3d.stl --pixel-size 0.3
```

## 🛠️ Tech Stack & Skills Demonstrated

*   **Languages:** Python (core logic, math operations, and data structures).
*   **Methodologies:** Data engineering pipelines, robust exception/error handling, closed-loop control, and algorithmic efficiency.
*   **Systems & Automation:** Modbus TCP industrial fieldbus, Victron Venus OS / Cerbo GX integration, BMS telemetry gateways, API data integrations, and headless server environments (Linux, Docker, Home Assistant ecosystems).

## 🚀 Setup

Clone the repository and install dependencies:

```bash
pip install -r requirements.txt
```
