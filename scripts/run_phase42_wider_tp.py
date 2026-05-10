"""
Phase 42 — Wider TP sweep dengan BE Trail v14 (V5 logic).

Test: keep current SL mechanic + entry logic + trail.
Lebarkan TP only: 1:2 (current), 1:3, 1:4, 1:5, 1:6, 1:8.

With BE Trail, theory: TP wider = more time for trail catch profit
on trades that didn't hit TP but ran far before reverse.
"""
import sys
from pathlib import Path
import json
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT / "scripts"))
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


def simulate_e44_pb_with_tp(date_groups, all_dates, tp_mult: float,
                              use_be_trail: bool = True, be_trigger_r: float = 1.0):
    """e44 PB state machine with configurable TP multiplier + V5 BE Trail."""
    pnl_total = 0.0
    n = w = l = 0
    be_saves = 0
    tp_hits = 0
    trail_exits = 0
    worst = 0.0

    PB_RETEST_TOL = 3.0
    PB_SL_BUFFER = 2.0
    PB_MAX_WAIT = 60
    MAX_ATT = 5

    for d in all_dates:
        if d not in date_groups: continue
        g = date_groups[d]
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
            be_triggered = False
            run_extreme = 0.0
            state = 0
            bk_dir = 0
            bk_idx = -1

            for i in range(1, len(Cl)):
                ch = Hi[i]; cl_ = Lo[i]; cc = Cl[i]; co = Op[i]
                ph = Hi[i-1]; pl = Lo[i-1]; pc = Cl[i-1]; po = Op[i-1]

                if in_trade:
                    sl_dist = abs(ep - sl_orig)
                    # BE Trail
                    if use_be_trail:
                        if not be_triggered:
                            if ed == 1 and ch >= ep + be_trigger_r * sl_dist:
                                sp = max(sp, ep); be_triggered = True; run_extreme = ch
                            elif ed == -1 and cl_ <= ep - be_trigger_r * sl_dist:
                                sp = min(sp, ep); be_triggered = True; run_extreme = cl_
                        else:
                            if ed == 1:
                                run_extreme = max(run_extreme, ch)
                                new_sp = run_extreme - sl_dist
                                sp = max(sp, new_sp)
                            else:
                                run_extreme = min(run_extreme, cl_)
                                new_sp = run_extreme + sl_dist
                                sp = min(sp, new_sp)

                    # Exit
                    if ed == 1:
                        if cl_ <= sp:
                            pnl = sp - ep
                            in_trade = False
                            pnl_total += pnl; n += 1
                            if pnl > 0: w += 1
                            else: l += 1
                            if pnl < worst: worst = pnl
                            if be_triggered:
                                if abs(sp - ep) <= 0.5: be_saves += 1
                                else: trail_exits += 1
                            be_triggered = False
                            continue
                        elif ch >= tp_:
                            pnl = tp_ - ep
                            in_trade = False
                            pnl_total += pnl; n += 1; w += 1; tp_hits += 1
                            be_triggered = False
                            continue
                    else:
                        if ch >= sp:
                            pnl = ep - sp
                            in_trade = False
                            pnl_total += pnl; n += 1
                            if pnl > 0: w += 1
                            else: l += 1
                            if pnl < worst: worst = pnl
                            if be_triggered:
                                if abs(sp - ep) <= 0.5: be_saves += 1
                                else: trail_exits += 1
                            be_triggered = False
                            continue
                        elif cl_ <= tp_:
                            pnl = ep - tp_
                            in_trade = False
                            pnl_total += pnl; n += 1; w += 1; tp_hits += 1
                            be_triggered = False
                            continue
                    continue

                if attempts >= MAX_ATT: continue

                # PB state machine
                if state == 0:
                    if cc > bx_hi:
                        state = 1; bk_dir = 1; bk_idx = i
                    elif cc < bx_lo:
                        state = 1; bk_dir = -1; bk_idx = i
                elif state == 1:
                    if i - bk_idx > PB_MAX_WAIT:
                        state = 0; bk_dir = 0
                        continue
                    if bk_dir == 1:
                        if cl_ <= bx_hi + PB_RETEST_TOL:
                            state = 2
                    else:
                        if ch >= bx_lo - PB_RETEST_TOL:
                            state = 2
                elif state == 2:
                    if bk_dir == 1:
                        if cl_ >= bx_hi - PB_RETEST_TOL and (is_pin(co, ch, cl_, cc, 1) or is_engulf(po, pc, co, cc, 1)):
                            sl_px = min(cl_, pl) - PB_SL_BUFFER
                            sl_d = cc - sl_px
                            if 0 < sl_d <= 30:
                                tp_px = cc + tp_mult * sl_d
                                ep = cc; sp = sl_px; sl_orig = sl_px; tp_ = tp_px; ed = 1
                                in_trade = True; attempts += 1; state = 0
                                be_triggered = False
                            else:
                                attempts += 1; state = 0
                    else:
                        if ch <= bx_lo + PB_RETEST_TOL and (is_pin(co, ch, cl_, cc, -1) or is_engulf(po, pc, co, cc, -1)):
                            sl_px = max(ch, ph) + PB_SL_BUFFER
                            sl_d = sl_px - cc
                            if 0 < sl_d <= 30:
                                tp_px = cc - tp_mult * sl_d
                                ep = cc; sp = sl_px; sl_orig = sl_px; tp_ = tp_px; ed = -1
                                in_trade = True; attempts += 1; state = 0
                                be_triggered = False
                            else:
                                attempts += 1; state = 0

    wr = 100 * w / n if n else 0
    return {
        'tp_mult': tp_mult,
        'pnl': round(pnl_total, 2),
        'usd_002': round(pnl_total * 2, 2),
        'usd_per_yr': round(pnl_total * 2 / 5, 2),
        'n': n,
        'w': w,
        'l': l,
        'wr': round(wr, 2),
        'tp_hits': tp_hits,
        'tp_hit_pct': round(100 * tp_hits / n, 2) if n else 0,
        'be_saves': be_saves,
        'trail_exits': trail_exits,
        'worst': round(worst, 2),
    }


def main():
    print("Loading...")
    df = load_data(CSV)
    dg, all_dates = build_date_groups(df)
    print(f"  {len(dg)} days\n")

    print("=" * 130)
    print("PHASE 42 — Wider TP Sweep (e44 PB + V5 BE Trail, lot 0.02)")
    print("=" * 130)
    print(f'{"TP mult":<10} | {"PnL pts":>10} | {"$/yr":>8} | {"trades":>6} | {"WR%":>5} | {"TP hit%":>7} | {"BE":>4} | {"TRAIL":>5} | {"worst":>7}')
    print('-' * 130)

    results = []
    for tp in [2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0]:
        r = simulate_e44_pb_with_tp(dg, all_dates, tp_mult=tp, use_be_trail=True)
        results.append(r)
        marker = ' ⭐' if tp == 2.0 else ''
        print(f'1:{tp:<6.1f}{marker:<3} | {r["pnl"]:>10.2f} | {r["usd_per_yr"]:>8.0f} | {r["n"]:>6} | {r["wr"]:>5.1f} | {r["tp_hit_pct"]:>6.1f}% | {r["be_saves"]:>4} | {r["trail_exits"]:>5} | {r["worst"]:>7.2f}')

    out = ROOT / 'data' / 'phase42_wider_tp_sweep.json'
    with open(out, 'w') as f:
        json.dump(results, f, indent=2)
    print(f'\n[saved] {out}')


if __name__ == '__main__':
    main()
