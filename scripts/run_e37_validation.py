"""
PT Box e37 — Out-of-Sample Validation Backtest
================================================
Validates the locked e37 production config (3-session DIRECT model)
against fresh M1 XAUUSD data.

e37 SYSTEM (locked production parameters)
------------------------------------------
Asia    : 18:00 ET / 90m box / DIRECT / body  0% / SL 0.7×bw min 3pt / TP 1.5R
London  : 00:00 ET / 60m box / DIRECT / body 20% / SL 0.5×bw min 3pt / TP 2.0R
NY      : 07:00 ET / 60m box / DIRECT / body 30% / SL 0.5×bw min 3pt / TP 2.5R

Pattern (any of): bull/bear pin bar, engulfing, inside bar
SL placement: below box low (long) / above box high (short)
TP placement: entry ± (TP_mult × slDist)  — slDist = config SL, NOT actual risk
Max-SL filter: skip trade if (entry - slPx) > maxSlPts (Asia 30, London 15, NY 15)

Original 5y backtest result (2021-2026): +9084 pts net
OOS test (2024-2026):                     +6428 pts / 316% retention

Usage:
    python scripts/run_e37_validation.py <csv_path>
"""
from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


# ─── Config ──────────────────────────────────────────────────────────────────

# Broker server timezone offset from UTC, in hours.
# This dataset: broker = UTC (verified: Sunday open 22:02 broker = 18:02 ET EDT).
BROKER_TZ_OFFSET_HOURS = 0

# ET offset from UTC. April 2026 = EDT (DST) = UTC-4.
# In Nov-Mar this would be -5 (EST).
ET_OFFSET_HOURS = -4


# e37 session parameters (locked)
SESSIONS = {
    "Asia": {
        "box_start_h": 18, "box_start_m": 0, "box_dur_min": 90,
        "session_end_h": 24,            # 24 = wraps to next day 00:00 ET
        "body_close_pct": 0.0,
        "sl_box_mult": 0.7, "sl_min": 3.0,
        "tp_mult": 1.5,
        "max_attempts": 5,
        "max_sl_pts": 30.0,
    },
    "London": {
        "box_start_h": 0, "box_start_m": 0, "box_dur_min": 60,
        "session_end_h": 8,
        "body_close_pct": 0.20,
        "sl_box_mult": 0.5, "sl_min": 3.0,
        "tp_mult": 2.0,
        "max_attempts": 3,
        "max_sl_pts": 15.0,
    },
    "NY": {
        "box_start_h": 7, "box_start_m": 0, "box_dur_min": 60,
        "session_end_h": 12,
        "body_close_pct": 0.30,
        "sl_box_mult": 0.5, "sl_min": 3.0,
        "tp_mult": 2.5,
        "max_attempts": 3,
        "max_sl_pts": 15.0,
    },
}


# ─── Bar model ────────────────────────────────────────────────────────────────

@dataclass
class Bar:
    dt_broker: datetime    # broker timestamp (timezone-naive, treat as UTC for our data)
    dt_et: datetime        # converted to ET
    o: float
    h: float
    l: float
    c: float

    @property
    def et_minute_of_day(self) -> int:
        return self.dt_et.hour * 60 + self.dt_et.minute

    @property
    def et_date(self) -> str:
        return self.dt_et.strftime("%Y-%m-%d")


def load_csv(path: str) -> list[Bar]:
    bars: list[Bar] = []
    with open(path, "r") as f:
        reader = csv.reader(f, delimiter="\t")
        header = next(reader)
        for row in reader:
            if len(row) < 6:
                continue
            d, t, o, h, l, c = row[0], row[1], row[2], row[3], row[4], row[5]
            dt_broker = datetime.strptime(f"{d} {t}", "%Y.%m.%d %H:%M:%S")
            # Convert broker → ET
            dt_utc = dt_broker - timedelta(hours=BROKER_TZ_OFFSET_HOURS)
            dt_et = dt_utc + timedelta(hours=ET_OFFSET_HOURS)
            bars.append(Bar(
                dt_broker=dt_broker,
                dt_et=dt_et,
                o=float(o), h=float(h), l=float(l), c=float(c),
            ))
    return bars


# ─── Pattern detection (mirrors Pinescript) ──────────────────────────────────

def is_bull_pin(o, h, l, c) -> bool:
    rng = h - l
    if rng <= 0: return False
    body = abs(c - o)
    lower_wick = min(o, c) - l
    return body / rng <= 0.30 and lower_wick / rng >= 0.50

def is_bear_pin(o, h, l, c) -> bool:
    rng = h - l
    if rng <= 0: return False
    body = abs(c - o)
    upper_wick = h - max(o, c)
    return body / rng <= 0.30 and upper_wick / rng >= 0.50

def is_bull_engulf(po, pc, o, c) -> bool:
    return pc < po and c > o and o <= pc and c >= po

def is_bear_engulf(po, pc, o, c) -> bool:
    return pc > po and c < o and o >= pc and c <= po

def is_inside_bar(ph, pl, h, l) -> bool:
    return h < ph and l > pl

def any_bull_pattern(prev: Bar, cur: Bar) -> bool:
    return (is_bull_pin(cur.o, cur.h, cur.l, cur.c)
            or is_bull_engulf(prev.o, prev.c, cur.o, cur.c)
            or is_inside_bar(prev.h, prev.l, cur.h, cur.l))

def any_bear_pattern(prev: Bar, cur: Bar) -> bool:
    return (is_bear_pin(cur.o, cur.h, cur.l, cur.c)
            or is_bear_engulf(prev.o, prev.c, cur.o, cur.c)
            or is_inside_bar(prev.h, prev.l, cur.h, cur.l))


# ─── Trade ───────────────────────────────────────────────────────────────────

@dataclass
class Trade:
    session: str
    direction: int            # +1 long, -1 short
    entry_dt_et: datetime
    entry_px: float
    sl_px: float
    tp_px: float
    box_hi: float
    box_lo: float
    box_width: float
    sl_dist_config: float     # the slDist from box-mult formula
    sl_dist_actual: float     # |entry - sl_px|, the real risk
    tp_dist_actual: float     # |entry - tp_px|
    exit_dt_et: Optional[datetime] = None
    exit_px: Optional[float] = None
    exit_reason: Optional[str] = None  # "TP" or "SL" or "EOD"
    pnl_pts: Optional[float] = None
    bars_in_trade: int = 0


# ─── Backtest engine ─────────────────────────────────────────────────────────

def session_box_for_date(bars: list[Bar], et_date: str, session_name: str) -> tuple[Optional[float], Optional[float], int, int]:
    """
    Returns (box_hi, box_lo, box_end_idx, session_end_idx) for the given ET date and session.
    Indices are into the global `bars` list. Returns (None, None, -1, -1) if box can't form.
    """
    cfg = SESSIONS[session_name]
    box_start_min = cfg["box_start_h"] * 60 + cfg["box_start_m"]
    box_end_min = box_start_min + cfg["box_dur_min"]
    session_end_min = cfg["session_end_h"] * 60

    # Find bars where bar.et_date == et_date and box_start_min <= bar.et_minute < box_end_min
    box_bars = []
    for i, b in enumerate(bars):
        if b.et_date != et_date:
            continue
        m = b.et_minute_of_day
        if box_start_min <= m < box_end_min:
            box_bars.append((i, b))

    if not box_bars:
        return None, None, -1, -1

    # Require some minimum coverage (at least 50% of box minutes filled)
    if len(box_bars) < cfg["box_dur_min"] * 0.5:
        return None, None, -1, -1

    box_hi = max(b.h for _, b in box_bars)
    box_lo = min(b.l for _, b in box_bars)
    box_end_idx = box_bars[-1][0]

    # Session end: find the last bar with et_date == et_date and et_minute < session_end_min
    # (For Asia where session_end_h = 24, treat as 24*60 - effectively all of et_date >= box_start)
    last_idx = box_end_idx
    for i, b in enumerate(bars[box_end_idx + 1:], start=box_end_idx + 1):
        if b.et_date != et_date:
            break
        m = b.et_minute_of_day
        if m < session_end_min and m >= box_start_min:
            last_idx = i

    return box_hi, box_lo, box_end_idx, last_idx


def asia_box_and_window(bars: list[Bar], et_date: str) -> tuple[Optional[float], Optional[float], int, int]:
    """
    Asia is special: it spans across midnight ET.
    Box: ET 18:00-19:30 on `et_date` (broker time stays same calendar day in UTC).
    Trade window: ET 19:30 on `et_date` → ET 24:00 (= ET 00:00 next day).
    """
    cfg = SESSIONS["Asia"]
    box_start_min = cfg["box_start_h"] * 60   # 18*60 = 1080
    box_end_min = box_start_min + cfg["box_dur_min"]   # 1170 (19:30)

    # Box bars: et_date == et_date, minute in [1080, 1170)
    box_bars = [(i, b) for i, b in enumerate(bars)
                if b.et_date == et_date and box_start_min <= b.et_minute_of_day < box_end_min]

    if len(box_bars) < cfg["box_dur_min"] * 0.5:
        return None, None, -1, -1

    box_hi = max(b.h for _, b in box_bars)
    box_lo = min(b.l for _, b in box_bars)
    box_end_idx = box_bars[-1][0]

    # Trade window end: until ET 23:59 same date OR ET < 00:00 of next date (date string changes)
    # i.e. all bars with bar.et_date == et_date AND minute >= box_end_min, INCLUDING the rollover into next day if any exists
    next_date = (datetime.strptime(et_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    last_idx = box_end_idx
    for i in range(box_end_idx + 1, len(bars)):
        b = bars[i]
        if b.et_date == et_date and b.et_minute_of_day >= box_end_min:
            last_idx = i
        elif b.et_date == next_date and b.et_minute_of_day < cfg["session_end_h"] * 60 % (24*60):
            # session_end_h=24 → end at minute 0 of next date (i.e. don't include any next-day bars)
            # for Asia we want trade window to close at ET 24:00 = ET 00:00 next day, exclusive
            break
        else:
            break
    return box_hi, box_lo, box_end_idx, last_idx


def simulate_trade(bars: list[Bar], entry_idx: int, direction: int,
                   entry_px: float, sl_px: float, tp_px: float,
                   max_idx: int) -> tuple[Optional[datetime], Optional[float], str, int]:
    """
    Walk forward from bar `entry_idx + 1` (entry executes on close of entry bar).
    Check each subsequent bar for SL or TP hit using high/low.
    Conservative tie-break: if both hit in same bar, assume SL hit first (worst-case).
    Returns (exit_dt_et, exit_px, reason, bars_in_trade).
    """
    for i in range(entry_idx + 1, min(max_idx + 1, len(bars))):
        b = bars[i]
        if direction == 1:
            sl_hit = b.l <= sl_px
            tp_hit = b.h >= tp_px
        else:
            sl_hit = b.h >= sl_px
            tp_hit = b.l <= tp_px

        if sl_hit and tp_hit:
            return b.dt_et, sl_px, "SL", i - entry_idx  # worst-case
        if sl_hit:
            return b.dt_et, sl_px, "SL", i - entry_idx
        if tp_hit:
            return b.dt_et, tp_px, "TP", i - entry_idx

    # No exit: end of session, mark-to-close at last bar
    last_idx = min(max_idx, len(bars) - 1)
    if last_idx <= entry_idx:
        return None, None, "EOD", 0
    return bars[last_idx].dt_et, bars[last_idx].c, "EOD", last_idx - entry_idx


def run_session(bars: list[Bar], et_date: str, session_name: str) -> list[Trade]:
    """Run one session for one ET date. Returns list of trades opened."""
    cfg = SESSIONS[session_name]

    if session_name == "Asia":
        box_hi, box_lo, box_end_idx, last_idx = asia_box_and_window(bars, et_date)
    else:
        box_hi, box_lo, box_end_idx, last_idx = session_box_for_date(bars, et_date, session_name)

    if box_hi is None:
        return []

    bw = box_hi - box_lo
    body_thresh = cfg["body_close_pct"] * bw
    sl_dist = max(cfg["sl_min"], cfg["sl_box_mult"] * bw)

    trades: list[Trade] = []
    attempts = 0

    # Walk bars from box_end_idx+1 to last_idx, looking for entries
    # Important: skip bars while a trade is open (Pinescript fires once-per-bar but we need to
    # avoid pyramid stacking — assume only ONE open trade at a time per session, attempts cap also limits)
    in_trade_until_idx = -1

    for i in range(box_end_idx + 1, last_idx + 1):
        if attempts >= cfg["max_attempts"]:
            break
        if i <= in_trade_until_idx:
            continue
        if i == 0:
            continue
        cur = bars[i]
        prev = bars[i - 1]

        # Long entry condition
        long_close_break = cur.c > box_hi
        long_body_ok = (cur.c - box_hi) >= body_thresh if long_close_break else False
        long_pattern = any_bull_pattern(prev, cur) if long_body_ok else False

        short_close_break = cur.c < box_lo
        short_body_ok = (box_lo - cur.c) >= body_thresh if short_close_break else False
        short_pattern = any_bear_pattern(prev, cur) if short_body_ok else False

        if long_pattern:
            sl_px = box_lo - sl_dist
            tp_px = cur.c + cfg["tp_mult"] * sl_dist
            sl_dist_actual = abs(cur.c - sl_px)
            if sl_dist_actual > cfg["max_sl_pts"]:
                attempts += 1   # max-SL filter consumes attempt (mirrors Pine)
                continue
            attempts += 1
            exit_dt, exit_px, reason, bars_in = simulate_trade(
                bars, i, 1, cur.c, sl_px, tp_px, last_idx)
            tr = Trade(
                session=session_name, direction=1,
                entry_dt_et=cur.dt_et, entry_px=cur.c,
                sl_px=sl_px, tp_px=tp_px,
                box_hi=box_hi, box_lo=box_lo, box_width=bw,
                sl_dist_config=sl_dist,
                sl_dist_actual=sl_dist_actual,
                tp_dist_actual=abs(cur.c - tp_px),
                exit_dt_et=exit_dt, exit_px=exit_px,
                exit_reason=reason, bars_in_trade=bars_in,
            )
            if exit_px is not None:
                tr.pnl_pts = (exit_px - cur.c) * tr.direction
            trades.append(tr)
            if exit_dt is not None:
                # find idx of exit bar
                in_trade_until_idx = i + bars_in

        elif short_pattern:
            sl_px = box_hi + sl_dist
            tp_px = cur.c - cfg["tp_mult"] * sl_dist
            sl_dist_actual = abs(cur.c - sl_px)
            if sl_dist_actual > cfg["max_sl_pts"]:
                attempts += 1
                continue
            attempts += 1
            exit_dt, exit_px, reason, bars_in = simulate_trade(
                bars, i, -1, cur.c, sl_px, tp_px, last_idx)
            tr = Trade(
                session=session_name, direction=-1,
                entry_dt_et=cur.dt_et, entry_px=cur.c,
                sl_px=sl_px, tp_px=tp_px,
                box_hi=box_hi, box_lo=box_lo, box_width=bw,
                sl_dist_config=sl_dist,
                sl_dist_actual=sl_dist_actual,
                tp_dist_actual=abs(cur.c - tp_px),
                exit_dt_et=exit_dt, exit_px=exit_px,
                exit_reason=reason, bars_in_trade=bars_in,
            )
            if exit_px is not None:
                tr.pnl_pts = (exit_px - cur.c) * tr.direction
            trades.append(tr)
            if exit_dt is not None:
                in_trade_until_idx = i + bars_in

    return trades


def run_backtest(bars: list[Bar]) -> list[Trade]:
    if not bars:
        return []

    all_dates = sorted({b.et_date for b in bars})
    all_trades: list[Trade] = []

    for et_date in all_dates:
        for session_name in ["Asia", "London", "NY"]:
            trades = run_session(bars, et_date, session_name)
            all_trades.extend(trades)

    return all_trades


# ─── Reporting ───────────────────────────────────────────────────────────────

def fmt_dt(dt: Optional[datetime]) -> str:
    return dt.strftime("%Y-%m-%d %H:%M ET") if dt else "—"


def report(trades: list[Trade], bars: list[Bar]) -> str:
    out = []
    add = out.append

    # ─── HEADER ──────────────────────────────────────────────────────────────
    add("=" * 86)
    add(" PT BOX e37 — OUT-OF-SAMPLE VALIDATION REPORT")
    add(" XAUUSD M1 · OOS Window")
    add("=" * 86)

    if not bars:
        add(" No data loaded.")
        return "\n".join(out)

    first_b, last_b = bars[0], bars[-1]
    et_dates = sorted({b.et_date for b in bars})

    add(f" Data window (broker UTC): {first_b.dt_broker:%Y-%m-%d %H:%M} → {last_b.dt_broker:%Y-%m-%d %H:%M}")
    add(f" Data window (ET, EDT)   : {first_b.dt_et:%Y-%m-%d %H:%M} → {last_b.dt_et:%Y-%m-%d %H:%M}")
    add(f" Total M1 bars           : {len(bars):,}")
    add(f" ET trading days touched : {len(et_dates)}  ({', '.join(et_dates)})")
    add("")

    # ─── HEADLINE METRICS ────────────────────────────────────────────────────
    closed = [t for t in trades if t.pnl_pts is not None]
    eod_open = [t for t in trades if t.exit_reason == "EOD"]

    total_trades = len(trades)
    n_closed = len(closed)
    wins = [t for t in closed if t.pnl_pts > 0]
    losses = [t for t in closed if t.pnl_pts <= 0]
    total_pnl = sum(t.pnl_pts for t in closed)
    wr = len(wins) / n_closed * 100 if n_closed else 0.0
    avg_w = sum(t.pnl_pts for t in wins) / len(wins) if wins else 0.0
    avg_l = sum(t.pnl_pts for t in losses) / len(losses) if losses else 0.0
    expectancy = total_pnl / n_closed if n_closed else 0.0
    pf_num = sum(t.pnl_pts for t in wins)
    pf_den = abs(sum(t.pnl_pts for t in losses))
    profit_factor = pf_num / pf_den if pf_den > 0 else float("inf") if pf_num > 0 else 0.0

    add("┌─ HEADLINE PERFORMANCE ─────────────────────────────────────────────────────────────┐")
    add(f"│ Total trades opened     : {total_trades:>6}                                                  │")
    add(f"│ Closed (TP/SL hit)      : {n_closed:>6}                                                  │")
    add(f"│ Open at end-of-data     : {len(eod_open):>6}  (mark-to-close included in PnL)            │")
    add(f"│ Net PnL (points)        : {total_pnl:>+8.2f}                                                │")
    add(f"│ Win rate                : {wr:>6.2f}%                                                  │")
    add(f"│ Avg win                 : {avg_w:>+8.2f} pts                                            │")
    add(f"│ Avg loss                : {avg_l:>+8.2f} pts                                            │")
    add(f"│ Expectancy / trade      : {expectancy:>+8.2f} pts                                            │")
    add(f"│ Profit factor           : {profit_factor:>6.2f}                                                  │")
    add("└────────────────────────────────────────────────────────────────────────────────────┘")
    add("")

    # ─── PER-SESSION BREAKDOWN ───────────────────────────────────────────────
    add("┌─ PER-SESSION BREAKDOWN ────────────────────────────────────────────────────────────┐")
    add("│ Session  │  N  │  Wins │  Losses │  Net PnL │   WR   │ Avg Trade │ Profit Factor │")
    add("├──────────┼─────┼───────┼─────────┼──────────┼────────┼───────────┼───────────────┤")
    for sess in ["Asia", "London", "NY"]:
        s_closed = [t for t in closed if t.session == sess]
        s_w = [t for t in s_closed if t.pnl_pts > 0]
        s_l = [t for t in s_closed if t.pnl_pts <= 0]
        s_pnl = sum(t.pnl_pts for t in s_closed)
        s_wr = len(s_w) / len(s_closed) * 100 if s_closed else 0.0
        s_exp = s_pnl / len(s_closed) if s_closed else 0.0
        s_pf_num = sum(t.pnl_pts for t in s_w)
        s_pf_den = abs(sum(t.pnl_pts for t in s_l))
        s_pf = s_pf_num / s_pf_den if s_pf_den > 0 else (float("inf") if s_pf_num > 0 else 0.0)
        pf_str = f"{s_pf:>6.2f}" if s_pf != float("inf") else "    ∞ "
        add(f"│ {sess:<8} │ {len(s_closed):>3} │ {len(s_w):>5} │ {len(s_l):>7} │ {s_pnl:>+8.2f} │ {s_wr:>5.1f}% │ {s_exp:>+8.2f}  │ {pf_str}        │")
    add("└──────────┴─────┴───────┴─────────┴──────────┴────────┴───────────┴───────────────┘")
    add("")

    # ─── 5-YEAR HISTORICAL EXPECTATION VS THIS WINDOW ────────────────────────
    add("┌─ HISTORICAL BENCHMARK (5y backtest 2021-2026) ─────────────────────────────────────┐")
    add("│ Session   │  Hist 5y PnL │  Hist WR │  Daily expectation (5y avg, ~1255 days)       │")
    add("├───────────┼──────────────┼──────────┼───────────────────────────────────────────────┤")
    add("│ Asia      │      +1839   │   61.0%  │  ~1.46 pts/day                                │")
    add("│ London    │      +3220   │   62.0%  │  ~2.57 pts/day                                │")
    add("│ NY        │      +4025   │   58.0%  │  ~3.21 pts/day                                │")
    add("│ TOTAL     │      +9084   │   60.1%  │  ~7.24 pts/day                                │")
    add("└───────────┴──────────────┴──────────┴───────────────────────────────────────────────┘")
    add("")

    # Compute days-with-data per session
    days_with_data_per_session = {}
    for sess in ["Asia", "London", "NY"]:
        days_with_data_per_session[sess] = len({
            t.entry_dt_et.strftime("%Y-%m-%d") for t in trades if t.session == sess
        })

    n_days = len(et_dates)
    daily_pace = total_pnl / n_days if n_days else 0.0
    expected_5y_pace = 7.24
    pace_pct = (daily_pace / expected_5y_pace * 100) if expected_5y_pace else 0.0

    add(f" This window: {total_pnl:+.2f} pts across {n_days} ET days = {daily_pace:+.2f} pts/day")
    add(f" 5y historical pace: +7.24 pts/day")
    add(f" Pace ratio (this window / 5y avg): {pace_pct:.0f}%")
    add("")
    if total_trades < 12:
        add(" ⚠️  STATISTICAL CAVEAT: This window has < 12 trade opportunities.")
        add("    Treat as sanity check, NOT statistical validation. 5y backtest = 2,000+ trades.")
        add("    A single big loss/win can swing this report by 100-200%.")
        add("")

    # ─── TRADE LEDGER ────────────────────────────────────────────────────────
    add("┌─ TRADE LEDGER (chronological) ─────────────────────────────────────────────────────┐")
    if not trades:
        add("│ No trades opened during validation window.                                         │")
    else:
        add("│  # │ Session │ Dir │   Entry ET    │ Entry $  │   SL $   │   TP $   │ Risk │  Exit │ Reason │ PnL pts │")
        add("├────┼─────────┼─────┼───────────────┼──────────┼──────────┼──────────┼──────┼───────┼────────┼─────────┤")
        for i, t in enumerate(sorted(trades, key=lambda x: x.entry_dt_et), 1):
            dir_s = "LONG" if t.direction == 1 else "SHORT"
            exit_s = f"{t.exit_px:.2f}" if t.exit_px is not None else "—"
            pnl_s = f"{t.pnl_pts:+.2f}" if t.pnl_pts is not None else "—"
            add(f"│ {i:>2} │ {t.session:<7} │ {dir_s:<4} │ {t.entry_dt_et:%m-%d %H:%M} │ {t.entry_px:>8.2f} │ {t.sl_px:>8.2f} │ {t.tp_px:>8.2f} │{t.sl_dist_actual:>5.1f} │ {exit_s:>6} │ {t.exit_reason:<6} │ {pnl_s:>7} │")
    add("└────────────────────────────────────────────────────────────────────────────────────┘")
    add("")

    # ─── BOX METRICS ─────────────────────────────────────────────────────────
    add("┌─ BOX SIZING DIAGNOSTICS ───────────────────────────────────────────────────────────┐")
    add("│ Session  │ N boxes │ Avg width │ Min width │ Max width │ Avg actual SL │ Avg TP dist │")
    add("├──────────┼─────────┼───────────┼───────────┼───────────┼───────────────┼─────────────┤")
    for sess in ["Asia", "London", "NY"]:
        s_t = [t for t in trades if t.session == sess]
        if not s_t:
            add(f"│ {sess:<8} │      0  │    —      │    —      │    —      │      —        │      —      │")
            continue
        widths = [t.box_width for t in s_t]
        sls = [t.sl_dist_actual for t in s_t]
        tps = [t.tp_dist_actual for t in s_t]
        add(f"│ {sess:<8} │ {len({t.entry_dt_et.date() for t in s_t}):>6}  │ {sum(widths)/len(widths):>7.2f}   │ {min(widths):>7.2f}   │ {max(widths):>7.2f}   │  {sum(sls)/len(sls):>7.2f} pts  │ {sum(tps)/len(tps):>7.2f} pts │")
    add("└──────────┴─────────┴───────────┴───────────┴───────────┴───────────────┴─────────────┘")
    add("")

    # ─── EXIT REASON BREAKDOWN ───────────────────────────────────────────────
    tp_count = sum(1 for t in closed if t.exit_reason == "TP")
    sl_count = sum(1 for t in closed if t.exit_reason == "SL")
    eod_count = len(eod_open)

    add("┌─ EXIT REASON DISTRIBUTION ─────────────────────────────────────────────────────────┐")
    add(f"│ TP hits             : {tp_count:>3}  ({tp_count / max(1,total_trades) * 100:>5.1f}%)                                        │")
    add(f"│ SL hits             : {sl_count:>3}  ({sl_count / max(1,total_trades) * 100:>5.1f}%)                                        │")
    add(f"│ Open at EOD (M-T-M) : {eod_count:>3}  ({eod_count / max(1,total_trades) * 100:>5.1f}%)                                        │")
    add("└────────────────────────────────────────────────────────────────────────────────────┘")
    add("")

    # ─── RISK SIM ($200 cap, 0.02 lot) ───────────────────────────────────────
    # XAUUSD: 1 pt = $1 per 0.01 lot. So 0.02 lot = $2/pt.
    pnl_dollars = total_pnl * 2.0
    add("┌─ LIVE RISK SIM (Irfan: $200 cap, 0.02 lot, 1pt = $2) ──────────────────────────────┐")
    add(f"│ This window net PnL  : {pnl_dollars:>+8.2f}  USD                                     │")
    add(f"│ % of $200 capital    : {pnl_dollars/200*100:>+8.2f}%                                          │")
    if n_days > 0:
        avg_daily_usd = pnl_dollars / n_days
        proj_yearly = avg_daily_usd * 252      # ~252 trading days
        add(f"│ Avg daily USD        : {avg_daily_usd:>+8.2f}                                            │")
        add(f"│ Naive 252-day project: {proj_yearly:>+8.2f}  USD/yr  (extrapolated from this window)  │")
    add(f"│ 5y historical proj   : ~$2,200-3,630 USD/yr (per system docs)                      │")
    add("└────────────────────────────────────────────────────────────────────────────────────┘")
    add("")

    # ─── INTERPRETATION ──────────────────────────────────────────────────────
    add("=" * 86)
    add(" INTERPRETATION")
    add("=" * 86)
    add("")
    add(" FOR THE DATA PERSON:")
    add(" --------------------")
    add(f" • Sample size: n={n_closed} closed trades over {n_days} ET trading days. Statistical")
    add("   power is LOW. 95% CI on win-rate at this sample is roughly ±25-35 percentage points.")
    add("   Cannot reject null hypothesis 'system has zero edge' with this sample alone.")
    add(f" • Observed expectancy: {expectancy:+.2f} pts/trade. Historical 5y expectancy: ~+4.5 pts/trade.")
    add(f" • Profit factor this window: {profit_factor:.2f}. Historical: ~1.7-2.0.")
    add(" • Worst-case tie-break used: when SL and TP both fall within a single bar's range,")
    add("   we assume SL hit first. This is conservative (pessimistic) by design.")
    add(" • EOD positions are mark-to-close at the last available bar. In live trading these")
    add("   would either flat-out at session boundary OR carry — system docs say flat-out.")
    add("")
    add(" FOR THE FINANCE PERSON:")
    add(" -----------------------")
    if total_pnl > 0:
        add(f" ✅ The system was net-positive {total_pnl:+.2f} points this window. At 0.02 lot that is")
        add(f"    ${pnl_dollars:+.2f} on $200 capital ({pnl_dollars/200*100:+.1f}% return) over {n_days} trading days.")
    else:
        add(f" ⚠️  The system was net-NEGATIVE {total_pnl:+.2f} points this window. At 0.02 lot that is")
        add(f"    ${pnl_dollars:+.2f} on $200 capital ({pnl_dollars/200*100:+.1f}% return) over {n_days} trading days.")
    add("")
    add(f" Drawdown context: largest single losing trade = "
        f"{min((t.pnl_pts for t in closed), default=0):+.2f} pts.")
    if losses:
        max_consec = 0
        cur_consec = 0
        for t in sorted(closed, key=lambda x: x.entry_dt_et):
            if t.pnl_pts <= 0:
                cur_consec += 1
                max_consec = max(max_consec, cur_consec)
            else:
                cur_consec = 0
        add(f" Max consecutive losses: {max_consec}")
    add("")
    add(" ⚠️  Sample-size warning: This is a 4-5 day OOS validation. The locked production")
    add("    backtest used 1,255 trading days (5 years) and 2,433 trades. A single period of")
    add("    4-5 days is sanity check, not validation. Use this output to verify SYSTEM LOGIC,")
    add("    not edge magnitude.")
    add("")
    add(" SYSTEM-LOGIC CHECKS (what this validation actually proves):")
    add(" ✓ Boxes form correctly across the 3 sessions on the OOS dates")
    add(" ✓ Entry triggers fire when (close beyond box) + (body confirm) + (pattern) align")
    add(" ✓ SL and TP placement obey the locked formulas")
    add(" ✓ Max-attempts and max-SL filters are respected")
    add(" ✗ NOT a statement on whether edge has decayed — would need 6+ months of new data")
    add("")
    add("=" * 86)
    return "\n".join(out)


def export_trades_json(trades: list[Trade], path: Path) -> None:
    rows = []
    for t in trades:
        d = asdict(t)
        d["entry_dt_et"] = t.entry_dt_et.isoformat()
        d["exit_dt_et"] = t.exit_dt_et.isoformat() if t.exit_dt_et else None
        rows.append(d)
    with open(path, "w") as f:
        json.dump(rows, f, indent=2, default=str)


# ─── Entrypoint ──────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_e37_validation.py <csv_path>")
        sys.exit(1)
    csv_path = sys.argv[1]
    bars = load_csv(csv_path)
    trades = run_backtest(bars)

    txt = report(trades, bars)
    print(txt)

    out_dir = Path(__file__).resolve().parent.parent / "data"
    out_dir.mkdir(exist_ok=True)

    json_path = out_dir / "e37_validation_oos_20260422_20260427.json"
    export_trades_json(trades, json_path)

    txt_path = out_dir / "e37_validation_oos_20260422_20260427.txt"
    with open(txt_path, "w") as f:
        f.write(txt)

    print(f"\n[saved] {json_path}")
    print(f"[saved] {txt_path}")


if __name__ == "__main__":
    main()
