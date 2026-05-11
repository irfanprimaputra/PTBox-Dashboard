"""
Phase 43 — Monkey Test (Parameter Robustness Sweep)

S.Y.S.T.E.M. Method Step T: Threshold Check.

Test: vary key parameters ±20-40% around default. Robust system shows
WIDE profitable region. Curve-fitted shows narrow spike.

Parameters tested (e44 PB + BE Trail v14):
- pbRetestTol     [default 3.0] → sweep 1.0, 2.0, 3.0, 4.0, 5.0, 6.0
- pbSlBuffer      [default 2.0] → sweep 0.5, 1.0, 2.0, 3.0, 4.0, 5.0
- pbTpMult        [default 2.0] → sweep 1.5, 2.0, 2.5, 3.0 (subset of Phase 42)
- pbMaxWaitBars   [default 60]  → sweep 30, 45, 60, 90, 120
- beTriggerR      [default 1.0] → sweep 0.5, 0.75, 1.0, 1.25, 1.5, 2.0
- maxAttempt      [default 5]   → sweep 1, 2, 3, 4, 5, 6, 8, 10

Robustness verdict:
- IF ≥80% variants stay profitable AND default near peak → ROBUST
- IF only default profitable → CURVE-FITTED
- IF wider variants better than default → DEFAULT UNDER-OPTIMIZED
"""
import sys
import json
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
from ptbox_engine_e37 import load_data, build_date_groups

CSV = "/Users/irfanprimaputra.b/Downloads/XAUUSD_M1_2021_-_2026.csv"


def is_pin(o, h, l, c, dir_):
    rng = h - l
    if rng <= 0: return False
    if dir_ == 1:
        return (c - l) / rng > 0.6 and c > o
    return (h - c) / rng > 0.6 and c < o


def is_engulf(po, pc, o, c, dir_):
    if dir_ == 1:
        return c > po and o < pc and c > o
    return c < po and o > pc and c < o


def simulate(dg, all_dates, *,
             pb_retest_tol=3.0, pb_sl_buffer=2.0, pb_tp_mult=2.0,
             pb_max_wait=60, be_trigger_r=1.0, max_attempt=5):
    """e44 PB simulator with BE Trail v14, all params configurable."""
    pnl = 0.0
    n = w = l = be = trail = tp_hits = sl_hits = 0
    worst = 0.0

    for d in all_dates:
        if d not in dg: continue
        g = dg[d]
        tm = g['tm'].values
        H = g['high'].values; L = g['low'].values; C = g['close'].values; O = g['open'].values

        for sess_name, box_start_h, box_dur, end_h in [
            ('Asia',   19, 90, 24),
            ('London', 0,  60, 8),
            ('NY',     7,  60, 13),
        ]:
            BS = box_start_h * 60
            BE_min = BS + box_dur
            SE = 1439 if end_h == 24 else end_h * 60 - 1

            box_mask = (tm >= BS) & (tm < BE_min)
            if box_mask.sum() < 5: continue
            bx_hi = H[box_mask].max(); bx_lo = L[box_mask].min()
            bw = bx_hi - bx_lo
            if bw < 1: continue

            delay = 25 if sess_name == 'NY' else 0
            tr = (tm >= BE_min + delay) & (tm < SE)
            if tr.sum() < 5: continue
            Hi = H[tr]; Lo = L[tr]; Cl = C[tr]; Op = O[tr]

            attempts = 0
            in_trade = False
            ed = 0; sp = tp_ = ep = 0.0; sl_orig = 0.0
            be_triggered = False; run_extreme = 0.0
            state = 0; bk_dir = 0; bk_idx = -1

            for i in range(1, len(Cl)):
                ch = Hi[i]; cl_ = Lo[i]; cc = Cl[i]; co = Op[i]
                ph = Hi[i-1]; pl = Lo[i-1]; pc = Cl[i-1]; po = Op[i-1]

                if in_trade:
                    sl_dist = abs(ep - sl_orig)
                    if not be_triggered:
                        if ed == 1 and ch >= ep + be_trigger_r * sl_dist:
                            sp = max(sp, ep); be_triggered = True; run_extreme = ch
                        elif ed == -1 and cl_ <= ep - be_trigger_r * sl_dist:
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
                                if abs(sp - ep) <= 0.5: be += 1
                                else: trail += 1
                            else:
                                sl_hits += 1
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
                                if abs(sp - ep) <= 0.5: be += 1
                                else: trail += 1
                            else:
                                sl_hits += 1
                            be_triggered = False
                            continue
                        elif cl_ <= tp_:
                            pnl_t = ep - tp_; in_trade = False
                            pnl += pnl_t; n += 1; w += 1; tp_hits += 1
                            be_triggered = False
                            continue
                    continue

                if attempts >= max_attempt: continue

                if state == 0:
                    if cc > bx_hi:
                        state = 1; bk_dir = 1; bk_idx = i
                    elif cc < bx_lo:
                        state = 1; bk_dir = -1; bk_idx = i
                elif state == 1:
                    if i - bk_idx > pb_max_wait:
                        state = 0; bk_dir = 0
                        continue
                    if bk_dir == 1:
                        if cl_ <= bx_hi + pb_retest_tol:
                            state = 2
                    else:
                        if ch >= bx_lo - pb_retest_tol:
                            state = 2
                elif state == 2:
                    if bk_dir == 1:
                        if cl_ >= bx_hi - pb_retest_tol and (is_pin(co, ch, cl_, cc, 1) or is_engulf(po, pc, co, cc, 1)):
                            sl_px = min(cl_, pl) - pb_sl_buffer
                            sl_d = cc - sl_px
                            if 0 < sl_d <= 30:
                                tp_px = cc + pb_tp_mult * sl_d
                                ep = cc; sp = sl_px; sl_orig = sl_px; tp_ = tp_px; ed = 1
                                in_trade = True; attempts += 1; state = 0
                                be_triggered = False
                            else:
                                attempts += 1; state = 0
                    else:
                        if ch <= bx_lo + pb_retest_tol and (is_pin(co, ch, cl_, cc, -1) or is_engulf(po, pc, co, cc, -1)):
                            sl_px = max(ch, ph) + pb_sl_buffer
                            sl_d = sl_px - cc
                            if 0 < sl_d <= 30:
                                tp_px = cc - pb_tp_mult * sl_d
                                ep = cc; sp = sl_px; sl_orig = sl_px; tp_ = tp_px; ed = -1
                                in_trade = True; attempts += 1; state = 0
                                be_triggered = False
                            else:
                                attempts += 1; state = 0

    wr = 100 * w / n if n else 0
    return {
        'pnl_pts': round(pnl, 2),
        'usd_per_yr_002': round(pnl * 2 / 5, 2),  # 5y, lot 0.02 = $2/pt
        'n': n, 'wr': round(wr, 2),
        'be': be, 'trail': trail, 'tp_hits': tp_hits, 'sl_hits': sl_hits,
        'worst': round(worst, 2),
    }


def sweep_param(dg, all_dates, param_name, values, defaults):
    print(f'\n=== SWEEP: {param_name} ===')
    print(f'{"Value":>10} | {"PnL pts":>9} | {"$/yr@002":>9} | {"trades":>6} | {"WR%":>5} | {"BE":>4} | {"TR":>4} | {"TP":>4} | {"SL":>4} | {"worst":>7}')
    print('-' * 95)
    results = []
    for v in values:
        params = dict(defaults)
        params[param_name] = v
        r = simulate(dg, all_dates, **params)
        r['param'] = param_name
        r['value'] = v
        results.append(r)
        marker = ' ⭐' if v == defaults[param_name] else ''
        print(f'{v:>10}{marker:<3} | {r["pnl_pts"]:>9.0f} | {r["usd_per_yr_002"]:>9.0f} | {r["n"]:>6} | {r["wr"]:>5.1f} | {r["be"]:>4} | {r["trail"]:>4} | {r["tp_hits"]:>4} | {r["sl_hits"]:>4} | {r["worst"]:>7.1f}')
    return results


def main():
    print("Loading 5y data...")
    df = load_data(CSV)
    dg, all_dates = build_date_groups(df)
    print(f"  {len(dg)} days\n")

    defaults = {
        'pb_retest_tol': 3.0,
        'pb_sl_buffer': 2.0,
        'pb_tp_mult': 2.0,
        'pb_max_wait': 60,
        'be_trigger_r': 1.0,
        'max_attempt': 5,
    }

    print("=" * 100)
    print("PHASE 43 — MONKEY TEST (Parameter Robustness Sweep)")
    print("=" * 100)
    print(f"Defaults: {defaults}\n")

    all_sweeps = {}

    # Baseline
    base = simulate(dg, all_dates, **defaults)
    print(f"BASELINE (current defaults): PnL {base['pnl_pts']:.0f} pts | ${base['usd_per_yr_002']:.0f}/yr | trades {base['n']} | WR {base['wr']:.1f}%\n")

    # Sweep each param
    all_sweeps['pb_retest_tol'] = sweep_param(dg, all_dates, 'pb_retest_tol', [1.0, 2.0, 3.0, 4.0, 5.0, 6.0], defaults)
    all_sweeps['pb_sl_buffer']  = sweep_param(dg, all_dates, 'pb_sl_buffer',  [0.5, 1.0, 2.0, 3.0, 4.0, 5.0], defaults)
    all_sweeps['pb_tp_mult']    = sweep_param(dg, all_dates, 'pb_tp_mult',    [1.5, 2.0, 2.5, 3.0], defaults)
    all_sweeps['pb_max_wait']   = sweep_param(dg, all_dates, 'pb_max_wait',   [30, 45, 60, 90, 120], defaults)
    all_sweeps['be_trigger_r']  = sweep_param(dg, all_dates, 'be_trigger_r',  [0.5, 0.75, 1.0, 1.25, 1.5, 2.0], defaults)
    all_sweeps['max_attempt']   = sweep_param(dg, all_dates, 'max_attempt',   [1, 2, 3, 4, 5, 6, 8, 10], defaults)

    # ROBUSTNESS VERDICT
    print('\n' + '=' * 100)
    print('🐒 MONKEY TEST VERDICT')
    print('=' * 100)
    base_pnl = base['pnl_pts']
    for param, results in all_sweeps.items():
        positive = sum(1 for r in results if r['pnl_pts'] > 0)
        within_20pct = sum(1 for r in results if abs(r['pnl_pts'] - base_pnl) / abs(base_pnl) < 0.20) if base_pnl != 0 else 0
        best = max(results, key=lambda x: x['pnl_pts'])
        default_rank = sorted(results, key=lambda x: x['pnl_pts'], reverse=True).index(next(r for r in results if r['value'] == defaults[param])) + 1
        n_variants = len(results)
        verdict = 'ROBUST' if positive >= n_variants * 0.8 and default_rank <= 3 else 'CURVE-FITTED' if default_rank > n_variants * 0.5 else 'PARTIAL'
        print(f'  {param:<20} | {positive}/{n_variants} positive | best={best["value"]} @ {best["pnl_pts"]:.0f}pts | default rank #{default_rank}/{n_variants} | {verdict}')

    # Save
    out = ROOT / 'data' / 'phase43_monkey_test.json'
    with open(out, 'w') as f:
        json.dump({'baseline': base, 'sweeps': all_sweeps}, f, indent=2)
    print(f'\n[saved] {out}')


if __name__ == '__main__':
    main()
