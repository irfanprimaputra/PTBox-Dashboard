---
title: PT Box Trade Journal Template
date: 2026-05-04
tags: [trading, journal, ptbox, live]
---

# 📋 PT Box Live Trade Journal

> Track every live trade. Real edge measured here, not in backtest.

## Tracking Spreadsheet Schema

Save as Google Sheets / Excel / Obsidian Bases:

| Field | Type | Example |
|-------|------|---------|
| trade_id | number | 1 |
| date | YYYY-MM-DD | 2026-05-05 |
| session | text | NY |
| entry_time_et | HH:MM | 09:08 |
| entry_time_wib | HH:MM | 20:08 |
| direction | text | LONG |
| box_high | float | 2348.50 |
| box_low | float | 2345.20 |
| box_width | float | 3.30 |
| entry_price | float | 2348.70 |
| sl_price | float | 2345.40 |
| tp1_price | float | 2358.60 |
| tp2_price | float | 2368.40 |
| sl_distance_pts | float | 3.30 |
| lot | float | 0.02 |
| confidence | 1-10 | 8 |
| pre_emotion | text | confident |
| pattern_at_breakout | text | pin_bar |
| pattern_at_pullback | text | engulfing |
| hit_type | text | TP1 |
| exit_price | float | 2358.60 |
| exit_time_et | HH:MM | 09:32 |
| pnl_pts | float | +9.90 |
| pnl_usd | float | +1.98 |
| post_emotion | text | satisfied |
| lesson | text | trail SL after TP1 |
| backtest_match | bool | true |

## Daily Summary

```markdown
## 2026-05-05 (Tue)

### Pre-Day Plan
- Asia: skip (busy 06:00-10:00 WIB)
- London: monitor 12:43-16:00 WIB
- NY: focus 20:00-24:00 WIB ⭐

### Macro Bias (manual check):
- DXY direction (5d): down → bullish gold
- 10Y yield: up slightly → mildly bearish
- VIX: 18 (neutral)
- Net: slight bullish lean

### Trades Today

#### #001 NY Direct LONG (09:08 ET / 20:08 WIB)
- Box: 2345.20-2348.50
- Entry: 2348.70 → TP1 2358.60 = +9.90 pts ($1.98)
- Lesson: Pattern at breakout = pin_bar valid, fast TP1 hit

#### #002 NY Direct SHORT (10:45 ET / 21:45 WIB)
- Box: 2360.50-2364.20
- Entry: 2360.10 → SL 2363.40 = -3.30 pts (-$0.66)
- Lesson: 2L rule kicks in next, stop NY today

### EOD Summary
- Trades: 2 (1W, 1L)
- PnL: +6.60 pts ($1.32)
- Daily DD: -3.30 pts max
- Cumulative: $1.32 / $200 = +0.66%

### Tomorrow Prep
- Watch for FOMC Wed 14:00 ET
- Reduce NY size 50% if regime drift z<-1 (check monthly monitor)
```

## Weekly Review Template

```markdown
## Week 2026-W19 Review

### Stats
- Trades: X (W: x, L: x)
- WR: x%
- PnL: $x
- Max DD: $x
- Cumulative since start: $x / $200 = +x%

### Regime Stability
- Asia drift z: -0.5 (normal)
- London drift z: +1.2 (improving)
- NY drift z: +0.8 (normal)

### Live vs Backtest
- Backtest WR Asia: 73% | Live: x%
- Backtest WR London: 31% | Live: x%
- Backtest WR NY: 27% | Live: x%
- Retention: x% (target >60%)

### Wins
- ...

### Losses / Mistakes
- ...

### Adjustments Next Week
- ...
```

## Monthly Review Template

Run `python3 scripts/regime_stability_monitor.py` first, paste output below.

```markdown
## Month 2026-05 Review

### Cumulative Performance
- Trades total: X
- Total PnL pts: x
- Total PnL USD: $x
- ROI: x%
- Max DD: $x

### Regime Stability (script output)
[Paste regime_stability_monitor.py output]

### Action Decisions
- [ ] Continue current params
- [ ] Reduce size 50% (if drift z<-1)
- [ ] Halt session X (if drift z<-2)
- [ ] Re-optimize parameters quarterly
- [ ] Scale up capital (if profit >$300 + 60%+ retention)

### Next Month Focus
- ...
```

## Discipline Rules — DO NOT BREAK

```
1. Position size: ALWAYS 0.02 lot, no exceptions
2. Daily stop: 2L OR 1W → close trading desk
3. Max DD: -30% peak → halt 1 week
4. NEVER trade without journal entry
5. NEVER trade outside session windows
6. NEVER ignore drift z<-1 alarm
7. Friday: review week, no new trades after 12:00 ET
8. Body kill switch: sleep <4h × 3 nights → STOP trading 1 week
```

## Anti-Defensiveness Reminders

- **Loss streak ≠ broken strategy.** Mean-rev can have 3-loss streaks even with 73% WR.
- **Win streak ≠ permission to size up.** Stay 0.02 lot until milestone hit.
- **Backtest result ≠ entitled live result.** Live = backtest × 60-80% realistic.
- **Drawdown ≠ panic-sell strategy.** Trust process, monitor regime, adjust size only.

## Sample Annotated Win Day (NY, gold rally regime)

```markdown
## 2026-05-08 (Thu) — NY direct breakout perfect setup

### Pre-trade context
- DXY weakening (5-day MA slope down)
- US 10Y yield down 5 bps → bullish gold
- VIX 22 (risk-off, gold safe-haven flow)
- Macro bias: STRONG BULLISH gold

### Trade #045
- Time: 09:33 ET (20:33 WIB)
- Box: 2380.40-2384.80
- Breakout candle: 09:33 close 2386.50 → bullish pin bar
- Pattern at breakout: ✅ pin bar (long lower wick rejection)
- Entry: 2386.50
- SL: 2378.20 (box low - 2.20 buffer = 8.30 pts risk)
- TP1: 2411.40 (3R = +24.90 pts)
- TP2: 2436.30 (6R = +49.80 pts)

### Execution
- Entered: 2386.55 (5 cents slippage)
- TP1 hit: 09:48 ET (15 min later)
- Trail SL to 2386.50 (breakeven)
- Price ran to 2418, retraced
- TP2 not hit, SL trail at 2415 hit
- Exit: 2415 = +28.45 pts ($5.69)

### Reflection
- Strong macro alignment → high confidence justified
- Trail SL after TP1 saved profit when retrace happened
- Lesson: macro alignment + pattern + trail = recipe

### Cumulative
- 45 trades, 18W / 27L
- PnL: $94.50 (+47% on $200)
- Live retention vs backtest: 72% (good)
```
