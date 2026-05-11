"""
Phase 45 — S/R Level Strategy (PARALLEL to PT Box).

NEW PARADIGM: level-based mean-revert / continuation, 24h window.

User goal: capture clean trend days that PT Box misses (need box+pullback).

Mechanic:
- Daily levels auto-detect: PDH, PDL, PDM, Daily Pivot, S1, R1
- Entry: price touch level + rejection candle (pin/engulf)
- SL: fixed 5pt
- TP: 2× SL (1:2 RR)
- BE Trail v14 (BE @ +1R, then trail)
- Direction bias: trade with daily trend only (optional)

Variants tested:
- V1: Touch + reject at PDH/PDL (mean-revert)
- V2: Touch + reject at all 5 levels (PDH/PDL/PP/S1/R1)
- V3: V2 + daily trend bias filter (skip counter-trend)
- V4: Break PDH + retest = continuation entry
"""
import sys
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
from ptbox_engine_e37 import load_data, build_date_groups

CSV = "/Users/irfanprimaputra.b/Downloads/XAUUSD_M1_2021_-_2026.csv"


def compute_daily_levels(date_groups, all_dates):
    """Compute PDH/PDL/PDM/PP/S1/R1 for each day based on prior day."""
    levels = {}
    sorted_dates = sorted(all_dates)
    for i, d in enumerate(sorted_dates):
        if i == 0: continue
        prev_d = sorted_dates[i-1]
        if prev_d not in date_groups: continue
        prev_g = date_groups[prev_d]
        if len(prev_g) < 100: continue
        pdh = float(prev_g['high'].max())
        pdl = float(prev_g['low'].min())
        pdc = float(prev_g['close'].iloc[-1])
        pdm = (pdh + pdl) / 2
        pp = (pdh + pdl + pdc) / 3
        r1 = 2 * pp - pdl
        s1 = 2 * pp - pdh
        levels[d] = {'pdh': pdh, 'pdl': pdl, 'pdm': pdm, 'pp': pp, 's1': s1, 'r1': r1, 'pdc': pdc}
    return levels


def daily_bias(prev_3day_closes, today_open, levels):
    """Score 0-100: 0=strong sell, 50=neutral, 100=strong buy."""
    if len(prev_3day_closes) < 3:
        return 50
    score = 50
    # 3-day trend
    if prev_3day_closes[-1] > prev_3day_closes[-3]: score += 15
    elif prev_3day_closes[-1] < prev_3day_closes[-3]: score -= 15
    # Open vs PDM
    if today_open > levels['pdm']: score += 10
    else: score -= 10
    # Open vs PDC
    if today_open > levels['pdc']: score += 8
    else: score -= 8
    # Position in PDH-PDL range
    range_pct = (today_open - levels['pdl']) / (levels['pdh'] - levels['pdl']) if levels['pdh'] != levels['pdl'] else 0.5
    if range_pct > 0.7: score += 5
    elif range_pct < 0.3: score -= 5
    return max(0, min(100, score))


def is_bull_reject(po, ph, pl, pc, co, ch, cl, cc):
    rng = ch - cl
    if rng <= 0: return False
    pin = (cc - cl) / rng > 0.55 and cc > co
    engulf = cc > po and co < pc and cc > co
    return pin or engulf


def is_bear_reject(po, ph, pl, pc, co, ch, cl, cc):
    rng = ch - cl
    if rng <= 0: return False
    pin = (ch - cc) / rng > 0.55 and cc < co
    engulf = cc < po and co > pc and cc < o if False else (cc < po and co > pc and cc < co)
    return pin or engulf


def simulate_sr_strategy(date_groups, all_dates, levels, *,
                         variant='V1', sl_pts=5.0, tp_mult=2.0, max_attempts=5,
                         touch_tol=1.0, use_be_trail=True, use_bias=False):
    """Run S/R strategy backtest."""
    pnl = 0.0
    n = w = l = be_saves = trail_exits = tp_hits = 0
    worst = 0.0

    sorted_dates = sorted(all_dates)
    closes_history = []

    for d_idx, d in enumerate(sorted_dates):
        if d not in date_groups: continue
        if d not in levels: continue
        g = date_groups[d]
        if len(g) < 100: continue

        lv = levels[d]
        today_open = float(g['close'].iloc[0])

        # Update 3-day close history
        bias_score = daily_bias(closes_history, today_open, lv) if len(closes_history) >= 3 else 50
        closes_history.append(float(g['close'].iloc[-1]))
        if len(closes_history) > 3: closes_history.pop(0)

        # Allowed direction based on bias
        allow_long = True; allow_short = True
        if use_bias:
            if bias_score < 40: allow_long = False
            if bias_score > 60: allow_short = False

        # Define active levels based on variant
        if variant == 'V1':
            active_levels = [('pdh', 'short'), ('pdl', 'long')]
        elif variant in ('V2', 'V3'):
            active_levels = [('pdh', 'short'), ('pdl', 'long'), ('r1', 'short'), ('s1', 'long'), ('pp', 'both')]
        elif variant == 'V4':
            active_levels = [('pdh', 'break_long'), ('pdl', 'break_short')]
        else:
            active_levels = [('pdh', 'short'), ('pdl', 'long')]

        H = g['high'].values; L_ = g['low'].values; C = g['close'].values; O = g['open'].values
        tm = g['tm'].values

        attempts = 0
        in_trade = False
        ed = 0; sp = tp_ = ep = 0.0; sl_orig = 0.0
        be_triggered = False; run_extreme = 0.0
        last_entry_bar = -10

        for i in range(2, len(C) - 1):
            ch = H[i]; cl_ = L_[i]; cc = C[i]; co = O[i]
            ph = H[i-1]; pl = L_[i-1]; pc = C[i-1]; po = O[i-1]

            if in_trade:
                sl_dist = abs(ep - sl_orig)
                if use_be_trail:
                    if not be_triggered:
                        if ed == 1 and ch >= ep + 1.5 * sl_dist:  # 1.5R trigger (Phase 44 optimal)
                            sp = max(sp, ep); be_triggered = True; run_extreme = ch
                        elif ed == -1 and cl_ <= ep - 1.5 * sl_dist:
                            sp = min(sp, ep); be_triggered = True; run_extreme = cl_
                    else:
                        if ed == 1:
                            run_extreme = max(run_extreme, ch)
                            sp = max(sp, run_extreme - sl_dist)
                        else:
                            run_extreme = min(run_extreme, cl_)
                            sp = min(sp, run_extreme + sl_dist)

                if ed == 1:
                    if cl_ <= sp:
                        pnl_t = sp - ep; in_trade = False
                        pnl += pnl_t; n += 1
                        if pnl_t > 0: w += 1
                        else: l += 1
                        if pnl_t < worst: worst = pnl_t
                        if be_triggered:
                            if abs(sp - ep) <= 0.5: be_saves += 1
                            else: trail_exits += 1
                        be_triggered = False
                        continue
                    elif ch >= tp_:
                        pnl_t = tp_ - ep; in_trade = False
                        pnl += pnl_t; n += 1; w += 1; tp_hits += 1
                        be_triggered = False
                        continue
                else:
                    if ch >= sp:
                        pnl_t = ep - sp; in_trade = False
                        pnl += pnl_t; n += 1
                        if pnl_t > 0: w += 1
                        else: l += 1
                        if pnl_t < worst: worst = pnl_t
                        if be_triggered:
                            if abs(sp - ep) <= 0.5: be_saves += 1
                            else: trail_exits += 1
                        be_triggered = False
                        continue
                    elif cl_ <= tp_:
                        pnl_t = ep - tp_; in_trade = False
                        pnl += pnl_t; n += 1; w += 1; tp_hits += 1
                        be_triggered = False
                        continue
                continue

            if attempts >= max_attempts: continue
            if i - last_entry_bar < 30: continue  # min 30 bar gap between entries

            # Check each level for touch + rejection
            for level_name, dir_type in active_levels:
                level = lv[level_name]
                touched = abs(cc - level) <= touch_tol or (cl_ <= level + touch_tol and ch >= level - touch_tol)
                if not touched: continue

                # V4: break + retest continuation
                if variant == 'V4':
                    if dir_type == 'break_long' and cc > level and not allow_long: continue
                    if dir_type == 'break_long' and cc > level and is_bull_reject(po, ph, pl, pc, co, ch, cl_, cc):
                        sl_px = cc - sl_pts; tp_px = cc + tp_mult * sl_pts
                        ep = cc; sp = sl_px; sl_orig = sl_px; tp_ = tp_px; ed = 1
                        in_trade = True; attempts += 1; last_entry_bar = i; be_triggered = False
                        break
                    if dir_type == 'break_short' and cc < level and not allow_short: continue
                    if dir_type == 'break_short' and cc < level and is_bear_reject(po, ph, pl, pc, co, ch, cl_, cc):
                        sl_px = cc + sl_pts; tp_px = cc - tp_mult * sl_pts
                        ep = cc; sp = sl_px; sl_orig = sl_px; tp_ = tp_px; ed = -1
                        in_trade = True; attempts += 1; last_entry_bar = i; be_triggered = False
                        break
                    continue

                # V1-V3: touch + rejection
                if dir_type in ('long', 'both') and allow_long and is_bull_reject(po, ph, pl, pc, co, ch, cl_, cc):
                    sl_px = cc - sl_pts; tp_px = cc + tp_mult * sl_pts
                    ep = cc; sp = sl_px; sl_orig = sl_px; tp_ = tp_px; ed = 1
                    in_trade = True; attempts += 1; last_entry_bar = i; be_triggered = False
                    break
                if dir_type in ('short', 'both') and allow_short and is_bear_reject(po, ph, pl, pc, co, ch, cl_, cc):
                    sl_px = cc + sl_pts; tp_px = cc - tp_mult * sl_pts
                    ep = cc; sp = sl_px; sl_orig = sl_px; tp_ = tp_px; ed = -1
                    in_trade = True; attempts += 1; last_entry_bar = i; be_triggered = False
                    break

    wr = 100 * w / n if n else 0
    return {
        'variant': variant,
        'pnl_pts': round(pnl, 2),
        'usd_per_yr_002': round(pnl * 2 / 5, 2),
        'n': n, 'wr': round(wr, 2),
        'be_saves': be_saves, 'trail_exits': trail_exits, 'tp_hits': tp_hits,
        'worst': round(worst, 2),
    }


def main():
    print("Loading 5y data...")
    df = load_data(CSV)
    dg, all_dates = build_date_groups(df)
    print(f"  {len(dg)} days\n")

    print("Computing daily S/R levels...")
    levels = compute_daily_levels(dg, all_dates)
    print(f"  Levels computed for {len(levels)} days\n")

    print("=" * 110)
    print("PHASE 45 — S/R Level Strategy Sweep (PARALLEL to PT Box)")
    print("=" * 110)
    print(f'{"Variant":<10} | {"Description":<40} | {"PnL pts":>9} | {"$/yr":>7} | {"trades":>7} | {"WR%":>5} | {"worst":>7}')
    print('-' * 110)

    variants = [
        ('V1', 'PDH/PDL touch + reject (mean-revert)'),
        ('V2', 'PDH/PDL/R1/S1/PP all levels'),
        ('V3', 'V2 + daily bias filter (with trend)'),
        ('V4', 'PDH/PDL break + retest (continuation)'),
    ]

    all_results = {}
    for v, desc in variants:
        use_bias = v == 'V3'
        r = simulate_sr_strategy(dg, all_dates, levels, variant=v, use_bias=use_bias)
        all_results[v] = r
        print(f'{v:<10} | {desc:<40} | {r["pnl_pts"]:>+9.0f} | {r["usd_per_yr_002"]:>+7.0f} | {r["n"]:>7} | {r["wr"]:>5.1f} | {r["worst"]:>+7.0f}')

    # Verdict
    print('\n' + '=' * 110)
    print("VERDICT")
    print('=' * 110)
    best = max(all_results.items(), key=lambda x: x[1]['pnl_pts'])
    print(f"BEST: {best[0]} — PnL {best[1]['pnl_pts']:.0f} pts | ${best[1]['usd_per_yr_002']:+.0f}/yr | WR {best[1]['wr']:.1f}%")

    if best[1]['pnl_pts'] > 500:
        print(f"\n✅ POSITIVE EXPECTANCY — Worth deploying as Pine v16 (parallel to PT Box)")
        print(f"   Combined income: PT Box ${1720} + S/R {best[0]} ${best[1]['usd_per_yr_002']:.0f} = ${1720 + best[1]['usd_per_yr_002']:.0f}/yr")
    elif best[1]['pnl_pts'] > 0:
        print(f"\n⚠️  MARGINAL — positive but small edge, may not justify complexity")
    else:
        print(f"\n❌ REJECTED — no positive expectancy, 8× iron law candidate")

    out = ROOT / 'data' / 'phase45_sr_strategy.json'
    with open(out, 'w') as f:
        json.dump({'levels_computed': len(levels), 'results': all_results}, f, indent=2)
    print(f'\n[saved] {out}')


if __name__ == '__main__':
    main()
