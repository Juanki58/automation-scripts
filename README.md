# Automation & System Scripts Portfolio

Welcome to my public repository. This space is dedicated to showcasing clean, production-ready automation scripts, data pipelines, and system configurations designed to optimize business workflows and system efficiency.

## 📊 Repository Contents

### 1. Market Data Automation (`data_processor.py`)
A Python-based automation script designed to clean and process raw financial or operational data feeds.
*   **Key Features:** Automated data cleaning (handling type errors and anomalies), calculation of core metrics (Moving averages, price volatility, peaks, and drops), and simulated real-time API feed processing.
*   **Use Case:** Ideal for businesses looking to automate daily market reporting, portfolio risk analysis, or data pipeline optimization without manual oversight.

### 2. System Health & Backup Monitor (`system_monitor_backup.py`)
Proactive infrastructure monitoring script with automated backup and alerting capabilities.
*   **Key Features:** Disk usage health checks, compressed tarball backups, and WhatsApp Cloud API alerts when disk usage exceeds 90%.
*   **Use Case:** Headless server maintenance, DevOps monitoring routines, and automated log archival.

### 3. Victron Industrial BMS Safety Supervisor (`victron_industrial_bms_safety.py`)
Closed-loop safety supervisor for photovoltaic plants that protects the battery bank by acting on Victron Energy equipment in real time.
*   **Architecture:** Reads cell-level telemetry from a **JK BMS** (via Modbus RTU, MQTT, or corporate API gateway) and writes active countermeasures to a **Color Control GX / Cerbo GX** over **Modbus TCP** (port 502).
*   **Key Features:**
    *   Continuous 5-second sampling loop with industrial-grade logging.
    *   Configurable safety thresholds via `config.json` (cell voltage, temperature limits).
    *   Active mitigation: charge/discharge current limits and emergency inverter shutdown through Victron holding registers (2704, 2705, 2706).
    *   Thermal protection (emergency shutdown above 55 °C, zero charge current below 0 °C).
    *   Individual cell protection against overvoltage, warning-level charge reduction, and deep-discharge prevention.
*   **Use Case:** Industrial PV + storage installations where the JK BMS is the source of truth for cell health and the Victron GX gateway must enforce safety limits on inverters and chargers without human intervention.

## 🛠️ Tech Stack & Skills Demonstrated
*   **Languages:** Python (Core logic, math operations, and data structures).
*   **Methodologies:** Data engineering pipelines, robust exception/error handling, closed-loop control, and algorithmic efficiency.
*   **Systems & Automation:** Modbus TCP industrial fieldbus, Victron Venus OS / Cerbo GX integration, BMS telemetry gateways, API data integrations, and headless server environments (Linux, Docker, Home Assistant ecosystems).

## 🚀 How to Run the Scripts
Clone the repository and install dependencies:
```bash
pip install -r requirements.txt
```

**Market data automation:**
```bash
python data_processor.py
```

**System health monitor:**
```bash
python system_monitor_backup.py
```

**Victron BMS safety supervisor:**
```bash
# Edit config.json with your Cerbo GX IP and safety thresholds
python victron_industrial_bms_safety.py
```
