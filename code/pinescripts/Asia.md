---
title: PT Box Asian Pine Script (TradingView)
date: 2026-04-27
tags:
  - trading
  - pinescript
  - tradingview
  - asian
status: active
aliases:
  - Pine Script Asian
  - PT Box Asian Indicator
---

# 📜 PT Box Asian Pine Script

> [!info] Generated to match user's NY/London pattern
> Asian config dari [[PT-Box-System]]: 19:23 NY, 7-min box. SL/TP dari engine CONFIG (TP1=15, TP2=30 RR 1:5/1:10). SL anchor: wick-based (matching London style — Asian low-vol, butuh breathing room).

## 🎯 Setup Specs

```
Box Window: 19:23 NY (06:23 WIB next day), 7-minute box
SL = pullback_wick ± 3 pts (WICK-based mode, matching London)
TP1 = +15 pts (RR 1:5)
TP2 = +30 pts (RR 1:10)
Max 3 attempts/day
Pattern filter: NONE
```

**Phase 4 walk-forward result Asian (relevant):**
- Phase 1 baseline: -625 pts
- Phase 4 #1 dyn_sl_tp: -828 pts (worse — proportional logic ga cocok small box)
- Phase 4 #2 any_pattern: -740 pts (still negative)
- **Ceiling -180 pts** (even with future-data cheating, Asian rugi)

**Verdict:** Asian **STRUCTURALLY broken** di period 2021-2026. Live trading Asian = high risk of consistent loss. Phase 5 plan: test NEW model (direct breakout / mean-reversion / time-of-day filter) — saat ini **CAUTION** kalau live trade Asian.

## 🔧 SL Methodology Note

| Session | SL Anchor |
|---|---|
| NY | Box edge (day_hi/day_lo ± 3) |
| London | Pullback wick (low/high ± 3) |
| **Asian** | **Pullback wick (low/high ± 3)** |

Asian low-vol → seringkali pullback dalam, butuh wick anchor (matching London logic).

## 📋 Pine Script v5 Code

```pinescript
//@version=5
indicator("PT Asian", overlay=true, max_boxes_count=500, max_lines_count=500, max_labels_count=500)

// INPUTS
box_hour     = input.int(19,   "PT Box Hour (NY time)",  minval=0, maxval=23)
box_minute   = input.int(23,   "PT Box Minute",          minval=0, maxval=59)
box_duration = input.int(7,    "Box Duration (minutes)", minval=1, maxval=60)
sl_buf       = input.float(3,  "SL Buffer (points)",     minval=0.1)
tp1_pts      = input.float(15, "TP1 (points)",           minval=0.1)
tp2_pts      = input.float(30, "TP2 (points)",           minval=0.1)
max_att      = input.int(3,    "Max Attempts per day",   minval=1, maxval=6)
show_box     = input.bool(true, "Show PT Box")
show_sig     = input.bool(true, "Show Signals")

// NY TIME
ny_h       = hour(time,      "America/New_York")
ny_m       = minute(time,    "America/New_York")
ny_dw      = dayofweek(time, "America/New_York")
is_weekday = ny_dw != dayofweek.saturday and ny_dw != dayofweek.sunday

// BOX FORMATION
is_box_candle = is_weekday and ny_h == box_hour and ny_m >= box_minute and ny_m < (box_minute + box_duration)
is_box_end    = is_weekday and ny_h == box_hour and ny_m == (box_minute + box_duration)
is_new_day    = is_weekday and ny_h == box_hour and ny_m == box_minute

var float bx_hi      = na
var float bx_lo      = na
var bool  bx_forming = false
var bool  bx_ready   = false

if is_new_day
    bx_hi      := high
    bx_lo      := low
    bx_forming := true
    bx_ready   := false

if bx_forming and is_box_candle and not is_new_day
    bx_hi := math.max(bx_hi, high)
    bx_lo := math.min(bx_lo, low)

if is_box_end and bx_forming
    bx_forming := false
    bx_ready   := true
    if show_box
        box.new(bar_index - box_duration, bx_lo, bar_index + 80, bx_hi, bgcolor=color.new(color.orange, 85), border_color=color.new(color.orange, 20), border_width=1)

// DAY STATE
var float day_hi     = na
var float day_lo     = na
var int   attempt    = 0
var int   bk_dir     = 0
var bool  in_trade   = false
var float entry_px   = na
var float sl_px      = na
var float tp1_px     = na
var float tp2_px     = na
var bool  day_done   = false
var int   bk_bar     = na
var int   sl_bar     = na

if is_new_day
    day_hi   := na
    day_lo   := na
    attempt  := 0
    bk_dir   := 0
    in_trade := false
    entry_px := na
    sl_px    := na
    tp1_px   := na
    tp2_px   := na
    day_done := false
    bk_bar   := na
    sl_bar   := na

if is_box_end and bx_ready
    day_hi := bx_hi
    day_lo := bx_lo

is_after_box   = bx_ready and not bx_forming and not na(day_hi) and not na(day_lo)
is_past_sl_bar = na(sl_bar) or bar_index > sl_bar

// BREAKOUT
if is_after_box and not in_trade and not day_done and is_past_sl_bar
    if close > day_hi and bk_dir != 1
        bk_dir := 1
        bk_bar := bar_index
    else if close < day_lo and bk_dir != -1
        bk_dir := -1
        bk_bar := bar_index

is_past_breakout_bar = not na(bk_bar) and bar_index > bk_bar

// PULLBACK
pullback_up   = is_after_box and is_past_breakout_bar and bk_dir == 1
              and not in_trade and not day_done and attempt < max_att
              and close > day_hi
              and low   <= day_hi

pullback_down = is_after_box and is_past_breakout_bar and bk_dir == -1
              and not in_trade and not day_done and attempt < max_att
              and close < day_lo
              and high  >= day_lo

is_pullback = pullback_up or pullback_down

// ENTRY — WICK-based SL (Asian)
var int   total_win  = 0
var int   total_loss = 0
var int   total_chop = 0
var float total_pnl  = 0.0

if is_pullback and not in_trade
    attempt  := attempt + 1
    in_trade := true
    entry_px := close
    if bk_dir == 1
        sl_px  := low  - sl_buf
        tp1_px := entry_px + tp1_pts
        tp2_px := entry_px + tp2_pts
    else
        sl_px  := high + sl_buf
        tp1_px := entry_px - tp1_pts
        tp2_px := entry_px - tp2_pts
    if show_sig
        label.new(bar_index, bk_dir == 1 ? low - (day_hi - day_lo) * 0.5 : high + (day_hi - day_lo) * 0.5, (bk_dir == 1 ? "BUY " : "SELL ") + str.tostring(attempt) + "x", style=bk_dir == 1 ? label.style_label_up : label.style_label_down, color=color.new(color.teal, 10), textcolor=color.white, size=size.small)

// TRADE MANAGEMENT
if in_trade and not na(sl_px) and not na(tp1_px)
    hit_sl  = bk_dir == 1 ? low  <= sl_px  : high >= sl_px
    hit_tp1 = bk_dir == 1 ? high >= tp1_px : low  <= tp1_px
    hit_tp2 = bk_dir == 1 ? high >= tp2_px : low  <= tp2_px

    if hit_tp2
        total_win := total_win + 1
        total_pnl := total_pnl + tp2_pts
        in_trade  := false
        day_done  := true
        if show_sig
            label.new(bar_index, tp2_px, "TP2 ✓", style=label.style_label_down, color=color.new(color.green, 0), textcolor=color.white, size=size.tiny)
    else if hit_tp1
        total_win := total_win + 1
        total_pnl := total_pnl + tp1_pts
        in_trade  := false
        day_done  := true
        if show_sig
            label.new(bar_index, tp1_px, "TP1 ✓", style=label.style_label_down, color=color.new(color.lime, 0), textcolor=color.white, size=size.tiny)
    else if hit_sl
        total_loss := total_loss + 1
        total_pnl  := total_pnl - math.abs(entry_px - sl_px)
        in_trade   := false
        bk_dir     := 0
        bk_bar     := na
        sl_bar     := bar_index
        if attempt >= max_att
            total_chop := total_chop + 1
            day_done   := true
            if show_sig
                label.new(bar_index, sl_px, "CHOP ✗", style=label.style_label_up, color=color.new(color.orange, 0), textcolor=color.white, size=size.tiny)
        else
            if show_sig
                label.new(bar_index, sl_px, "SL ✗ " + str.tostring(attempt) + "/" + str.tostring(max_att), style=label.style_label_up, color=color.new(color.red, 0), textcolor=color.white, size=size.tiny)

// ALERTS
alertcondition(pullback_up,   title="🟢 Asian BUY Signal",  message="PT BOX Asian — BUY\nEntry: next candle OPEN\nSL = pullback_low - 3pts\nTP1 = +15pts | TP2 = +30pts")
alertcondition(pullback_down, title="🔴 Asian SELL Signal", message="PT BOX Asian — SELL\nEntry: next candle OPEN\nSL = pullback_high + 3pts\nTP1 = -15pts | TP2 = -30pts")
alertcondition(is_box_end and bx_ready, title="📦 Asian Box Formed", message="PT BOX Asian — Box terbentuk. Standby breakout.")

// PLOTS
plot(in_trade ? sl_px  : na, "SL",  color=color.new(color.red,    20), linewidth=1, style=plot.style_linebr)
plot(in_trade ? tp1_px : na, "TP1", color=color.new(color.lime,   20), linewidth=1, style=plot.style_linebr)
plot(in_trade ? tp2_px : na, "TP2", color=color.new(color.green,  20), linewidth=1, style=plot.style_linebr)
plot(is_after_box ? day_hi : na, "BoxHi", color=color.new(color.orange, 50), linewidth=1, style=plot.style_linebr)
plot(is_after_box ? day_lo : na, "BoxLo", color=color.new(color.orange, 50), linewidth=1, style=plot.style_linebr)

// STATS TABLE — top right (biar ga overlap NY bottom-right & London bottom-left)
if barstate.islast
    total_trades = total_win + total_loss
    win_rate     = total_trades > 0 ? (float(total_win) / float(total_trades)) * 100 : 0.0
    rr           = sl_buf > 0 ? tp2_pts / sl_buf : 0.0
    var table t  = table.new(position.top_right, 2, 12, bgcolor=color.new(color.black, 60), border_color=color.new(color.gray, 40), border_width=1, frame_color=color.new(color.orange, 20), frame_width=2)
    table.cell(t, 0, 0,  "PT Asian",          bgcolor=color.new(color.orange, 20), text_color=color.white, text_size=size.normal)
    table.cell(t, 1, 0,  str.tostring(box_hour) + ":" + (box_minute < 10 ? "0" : "") + str.tostring(box_minute) + " Asian", bgcolor=color.new(color.orange, 20), text_color=color.white, text_size=size.normal)
    table.cell(t, 0, 1,  "Total Win",      text_color=color.white,  text_size=size.small)
    table.cell(t, 1, 1,  str.tostring(total_win),  text_color=color.green,  text_size=size.small)
    table.cell(t, 0, 2,  "Total Loss",     text_color=color.white,  text_size=size.small)
    table.cell(t, 1, 2,  str.tostring(total_loss), text_color=color.red,    text_size=size.small)
    table.cell(t, 0, 3,  "Chop Days",      text_color=color.white,  text_size=size.small)
    table.cell(t, 1, 3,  str.tostring(total_chop), text_color=color.orange, text_size=size.small)
    table.cell(t, 0, 4,  "Win Rate",       text_color=color.white,  text_size=size.small)
    table.cell(t, 1, 4,  str.tostring(math.round(win_rate, 1)) + "%", text_color=win_rate >= 50 ? color.green : color.red, text_size=size.small)
    table.cell(t, 0, 5,  "Net P&L (pts)",  text_color=color.white,  text_size=size.small)
    table.cell(t, 1, 5,  str.tostring(math.round(total_pnl, 1)), text_color=total_pnl >= 0 ? color.green : color.red, text_size=size.small)
    table.cell(t, 0, 6,  "RR (TP2/SL)",    text_color=color.white,  text_size=size.small)
    table.cell(t, 1, 6,  "1:" + str.tostring(math.round(rr, 1)), text_color=color.yellow, text_size=size.small)
    table.cell(t, 0, 7,  "SL Buf/TP1/TP2", text_color=color.white,  text_size=size.small)
    table.cell(t, 1, 7,  str.tostring(sl_buf) + "/" + str.tostring(tp1_pts) + "/" + str.tostring(tp2_pts), text_color=color.gray, text_size=size.small)
    table.cell(t, 0, 8,  "Max Attempt",    text_color=color.white,  text_size=size.small)
    table.cell(t, 1, 8,  str.tostring(max_att) + "x", text_color=color.gray, text_size=size.small)
    table.cell(t, 0, 9,  "Today Attempt",  text_color=color.white,  text_size=size.small)
    table.cell(t, 1, 9,  str.tostring(attempt) + "/" + str.tostring(max_att), text_color=color.white, text_size=size.small)
    table.cell(t, 0, 10, "Breakout Dir",   text_color=color.white,  text_size=size.small)
    table.cell(t, 1, 10, bk_dir == 1 ? "LONG" : bk_dir == -1 ? "SHORT" : "Wait", text_color=bk_dir == 1 ? color.green : bk_dir == -1 ? color.red : color.gray, text_size=size.small)
    table.cell(t, 0, 11, "In Trade",       text_color=color.white,  text_size=size.small)
    table.cell(t, 1, 11, in_trade ? "YES" : "NO", text_color=in_trade ? color.yellow : color.gray, text_size=size.small)
```

## 🎨 Visual Differentiator

| Session | Box Color | Stats Position |
|---|---|---|
| 🔴 NY | Purple | Bottom-right |
| 🟣 London | Purple | Bottom-left |
| 🟠 Asian | **Orange** | **Top-right** |

3 indicator running paralel di chart, masing-masing color/position beda biar ga overlap.

## ⚠️ Live Trading Caution untuk Asian

Per Phase 4 walk-forward + ceiling check, **Asian session strukturally broken** di period 2021-2026:
- Even dengan future-data optimization (cheating), Asian rugi -180 pts
- Pass rate consistently rendah (12.5% di Phase 1, 0% di Phase 4 #2 any_pattern)

**Recommend:**
- Live trade Asian dengan **very small lot** (0.01) atau **paper trade only**
- Monitor live performance vs backtest expectation
- Phase 5 priority untuk Asian: NEW MODEL (direct breakout / mean-reversion / 22:00-23:00 narrow window)

## 🔗 Related

- [[PT-Box-NY-Pinescript]] — NY variant
- [[PT-Box-London-Pinescript]] — London variant
- [[PT-Box-Pinescripts-Index]] — Master overview
- [[PT-Box-System]] — Methodology base
- [[Phase-4-Experiment-Log]] — Asian future Phase 5 angles (A1-A4)
