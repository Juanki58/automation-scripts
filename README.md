# Automation & System Scripts Portfolio

Welcome to my public repository. This space is dedicated to showcasing clean, production-ready automation scripts, data pipelines, and system configurations designed to optimize business workflows and system efficiency.

> **Repo boundary:** this tree is **not** the Victron/JK BMS app and **not** NaviCore INS.  
> Full BMS code: [`solar-telemetry`](https://github.com/Juanki58/solar-telemetry).  
> Navigation: [`NaviCore-3D`](https://github.com/Juanki58/NaviCore-3D).  
> Details: [`docs/REPO_BOUNDARY.md`](docs/REPO_BOUNDARY.md).

## Servicios separados (no mezclar)

| Qué | Dónde | URL / puerto |
|-----|-------|----------------|
| **Monitor baterías / Victron / JK BMS** | Repo hermano [`solar-telemetry`](https://github.com/Juanki58/solar-telemetry) (stub local: `solar-telemetry/`) | `http://127.0.0.1:8501` |
| **Ambiq / mercado (AMBQ)** | `market-analysis/` | `http://127.0.0.1:8502` |

Cada producto tiene su propio repo o carpeta, `config.json` y puerto Streamlit.

---

## Repository Structure

```
automation-scripts/
├── solar-telemetry/        # STUB → apunta al repo Juanki58/solar-telemetry
├── api-integrations/       # WhatsApp Cloud API y alertas modulares
├── market-analysis/        # Seguimiento financiero y métricas de mercado
├── automation-utilities/   # Herramientas mecánicas (imagen → STL 3D)
├── business-tools/         # Generadores de documentación comercial (demo)
├── scripts/windows/        # Autostart (lanza sibling solar-telemetry + Ambiq)
├── docs/REPO_BOUNDARY.md
├── requirements.txt
└── README.md
```

## Repository Contents

### 1. Solar Telemetry (external repo)

**Source of truth:** https://github.com/Juanki58/solar-telemetry  
**Local (recommended):** `C:\Users\juanc\projects\solar-telemetry`

The folder `solar-telemetry/` here is only a pointer. Do not copy BMS modules back into this repo.

```powershell
cd ..\solar-telemetry
.\scripts\windows\Start-BIntelligent.bat
```

Compat launcher from this repo (if sibling checkout exists):

```bash
python bms_web_monitor.py
```

### 2. API Integrations (`api-integrations/`)

| Script | Description |
|--------|-------------|
| `whatsapp_alerts.py` | Sends approved WhatsApp template alerts via Meta Cloud API |
| `system_monitor_backup.py` | Disk health checks, tarball backups, WhatsApp alerts above 90% usage |

```bash
python api-integrations/system_monitor_backup.py
```

### 3. Market Analysis (`market-analysis/`)

**Solo finanzas — Ambiq (AMBQ).** Puerto y host distintos al BMS.

| Script | Description |
|--------|-------------|
| `ambiq_monitor.py` | Dashboard Streamlit de cotización AMBQ |
| `ambiq_data.py` | Descarga datos vía yfinance |
| `data_processor.py` | Métricas de mercado |
| `config.example.json` | Host `127.0.0.1`, puerto `8502` |

```bash
streamlit run market-analysis/ambiq_monitor.py
# → http://127.0.0.1:8502
```

Ver `market-analysis/README.md`.

### 4. Automation Utilities (`automation-utilities/`)

| Script | Description |
|--------|-------------|
| `convert_to_3d.py` | Downloads shield image (if missing) and converts to relief STL |
| `image_to_stl.py` | Image → 3D STL |

```bash
cd automation-utilities
python image_to_stl.py escudo3.0.jpeg -o escudo3.0_3d.stl --mode bw
```

### 5. Business Tools (`business-tools/`)

Demo commercial documentation generators (portfolio sample). The generated PDF is gitignored.

```bash
python business-tools/generar_dosier.py
```

> **Note:** Treat market claims in this demo as illustrative unless backed by a cited source.

### 6. Windows Autostart (`scripts/windows/`)

| Script | Description |
|--------|-------------|
| `start-plant-services.ps1` | Starts Docker/Home Assistant, sibling BMS monitor (:8501), Ambiq (:8502) |
| `stop-plant-services.ps1` | Stops BMS and Ambiq Streamlit processes (Docker untouched) |
| `register-autostart.ps1` | Creates scheduled task `PlantServices-Autostart` on login |

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\register-autostart.ps1
powershell -ExecutionPolicy Bypass -File scripts\windows\start-plant-services.ps1
powershell -ExecutionPolicy Bypass -File scripts\windows\stop-plant-services.ps1
```

Log: `%LOCALAPPDATA%\plant-services\startup.log`

## Setup

```bash
pip install -r requirements.txt
# BMS app: clone and install sibling repo solar-telemetry separately
```
