"""PT Box Engine — e37 canonical (consolidated).

Single entry point for all PT Box backtest operations at e37 config.

Re-exports from `ptbox_quarterly_v3` (canonical core) + adds e37-specific
session backtest functions used in the iteration journey (e26-e37).

Usage:
    from ptbox_engine_e37 import (
        load_data, build_date_groups,
        backtest_asia, backtest_london, backtest_ny,
        E37_CONFIG,
    )

    df = load_data("/path/to/XAUUSD_M1.csv")
    dg, dates = build_date_groups(df)
    result = backtest_ny(dg, dates, **E37_CONFIG["ny"])
"""
import sys
from pathlib import Path

# Re-export canonical core
sys.path.insert(0, str(Path(__file__).parent))
from ptbox_quarterly_v3 import (  # noqa: F401
    CONFIG,
    load_data,
    build_date_groups,
    PATTERN_VARIANTS,
)

import numpy as np
import pandas as pd

# ═══════════════════════════════════════════════════════════════════
# e37 LOCKED CONFIG (live-ready, OOS validated 316% retention)
# ═══════════════════════════════════════════════════════════════════
E37_CONFIG = {
    "asia": {
        "box_start_h": 18, "box_start_m": 0, "box_dur": 90,
        "session_end_h": 24,   # 24 = next-day midnight extended
        "sl_box_mult": 0.7, "min_sl": 3.0,
        "tp_mult": 1.5,
        "body_pct": 0.0,
        "max_sl_pts": 30.0,
    },
    "london": {
        "box_start_h": 0, "box_start_m": 0, "box_dur": 60,
        "session_end_h": 8,
        "sl_box_mult": 0.5, "min_sl": 3.0,
        "tp_mult": 2.0,
        "body_pct": 0.20,
        "max_sl_pts": 15.0,
    },
    "ny": {
        "box_start_h": 7, "box_start_m": 0, "box_dur": 60,
        "session_end_h": 12,
        "sl_box_mult": 0.5, "min_sl": 3.0,
        "tp_mult": 2.5,
        "body_pct": 0.30,
        "max_sl_pts": 15.0,
    },
}

# ═══════════════════════════════════════════════════════════════════
# Pattern detectors
# ═══════════════════════════════════════════════════════════════════
def is_pin(o, h, l, c, direction):
    rng = h - l
    if rng <= 0:
        return False
    body = abs(c - o)
    if body / rng > 0.30:
        return False
    if direction == 1:
        return (min(o, c) - l) / rng >= 0.50
    return (h - max(o, c)) / rng >= 0.50


def is_engulf(po, pc, o, c, direction):
    if direction == 1:
        return pc < po and c > o and o <= pc and c >= po
    return pc > po and c < o and o >= pc and c <= po


def is_inside(ph, pl, h, l):
    return h < ph and l > pl


def pattern_any(po, ph, pl, pc, o, h, l, c, direction):
    return (
        is_pin(o, h, l, c, direction)
        or is_engulf(po, pc, o, c, direction)
        or is_inside(ph, pl, h, l)
    )


# ═══════════════════════════════════════════════════════════════════
# Session backtest — DIRECT model (used by all 3 sessions in e37)
# ═══════════════════════════════════════════════════════════════════
def backtest_session_direct(
    date_groups, all_dates,
    box_start_h, box_start_m, box_dur, session_end_h,
    sl_box_mult=0.5, min_sl=3.0, tp_mult=2.0, body_pct=0.0,
    max_sl_pts=None, min_box_width=1.0,
    pattern_fn=pattern_any,
):
    """Generic DIRECT-model session backtest.

    Used identically for Asia/London/NY in e37 (they differ only in params).
    Returns dict: pnl, trades, wins, losses, wr, avg_sl, med_sl.
    """
    BS = box_start_h * 60 + box_start_m
    BE = BS + box_dur
    if session_end_h == 24:
        SESSION_END = 24 * 60   # midnight wrap (next-day open at 00:00 ET)
    else:
        SESSION_END = session_end_h * 60

    tw = tl = 0
    pnl_list = []
    sl_dists = []

    for day in all_dates:
        if day not in date_groups:
            pnl_list.append(0.); continue

        g = date_groups[day]
        tm = g['tm'].values
        H = g['high'].values; L = g['low'].values
        C = g['close'].values; O = g['open'].values

        bk = (tm >= BS) & (tm < BE)
        if bk.sum() == 0:
            pnl_list.append(0.); continue
        bx_hi = H[bk].max(); bx_lo = L[bk].min()
        bw = bx_hi - bx_lo
        if bw < min_box_width:
            pnl_list.append(0.); continue

        tr = (tm >= BE) & (tm < SESSION_END)
        if tr.sum() < 3:
            pnl_list.append(0.); continue

        Hi = H[tr]; Lo = L[tr]; Cl = C[tr]; Op = O[tr]

        sl_dist = max(min_sl, sl_box_mult * bw)
        if max_sl_pts is not None and sl_dist > max_sl_pts:
            pnl_list.append(0.); continue
        body_thresh = body_pct * bw if body_pct > 0 else 0

        in_trade = False
        ed = 0; sp = tp = 0.; ep = 0.
        dp = 0.; dw = dl = 0
        entered = False

        for i in range(1, len(Cl)):
            ch = Hi[i]; cl = Lo[i]; cc = Cl[i]; co = Op[i]
            ph = Hi[i - 1]; pl = Lo[i - 1]; pc = Cl[i - 1]; po = Op[i - 1]

            if in_trade:
                if ed == 1:
                    if cl <= sp:
                        dl += 1; dp -= sl_dist; in_trade = False; continue
                    if ch >= tp:
                        dw += 1; dp += (tp - ep); in_trade = False; continue
                else:
                    if ch >= sp:
                        dl += 1; dp -= sl_dist; in_trade = False; continue
                    if cl <= tp:
                        dw += 1; dp += (ep - tp); in_trade = False; continue
                continue

            if entered:
                continue

            if cc > bx_hi:
                if cc - bx_hi < body_thresh:
                    continue
                if pattern_fn(po, ph, pl, pc, co, ch, cl, cc, 1):
                    ep = cc; ed = 1
                    sp = bx_lo - sl_dist
                    tp = ep + tp_mult * sl_dist
                    in_trade = True; entered = True
                    sl_dists.append(sl_dist)
                    continue
            elif cc < bx_lo:
                if bx_lo - cc < body_thresh:
                    continue
                if pattern_fn(po, ph, pl, pc, co, ch, cl, cc, -1):
                    ep = cc; ed = -1
                    sp = bx_hi + sl_dist
                    tp = ep - tp_mult * sl_dist
                    in_trade = True; entered = True
                    sl_dists.append(sl_dist)
                    continue

        tw += dw; tl += dl
        pnl_list.append(dp)

    tt = tw + tl
    return {
        'pnl': float(np.sum(pnl_list)),
        'trades': tt, 'wins': tw, 'losses': tl,
        'wr': 100.0 * tw / tt if tt else 0,
        'avg_sl': float(np.mean(sl_dists)) if sl_dists else 0,
        'med_sl': float(np.median(sl_dists)) if sl_dists else 0,
        'pnl_per_day': pnl_list,
    }


# ═══════════════════════════════════════════════════════════════════
# Convenience wrappers per session (use E37_CONFIG defaults)
# ═══════════════════════════════════════════════════════════════════
def backtest_asia(date_groups, all_dates, **overrides):
    cfg = {**E37_CONFIG["asia"], **overrides}
    return backtest_session_direct(date_groups, all_dates, **cfg)


def backtest_london(date_groups, all_dates, **overrides):
    cfg = {**E37_CONFIG["london"], **overrides}
    return backtest_session_direct(date_groups, all_dates, **cfg)


def backtest_ny(date_groups, all_dates, **overrides):
    cfg = {**E37_CONFIG["ny"], **overrides}
    return backtest_session_direct(date_groups, all_dates, **cfg)


def run_e37_full(csv_path):
    """Run all 3 sessions at e37 config. Returns combined dict."""
    df = load_data(csv_path)
    dg, dates = build_date_groups(df)
    asia = backtest_asia(dg, dates)
    london = backtest_london(dg, dates)
    ny = backtest_ny(dg, dates)
    total = asia['pnl'] + london['pnl'] + ny['pnl']
    return {
        'asia': asia,
        'london': london,
        'ny': ny,
        'total_pnl': total,
        'days': len(dates),
    }


if __name__ == "__main__":
    csv = "/Users/irfanprimaputra.b/Downloads/XAUUSD_M1_2021_-_2026.csv"
    if len(sys.argv) > 1:
        csv = sys.argv[1]
    print(f"Running e37 full backtest on {csv}")
    r = run_e37_full(csv)
    print(f"\n{'Session':<10} | {'PnL':>8} | {'Trades':>6} | {'WR':>5} | {'avg SL':>6}")
    print("-" * 50)
    for sess in ['asia', 'london', 'ny']:
        s = r[sess]
        print(f"{sess.upper():<10} | {s['pnl']:>+8.0f} | {s['trades']:>6} | {s['wr']:>4.1f}% | {s['avg_sl']:>5.1f}pt")
    print("-" * 50)
    print(f"{'TOTAL':<10} | {r['total_pnl']:>+8.0f} pts ({r['days']} days)")
