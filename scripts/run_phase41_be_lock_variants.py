"""
Phase 41 — BE Trail Lock Variants Sweep.

Test: instead of BE at entry (V5 winner), what if BE locks 1/2/3pt profit?
Then trail upward from locked level.

User question: "BE kenapa ga dinaikin 2pt dari lokasi entry?"

Variants tested:
- V5_lock0 (current LIVE) — BE at entry, then trail
- V5_lock1 — BE at entry + 1pt, then trail
- V5_lock2 — BE at entry + 2pt, then trail (USER PROPOSAL)
- V5_lock3 — BE at entry + 3pt, then trail
- V5_lock50pct — BE at entry + 50% of run extreme, then trail
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


def simulate_be_lock(date_groups, all_dates, lock_pts: float, lock_pct: float = None,
                     be_trigger_r: float = 1.0):
    """V5-style: trigger at +1R favor, then BE @ entry+lock_pts (or entry+lock_pct*run_extreme), then trail."""
    pnl_total = 0.0
    n = w = l = 0
    worst = 0.0
    be_saves = 0
    be_premature = 0
    sl_dists = {'Asia': [], 'London': [], 'NY': []}
    per_sess = {s: {'pnl': 0, 'n': 0, 'w': 0, 'l': 0, 'worst': 0, 'be': 0} for s in ['Asia','London','NY']}

    for d in all_dates:
        if d not in date_groups: continue
        g = date_groups[d]

        # Box detection per session
        for sess_name, box_start_h, box_dur, end_h, sl_box_mult, body_pct, tp_mult, max_sl in [
            ('Asia',   19, 90, 24,  0.7, 0.0,  1.5, 30),
            ('London', 0,  60, 8,   0.9, 0.20, 2.0, 15),
            ('NY',     7,  60, 13,  0.5, 0.30, 2.5, 15),
        ]:
            BS = box_start_h * 60
            BE_min = BS + box_dur
            SE = 1439 if end_h == 24 else end_h * 60 - 1

            tm = g['tm'].values
            H = g['high'].values; L = g['low'].values; C = g['close'].values; O = g['open'].values
            box_mask = (tm >= BS) & (tm < BE_min)
            if box_mask.sum() < 5: continue

            bx_hi = H[box_mask].max(); bx_lo = L[box_mask].min()
            bw = bx_hi - bx_lo
            if bw < 1: continue

            # NY delay 25min
            delay = 25 if sess_name == 'NY' else 0
            tr = (tm >= BE_min + delay) & (tm < SE)
            if tr.sum() < 5: continue
            Hi = H[tr]; Lo = L[tr]; Cl = C[tr]; Op = O[tr]; Tm = tm[tr]

            attempts = 0
            in_trade = False
            ed = 0; sp = tp_ = ep = 0.0; sl_orig = 0.0
            be_triggered = False
            run_extreme = 0.0

            for i in range(1, len(Cl)):
                ch = Hi[i]; cl_ = Lo[i]; cc = Cl[i]; co = Op[i]
                ph = Hi[i-1]; pl = Lo[i-1]; pc = Cl[i-1]

                if in_trade:
                    sl_dist = abs(ep - sl_orig)
                    if not be_triggered:
                        # Trigger BE at +1R favor
                        if ed == 1 and ch >= ep + be_trigger_r * sl_dist:
                            # Lock level computation
                            if lock_pct is not None:
                                lock_level = ep + lock_pct * (ch - ep)
                            else:
                                lock_level = ep + lock_pts
                            sp = max(sp, lock_level)
                            be_triggered = True
                            run_extreme = ch
                        elif ed == -1 and cl_ <= ep - be_trigger_r * sl_dist:
                            if lock_pct is not None:
                                lock_level = ep - lock_pct * (ep - cl_)
                            else:
                                lock_level = ep - lock_pts
                            sp = min(sp, lock_level)
                            be_triggered = True
                            run_extreme = cl_
                    else:
                        # Trail
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
                            pnl_total += pnl; per_sess[sess_name]['pnl'] += pnl
                            n += 1; per_sess[sess_name]['n'] += 1
                            if pnl > 0: w += 1; per_sess[sess_name]['w'] += 1
                            else: l += 1; per_sess[sess_name]['l'] += 1
                            if pnl < worst: worst = pnl
                            if pnl < per_sess[sess_name]['worst']: per_sess[sess_name]['worst'] = pnl
                            if be_triggered: be_saves += 1; per_sess[sess_name]['be'] += 1
                            be_triggered = False
                            continue
                        elif ch >= tp_:
                            pnl = tp_ - ep
                            in_trade = False
                            pnl_total += pnl; per_sess[sess_name]['pnl'] += pnl
                            n += 1; w += 1; per_sess[sess_name]['n'] += 1; per_sess[sess_name]['w'] += 1
                            be_triggered = False
                            continue
                    else:
                        if ch >= sp:
                            pnl = ep - sp
                            in_trade = False
                            pnl_total += pnl; per_sess[sess_name]['pnl'] += pnl
                            n += 1; per_sess[sess_name]['n'] += 1
                            if pnl > 0: w += 1; per_sess[sess_name]['w'] += 1
                            else: l += 1; per_sess[sess_name]['l'] += 1
                            if pnl < worst: worst = pnl
                            if pnl < per_sess[sess_name]['worst']: per_sess[sess_name]['worst'] = pnl
                            if be_triggered: be_saves += 1; per_sess[sess_name]['be'] += 1
                            be_triggered = False
                            continue
                        elif cl_ <= tp_:
                            pnl = ep - tp_
                            in_trade = False
                            pnl_total += pnl; per_sess[sess_name]['pnl'] += pnl
                            n += 1; w += 1; per_sess[sess_name]['n'] += 1; per_sess[sess_name]['w'] += 1
                            be_triggered = False
                            continue
                    continue

                if attempts >= 5: continue

                # PB state machine entry (simplified)
                if cc > bx_hi:
                    sl_d = max(3, sl_box_mult * bw)
                    sl_d = min(sl_d, max_sl)
                    sp_n = cc - sl_d
                    tp_n = cc + tp_mult * sl_d
                    ep = cc; sp = sp_n; sl_orig = sp_n; tp_ = tp_n; ed = 1
                    in_trade = True; attempts += 1; be_triggered = False
                elif cc < bx_lo:
                    sl_d = max(3, sl_box_mult * bw)
                    sl_d = min(sl_d, max_sl)
                    sp_n = cc + sl_d
                    tp_n = cc - tp_mult * sl_d
                    ep = cc; sp = sp_n; sl_orig = sp_n; tp_ = tp_n; ed = -1
                    in_trade = True; attempts += 1; be_triggered = False

    wr = 100 * w / n if n else 0
    return {
        'pnl': round(pnl_total, 2),
        'n': n,
        'w': w,
        'l': l,
        'wr': round(wr, 2),
        'worst': round(worst, 2),
        'be_saves': be_saves,
        'per_sess': {s: {**v, 'pnl': round(v['pnl'], 2), 'worst': round(v['worst'], 2)} for s, v in per_sess.items()},
    }


def main():
    print("Loading data...")
    df = load_data(CSV)
    dg, all_dates = build_date_groups(df)
    print(f"  {len(dg)} days\n")

    variants = [
        ('V5_lock0_current_LIVE', 0.0, None),
        ('V5_lock1', 1.0, None),
        ('V5_lock2_USER_PROPOSAL', 2.0, None),
        ('V5_lock3', 3.0, None),
        ('V5_lock50pct', None, 0.5),
    ]

    print("=" * 110)
    print("PHASE 41 — BE Trail Lock Variants (5y, lot 0.02)")
    print("=" * 110)
    print(f'{"Variant":<28} | {"PnL pts":>9} | {"USD@002":>9} | {"trades":>6} | {"WR%":>6} | {"worst":>8} | {"BE saves":>9}')
    print('-' * 110)

    results = []
    for name, lock_pts, lock_pct in variants:
        if lock_pts is not None:
            r = simulate_be_lock(dg, all_dates, lock_pts=lock_pts)
        else:
            r = simulate_be_lock(dg, all_dates, lock_pts=0, lock_pct=lock_pct)
        r['name'] = name
        results.append(r)
        usd = r['pnl'] * 2
        print(f'{name:<28} | {r["pnl"]:>9.2f} | {usd:>9.2f} | {r["n"]:>6} | {r["wr"]:>6.2f} | {r["worst"]:>8.2f} | {r["be_saves"]:>9}')

    # Per-session for top 3
    print('\n' + '=' * 110)
    print('PER-SESSION BREAKDOWN')
    print('=' * 110)
    for r in results:
        print(f'\n{r["name"]}:')
        for s in ['Asia', 'London', 'NY']:
            ps = r['per_sess'][s]
            wr_s = 100*ps['w']/ps['n'] if ps['n'] else 0
            print(f"  {s:<8} | n={ps['n']:>4} | PnL {ps['pnl']:>+8.2f} | WR {wr_s:>5.1f}% | worst {ps['worst']:>+7.2f} | BE {ps['be']:>3}")

    # Save
    out = ROOT / 'data' / 'phase41_be_lock_variants.json'
    with open(out, 'w') as f:
        json.dump(results, f, indent=2)
    print(f'\n[saved] {out}')


if __name__ == '__main__':
    main()
