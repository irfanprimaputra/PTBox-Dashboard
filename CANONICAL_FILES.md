# 📦 PT Box — Canonical Files (Single Source of Truth)

**Current LIVE versions (split into 2 separate Pine files for clarity):**
- 🔵 `code/pinescripts/PTBox_e41_breakout.pine` — BREAKOUT mode (5y +3983 / WR 61% / OOS 9/10 Q+)
- 🌊 `code/pinescripts/PTBox_e44_pullback.pine` — PULLBACK mode (5y +4923 / WR 42% / max5 attempt / OOS 10/10 Q+) ⭐ RECOMMENDED
- 🔀 `code/pinescripts/PTBox_e37.pine` — combined toggle version (legacy, kept as backup)

**maxAttempt = 5 (2026-05-06 SYNC):** Pine default 1→5 to match Python backtest peak edge. At max5: $1,813/yr at 0.02 lot, worst single trade -$116. Better both PnL AND safety vs max1.

**Last updated:** 2026-05-10 (Pine v15 LIVE — BE Trail + V2 Asia Tight SL. Phase 40 stop rules + Phase 42 wider TP rejected. TP 1:2 confirmed optimal. 7× iron law.)

⚠️ **MAJOR CORRECTION 2026-05-05:** Engine had loss accounting bug under-counting
losses by ~bw per trade. True 5y PnL = **+3223** (was claimed +9084 inflated).
See "Pine v12" section below for details.

> Aturan: setiap iterasi PT Box, update file ini supaya new conversation tidak bingung.
> Kalau lu liat file di luar list ini → itu ARCHIVE / EXPERIMENT, jangan dipake live.

---

## 🟢 LIVE FILES (yang dipake production)

### 1. TradingView Indicators — SPLIT (2026-05-06)
```
✅ code/pinescripts/PTBox_e41_breakout.pine  (1082 lines, BREAKOUT mode)
✅ code/pinescripts/PTBox_e44_pullback.pine  (1193 lines, PULLBACK mode) ⭐ RECOMMENDED
⚠️ code/pinescripts/PTBox_e37.pine          (legacy combined-toggle, kept as backup)
```
- Pine v6 each
- e41 title: `"PT Box e41 BREAKOUT (5y +3983 · WR 61% · OOS 9/10 Q+)"`
- e44 title: `"PT Box e44 PULLBACK (5y +4301 · WR 35% · OOS 10/10 Q+ · 5.8× safer)"`
- Symbol: XAUUSD · Timeframe: M1 · Chart timezone: UTC-4
- Use ONE at a time on chart. e44 RECOMMENDED for $200 cap (psychology + safety).

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
⚠️ data/phase7_e37_oos_validation.json ← STALE: pre-v11 bugfix (claimed +6428 OOS / 316% retention)
✅ data/e37_validation_v11_20260422_20260505.json ← v11+ canonical, 11-day OOS Apr 22-May 5 2026
✅ data/e37_validation_v11_20260422_20260505.txt  ← human-readable report
```
**Note:** the 316% retention claim was based on inflated (v10) accounting and is invalidated.
Need new long-window (60-90 day) OOS run on engine v11+ before re-citing retention numbers.

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

## 📏 Phase 42 — Wider TP Sweep REJECTED

**Date:** 2026-05-10
**Status:** REJECTED — TP 1:2 confirmed OPTIMAL.
**Files:**
```
✅ scripts/run_phase42_wider_tp.py
✅ data/phase42_wider_tp_sweep.json
✅ Vault: ...Phase-42-Wider-TP-Sweep.md
```

**Test:** User question "what if TP dilebarin?" with BE Trail v14 active.
**7 variants:** TP 1:2 (current), 1:2.5, 1:3, 1:4, 1:5, 1:6, 1:8.

**Result:** ALL wider variants LOSE vs 1:2 baseline.

| TP mult | $/yr (rel) | TP hit % |
|---------|-----------:|---------:|
| 1:2 ⭐ | **best** | 15.6% |
| 1:3 | -$426 | 4.4% |
| 1:5 | -$599 | 0.3% |
| 1:8 | -$616 | 0.0% |

**Why:** Gold M1 jarang gerak >3R sebelum reverse. Wider TP = TP hardly ever hit. Trail catches LESS than 1:2 TP would have given.

Confirms Phase 36 pattern (cap SL + bigger TP also failed).

**Kill list (8 dead variants):** Wider TP, Cap SL ≤5pt, Tighter SL <3pt, Compound sizing, Filter sweeps (3×), Max consec/flip skip stop.

---

## 🛑 Phase 40 — Stop Rules Backtest + Live Plan

**Date:** 2026-05-10
**Status:** Pine v15 LIVE. Stop rules validated. Live plan documented.
**Files:**
```
✅ scripts/run_phase40_stop_rules_sim.py
✅ data/phase40_stop_rules_sim.json
✅ Vault: ...Backtest-Results/Phase-40-Stop-Rules-Backtest.md
✅ Vault: ...Setup/PT-Box-Live-Plan-Modal-Kecil.md
```

**Phase 40 Verdict (5y, lot 0.02):**
- ⭐ **Weekly stop -$100** = -2% income only (BEST balance)
- Daily stop -$50 = -7% (decent safety)
- Daily stop -$30 = -23% (too tight)
- ❌ Max 3 consecutive loss = -39% (DISASTER)
- ❌ Flip skip = -31% (worst day GETS WORSE -$209)

**7× IRON LAW**: filter/stop rules sering FAIL forward (e23/P16/e45/P21/P29/P39/**P40**).

**Final live plan modal $115:**
```
LOT 0.01 sampai modal $400
DAILY STOP -$25 / WEEKLY STOP -$50
NO consec loss rule, NO flip skip rule
```

**Pine v15 deployed:**
- Asia: 🛡️ V2 Tight SL (Phase 24 winner — worst -$10)
- London: e44 PB (unchanged)
- NY: e44 PB (unchanged)
- + BE Trail v14 (all 3 sessions)

---

## ❌ Phase 39 — Compound Sizing (Opsi B) REJECTED

**Date:** 2026-05-10
**Status:** REJECTED — Pine UNCHANGED. 6× IRON LAW confirmed.
**Files:**
```
✅ scripts/run_phase39_compound_sizing.py     ← 8-variant sweep
✅ data/phase39_compound_sizing.json
✅ Vault: ...Phase-39-Compound-Sizing-REJECTED.md
```

**Result:** ALL 8 variants fail Phase A gate (PnL Δ ≥ +30%). BEST = +2.2% boost ($37/yr extra). Tier-up rare karena P(3 consecutive wins at 42% WR) = 7.4% per cluster.

**Memo iterasi 2026-05-07 estimate +50% boost SALAH** — assumed every 3rd consecutive triggers immediate, ignored streak rarity at moderate WR.

**6× IRON LAW**: descriptive sizing/filter concepts often FAIL forward (e23/P16/e45/P21/P29/P39).

**Real income paths (validated):**
- Bump lot 0.02 → 0.03: +$860/yr
- Pro → Zero account: +$370-700/yr
- V2 Asia Tight SL (Phase 24): +$92/yr + 86% safer worst
- BE Trail v14 (deployed): +$48/yr + WR 35→51%

---

## 🤖 MT5 EA v14.1 — Pine v14 mirror (auto-execute)

**Date:** 2026-05-10
**Status:** LIVE PRODUCTION (95% Pine parity)
**Files:**
```
✅ code/mql5/PTBox_e44_v14.mq5                    ← 528 lines
✅ Vault: ...Setup/MT5-EA-v14-Setup.md             ← deploy + troubleshoot
```

**v14.1 Pine parity gap close:**
- maxAttempt 1 → 5 per session (was missing 80% setups)
- ATR filter (e38) skip <30th pctile
- TP boost (e39) 1.3× when ATR ≥72nd
- NY delay 25min (e40)
- Pattern detection: engulf+pin+hammer+inside (was engulf+pin only)
- Per-day ATR cache, attempt counter (replaces hadEntry bool)

**Reflection options (3 modes):**
1. **Standalone** ⭐ recommended — MT5 EA + Pine v14 jalan parallel same logic, $0 cost
2. Manual mirror — Pine alert HP → user manual click
3. PineConnector bridge — $5-19/mo full auto webhook

**Setup:** copy `~/Downloads/PTBox_e44_v14.mq5` to MT5 Experts folder → F4 MetaEditor → F7 compile → drag to XAUUSD M1 chart → set Broker_GMTOffset → ☺ active.

**Test demo 3 sesi (Asia + London + NY) sebelum live attach.**

---

## 🛡️ Pine v14 — BE TRAIL DEPLOYED (Phase 17 V5 winner)

**Date:** 2026-05-10
**Status:** LIVE — first BE Trail ever deployed to Pine production. Toggleable.
**Files:**
```
✅ code/pinescripts/PTBox_e44_pullback.pine   ← v14 (was v13)
✅ Vault: ...Pine-v14-BE-Trail-Deploy.md
```

**Mechanic:**
- Trade reach **+1×R favor** (default, configurable 0.5-2.0R) → SL otomatis pindah ke entry (BE)
- Setelah BE armed → SL trail follows running max(high)/min(low) by sl_distance
- Exit reason logged: `BE` (sl ~= entry) atau `TRAIL` (sl past entry profitable) atau `SL`/`TP`

**Backtest Phase 17 V5 (validated 2026-05-08):**
| Metric | e44 PB v13 | + BE Trail v14 | Δ |
|--------|-----------:|---------------:|--:|
| WR | 34.9% | **51.2%** | **+16.2pt 🚀** |
| 5y PnL | +$4,301 | +$4,349 | +$48 |
| Worst trade | -$74 | ~-$74 | sama |

**Inputs added:** `useBeTrail` (default true), `beTriggerR` (default 1.0), `beShowTrailLine` (default true)
**Trade struct extended:** `slOrig`, `beTriggered`, `runExtreme` (3 new fields)
**Visual:** SL line update real-time saat trail. Exit marker "🛡️ BE" (aqua) atau "🎯 TRAIL" (aqua).

**Mental impact:** Profit ga balik ke loss lagi. WR 51% feel = 5/10 menang vs 35% feel = 3/10 menang.

---

## 🌍 Phase 38 — Yearly Regime Split (Trump-2 Era Mental Matrix)

**Date:** 2026-05-10
**Status:** RESEARCH — mental framework regime-aware overlay. Pine UNCHANGED.
**Files:**
```
✅ scripts/run_phase38_regime_split.py     ← yearly trajectory split (sums 100%)
✅ data/phase38_regime_split.json
✅ Vault: ...Phase-38-Regime-Split-Trump2-Era.md
```

**Key Finding:** REGIME SHIFT Biden(2021-2024)→Trump-2(2025-2026):
- NO_MOVE: 60.4% → 19.4% (-41pp 🔻 chop dead)
- FLIP→SL: 3.1% → 15.1% (+12pp 🔺 whipsaw 5×)
- CLEAN→TP: 8.1% → 15.8% (+7.7pp 🔺 trend 2×)
- INSTANT→SL: 4.3% → 11.9% (+7.6pp)
- Income: $605/yr (2021) → $2,850/yr (2025) → ~$10K/yr 2026 run-rate

**Trump-2 Mental Matrix (per 10 trades, sums 100%):**
1.6 CLEAN→TP win + 1.5 FLIP→SL pain + 1.4 PROFIT_RETRACE (50/50) + 1.2 INSTANT→SL + 0.9 CLEAN→SL + 1.9 NO_MOVE + 0.6 FLIP→TP recovery (rare +$34!) + 0.8 other.

**Geopolitical overlay:** Tantrum → INSTANT+CLEAN binary; war → CLEAN→TP gold safe-haven; ceasefire → FLIP dump. Mental skip headlines escalate, NOT systematic filter (5× iron law).

**User 2026-05-08 -$49 cluster:** NORMAL Trump-era P75-P85, BUKAN system defect. Per-era expected ~2.7 pain slot per 10 trades.

---

## ⏰ Phase 35 — 24-Hour No-Session PT Box (CONDITIONAL WIN)

**Date:** 2026-05-09
**Status:** Conditional deploy IF + only IF Zero account adopted.
**Files:**
```
✅ scripts/run_24h_pt_box_test.py           ← 6-variant 24h test
✅ data/phase35_24h_pt_box_test.json
✅ Vault: ...Phase-35-24h-NoSession-PT-Box.md
```

**Key Finding:** PT Box session constraint = HIDDEN SPREAD MANAGEMENT. Removing session = more trades = spread eats edge (Pro tier). Switch Zero account → 24h V6 wins big.

| Setup | $/yr |
|-------|-----:|
| Pro + 3-session (current) | $932 |
| Pro + 24h V6 | $362 (LOSE) |
| Zero + 3-session | $1,576 |
| **Zero + 24h V6** | **$2,648** ⭐ |

Pro→Zero+24h = +185% income vs current.

---

## 🎯 Phase 34 — Mentor LuxAlgo Sessions (REJECTED)

**Date:** 2026-05-09
**Files:** `scripts/run_mentor_sessions_test.py` + `data/phase34_mentor_sessions_test.json`
**Result:** PT Box current WIN ALL 3 sessions vs mentor (Asia 17-24, London 3-7, NY 8-12 ET). Apple-to-apple TOTAL: PT Box +4,301 vs Mentor +1,842 = -$2,459. Mentor's tighter windows = less EOD edge captured.

---

## 🕯️ Phase 33 — Candle Pattern Classifier

**Date:** 2026-05-09
**Files:** `scripts/run_candle_pattern_classifier.py` + `data/phase33_candle_pattern_classifier.json`
**Result:** Entry bar 12+ patterns. MARUBOZU best WR 43.8%, INSIDE_BAR worst 38.1% (5.7pt spread). PIN BAR overrated baseline 41.7%. DOJI surprise 43.4%. Filter alone tidak material.

---

## ⚖️ Phase 32 — WIN vs LOSS Pattern Compare

**Date:** 2026-05-09
**Files:** `scripts/run_win_vs_loss_pattern_compare.py` + `data/phase32_win_vs_loss_compare.json`
**Result:** 19 features compare. ALL pre-entry Cohen d <0.15 (WEAK). Counter-intuitions: SL ≥5pt = +5.6pt WR, round numbers HELP. POST-ENTRY signals strong but Phase 21 cuts winners equally.

---

## 🎯 Phase 31 — Mentor 5min Box Test (REJECTED)

**Date:** 2026-05-09
**Files:** `scripts/run_mentor_5min_box_sweep.py` + `data/phase31_mentor_5min_box_sweep.json`
**Result:** ALL FAIL — best 60min +1,106 vs baseline +4,301 (-75% PnL). SL cap 3pt skip 50% setups. WR drops 42→28%.

---

## 🎯 Phase 30 — Loss Clustering Research

**Date:** 2026-05-09
**Files:** `scripts/run_loss_clustering_research.py` + `data/phase30_loss_clustering_research.json`
**Result:** Loss streaks RANDOM no autocorrelation. Min 25 ET worst loss density 64.7%. Round numbers HELP. Same-day post-loss next session BETTER (mean reversion). Mental rules only.

---

## ⏰ Phase 29 — SLOW_GRIND Filter Sweep (5× IRON LAW)

**Date:** 2026-05-09
**Status:** ALL 7 variants FAIL. 5× iron law confirmed.
**Files:** `scripts/run_slow_grind_filter_sweep.py` + `data/phase29_slow_grind_filter_sweep.json`
**Result:** Best T7 +$10/yr only. Iron Law: descriptive loss pattern ≠ exploitable forward filter. (e23/P16/e45/P21/P29 all fail same.)

---

## 🔬 Phase 28 — Entry-to-SL Bar Progression

**Date:** 2026-05-09
**Files:** `scripts/run_entry_to_sl_progression.py` + `data/phase28_entry_to_sl_progression.json`
**Result:** Bar-by-bar trace 6,567 trades. SLOW_GRIND = #1 loss killer (47.5%, median 41 bars). V_SHAPE_FAIL = 19.2% (BE Trail target). 60.3% SL hits >20 bars.

---

## 💸 Phase 27 — Exness Spread Reality Check (WEB-VERIFIED 2026)

**Date:** 2026-05-09
**Status:** Documentation. Spread numbers updated dari web search.
**Files:**
```
✅ Vault: 03-Trading/01-Forex/Strategies/PT-Box/Backtest-Results/Phase-27-Exness-Spread-Reality.md
```

**Real Exness XAUUSD Cost (2026):**
| Tier | Per Trade Cost (0.02 lot) | Net/yr |
|------|--------------------------:|-------:|
| Standard | $0.40-0.70 | low |
| Pro (real $0.10-0.20) | $0.022-0.32 range | **$1,150-1,545/yr** |
| Raw ($3.50/lot/side) | $0.14 | $1,536/yr |
| Zero ($2.50-5/side) | $0.10-0.20 | $1,457-1,589/yr |

**Key Finding:** My initial $0.30 Pro estimate LIKELY HIGH. Real Pro spread $0.10-0.20 likely. Tier switch advantage tipis ($0-200/yr) — Pro tier mungkin udah cukup murah.

**Action:** Verify live spread di Exness app.

---

## 💰 Phase 26 — Max Attempt × Spread Optimization

**Date:** 2026-05-09
**Status:** Documentation. Max=5 confirmed optimal all tiers.
**Files:**
```
✅ scripts/run_max_attempt_spread_optimization.py
✅ data/phase26_max_attempt_spread_optim.json
✅ Vault: ...Phase-26-Max-Attempt-Spread-Optimization.md
```

**KEY: Max=5 OPTIMAL all tiers. Reducing attempts = WORSE net.**

| Max | Pro Net/yr | Raw Net/yr | Zero Net/yr |
|----:|-----------:|-----------:|------------:|
| 1 | $304 | $452 | $510 |
| 3 | $729 | $1,097 | $1,275 |
| **5** | **$887** | **$1,310** | **$1,516** ⭐ |

**Why max=5 win**: later attempts higher WR (Phase 17), system filters quality, EOD edge needs volume.

---

## 🔀 Phase 25 — M5 Multi-TF Backtest (NOT ADOPT)

**Date:** 2026-05-09
**Status:** Tested, NOT adopt.
**Files:**
```
✅ scripts/run_m5_multitf_backtest.py
✅ data/m5_e44pb_backtest.json
✅ Vault: ...Phase-25-M5-MultiTF-Backtest.md
```

**Result M5 vs M1:**
- Trades: 3,889 vs 6,574 (-41%)
- PnL: +3,677 vs +4,301 (-624 lower)
- WR: 44.4% vs 42.1% (+2.3pt better)
- **Worst trade: -$203 vs -$74 (2.7× WORSE)**

NOT deploy standalone (lower PnL) atau paralel (worst-trade scary + 2× mental load).

---

## 🎯 Phase 24 — Asia BO + Tight SL Sweep (HYBRID CONCEPT, V2 WINNER)

**Date:** 2026-05-09
**Status:** Research, V2 winner identified, pending London + NY sweep + Pine v14 design.
**Files:**
```
✅ scripts/run_asia_e41_tight_sl_sweep.py     ← 8-variant Asia SL sweep
✅ data/phase24_asia_e41_tight_sl_sweep.json  ← machine-readable result
✅ Vault: 03-Trading/01-Forex/Strategies/PT-Box/Backtest-Results/Phase-24-Asia-Tight-SL-Sweep.md
```

**Test:** Asia direct breakout entry (e41 mechanic) + tight SL fixed cap (e44 mental). 8 SL variants tested.

**WINNER V2 (Asia BO + SL fixed 5pt):**
- PnL +664 (vs e44 PB Asia +572 = **+16% better**)
- WR 47.4% (vs e44 44.1% = +3.3pt)
- Worst trade -$10 (vs e44 -$74 = **7.4× SAFER!**)
- avg SL 5pt (mental cap match user goal)

**Hybrid SCENARIO 9 (V2 Asia + e44 London + e44 NY):** +4,393 vs e44 ALL +4,301 (+92 modest PnL gain, MASSIVE mental gain).

**Key Pattern:**
- Fixed-pt SL = mental cap (worst capped exactly at SL distance)
- Proportional SL exposed wide-box outliers (-$88 to -$147 worst at 0.5-0.7×bw)
- V1 too tight (4pt = whipsaw), V3-V5 over-cushion (6-8pt)
- V2 fixed 5pt = sweet spot

**Pending:** London + NY same-style sweep. Pine v14 per-session entry-mode patch design.

---

## 🌍 Phase 23 — EURUSD Multi-Asset Port (EDGE TRANSFER, WEAK)

**Date:** 2026-05-09
**Status:** Edge transferable but weaker per capital unit. Gold remains primary.
**Files:**
```
✅ scripts/run_eurusd_backtest.py         ← EURUSD 10y backtest harness
✅ data/eurusd_e44pb_backtest.json        ← per-trade ledger + summary
✅ pages/7_🌍_Multi_Asset.py              ← dashboard NEW page (gold vs EURUSD compare)
✅ Vault: 03-Trading/01-Forex/Strategies/PT-Box/Backtest-Results/Phase-23-EURUSD-Multi-Asset-Port.md
```

**Key Findings (5y APPLE-TO-APPLE 2021-2026):**
- EURUSD 5y total: +2,317 pips, WR 36.5%, PF ~1.05, +434 pips/yr
- NY dominant (+2,150 pips, PF 1.19), London NEAR-ZERO (+70, PF 1.01 degrading), Asia marginal (+96, PF 1.03)
- Gold capital efficiency 20× higher per capital unit (860% vs 43% annual return)
- Gold 2× per-yr at standard lot
- Recommend: $200 cap = gold-only. $1K+ = gold + EURUSD NY-only (skip Asia/London).

**Dashboard Cleanup (2026-05-09):**
- Resolved duplicate prefix `4_` (moved Code_Library to 8)
- Added Multi-Asset page (7)
- Renumbered archive pages 9-11
- Rewrote home page (app.py) with multi-asset hero + recent phases timeline + 7-rule constraints
- Final page order: 1=Live_Deploy · 2=Phase7_Results · 3=Trade_Analytics · 4=Strategy_Tester · 5=Macro_Sentiment · 6=Live_Journal · 7=Multi_Asset · 8=Code_Library · 9=Timeline_Archive · 10=Detail_Archive · 11=Compare_Archive

---

## 📔 Live Trading Journal (Dashboard Page 6)

**Date:** 2026-05-08
**Status:** Live record — track real broker trades vs backtest expectation.
**Files:**
```
✅ data/live_trades_journal.json                ← live trade ledger (editable)
✅ pages/6_📔_Live_Journal.py                   ← dashboard display + analytics
✅ Vault: 03-Trading/01-Forex/Strategies/PT-Box/Live-Journal/
```

**First entry:** 2026-05-08 Whipsaw Day Case Study — user lost $49.25 di 3 consecutive trades London/NY-pre. Pattern = WHIPSAW. 2.2× wider loss vs avg, P95-P99 worst-day percentile. Mental: NOT system defect, chop regime day.

To add new live trade days: edit `data/live_trades_journal.json` directly per template structure (date, label, regime_tag, trades[], daily_summary, pattern_decode, lessons).

---

## 🔬 Phase 22 — NFP/CPI/FOMC Day Impact (ACTIONABLE INSIGHT)

**Date:** 2026-05-08
**Status:** Documentation, actionable insight for tonight 8 May NFP.
**Files:**
```
✅ scripts/run_nfp_cpi_impact_analysis.py        ← macro day tagging + analysis
✅ data/phase22_nfp_cpi_impact.json              ← machine-readable result
✅ Vault: 03-Trading/01-Forex/Strategies/PT-Box/Backtest-Results/Phase-22-NFP-CPI-FOMC-Impact.md
```

**Key Findings:**
- NFP day historikal **+7.68 pts/day = 1.78× normal** (counter-intuitive)
- NY NFP WR **48.2%** vs normal NY 41.3%
- NY hour **10-11 ET = 60% WR** sweet spot
- Hour 9 ET avoid (37.5% WR transition noise)
- Worst-ever NFP single trade: -$37 at 0.02 lot
- Skip-NFP filter LOSES -78pts/yr

**Macro date derivation:**
- NFP: First Friday tiap bulan (deterministik)
- CPI: ~13th tiap bulan (BLS approximate)
- FOMC: hardcoded historical schedule 2021-2026

**Action: Trade NFP, jangan skip. NY hour 10-11 ET priority.**

---

## 🔬 Phase 21 — Early-Exit Sweep (HYPOTHESIS B BUSTED)

**Date:** 2026-05-08
**Status:** ALL 6 variants FAIL. 4× iron law confirmed (descriptive ≠ forward edge).
**Trigger:** User pain $50 London 3-attempt loss 2026-05-08
**Files:**
```
✅ scripts/run_early_exit_sweep.py        ← 6-variant early-exit harness
✅ data/phase21_early_exit_sweep.json     ← machine-readable result
✅ Vault: 03-Trading/01-Forex/Strategies/PT-Box/Backtest-Results/Phase-21-Early-Exit-Sweep.md
```

**Variants tested:**
- B1 cut bar+5 counter>3pt: Δ -939
- B2 bar+3>3pt: -763
- B3 bar+5>2pt: -1,235
- B4 bar+5>4pt: -541 (least drag)
- B5 bar+1>1pt: -1,491
- B6 combo: -1,594

**Why fail:** Filter cut WIN trades equally as losers. B1 decompose: save 425 from full SL (+2,125pts) but lose 167 winners (-1,670pts) + early-exit aggregate -1,633pts. Net -939.

**4× Iron Law confirmed:** e23 DoW skip + Phase 16 S1-S10 + e45 SMC + Phase 21 early-exit ALL fail same pattern. PT Box edge already absorbed at structural level.

**User real talk:** $50 lost = 25pt across 3 trades = 8.3pt avg/trade (wider than typical 3-5pt). 3-day sample too small. Daily loss clustering 72.5% days have ≥3 losses NORMAL. Bad cluster, not system defect.

**Strongest recommend:** equity protection -15% drawdown halt, lot reduction during streak loss, mode switch e44↔e41 variety. NO filter deployment.

---

## 🔬 Phase 20 — Candle Pattern Visual Forensic (HYPOTHESIS SOURCE)

**Date:** 2026-05-08
**Status:** 4 hypothesis surfaced. Phase 21 validation FAILED.
**Files:**
```
✅ scripts/run_candle_pattern_forensic.py   ← visual+trend feature extractor
✅ data/phase20_candle_pattern_forensic.json ← machine-readable result
✅ Vault: 03-Trading/01-Forex/Strategies/PT-Box/Backtest-Results/Phase-20-Candle-Pattern-Forensic.md
```

**Top predictive single-filter discovered:**
- Max counter 5-bar > 3pt = 81% loss rate (n=738) — HUGE skew
- Bar+1 counter > 1pt = 71% loss rate
- Bar+1 favor positive = 48% WR vs negative 36%

**Visual pattern verbal:**
- LOSS = weak entry candle + instant counter + 2× counter pressure
- WIN = strong body entry + immediate favor + 0.5× counter pressure

Phase 21 validate B-hypothesis → ALL FAIL. Lesson: descriptive ≠ forward edge.

---

## 🔬 Phase 19 — Loss Forensic Analysis (DATA-DRIVEN INSIGHT)

**Date:** 2026-05-08
**Status:** 5 hypothesis skip rules surfaced. PENDING validation. e44 baseline UNCHANGED.
**Files:**
```
✅ scripts/run_loss_forensic.py             ← multi-feature forensic harness
✅ data/phase19_loss_forensic.json          ← machine-readable result
✅ Vault: 03-Trading/01-Forex/Strategies/PT-Box/Backtest-Results/Phase-19-Loss-Forensic-Analysis.md
```

**Top 5 Patterns Found (3,807 losing trades 5y):**

1. **Trade Duration = Predictor #1** — Flash <5min=82% loss, Grind >60min=44% loss (56% WIN). Patience pays.
2. **Tight SL Paradox** — Tight 3-5pt=60% loss, Wide 8-12pt=45% loss. Counter-mental: tight retest whipsaws more.
3. **Hour 8 ET = WORST** (62.7% loss). NY pre-8:30 macro trap. Hour 7 ET = BEST 45.5%.
4. **Counter-trend pre-box** = 60% loss vs ALIGNED 56%.
5. **Februari = Worst Month** 62.9% loss (Q1 Fed/CPI cycle).

**Loss Distribution:** 95% < 8pt, max -36.9pt. Daily clustering 72.5% days ≥3 losses (NORMAL).

**5 Hypothesis Skip Rules (NOT auto-deployed):** Hold ≥60min, skip Hour 8 ET, skip counter-trend, avoid narrow box 5-10pt, Feb cautious. Phase 16 caveat: filter sweep mostly fails — these need validation.

---

## 🔬 Phase 18 — EOD Force-Close Impact Analysis (STRUCTURAL FINDING)

**Date:** 2026-05-08
**Status:** Documentation only. EOD force-close = STRUCTURAL EDGE source, BUKAN bug.
**Files:**
```
✅ scripts/run_eod_impact_analysis.py     ← 3-scenario harness
✅ data/phase18_eod_impact_analysis.json  ← machine-readable result
✅ Vault: 03-Trading/01-Forex/Strategies/PT-Box/Backtest-Results/Phase-18-EOD-Impact-Analysis.md
```

**Key Finding:** EOD force-close kontribusi 54% e44 PnL (+2,334 dari +4,301). Asia closed-only NEGATIF -19 — semua Asia edge dari EOD M-T-M. Live trader WAJIB manual force-close di session-end. Drop -19% PnL kalau "let SL/TP only".

**Live Trading Reality:**
- Manual close di session-end → +$1,720/yr at lot 0.02 ✓
- Natural SL/TP only → +$1,394/yr (-19%)

Pine `forceSessionEndClose` (lines 663-688) = essential mechanism, jangan dimatikan.

---

## 🔬 Phase 17 — BE Trail Sweep on e44 PB (RESEARCH, NOT DEPLOYED)

**Date:** 2026-05-08
**Status:** V5 winner found, NOT auto-deployed pending user decision.
**Files:**
```
✅ scripts/run_be_trail_sweep.py        ← 6-variant sweep harness
✅ data/phase17_be_trail_sweep.json     ← machine-readable result
✅ Vault: 03-Trading/01-Forex/Strategies/PT-Box/Backtest-Results/Phase-17-BE-Trail-Sweep.md
```

**Variants Tested (V0 baseline + V1-V6 BE variants):**
- V1 BE @ +1R, V2 BE @ +0.5R, V3 BE+1pt @ +1R, V4 BE @ +1.5R
- V5 TRAIL @ +1R then trail running extreme ⭐
- V6 BE @ opposite-box-edge

**Result:** V5 = +48 PnL / +16.2pt WR (34.9 → 51.2%) / worst trade unchanged. Best balance for user mental model. NOT auto-deployed; Pine port 2-3 jam effort if user gas. e44 baseline UNCHANGED.

---

## 🔬 Phase 16 — S1-S10 Session-Behaviour Filter Sweep (TESTED, ALL REJECTED)

**Date:** 2026-05-07
**Status:** All 10 filters fail PnL improvement on e41 baseline. Baseline UNCHANGED.
**Files:**
```
✅ scripts/run_S_filter_sweep.py     ← sweep harness (5y closed-only PnL)
✅ data/phase16_S1_S10_sweep.json    ← machine-readable result
✅ Vault: 03-Trading/01-Forex/Strategies/PT-Box/Backtest-Results/Phase-16-S1-S10-Filter-Sweep.md
```

**Filters tested (all Pinescript-implementable, no external news feed):**
- S1 Asia H/L → London/NY ±5pt level confluence
- S2 London H/L → NY ±5pt level confluence
- S3 Box breaks pre-box 15min OR
- S4 Pre-box 2h direction align
- S5 Skip NY if Asia+London chop signature
- S6 Skip lowest-25% ATR hour bucket ⭐ only WR/PF improver
- S7 NY entry 8-11 ET overlap window only
- S8 Asia tight (<12pt) → London/NY confluence
- S9 Asia false-break counter direction
- S10 Skip Asia after net-negative day

**Result:** Best Δ PnL = -103 (S5 near-neutral). S6 raises WR +1.3pt and PF +0.09 but PnL drops -22% from -30% trade count. **Filter layer saturation confirmed.** e41 baseline (+4145 closed / WR 60.9% / PF 1.63) unchanged.

**Insight:** PT box edge in REGIME + RISK + TIMING + SL layers; filter-on-top does not add edge. Saturation across all 4 layers (entry/SL/session/filter) now confirmed.

---

## 🔬 e45 — Pullback + SMC enhancements (TESTED, REJECTED)

**Status:** All 6 user-suggested SMC enhancements tested on top of e44 pullback. Only V4 FVG retest improved total PnL — but closed PnL DROPPED -1233. Edge degradation hidden by EOD M-T-M inflation. **REJECTED.**

**Sweep results (5y backtest):**
| Variant | Total | Closed | Δ e44 | Verdict |
|---|---|---|---|---|
| e44 baseline | +4301 | +1852 | 0 | reference |
| V4 FVG retest | +4743 | **+619** | +442 | ❌ closed edge collapsed |
| V1b close-extreme | +4133 | +1630 | -61 | ≈ neutral |
| V5 fib 38.2% | +4009 | +1028 | -186 | ❌ |
| V6 body≥50% | +3959 | +1708 | -236 | ❌ |
| V1a strict pin | +3502 | +819 | -693 | ❌ |
| V3 prior S/R | +3028 | +1414 | -1167 | ❌ over-filter |
| V2 prior box S/D | +2926 | +1382 | -1269 | ❌ over-filter |

**Lesson — V4 FVG trap:** total PnL improvement (+442) is artifact of EOD M-T-M drift (+1790) hiding closed PnL collapse (-1233). Same pattern as min_SL trap (e41 tier-4). Live trader can't reliably capture EOD-dependent edge with manual execution.

**Final stack: TWO modes only — e41 BREAKOUT + e44 PULLBACK.** No e45 deployed.

---

## 🔀 e44 PARALLEL — PULLBACK Entry Mode (psychology-friendly alternative)

**Status:** Deployed in Pine v13 as **toggleable mode**. e41 BREAKOUT remains default.

**Mechanics:** Instead of entering AT breakout (wide SL), wait for retest of box edge after breakout, enter on rejection (pin/engulf at S/R flip). Tight SL placement at retest extreme ± 2pt buffer.

**Config:**
- max_attempts = 5/session/day (vs e41 1)
- retest_tolerance = 3pt (price must come within 3pt of box edge)
- sl_buffer = 2pt
- tp_mult = 2.0 × actual_risk (true 1:2 R:R)
- max_wait_bars = 60 (timeout)

**5y backtest comparison:**
| Metric | e41 BREAKOUT | e44 PULLBACK |
|---|---|---|
| 5y Total PnL | +3983 | **+4301** (+8%) |
| WR | 60.9% | 34.9% (lower, expected for 1:2 R:R) |
| avg SL pts | 13.7 | **4.2** (3.3× tighter) |
| Max single loss | -216 (**$432**) | -37 (**$74**, 5.8× safer) |
| Trades over 5y | 1589 | 5203 (3.3× more) |
| Yearly USD est | $1467 | **$1584** |

**OOS validation (e44):**
- Train: +1195 (+388/yr) · Test: +3106 (+1322/yr) · Retention: 341%
- Test quarters: **10/10 positive** ✅ (vs e41 9/10)
- Verdict: PASS

**Per-session:**
- Asia: -19 (basically flat — pullback inefficient on slow Asia session)
- London: +679 (35.5% WR)
- NY: +1306 (best contributor, 36.3% WR)

**When to use which:**
- 🔵 **BREAKOUT (e41)** — high WR feels good, but $432 worst trade is dangerous
- 🌊 **PULLBACK (e44)** — capped per-trade risk ($74 max), more frequent action, but 65% losing days psychologically harder

**Pine toggle:** Settings → "🔀 Entry Mode (e41 vs e44)" → select BREAKOUT or PULLBACK

---

## 🔬 e42 RESEARCH (Tier-5 entry-trigger sweep — saturation reached)

**Status:** Research-validated, marginal gain (+45 pts), **NOT deployed to Pinescript** (deployment cost > value).

**Tested:** 15 entry-trigger refinements stacked on e41:
- Pullback / second-break entries: ALL FAILED (-1116 to -2067) — system designed for first break
- Pattern variants (engulf only, pin only, strong body, close-extreme): ALL FAILED (-452 to -1102)
- Continuation push distance (0.2-0.5×bw): ALL FAILED (-299 to -977)
- 3-bar momentum confirmation: FAILED (-476)
- Bar-delay after first break: ONLY winner — 3 bars = +45 (marginal)

**Lesson:** PT box edge is in REGIME (e38) + RISK (e39) + TIMING (e40, e41 NY/Asia start) + SL CALIBRATION (e41 London). Entry-trigger sophistication adds little. System already enters at near-optimal moment.

**e42 OOS:** Train +772 / Test +3255 / retention 552% / 9/10 Q+ — VALID but marginal.

**Decision:** Keep e41 as live Pine baseline. e42 documented in registry as research finding. Future iterations should focus on different angles (position sizing, walk-forward param refresh, multi-symbol portfolio).

---

## 📊 e41 CONFIG (CURRENT LIVE — e40 + session time/SL adjustments)

**Stack:** e37 → e38 ATR filter → e39 TP boost → e40 NY delay → **e41 session params**

**Three new variables (e41):**
1. **Asia start 18:00 → 19:00 ET** (1h later, aligns with Tokyo open vol)
2. **London SL 0.5 → 0.9 × bw** (wider, captures momentum)
3. **NY session end 12 → 13 ET** (1h more for trade resolution)

**5y backtest (1368 days):**
| Variant | Closed | EOD | TOTAL | Trades | WR | Δ vs e37 |
|---|---|---|---|---|---|---|
| e37 baseline | +3223 | -1468 | +1755 | 2433 | 60.2% | 0 |
| e38 (ATR filter) | +3540 | -929 | +2611 | 1868 | 63.1% | +856 |
| e39 (e38 + TP boost) | +3307 | -186 | +3121 | 1766 | 60.1% | +1366 |
| e40 (e39 + NY delay) | +3488 | -171 | +3317 | 1740 | 60.9% | +1562 |
| **e41 (time/SL adj)** | **+4145** | **-162** | **+3983** | **1589** | **60.9%** | **+2228 (+127%)** ⭐ |

**Per-session 5y (e41):**
- 🟢 Asia: closed +1024 (263 tr, 68% WR) — fewer but better trades, late Asia 19-22 ET dominance
- 🔵 London: closed +1238 (628 tr, 58% WR) — wider SL captures momentum, lower WR but higher avg win
- 🟡 NY: closed +1883 (698 tr, 61% WR) — extended end + delay = clean noise-free entries

**OOS validation (train ≤ 2023, test > 2023):**
- Train: +755 pts (+245/yr) WR 57.1%
- Test: +3228 pts (+1374/yr) WR 64.9%
- Retention: **560%** · Test quarters: **9/10 positive ✅**

**Live estimate:** ~+733 pts/year × $2/pt = **~$1467/year on $200 cap** (vs e37 $647 = +$820/yr realistic gain)

**SMC concepts tested — ALL FAILED:**
- Order Block bias align: -119 pts ✗
- Fair Value Gap align: -2 pts (neutral)
- Break of Structure align: -476 pts ✗
- BOS presence-only: -1843 pts ✗ (massive over-filter)

**Insight:** PT box is fundamentally a regime-filtered raw-breakout system. SMC concepts (order blocks, FVG, BOS) all over-filter or add no value. The 4 winning improvements (ATR filter, TP boost, NY delay, time grid) are all REGIME / TIMING / RISK adjustments — NOT predictive structural filters.

---

## 📊 e40 CONFIG (CURRENT — e39 + NY killzone delay 25min) — superseded by e41

**Stack:** e37 base → e38 ATR filter → e39 TP boost → **e40 NY entry delay**

**New variable (e40):** Delay NY entries by 25 min after box close.
**Rule:** NY box still 07:00-08:00 ET. Trades only fire from 08:25 onward.
**Why:** 8:30-8:55 ET window = macro release noise (NFP/CPI/Retail). Wait for noise to resolve.

**5y backtest (1368 days):**
| Variant | Closed | EOD | TOTAL | Trades | WR | Δ vs e37 |
|---|---|---|---|---|---|---|
| e37 baseline | +3223 | -1468 | +1755 | 2433 | 60.2% | 0 |
| e38 (ATR filter) | +3540 | -929 | +2611 | 1868 | 63.1% | +856 |
| e39 (e38 + TP boost) | +3307 | -186 | +3121 | 1766 | 60.1% | +1366 |
| **e40 (e39 + NY delay)** | **+3488** | **-171** | **+3317** | **1740** | **60.9%** | **+1562 (+89%)** ⭐ |

**OOS validation (train ≤ 2023, test > 2023):**
- Train: +662 pts (+215/yr) WR 56.2%
- Test: +2655 pts (+1130/yr) WR 65.1%
- Retention: **526%** · Test quarters: **9/10 positive ✅**

**Live estimate:** ~+611 pts/year × $2/pt = **~$1222/year on $200 cap**

**Stability check (NY delay sweep):**
| Delay (min) | Total | Δ e39 |
|---|---|---|
| 0 (no delay) | +3121 | 0 |
| 20 | +3154 | +33 |
| **25** ⭐ | **+3317** | **+196** |
| 30 | +3277 | +156 |
| 35 | +3222 | +101 |
| 40+ | <+3100 | varies |

20-35 min cluster all positive — robust optimum.

---

## 📊 e39 CONFIG (e38 + asymmetric TP per ATR — superseded by e40 but stable)

**Stack:** e37 base → e38 ATR filter → e39 TP boost on high-ATR days

**New variable (e39):** ATR rank within rolling 30-day window.
**Rule:** When today's ATR rank ≥ 72nd percentile, multiply session TP by 1.30.
- Asia 1.5R → 1.95R, London 2.0R → 2.6R, NY 2.5R → 3.25R

**5y backtest (1368 days):**
| Variant | Closed | EOD | TOTAL | Trades | WR | Δ vs e37 |
|---|---|---|---|---|---|---|
| e37 baseline | +3223 | -1468 | +1755 | 2433 | 60.2% | 0 |
| e38 (ATR filter) | +3540 | -929 | +2611 | 1868 | 63.1% | +856 |
| **e39 (e38 + TP boost)** | **+3307** | **-186** | **+3121** | **1766** | **60.1%** | **+1366** ⭐ |

**Why e39 wins despite lower closed-PnL & WR than e38:**
- Wider TP on high-ATR days = higher chance of hitting before EOD
- EOD drag collapses from -929 → -186 (80% reduction)
- Net: closed PnL down -233 pts, but EOD recovery +743 pts → +510 net gain

**OOS validation (train ≤ 2023, test > 2023):**
- Train: +650 pts (+211/yr) WR 55.7%
- Test: +2471 pts (+1052/yr) WR 64.6%
- Retention: 498% · Test quarters: **9/10 positive ✅**

**Live estimate:** ~+574 pts/year × $2/pt = **~$1149/year on $200 cap** (TOTAL incl EOD-actual)

**Stability check (TP boost sweep around optimum):**
| ATR pctile | TP×1.20 | TP×1.25 | TP×1.30 | TP×1.35 |
|---|---|---|---|---|
| 65th | 3064 | 3064 | 3112 | 2848 |
| 70th | 3038 | 3060 | 3113 | 2834 |
| **72th** | 2974 | 3052 | **3121** ⭐ | 2828 |
| 75th | 2955 | 3019 | 3072 | 2763 |
| 80th | 2943 | 3008 | 3063 | 2742 |

Cluster around 65-75th × 1.30 → robust optimum, not a fluke.

---

## 📊 e38 CONFIG (e37 + ATR regime filter — superseded by e39 but stable)

**New variable:** ATR regime filter (rolling 30-day intraday H-L range).
**Rule:** Skip days where today's intraday H-L < 30th percentile of last 30 days.
**Filters out:** ~30% of days (the calmest = where breakouts fail systematically).

| Session | Box | Model | SL | TP | Body | PnL 5y | WR |
|---|---|---|---|---|---|---|---|
| 🟢 Asia | 18:00/90m ET | DIRECT | 0.7×bw, min 3pt | 1.5R | 0% | **+838** | 64% |
| 🔵 London | 00:00/60m ET | DIRECT | 0.5×bw, min 3pt | 2.0R | 20% | **+1132** | 63% |
| 🟡 NY | 07:00/60m ET | DIRECT | 0.5×bw, min 3pt | 2.5R | 30% | **+1570** | 62% |
| **TOTAL** | | | | | | **+3540** | **63.1%** |

**Closed-only PnL (5y):** +3540 vs e37 +3223 = **+317 pts** (+10%)
**Total incl. EOD M-T-M (5y):** +2611 vs e37 +1755 = **+856 pts (+49%)** ⭐
**Live estimate:** ~+481 pts/year × $2/pt = **~$962/year on $200 cap** (realistic, incl. EOD)
**Trade count:** 1868 (vs e37 2433) — selective, fewer entries, higher quality

**OOS validation (e38, 2026-05-05):**
- Train 2021-23: +545 pts (+177/yr) WR 59.2%
- Test 2024-26:  +2066 pts (+879/yr) WR 67.2%
- Retention: 496% · Test quarters positive: **9/10** · Verdict: **PASS** ✅

### e37 baseline (filter OFF) — for comparison
| Session | PnL 5y | WR | Trades |
|---|---|---|---|
| 🟢 Asia | +855 | 61% | 594 |
| 🔵 London | +1186 | 62% | 958 |
| 🟡 NY | +1182 | 58% | 881 |
| **TOTAL** | **+3223 closed / +1755 total** | 60.2% | 2433 |

(5y = 2021-2026, 1368 trading days, max-SL filter OFF — both configs)
**OOS:** needs re-validation with corrected engine (was claimed 316% retention but on inflated baseline).

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
NOTE: PnL values below are PRE-v11 (buggy -sl_dist accounting). Iteration deltas remain
directionally valid (relative comparisons). True absolute values are ~35% of stated.

e20d  baseline                       +976  (pre-bugfix)
e26   NY iterations                  +~1200
e27e  NY strict + body50%            +1422  (+314)
e30   timing 9:07/10m                +1662  (+240)
e31   NY TP=6R → TP=2.5R             +2964  (+1302) ⚡
e32   Wyckoff pre-session 07:00/60m  +3691  (+727)  ⚡
e33   NY any pattern + body30%       +4025  (+334)
e35   London DIRECT + 00:00/60m      +5086  (+1061)
e36   ALL 3 sessions DIRECT          +8192  (+3106) ⚡
e37   extended session windows       +9084  (+892)
e37 + v11 engine fix (correct loss accounting):
                                     +3223 closed / +1755 total (5y baseline)
e38   ATR(30d, 30th pctile) regime filter:
                                     +3540 closed / +2611 total (5y) ⭐ CURRENT
                                     OOS PASS (test 9/10 Q+, retention 496%)
```

**e38 sweep results** (2026-05-05, full 5y `phase8_e38_v12_iteration.json`):
| Test | TOTAL PnL | Δ vs e37 | Verdict |
|---|---|---|---|
| **e38 ATR(30d,30th)** | **+2611** | **+856** | ⭐ adopted |
| ATR(30d,50th) median | +2394 | +639 | runner-up |
| Trend bias D1 SMA20 | +1718 | -36 | neutral |
| EOD time-cap 180min | +1600 | -154 | killed winners |
| Volume filter (rolling) | +1450 | -304 | tickvol noise |
| Box-quality filter | +1051 | -703 | over-filtered |
| EOD cap 60min | +989 | -766 | worst |
| ATR LOW (control) | -619 | -2374 | ✓ confirms ATR signal |

**Investigations (not adopted):**
- London FLAT 5pt SL → would lose -612 PnL for zero edge gain. STAYED e37 dynamic SL.
- Volume confirmation (tickvol > rolling): -305 pts. MT5 tickvol too noisy.
- Box-quality (skip wide-box days): -703 pts. NY hardest hit (boxes naturally wide).
- EOD time-cap exits (60-180 min): all WORSE. Caps kill winning runners.

**Pine v10 hotfix (2026-05-05):**
- Asia 0-trade bug: `asiaSessionEndH` default was 0 → Pine session range `mod < 0` always false → DIRECT entry never fired. Default fixed to 24 (midnight extended).
- Stats panel display strings updated to reflect actual e37 config (was showing legacy "ext+1/mid" + "0.5×bw/3R/6R").

**Pine v11 sync (2026-05-05):**
- Max attempts/day defaults: 5/3/3 → **1/1/1** (Asia/London/NY).
- Reason: engine canonical fires 1 entry/day per session. Pine multi-attempt was 4.7x over-firing Asia → user panel showed 33 trades/-217 PnL vs engine 7 trades/+21.
- e37 canonical = **1 entry/day per session, locked**.

**Pine v12 + ENGINE BUGFIX (2026-05-05) — MAJOR CORRECTION:**
- Engine `code/ptbox_engine_e37.py` had loss accounting bug:
  ```
  WRONG: dp -= sl_dist          (only counts slDist amount)
  FIXED: dp -= (ep - sp)        (full entry-to-SL distance = bw + slDist)
  ```
  For DIRECT breakout where entry > boxHi but SL < boxLo, real loss includes
  the box-width crossing. Engine was under-counting losses by ~bw per loss.
- Engine `max_sl_pts` filter was using slDist (incomplete), now uses actual risk
  (entry-to-SL = bw + slDist), matching Pine.
- True 5y PnL: **+3223** (was claimed +9084, off by 65%).
- Pine `useMaxSlFilter` default true → false to match engine canonical (filter
  was killing PnL especially for NY: filter @15 made NY -37, filter OFF NY +1182).
- Per-session canonical: Asia +855 / London +1186 / NY +1182 (5y 2021-2026).
- Validation gold-standard: `data/e37_validation_apr22-may05.json` (21 trades, +169 pts, Apr 22 - May 5 2026).
- Reproduce: `python3 scripts/run_e37_detail.py <CSV>` for per-trade detail.

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
