"""
Phase 47 — Mentor V3 Style: 5min Box + 3pt SL + Displacement Entry + 1:10 RR

User shared mentor's approach (3 SMC components: Sweep, Supply/Demand, FVG).
Mentor's PT Box variant uses 5-min box duration + displacement entry + tight 3pt SL.

V3 logic:
- Box = first 5 minutes of session
- Look for displacement candle INSIDE box (large body, close at extreme)
- Entry direction of displacement
- SL fixed 3pt
- TP 1:5, 1:10, 1:15 variants
- HTF bias filter optional (D1 last 3 close trend)
- BE Trail at +1R favor

Compare:
- V3 alone (no HTF filter)
- V3 + HTF bias filter
- V3 different TP ratios
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


def is_displacement(o, h, l, c, min_range=2.0, body_pct=0.7, extreme_pct=0.3):
    """Detect displacement candle: large body + close at extreme."""
    rng = h - l
    if rng < min_range: return None
    body = abs(c - o)
    if body / rng < body_pct: return None
    # Close at extreme
    if c > o:  # bull candle
        close_pos = (c - l) / rng  # 1.0 = closed at high
        if close_pos > (1 - extreme_pct):
            return 1  # bullish displacement
    else:  # bear candle
        close_pos = (h - c) / rng  # 1.0 = closed at low
        if close_pos > (1 - extreme_pct):
            return -1  # bearish displacement
    return None


def get_daily_bias(closes_history):
    """HTF bias from last 3 daily closes. 1=bull, -1=bear, 0=neutral."""
    if len(closes_history) < 3: return 0
    if closes_history[-1] > closes_history[-3] * 1.005: return 1
    if closes_history[-1] < closes_history[-3] * 0.995: return -1
    return 0


def simulate_mentor_v3(dg, all_dates, *,
                       sl_pts=3.0, tp_ratio=10.0, use_bias_filter=False,
                       max_attempts_per_day=3, use_be_trail=True, be_trigger_r=1.0):
    pnl = 0.0
    n = w = l = be_saves = trail_exits = tp_hits = sl_hits = 0
    worst = 0.0
    closes_history = []

    sorted_dates = sorted(all_dates)
    for d in sorted_dates:
        if d not in dg: continue
        g = dg[d]
        if len(g) < 100:
            closes_history.append(float(g['close'].iloc[-1]) if len(g) else 0)
            continue

        # HTF bias from prior 3 day closes
        bias = get_daily_bias(closes_history)
        closes_history.append(float(g['close'].iloc[-1]))
        if len(closes_history) > 3: closes_history.pop(0)

        allow_long = (not use_bias_filter) or bias >= 0
        allow_short = (not use_bias_filter) or bias <= 0

        tm = g['tm'].values
        H = g['high'].values; L_ = g['low'].values; C = g['close'].values; O = g['open'].values

        # 3 sessions: Asia 19:00, London 00:00, NY 07:00
        sessions = [('Asia', 19*60), ('London', 0), ('NY', 7*60)]
        day_attempts = 0

        for sess_name, sess_start_min in sessions:
            if day_attempts >= max_attempts_per_day: break

            # 5-min box window
            box_window = (tm >= sess_start_min) & (tm < sess_start_min + 5)
            if box_window.sum() < 3: continue

            # Look for displacement IN box window
            box_indices = np.where(box_window)[0]
            entry_idx = None
            ed = 0
            ep = 0.0

            for idx in box_indices:
                d_dir = is_displacement(O[idx], H[idx], L_[idx], C[idx])
                if d_dir is not None:
                    # Check bias filter
                    if d_dir == 1 and not allow_long: continue
                    if d_dir == -1 and not allow_short: continue
                    entry_idx = idx
                    ed = d_dir
                    ep = C[idx]
                    break

            if entry_idx is None: continue
            day_attempts += 1

            # Set SL/TP
            if ed == 1:
                sl = ep - sl_pts
                tp = ep + tp_ratio * sl_pts
            else:
                sl = ep + sl_pts
                tp = ep - tp_ratio * sl_pts
            sl_orig = sl
            be_triggered = False
            run_extreme = ep

            # Walk forward from entry_idx + 1 until exit or end of day
            for j in range(entry_idx + 1, len(C)):
                jh = H[j]; jl = L_[j]
                sl_dist = abs(ep - sl_orig)

                # BE Trail
                if use_be_trail:
                    if not be_triggered:
                        if ed == 1 and jh >= ep + be_trigger_r * sl_dist:
                            sl = max(sl, ep); be_triggered = True; run_extreme = jh
                        elif ed == -1 and jl <= ep - be_trigger_r * sl_dist:
                            sl = min(sl, ep); be_triggered = True; run_extreme = jl
                    else:
                        if ed == 1:
                            run_extreme = max(run_extreme, jh)
                            sl = max(sl, run_extreme - sl_dist)
                        else:
                            run_extreme = min(run_extreme, jl)
                            sl = min(sl, run_extreme + sl_dist)

                # Exit check
                if ed == 1:
                    if jl <= sl:
                        pnl_t = sl - ep; pnl += pnl_t; n += 1
                        if pnl_t > 0: w += 1
                        else: l += 1
                        if pnl_t < worst: worst = pnl_t
                        if be_triggered:
                            if abs(sl - ep) <= 0.5: be_saves += 1
                            else: trail_exits += 1
                        else: sl_hits += 1
                        break
                    elif jh >= tp:
                        pnl_t = tp - ep; pnl += pnl_t; n += 1; w += 1; tp_hits += 1
                        break
                else:
                    if jh >= sl:
                        pnl_t = ep - sl; pnl += pnl_t; n += 1
                        if pnl_t > 0: w += 1
                        else: l += 1
                        if pnl_t < worst: worst = pnl_t
                        if be_triggered:
                            if abs(sl - ep) <= 0.5: be_saves += 1
                            else: trail_exits += 1
                        else: sl_hits += 1
                        break
                    elif jl <= tp:
                        pnl_t = ep - tp; pnl += pnl_t; n += 1; w += 1; tp_hits += 1
                        break

    wr = round(100 * w / n, 2) if n else 0
    usd_per_yr_002 = round(pnl * 2 / 5, 2)
    return {
        'pnl_pts': round(pnl, 2),
        'usd_per_yr_002': usd_per_yr_002,
        'n': n, 'wr': wr,
        'be_saves': be_saves, 'trail_exits': trail_exits,
        'tp_hits': tp_hits, 'sl_hits': sl_hits,
        'worst': round(worst, 2),
    }


def main():
    print("Loading 5y data...")
    df = load_data(CSV)
    dg, all_dates = build_date_groups(df)
    print(f"  {len(dg)} days\n")

    print("=" * 110)
    print("PHASE 47 — Mentor's V3 Style Backtest")
    print("=" * 110)
    print("Setup: 5-min session box + displacement candle entry + 3pt SL + variable TP")
    print()

    variants = [
        ('V3a: TP 1:5 no bias',         {'tp_ratio': 5,  'use_bias_filter': False}),
        ('V3b: TP 1:10 no bias',        {'tp_ratio': 10, 'use_bias_filter': False}),
        ('V3c: TP 1:15 no bias',        {'tp_ratio': 15, 'use_bias_filter': False}),
        ('V3d: TP 1:5 + HTF bias',      {'tp_ratio': 5,  'use_bias_filter': True}),
        ('V3e: TP 1:10 + HTF bias',     {'tp_ratio': 10, 'use_bias_filter': True}),
        ('V3f: TP 1:15 + HTF bias',     {'tp_ratio': 15, 'use_bias_filter': True}),
    ]

    print(f'{"Variant":<30} | {"PnL pts":>10} | {"$/yr@002":>10} | {"trades":>7} | {"WR%":>6} | {"TP":>5} | {"SL":>5} | {"BE":>4} | {"TR":>4} | {"worst":>7}')
    print('-' * 130)

    all_results = {}
    for name, params in variants:
        r = simulate_mentor_v3(dg, all_dates, **params)
        all_results[name] = r
        print(f'{name:<30} | {r["pnl_pts"]:>+10.0f} | {r["usd_per_yr_002"]:>+10.0f} | {r["n"]:>7} | {r["wr"]:>6.2f} | {r["tp_hits"]:>5} | {r["sl_hits"]:>5} | {r["be_saves"]:>4} | {r["trail_exits"]:>4} | {r["worst"]:>+7.0f}')

    # Verdict
    print('\n' + '=' * 110)
    print("VERDICT")
    print('=' * 110)
    best = max(all_results.items(), key=lambda x: x[1]['pnl_pts'])
    print(f"BEST: {best[0]} → PnL {best[1]['pnl_pts']:.0f}pts, ${best[1]['usd_per_yr_002']:+.0f}/yr, WR {best[1]['wr']:.1f}%")

    if best[1]['pnl_pts'] > 500:
        print(f"\n✅ POSITIVE EXPECTANCY — Mentor's V3 systematic-able")
        print(f"   Combined PT Box ${1500} + V3 ${best[1]['usd_per_yr_002']:.0f} = ${1500 + best[1]['usd_per_yr_002']:.0f}/yr")
    elif best[1]['pnl_pts'] > 0:
        print(f"\n⚠️ MARGINAL — works but small edge, manual mentor discretion likely better")
    else:
        print(f"\n❌ REJECTED systematic — mentor's edge in DISCRETION, not pure mechanics")

    out = ROOT / 'data' / 'phase47_mentor_v3.json'
    with open(out, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f'\n[saved] {out}')


if __name__ == '__main__':
    main()
