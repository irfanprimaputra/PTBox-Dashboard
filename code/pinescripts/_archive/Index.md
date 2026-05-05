---
title: PT Box Pine Scripts — Master Index
date: 2026-04-27
tags:
  - trading
  - pinescript
  - tradingview
  - index
status: active
aliases:
  - Pine Scripts Index
  - PT Box Indicators
---

# 📊 PT Box Pine Scripts — Master Index

> [!info] 3 indicator paralel di TradingView
> Setiap session punya script terpisah dengan parameter + SL methodology yg berbeda. Run all 3 paralel di chart XAUUSD M1, alert masing-masing.

## 🎯 Overview Setup Per Session

| Session | Box Time (NY) | Box Time (WIB) | Box Dur | SL/TP | Pattern Filter | Status |
|---|---|---|---|---|---|---|
| 🟣 [[PT-Box-London-Pinescript\|London]] ⭐ | **01:00** | 12:00 | 7m | **Dynamic** (max(3, 0.5×box) / 3×SL / 6×SL) | **any** (pin/engulf/inside) | Phase 4 #2 enhanced (+468 pts) |
| 🔴 [[PT-Box-NY-Pinescript\|NY]] | 09:03 | 20:03 | 5m | Fixed (3 / 9 / 18) | none | Improve di conversation lain |
| 🟠 [[PT-Box-Asian-Pinescript\|Asian]] | 19:23 | 06:23 (next day) | 7m | Fixed (3 / 15 / 30) | none | Improve di conversation lain |

**London = Phase 4 #2 enhanced** (5 yr walk-forward optimization applied).
**NY & Asian = canonical baseline** (lu improve di conversation berbeda).

## 📊 Phase 4 Backtest Performance per Session (CONTEXT)

19-quarter walk-forward (Q3 2021 - Q1 2026):

| Session | Phase 1 Baseline | Phase 4 #1 dyn_sl_tp | Phase 4 #2 any_pattern | Ceiling | Live Verdict |
|---|---|---|---|---|---|
| London | -1,638 | +142 ⭐ | **+468** ⭐⭐ | +820 | **Edge confirmed**, deploy live ✅ |
| NY | -235 | -117 | -290 | +237 | Ambiguous, near break-even |
| Asian | -625 | -828 | -740 | -180 | **Structurally broken** ⚠️ |

**Combined system live (Phase 1 baseline params, current scripts):** ~-2,498 pts across 5 yr backtest.

## 🚀 TradingView Setup Steps

### 1. Chart prep
- Symbol: **XAUUSD**
- Timeframe: **M1**
- Chart timezone: any (script pake `hour(time, "America/New_York")` jadi independent)

### 2. Add 3 indicators
- Pine Editor → paste script → Save → "Add to chart"
- Repeat untuk NY, London, Asian script
- Total 3 indicator instance running paralel

### 3. Setup alerts (per indicator)
Right-click chart → Add Alert → Condition: indicator → pilih signal yg lu mau:
- 🟢 Asian/London/NY BUY Signal
- 🔴 Asian/London/NY SELL Signal
- 📦 Asian/London/NY Box Formed (optional, standby reminder)

Notification: Phone push, Email, Webhook ke Discord/Telegram.

### 4. Live execution flow
```
Box terbentuk → 📦 alert masuk → standby
   ↓
Breakout + pullback + (no pattern filter) → 🟢/🔴 alert masuk
   ↓
ENTRY di MT5 di NEXT candle OPEN @ market price
   ↓
Set SL + TP1 + TP2 manual di MT5 berdasarkan level di indicator label
   ↓
Wait outcome → SL/TP1/TP2 hit → script auto-track stats
```

## ⚙️ SL Methodology Comparison

| Anchor | Formula (BUY) | Effect | Used By |
|---|---|---|---|
| **Box edge** | `day_hi - 3pts` | Tight SL, frequent hits, smaller losses | NY (momentum session) |
| **Pullback wick** | `pullback_low - 3pts` | Wider SL, fewer hits, bigger losses | London, Asian |

User chose per session intuition:
- NY = momentum, news-driven → tight SL limit damage
- London = often deep pullback → wick anchor breathing room
- Asian = low-vol, deep pullback common → wick anchor

## 📋 Live Trading Recommendations

### 🟣 London — DEPLOY CONFIDENT ⭐
- Edge confirmed Phase 4 #2 (+468 pts, 63.2% pass rate)
- Current live config = Phase 1 baseline (suboptimal)
- **Future enhancement:** add dynamic SL/TP + pattern filter (Phase 5)
- Lot sizing: per capital risk tolerance, gradually scale 0.02 → 0.20+

### 🔴 NY — DEPLOY CAUTIOUS
- Near break-even (Phase 1 -235 pts)
- Pattern filter HURT NY, jangan tambahin
- **Future enhancement:** news calendar filter, trend continuation gate
- Lot sizing: smaller than London (0.01-0.02)

### 🟠 Asian — DEPLOY VERY SMALL or PAPER
- Structurally broken (ceiling -180 pts)
- High risk consistent loss
- **Future enhancement:** NEW MODEL (direct breakout / mean-reversion / time narrow)
- Lot sizing: minimum 0.01 atau paper trade until Phase 5 fix

## 🎯 Combined Live Strategy

**Conservative approach (recommended):**
- London: 0.05 lot
- NY: 0.02 lot
- Asian: 0.01 lot or paper

**Risk per session per trade @ SL=3pts:**
- London 0.05 lot × $5/pt × 3 pts = **$15/trade**
- NY 0.02 lot × $2/pt × 3 pts = **$6/trade**
- Asian 0.01 lot × $1/pt × 3 pts = **$3/trade**

Total max daily risk (worst case 3 attempts × 3 sessions all hit SL):
$15×3 + $6×3 + $3×3 = **$72/day max risk**

Per $200 capital: 36% drawdown worst-case-day. Adjust lot kalau too aggressive.

## 🔄 Phase 5 Roadmap Per Session

Lihat [[Phase-4-Experiment-Log]] untuk detail. Singkat:

**Asian:** A1 (direct breakout) / A2 (mean-reversion) / A3 (22:00-23:00 narrow window) / A4 (NY carry-over filter)
**NY:** B1 (state machine) / B2 (news filter) / B3 (trend continuation) / B4 (hour split) / B5 (spread filter)
**London:** KEEP, tambahkan dyn_sl_tp + any_pattern (Phase 4 #2 winner)
**Shared:** S1 (day-of-week filter) / S2 (adaptive box duration) / S3 (equity protection rule)

## 🔗 Related

- [[PT-Box-NY-Pinescript]] — NY canonical
- [[PT-Box-London-Pinescript]] — London canonical
- [[PT-Box-Asian-Pinescript]] — Asian canonical
- [[PT-Box-System]] — Methodology base
- [[Phase-4-Session-2026-04-27]] — Phase 4 result summary
- [[Phase-4-Experiment-Log]] — Variant registry + Phase 5 backlog
- [[Phase-4-Optimization-Plan]] — Master plan
- [[Trading-Roadmap]] — Timeline
