# PT Box Research Lab — Local Dashboard

Streamlit dashboard untuk PT Box research workflow — iteration history, config inspection, code browser.

## Quick Start

```bash
cd ~/Documents/PTBox-Dashboard
streamlit run app.py
```

Open browser: http://localhost:8501

## Pages

1. **🏠 Home (`app.py`)** — Current best metrics + navigation
2. **📋 Timeline** — All iterations e001-e013, PnL progression chart, filterable cards
3. **🔍 Detail** — Drill into specific iteration: per-session bars, equity curve, per-Q table, config, code reference
4. **🆚 Compare** — Side-by-side delta between 2 iterations with overlay equity curve
5. **💻 Code Library** — Browse Pinescript / MQL5 / Python source

## Data Sources

- `~/Downloads/ptbox_phase4_experiments.csv` — master registry
- `~/Downloads/ptbox_phase4_*.csv` — per-Q results Phase 4
- `~/Downloads/ptbox_phase5_*.csv` — per-Q results Phase 5
- `Vault/.../PT-Box/Implementation/*.md` — Pinescript notes
- `~/Downloads/PTBox_*.mq5` — MQL5 source
- `~/Downloads/ptbox_quarterly_v*.py` — Python engines

## Stack

- Python 3.9.6
- Streamlit 1.50
- Plotly 6.7
- Pandas 2.3

## Update

Restart Streamlit untuk reload data after running new backtest. Cache otomatis invalidate.
