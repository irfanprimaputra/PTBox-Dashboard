# 📦 PT Box — Canonical Files (Single Source of Truth)

**Current version:** `e37` · OOS validated 316% · Live-ready
**Last updated:** 2026-05-05

> Aturan: setiap iterasi PT Box, update file ini supaya new conversation tidak bingung.
> Kalau lu liat file di luar list ini → itu ARCHIVE / EXPERIMENT, jangan dipake live.

---

## 🟢 LIVE FILES (yang dipake production)

### 1. TradingView Indicator
```
✅ code/pinescripts/PTBox_e37.pine
```
- Pine v6, 898 lines
- Title: `"PT Box e37 (live · OOS 316%)"`
- Symbol: XAUUSD · Timeframe: M1 · Chart timezone: UTC-4

### 2. MetaTrader 5 Indicator
```
✅ code/mql5/PTBox_e37.mq5
```
- MQL5, 476 lines
- Mac via Rosetta/Wine compatible
- Configure `ET_GMTOffset` (-4 EDT / -5 EST) + `Broker_GMTOffset`

### 3. Python Backtest Engine
```
✅ code/ptbox_engine_e37.py            ← consolidated canonical engine
```
Wrapper around `ptbox_quarterly_v3.py` core + e37-specific session backtest functions.
For ad-hoc sweeps: `scripts/run_london_5pt_target.py` shows pattern.

### 4. Trade Data
```
✅ data/ptbox_e37_trades.csv           ← 2433 trades (5y), used by Trade Analytics page
```

### 5. OOS Validation
```
✅ data/phase7_e37_oos_validation.json ← retention 316%, 10/10 quarters positive
```

### 6. Sweep Results (e37 baseline)
```
✅ data/phase7_e37_extended.json          ← Asia + NY top10
✅ data/phase7_e37_london_extended.json   ← London top15
✅ data/phase7_london_5pt_target.json     ← 5pt SL investigation (NOT adopted)
```

### 7. Vault Master Doc
```
✅ ~/Documents/Obsidian/Irfan-Vault/03-Trading/01-Forex/Strategies/PT-Box/00-PT-Box-System.md
```

### 8. Streamlit Dashboard
```
✅ app.py                                  ← home (e37 hero)
✅ pages/1_🎯_Live_Deploy.py               ← session times Asia 18-00, London 0-8, NY 7-12 ET
✅ pages/2_🚀_Phase7_Results.py            ← Phase 7 timeline + OOS callout
✅ pages/3_📊_Trade_Analytics.py           ← uses ptbox_e37_trades.csv
```

---

## 📊 e37 CONFIG (locked)

| Session | Box | Model | SL | TP | Body | PnL 5y | WR |
|---|---|---|---|---|---|---|---|
| 🟢 Asia | 18:00/90m ET | DIRECT | 0.7×bw, min 3pt | 1.5R | 0% | +1839 | 61% |
| 🔵 London | 00:00/60m ET | DIRECT | 0.5×bw, min 3pt | 2.0R | 20% | +3220 | 62% |
| 🟡 NY | 07:00/60m ET | DIRECT | 0.5×bw, min 3pt | 2.5R | 30% | +4025 | 58% |
| **TOTAL** | | | | | | **+9084** | |

**OOS:** Train 2021-2023 → Test 2024-2026 = +6428 OOS / 316% retention / 10/10 Q positive
**Live estimate:** ~$2200-3630/yr at lot 0.02 / cap $200

---

## 📦 ARCHIVE (do NOT use live)

```
code/pinescripts/_archive/
  Asia.md, London.md, NY.md, Index.md     ← pre-Phase7 docs (now in vault)
  PTBox_e37_strategy.pine                 ← strategy variant (rejected, indicator preferred)

code/_archive/
  ptbox_backtest.py                       ← pre-Phase7
  ptbox_quarterly.py                      ← v1
  ptbox_quarterly_v2.py                   ← v2
  ptbox_quarterly_v4.py                   ← extends v3 (v3 is canonical core)
  ptbox_quarterly_v5.py                   ← incomplete
  ptbox_run.py                            ← pre-Phase7
  ptbox_v6_trade_export.py                ← export utility, used once

scripts/_archive/
  run_phase7_e16..e26 (11 files)          ← iteration history
  run_phase7_ny_variants.py               ← pre-e16
  run_phase7_variants.py                  ← pre-e16
```

Active scripts kept at `scripts/` root:
- `run_phase7_oos_robustness.py` — OOS validation runner
- `regime_stability_monitor.py` — quarterly health check
- `run_london_5pt_target.py` — London SL sweep (latest experiment)
- `refresh-data.sh` — data pipeline

---

## 🔄 ITERATION JOURNEY (e20d → e37)

```
e20d  baseline                       +976
e26   NY iterations                  +~1200
e27e  NY strict + body50%            +1422  (+314)
e30   timing 9:07/10m                +1662  (+240)
e31   NY TP=6R → TP=2.5R             +2964  (+1302) ⚡
e32   Wyckoff pre-session 07:00/60m  +3691  (+727)  ⚡
e33   NY any pattern + body30%       +4025  (+334)
e35   London DIRECT + 00:00/60m      +5086  (+1061)
e36   ALL 3 sessions DIRECT          +8192  (+3106) ⚡
e37   extended session windows       +9084  (+892)  ⭐ CURRENT
```

**Investigations (not adopted):**
- `e38` London FLAT 5pt SL → would lose -612 PnL for zero edge gain. STAYED e37.

---

## 🛠️ HOW TO ITERATE (next time)

1. Run sweep script di `scripts/` (template: `run_london_5pt_target.py`)
2. Save result JSON ke `data/phase7_<id>_*.json`
3. **Decision:** adopt or reject?
4. **If adopt:**
   - Update `code/pinescripts/PTBox_e37.pine` (or rename to next version)
   - Update `code/mql5/PTBox_e37.mq5`
   - Update `code/ptbox_engine_e37.py`
   - Update Streamlit dashboards (home + Phase7)
   - Update vault `00-PT-Box-System.md` changelog
   - Update **THIS FILE** (canonical refs)
5. **If reject:** add line to "Investigations not adopted" section above
6. Commit (single commit covers all 3 targets)
7. Refresh clipboard + Downloads for Pinescript

---

## 💡 WHY THIS FILE EXISTS

Sebelumnya file naming chaos:
- `PTBox_e20d.pine` ternyata isinya e37 → bingung
- 8 Python engine files, ga jelas mana yang final
- 11 script Phase 7 iteration mixed dengan active scripts
- New conversation Claude harus discover ulang setiap kali → wasted context + hallucination risk

**Solusi:** file ini = first thing baca tiap new conversation. Auto-memory `ptbox_canonical_files` pin ke MEMORY.md root.
