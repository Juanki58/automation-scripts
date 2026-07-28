# Market Analysis — Ambiq (AMBQ)

**Servicio separado del monitor BMS solar.** No comparte código, config ni puerto con `solar-telemetry/`.

| Servicio | Carpeta | URL por defecto |
|----------|---------|-----------------|
| Monitor baterías / Victron / JK | `solar-telemetry/` | `http://0.0.0.0:8501` |
| Monitor Ambiq / mercado | `market-analysis/` | `http://127.0.0.1:8502` |

## Arranque

```powershell
cd market-analysis
copy config.example.json config.json
pip install yfinance
python -m streamlit run ambiq_monitor.py
```

O desde la raíz del repo:

```powershell
python -m streamlit run ambiq_monitor.py
```

Abre **http://127.0.0.1:8502** (solo este equipo; no expuesto en la red de planta).

## Configuración (`config.json`)

- `bind_host` — `127.0.0.1` (local) u otra IP si quieres exponerlo en otra interfaz
- `bind_port` — `8502` (nunca usar 8501, reservado al BMS)
- `ticker` — `AMBQ`
- `history_period` — ventana para yfinance (`3mo`, `6mo`, `1y`, …)
- `refresh_seconds` — auto-refresco del dashboard
