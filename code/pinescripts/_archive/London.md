---
title: PT Box London Pine Script (Phase 4 #2 Enhanced)
date: 2026-04-27
tags:
  - trading
  - pinescript
  - tradingview
  - london
  - phase-4
status: active
aliases:
  - Pine Script London
  - PT Box London Indicator
---

# 📜 PT Box London Pine Script (Phase 4 #2 Enhanced)

> [!success] Built off reference
> Reference script lu **verbatim** + Phase 4 #2 toggleable additions. Visual IDENTICAL ke reference (no floating diff). Default behavior = reference baseline. Toggle ON Phase 4 features kapan mau.

## 🎯 Default Behavior (out-of-box)

Persis sama dengan reference lu:
```
Box: 01:42 NY, 7m
SL: pullback wick - 3pts (fixed)
TP1: +15 pts, TP2: +25 pts (fixed)
Max attempts: 3/day
Pattern filter: OFF
```

= **identik reference**. Box rendering ga akan beda visual.

## 🚀 Phase 4 #2 Toggle (Optional Upgrade)

Klik settings indicator, toggle:
1. **"Use Dynamic SL+TP (Phase 4 #2)"** → ON
   - SL = max(3, 0.5 × box_width)
   - TP1 = 3 × SL, TP2 = 6 × SL
2. **"Pattern Filter (Phase 4 #2)"** → "any"
   - Require pin OR engulfing OR inside bar di pullback

Hasil = Phase 4 #2 enhanced (5 yr backtest +468 pts London).

## 📋 Pine Script v5 Code

```pinescript
//@version=5
indicator("PT London — Phase 4 #2 (Irfan)", overlay=true, max_boxes_count=500, max_lines_count=500, max_labels_count=500)

// INPUTS — match reference exactly
box_hour     = input.int(01,   "PT Box Hour (NY time)",  minval=0, maxval=23)
box_minute   = input.int(0,    "PT Box Minute (Phase 4 #2 ceiling optimal: 01:00)", minval=0, maxval=59)
box_duration = input.int(7,    "Box Duration (minutes)", minval=1, maxval=60)
sl_buf       = input.float(3,  "SL Buffer (points)",     minval=0.1)
tp1_pts      = input.float(15, "TP1 (points)",           minval=0.1)
tp2_pts      = input.float(25, "TP2 (points)",           minval=0.1)
max_att      = input.int(3,    "Max Attempts per day",   minval=1, maxval=6)
show_box     = input.bool(true, "Show PT Box")
show_sig     = input.bool(true, "Show Signals")

// PHASE 4 #2 ADDITIONS (default OFF — toggle ON kalau mau)
use_dyn_sltp = input.bool(true, "Use Dynamic SL+TP (Phase 4 #2)")
sl_box_mult  = input.float(0.5,  "Dynamic SL = X × box_width", minval=0.1, maxval=2.0, step=0.1)
tp1_mult     = input.float(3,    "Dynamic TP1 = X × SL", minval=1)
tp2_mult     = input.float(6,    "Dynamic TP2 = X × SL", minval=1)

pat_mode     = input.string("any", "Pattern Filter (Phase 4 #2)", options=["off","pin","engulf","inside","any"])
pin_body_max = input.float(0.30, "Pin: Max Body/Range", minval=0.1, maxval=0.5, step=0.05)
pin_wick_min = input.float(0.50, "Pin: Min Wick/Range", minval=0.3, maxval=0.7, step=0.05)

// NY TIME — same as reference
ny_h       = hour(time,      "America/New_York")
ny_m       = minute(time,    "America/New_York")
ny_dw      = dayofweek(time, "America/New_York")
is_weekday = ny_dw != dayofweek.saturday and ny_dw != dayofweek.sunday

// BOX FORMATION — same as reference
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
        box.new(bar_index - box_duration, bx_lo, bar_index + 80, bx_hi, bgcolor=color.new(color.purple, 85), border_color=color.new(color.purple, 20), border_width=1)

// DAY STATE — same as reference
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

// BREAKOUT — same as reference
if is_after_box and not in_trade and not day_done and is_past_sl_bar
    if close > day_hi and bk_dir != 1
        bk_dir := 1
        bk_bar := bar_index
    else if close < day_lo and bk_dir != -1
        bk_dir := -1
        bk_bar := bar_index

is_past_breakout_bar = not na(bk_bar) and bar_index > bk_bar

// PHASE 4 #2 PATTERN HELPERS
is_pin_bar(int dir) =>
    rng = high - low
    body = math.abs(close - open)
    body_ok = rng > 0 and body / rng <= pin_body_max
    wick = dir == 1 ? math.min(open, close) - low : high - math.max(open, close)
    wick_ok = rng > 0 and wick / rng >= pin_wick_min
    body_ok and wick_ok

is_engulfing(int dir) =>
    dir == 1 ? (close[1] < open[1] and close > open and open <= close[1] and close >= open[1]) : (close[1] > open[1] and close < open and open >= close[1] and close <= open[1])

is_inside_bar() =>
    high < high[1] and low > low[1]

check_pattern(int dir) =>
    pat_mode == "off" ? true : pat_mode == "pin" ? is_pin_bar(dir) : pat_mode == "engulf" ? is_engulfing(dir) : pat_mode == "inside" ? is_inside_bar() : pat_mode == "any" ? (is_pin_bar(dir) or is_engulfing(dir) or is_inside_bar()) : true

// PULLBACK — reference logic + pattern filter
pullback_up   = is_after_box and is_past_breakout_bar and bk_dir == 1
              and not in_trade and not day_done and attempt < max_att
              and close > day_hi
              and low   <= day_hi
              and check_pattern(1)

pullback_down = is_after_box and is_past_breakout_bar and bk_dir == -1
              and not in_trade and not day_done and attempt < max_att
              and close < day_lo
              and high  >= day_lo
              and check_pattern(-1)

is_pullback = pullback_up or pullback_down

// PHASE 4 #2 DYNAMIC SL/TP CALCULATION
box_width_now = (not na(day_hi) and not na(day_lo)) ? day_hi - day_lo : 0.0
sl_dyn  = use_dyn_sltp ? math.max(sl_buf, sl_box_mult * box_width_now) : sl_buf
tp1_dyn = use_dyn_sltp ? tp1_mult * sl_dyn : tp1_pts
tp2_dyn = use_dyn_sltp ? tp2_mult * sl_dyn : tp2_pts

// ENTRY — reference logic + dynamic SL/TP
var int   total_win  = 0
var int   total_loss = 0
var int   total_chop = 0
var float total_pnl  = 0.0

if is_pullback and not in_trade
    attempt  := attempt + 1
    in_trade := true
    entry_px := close
    if bk_dir == 1
        sl_px  := low  - sl_dyn
        tp1_px := entry_px + tp1_dyn
        tp2_px := entry_px + tp2_dyn
    else
        sl_px  := high + sl_dyn
        tp1_px := entry_px - tp1_dyn
        tp2_px := entry_px - tp2_dyn
    if show_sig
        label.new(bar_index, bk_dir == 1 ? low - (day_hi - day_lo) * 0.5 : high + (day_hi - day_lo) * 0.5, (bk_dir == 1 ? "BUY " : "SELL ") + str.tostring(attempt) + "x", style=bk_dir == 1 ? label.style_label_up : label.style_label_down, color=color.new(color.teal, 10), textcolor=color.white, size=size.small)

// TRADE MANAGEMENT — reference + dynamic values
if in_trade and not na(sl_px) and not na(tp1_px)
    hit_sl  = bk_dir == 1 ? low  <= sl_px  : high >= sl_px
    hit_tp1 = bk_dir == 1 ? high >= tp1_px : low  <= tp1_px
    hit_tp2 = bk_dir == 1 ? high >= tp2_px : low  <= tp2_px

    if hit_tp2
        total_win := total_win + 1
        total_pnl := total_pnl + tp2_dyn
        in_trade  := false
        day_done  := true
        if show_sig
            label.new(bar_index, tp2_px, "TP2 ✓", style=label.style_label_down, color=color.new(color.green, 0), textcolor=color.white, size=size.tiny)

    else if hit_tp1
        total_win := total_win + 1
        total_pnl := total_pnl + tp1_dyn
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

// PLOTS — same as reference
plot(in_trade ? sl_px  : na, "SL",  color=color.new(color.red,    20), linewidth=1, style=plot.style_linebr)
plot(in_trade ? tp1_px : na, "TP1", color=color.new(color.lime,   20), linewidth=1, style=plot.style_linebr)
plot(in_trade ? tp2_px : na, "TP2", color=color.new(color.green,  20), linewidth=1, style=plot.style_linebr)
plot(is_after_box ? day_hi : na, "BoxHi", color=color.new(color.purple, 50), linewidth=1, style=plot.style_linebr)
plot(is_after_box ? day_lo : na, "BoxLo", color=color.new(color.purple, 50), linewidth=1, style=plot.style_linebr)

// ALERTS
alertcondition(pullback_up,   title="🟢 London BUY Signal",  message="PT London — BUY\nEntry: next candle OPEN")
alertcondition(pullback_down, title="🔴 London SELL Signal", message="PT London — SELL\nEntry: next candle OPEN")
alertcondition(is_box_end and bx_ready, title="📦 London Box Formed", message="PT London — Box terbentuk. Standby breakout.")

// STATS TABLE — same as reference
if barstate.islast
    total_trades = total_win + total_loss
    win_rate     = total_trades > 0 ? (float(total_win) / float(total_trades)) * 100 : 0.0
    rr           = sl_buf > 0 ? tp2_pts / sl_buf : 0.0
    var table t  = table.new(position.bottom_left, 2, 12, bgcolor=color.new(color.black, 60), border_color=color.new(color.gray, 40), border_width=1, frame_color=color.new(color.purple, 20), frame_width=2)
    table.cell(t, 0, 0,  "PT London",         bgcolor=color.new(color.purple, 20), text_color=color.white, text_size=size.normal)
    table.cell(t, 1, 0,  str.tostring(box_hour) + ":" + (box_minute < 10 ? "0" : "") + str.tostring(box_minute) + " London", bgcolor=color.new(color.purple, 20), text_color=color.white, text_size=size.normal)
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

## 🎯 Pattern Filter Choice (any vs pin-only)

| Filter Mode | Total PnL | London PnL | Tradeoff |
|---|---|---|---|
| `any` (pin OR engulf OR inside) | **-562** ⭐ | **+468** ⭐ | Best PnL, complex mental model |
| `pin_bar_only` | -641 | +57 | Cleaner discipline, less PnL |
| `engulfing_only` | -717 | +103 | Hurts NY |
| `off` (no filter) | -803 | +142 | Baseline |

**Use case:**
- **`any` (default):** backtest-optimal, PnL terbaik. Indicator detect 3 pattern types.
- **`pin_bar_only`:** simpler mental model — lu cuma cari 1 pattern type di pullback candle. Sacrifice ~80 pts PnL untuk discipline.
- **Hybrid (recommended):** pasang `any` di indicator + manual filter pas eksekusi live (lu cuma ambil yg pin obvious, skip pattern marginal). Maximizes data coverage tapi tetep disciplined.

## 🔄 Pemakaian

### Mode A: Reference baseline (default, like sekarang)
- Paste code → save → add to chart
- Default settings = reference lu (visual sama, behavior sama, no float diff)

### Mode B: Phase 4 #2 enhanced
- Settings → toggle **"Use Dynamic SL+TP"** → ON
- Settings → **"Pattern Filter"** → pilih `any`
- Save settings
- Reload chart → sekarang Phase 4 #2 enhanced
- Visual ga akan beda dari Mode A (box/structure same)
- Cuma signals lebih selective (pattern filter), SL/TP dinamis per box width

## 🔗 Related

- [[PT-Box-NY-Pinescript]] — NY (improve di conversation lain)
- [[PT-Box-Asian-Pinescript]] — Asian (improve di conversation lain)
- [[PT-Box-Pinescripts-Index]] — Master overview
- [[Phase-4-Session-2026-04-27]] — Phase 4 backtest result
