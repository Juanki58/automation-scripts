# Solar Telemetry — BMS & Victron

Monitor de **planta solar y salud de baterías LiFePO4**. No incluye finanzas ni seguimiento bursátil.

| Servicio | URL por defecto |
|----------|-----------------|
| **Este módulo (BMS)** | `http://0.0.0.0:8501` |
| Ambiq / mercado | `market-analysis/` → `http://127.0.0.1:8502` |

## Arranque

```powershell
cd solar-telemetry
copy config.example.json config.json
python -m streamlit run bms_web_monitor.py
```

## Scripts

| Archivo | Uso |
|---------|-----|
| `bms_web_monitor.py` | Dashboard web (SoC, celdas JK, salud LiFePO4) |
| `bms_gui_monitor.py` | Panel escritorio tkinter |
| `victron_industrial_bms_safety.py` | Protección activa Modbus Victron |
| `jk_bms_client.py` | Cliente JK BMS v19 |
