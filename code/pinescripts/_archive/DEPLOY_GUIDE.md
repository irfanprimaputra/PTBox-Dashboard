---
title: PT Box e20d — TradingView Deploy Guide
date: 2026-05-04
tags: [trading, pinescript, deploy, ptbox]
---

# 🚀 PT Box e20d — Quick Deploy ke TradingView

## Step 1 — Copy Pine Script

1. Buka file: `code/pinescripts/PTBox_e20d.pine`
2. Copy semua isi (Cmd+A → Cmd+C)

## Step 2 — Paste ke TradingView Pine Editor

1. Buka [TradingView](https://tradingview.com)
2. Buka chart **XAUUSD**
3. Bottom-right → tab **Pine Editor**
4. Paste code (Cmd+V)
5. Click **Save** → kasih nama "PT Box e20d"
6. Click **Add to chart**

## Step 3 — Setting Chart

| Setting | Value |
|---------|-------|
| Symbol | XAUUSD (atau OANDA:XAUUSD / FOREXCOM:XAUUSD) |
| Timeframe | **M1** (1-minute) untuk live signals, **M5** untuk overview |
| Timezone | **UTC-4** (Right-click chart → Settings → Timezone → New York) |
| Layout | Dark mode recommended |

## Step 4 — Setup Alerts (HP push notification)

Setiap entry signal punya alert built-in. Setup:

1. Right-click chart → **Add Alert**
2. Condition: **PT Box e20d** → **Any alert() function call**
3. Frequency: **Once Per Bar Close**
4. Notifications: **Push to Phone** (TradingView mobile app required)
5. Click **Create**

Setelah setup, lu bakal dapet push notification HP setiap kali ada entry signal:
```
Asia FADE LONG @ 2345.50 | SL 2342.30 | TP 2348.10
London LONG @ 2350.20 | SL 2347.50 | TP1 2358.30 | TP2 2366.40
NY DIRECT SHORT @ 2360.10 | SL 2363.40 | TP1 2350.20 | TP2 2340.30
```

## Step 5 — Live Schedule (WIB Indonesia, summer/EDT)

| Session | Window WIB | Window UTC | Action |
|---------|-----------|-----------|--------|
| 🟢 Asia | **08:00-10:00 WIB** | 01:00-03:00 UTC | Set alarm 08:00 |
| 🔵 London | **12:43-16:00 WIB** | 05:43-09:00 UTC | Lunch break check |
| 🟡 NY | **20:03-24:00 WIB** | 13:03-17:00 UTC | After-work prime ⭐ |

**Note:** WIB = UTC+7. Engine ET = UTC-4 (EDT summer). Difference WIB - ET = 11 hours.

## Step 6 — Manual Trade Execution di Exness MT5

Karena belum ada EA, eksekusi manual:

1. **Saat alert masuk HP** → cek chart TradingView, pastikan signal valid
2. **Buka MT5 Exness**
3. **Buka order**:
   - Symbol: XAUUSD
   - Volume: **0.02 lot** (per $200 capital, 1% risk per trade)
   - Direction: BUY/SELL (per alert)
   - SL: input level dari alert
   - TP: input TP1 dulu (trail after hit kalau mau)
4. **Confirm execution**
5. **Journal** entry di template (next section)

## Step 7 — Risk Management Rules (HARD)

```
Position size: 0.02 lot per trade ($200 capital, ~1% risk)
Max DD: -30% peak → STOP, halt trading 1 week
Daily limit: stop after 2 losses OR 1 win (Asia rule, also good general)
Weekly review: Friday close → check live vs backtest expectancy
Monthly: run regime_stability_monitor.py, adjust size if drift z<-1
```

## Step 8 — Trade Journal Template

Use [Notion / Obsidian / Sheets]. Per trade entry:

```markdown
## Trade #001 — 2026-05-05

**Setup:**
- Session: NY direct breakout
- Entry time: 09:08 ET (20:08 WIB)
- Direction: LONG
- Box: 2345.20 / 2348.50

**Execution:**
- Entry price: 2348.70
- SL: 2345.40 (3.30 pts risk)
- TP1: 2358.60 (3R)
- TP2: 2368.40 (6R)
- Lot: 0.02

**Pre-trade emotion:**
- Confidence 1-10: 8 (clear breakout, pin bar at breakout candle)

**Outcome:**
- Hit: TP1
- PnL: +9.90 pts ($1.98)
- Exit time: 09:32 ET

**Lesson:**
- ✅ Pattern at breakout valid
- ⚠️ TP1 hit fast, TP2 missed (hit SL after retrace)
- 💡 Consider trail SL after TP1 next time
```

## Caveats — Real-World Live Differences

⚠️ **Backtest vs Live discrepancies:**
1. **Spread cost** — XAUUSD typical 20-30 cents = ~0.2-0.3 pts per trade
2. **Slippage** — fast market = entry/SL pakai harga buruk = -0.5 to -2 pts
3. **Commission** — Exness $7/lot rt = $0.14 per 0.02 lot rt
4. **Execution delay** — manual entry vs Pine signal = 5-30 sec difference

**Realistic expectation:** Live edge = backtest × 60-80%. e20d backtest +976 pts/5y → live ~+600-780 pts/5y theoretical at 0.02 lot.

## Troubleshooting

**Alert ga muncul:**
- Check Pine Editor errors (red triangle icon)
- Set chart ke M1 (alerts based on bar close)
- Verify timezone UTC-4

**Box ga ke-draw:**
- Belum masuk session window
- Box width terlalu sempit (filter min_box_width)
- Tunggu 1-2 menit pasca-window-end (engine cache)

**Entry signal tapi pattern ga match:**
- Pattern detection di Pine bisa beda 5-10% dari Python engine
- Pine pakai prev candle (i-1) reference, sesekali boundary timing beda
- Check manual: pin bar (small body, long wick), engulfing (current body engulfs prev), inside bar (high<prev high AND low>prev low)

## Pricing & Live Capital Math

- **$200 capital, lot 0.02:**
  - 1 pt move = $0.20
  - Asia trade: avg win 5 pts × $0.20 = $1
  - NY trade: avg win 18 pts × $0.20 = $3.60
  - Annual estimate (post-friction): ~$700-800/year

- **Scaling milestones (G3 path):**
  - $200 → $500: profit $300 + maintain 60%+ live retention vs backtest
  - $500 → $2000: profit $1500 + 6 months profitable
  - $2000 → $10k: track record 1 year + max DD <15%
  - $10k+: serious capital, consider prop firm or LP

## Next Steps

After 50 live trades:
1. Compare live PnL vs backtest expectation
2. Run regime_stability_monitor.py
3. Adjust if drift >1σ
4. Decide scale up or refine
