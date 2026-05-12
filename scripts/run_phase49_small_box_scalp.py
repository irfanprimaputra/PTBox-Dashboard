"""
Phase 49 — Small Box + Break-Only Entry Sweep (Scalp Mode).

User insight: mentor pakai PT Box duration kecil (5 min Asia jam 19:03-19:08).
PT Box current 60-90 min = terlalu lebar.
Test: smaller box + break-only entry + scalp 10pt TP.

Sweep A: Box Duration (5/10/15/30/60/90 min) × Entry Mode (BO-only vs BO+pullback)
Sweep B: TP type (1:2 RR / 10pt fixed / 15pt fixed / 20pt fixed)

Backtest: Trump-only era (2025-2026, 16 months) with BE Trail v14 (1.5R trigger).
"""
import sys
import json
from pathlib import Path
import numpy as np
from datetime import date

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
from ptbox_engine_e37 import load_data, build_date_groups

CSV = "/Users/irfanprimaputra.b/Downloads/XAUUSD_M1_2021_-_2026.csv"
TRUMP_START = date(2025, 1, 1)


def is_pin(o, h, l, c, dir_):
    rng = h - l
    if rng <= 0: return False
    if dir_ == 1: return (c - l) / rng > 0.6 and c > o
    return (h - c) / rng > 0.6 and c < o


def is_engulf(po, pc, o, c, dir_):
    if dir_ == 1: return c > po and o < pc and c > o
    return c < po and o > pc and c < o


def is_strong_body(o, h, l, c, dir_, min_body_pct=0.6):
    rng = h - l
    if rng <= 0: return False
    body = abs(c - o)
    if body / rng < min_body_pct: return False
    if dir_ == 1: return c > o
    return c < o


def simulate(dg, dates, *, box_dur=90, entry_mode='pullback',
             pb_retest_tol=3.0, pb_sl_buffer=2.0, tp_mode='rr',
             tp_mult=2.0, tp_fixed_pt=10.0, max_wait_bars=60,
             max_attempts=5, be_trigger_r=1.5, use_be_trail=True,
             sl_fixed_pt=None):
    """
    entry_mode:
      - 'pullback': current PT Box (BO + retest + reject)
      - 'breakout': pure breakout candle entry (no retest)
      - 'breakout_strong': breakout + strong body candle filter

    tp_mode:
      - 'rr': TP = tp_mult × actual SL distance
      - 'fixed': TP = entry ± tp_fixed_pt
    """
    pnl = 0.0
    n = w = l = be_saves = trail_exits = tp_hits = 0
    worst = 0.0

    for d in dates:
        if d not in dg: continue
        g = dg[d]
        if len(g) < 50: continue
        tm = g['tm'].values
        H = g['high'].values; L_ = g['low'].values; C = g['close'].values; O = g['open'].values

        # Sessions: Asia 19:00, London 0:00, NY 7:00 (ET)
        sessions = [
            ('Asia', 19 * 60, 24 * 60 - 1, 0),
            ('London', 0, 8 * 60 - 1, 0),
            ('NY', 7 * 60, 13 * 60 - 1, 25),
        ]

        for sess_name, sess_start, sess_end, sess_delay in sessions:
            BS = sess_start
            BE_min = BS + box_dur
            SE = sess_end

            box_mask = (tm >= BS) & (tm < BE_min)
            if box_mask.sum() < max(2, box_dur // 5): continue
            bx_hi = H[box_mask].max(); bx_lo = L_[box_mask].min()
            bw = bx_hi - bx_lo
            if bw < 0.5: continue  # too narrow

            tr = (tm >= BE_min + sess_delay) & (tm < SE)
            if tr.sum() < 5: continue
            Hi = H[tr]; Lo = L_[tr]; Cl = C[tr]; Op = O[tr]

            attempts = 0; in_trade = False
            ed = 0; sp = tp_ = ep = 0.0; sl_orig = 0.0
            be_triggered = False; run_extreme = 0.0
            state = 0; bk_dir = 0; bk_idx = -1

            for i in range(1, len(Cl)):
                ch = Hi[i]; cl_ = Lo[i]; cc = Cl[i]; co = Op[i]
                ph = Hi[i-1]; pl = Lo[i-1]; pc = Cl[i-1]; po = Op[i-1]

                if in_trade:
                    sl_dist = abs(ep - sl_orig)
                    if use_be_trail:
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

                # Entry logic per mode
                if entry_mode == 'breakout':
                    # Pure breakout, no retest
                    if cc > bx_hi:
                        # Long
                        sl_d = sl_fixed_pt if sl_fixed_pt else max(2.0, pb_sl_buffer + (bx_hi - bx_lo) * 0.3)
                        sl_px = cc - sl_d
                        if tp_mode == 'fixed':
                            tp_px = cc + tp_fixed_pt
                        else:
                            tp_px = cc + tp_mult * sl_d
                        ep = cc; sp = sl_px; sl_orig = sl_px; tp_ = tp_px; ed = 1
                        in_trade = True; attempts += 1; be_triggered = False
                    elif cc < bx_lo:
                        sl_d = sl_fixed_pt if sl_fixed_pt else max(2.0, pb_sl_buffer + (bx_hi - bx_lo) * 0.3)
                        sl_px = cc + sl_d
                        if tp_mode == 'fixed':
                            tp_px = cc - tp_fixed_pt
                        else:
                            tp_px = cc - tp_mult * sl_d
                        ep = cc; sp = sl_px; sl_orig = sl_px; tp_ = tp_px; ed = -1
                        in_trade = True; attempts += 1; be_triggered = False

                elif entry_mode == 'breakout_strong':
                    # Breakout + strong body candle filter
                    if cc > bx_hi and is_strong_body(co, ch, cl_, cc, 1):
                        sl_d = sl_fixed_pt if sl_fixed_pt else max(2.0, pb_sl_buffer + (bx_hi - bx_lo) * 0.3)
                        sl_px = cc - sl_d
                        tp_px = cc + (tp_fixed_pt if tp_mode == 'fixed' else tp_mult * sl_d)
                        ep = cc; sp = sl_px; sl_orig = sl_px; tp_ = tp_px; ed = 1
                        in_trade = True; attempts += 1; be_triggered = False
                    elif cc < bx_lo and is_strong_body(co, ch, cl_, cc, -1):
                        sl_d = sl_fixed_pt if sl_fixed_pt else max(2.0, pb_sl_buffer + (bx_hi - bx_lo) * 0.3)
                        sl_px = cc + sl_d
                        tp_px = cc - (tp_fixed_pt if tp_mode == 'fixed' else tp_mult * sl_d)
                        ep = cc; sp = sl_px; sl_orig = sl_px; tp_ = tp_px; ed = -1
                        in_trade = True; attempts += 1; be_triggered = False

                elif entry_mode == 'pullback':
                    # Current PT Box: BO state machine
                    if state == 0:
                        if cc > bx_hi:
                            state = 1; bk_dir = 1; bk_idx = i
                        elif cc < bx_lo:
                            state = 1; bk_dir = -1; bk_idx = i
                    elif state == 1:
                        if i - bk_idx > max_wait_bars:
                            state = 0; bk_dir = 0; continue
                        if bk_dir == 1 and cl_ <= bx_hi + pb_retest_tol: state = 2
                        elif bk_dir == -1 and ch >= bx_lo - pb_retest_tol: state = 2
                    elif state == 2:
                        if bk_dir == 1 and cl_ >= bx_hi - pb_retest_tol and (is_pin(co, ch, cl_, cc, 1) or is_engulf(po, pc, co, cc, 1)):
                            sl_px = min(cl_, pl) - pb_sl_buffer
                            sl_d = cc - sl_px
                            if 0 < sl_d <= 30:
                                tp_px = cc + (tp_fixed_pt if tp_mode == 'fixed' else tp_mult * sl_d)
                                ep = cc; sp = sl_px; sl_orig = sl_px; tp_ = tp_px; ed = 1
                                in_trade = True; attempts += 1; state = 0; be_triggered = False
                            else:
                                attempts += 1; state = 0
                        elif bk_dir == -1 and ch <= bx_lo + pb_retest_tol and (is_pin(co, ch, cl_, cc, -1) or is_engulf(po, pc, co, cc, -1)):
                            sl_px = max(ch, ph) + pb_sl_buffer
                            sl_d = sl_px - cc
                            if 0 < sl_d <= 30:
                                tp_px = cc - (tp_fixed_pt if tp_mode == 'fixed' else tp_mult * sl_d)
                                ep = cc; sp = sl_px; sl_orig = sl_px; tp_ = tp_px; ed = -1
                                in_trade = True; attempts += 1; state = 0; be_triggered = False
                            else:
                                attempts += 1; state = 0

    wr = round(100 * w / n, 2) if n else 0
    usd_yr = round(pnl * 2 / 1.33, 2)  # Trump era 1.33 years
    return {
        'pnl_pts': round(pnl, 2),
        'usd_per_yr': usd_yr,
        'n': n, 'wr': wr,
        'be_saves': be_saves, 'trail_exits': trail_exits, 'tp_hits': tp_hits,
        'worst': round(worst, 2),
    }


def main():
    print("Loading 5y data...")
    df = load_data(CSV)
    dg, all_dates = build_date_groups(df)
    trump_dates = [d for d in all_dates if d >= TRUMP_START]
    print(f"  Trump-2 era: {len(trump_dates)} days\n")

    print("=" * 130)
    print("PHASE 49 — Small Box + Break-Only Sweep (Scalp mode, Trump-only era)")
    print("=" * 130)

    # ===== SWEEP A: Box Duration × Entry Mode =====
    print("\n### SWEEP A: Box Duration × Entry Mode (TP 1:2 RR variable SL) ###")
    print(f'{"Variant":<35} | {"PnL pts":>9} | {"$/yr@002":>9} | {"trades":>6} | {"WR%":>5} | {"TP":>4} | {"BE":>4} | {"TR":>4} | {"worst":>7}')
    print('-' * 130)

    sweep_a = []
    for box_dur in [5, 10, 15, 30, 60, 90]:
        for mode in ['breakout', 'breakout_strong', 'pullback']:
            r = simulate(dg, trump_dates, box_dur=box_dur, entry_mode=mode,
                         tp_mode='rr', tp_mult=2.0)
            r['box_dur'] = box_dur
            r['entry_mode'] = mode
            sweep_a.append(r)
            name = f"box={box_dur}min · {mode}"
            print(f'{name:<35} | {r["pnl_pts"]:>+9.0f} | {r["usd_per_yr"]:>+9.0f} | {r["n"]:>6} | {r["wr"]:>5.1f} | {r["tp_hits"]:>4} | {r["be_saves"]:>4} | {r["trail_exits"]:>4} | {r["worst"]:>+7.0f}')

    best_a = max(sweep_a, key=lambda x: x['pnl_pts'])
    print(f"\n>>> SWEEP A BEST: box={best_a['box_dur']}min · {best_a['entry_mode']} → ${best_a['usd_per_yr']:+.0f}/yr <<<")

    # ===== SWEEP B: TP type with best config from A =====
    print(f"\n### SWEEP B: TP Mode (best config: box={best_a['box_dur']}min · {best_a['entry_mode']}) ###")
    print(f'{"TP Mode":<25} | {"PnL pts":>9} | {"$/yr@002":>9} | {"trades":>6} | {"WR%":>5} | {"TP hits":>7} | {"worst":>7}')
    print('-' * 100)

    sweep_b = []
    tp_configs = [
        ('RR 1:2 variable', 'rr', 2.0, None),
        ('TP 10pt fixed', 'fixed', None, 10.0),
        ('TP 15pt fixed', 'fixed', None, 15.0),
        ('TP 20pt fixed', 'fixed', None, 20.0),
    ]
    for name, tp_mode, tp_mult, tp_fixed in tp_configs:
        r = simulate(dg, trump_dates, box_dur=best_a['box_dur'], entry_mode=best_a['entry_mode'],
                     tp_mode=tp_mode, tp_mult=tp_mult or 2.0, tp_fixed_pt=tp_fixed or 10.0)
        r['name'] = name
        sweep_b.append(r)
        print(f'{name:<25} | {r["pnl_pts"]:>+9.0f} | {r["usd_per_yr"]:>+9.0f} | {r["n"]:>6} | {r["wr"]:>5.1f} | {r["tp_hits"]:>7} | {r["worst"]:>+7.0f}')

    best_b = max(sweep_b, key=lambda x: x['pnl_pts'])

    # ===== Final verdict =====
    print('\n' + '=' * 130)
    print("FINAL COMBINED VERDICT")
    print('=' * 130)
    print(f"BEST CONFIG: box={best_a['box_dur']}min · {best_a['entry_mode']} · {best_b['name']}")
    print(f"  PnL: {best_b['pnl_pts']:.0f}pts | ${best_b['usd_per_yr']:+.0f}/yr | WR {best_b['wr']:.1f}% | trades {best_b['n']}")

    baseline_usd_yr = 1494  # Phase 46 best BE 1.75R
    delta_usd_yr = best_b['usd_per_yr'] - baseline_usd_yr

    print(f"\nCompare current best (Phase 46 BE 1.75R baseline): ${baseline_usd_yr}/yr")
    print(f"New best vs Phase 46 baseline: ${delta_usd_yr:+.0f}/yr ({100*delta_usd_yr/baseline_usd_yr:+.1f}%)")

    if delta_usd_yr > 300:
        print(f"\n✅ DEPLOY recommendation: change Pine v15 to box={best_a['box_dur']}min · {best_a['entry_mode']} · {best_b['name']}")
    elif delta_usd_yr > 0:
        print(f"\n⚠️ MARGINAL: small improvement, may not justify mechanic change")
    else:
        print(f"\n❌ REJECTED: existing PT Box (90min + pullback + 1:2 RR) BEATS scalping variants")

    # Save
    out = ROOT / 'data' / 'phase49_small_box_scalp.json'
    with open(out, 'w') as f:
        json.dump({
            'sweep_a': sweep_a,
            'sweep_b': sweep_b,
            'best_a': best_a,
            'best_b': best_b,
            'baseline_usd_yr': baseline_usd_yr,
            'delta_usd_yr': delta_usd_yr,
        }, f, indent=2, default=str)
    print(f'\n[saved] {out}')


if __name__ == '__main__':
    main()
