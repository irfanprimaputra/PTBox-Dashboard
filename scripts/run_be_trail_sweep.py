"""
PT Box e44 PULLBACK — Breakeven (BE) Trail Sweep.

User goal: setelah trade running dan price sudah bergerak in favor X distance,
geser SL ke breakeven (entry price) supaya kalau retrace = exit at BE,
zero loss instead of full -SL hit.

Test 6 BE variants on top of e44 PB baseline (5y +4923 / WR 42.5% / PF ~1.20):

V0 BASELINE     = no BE trail
V1 BE@1R        = move SL to entry when price reaches +1R (entry ± sl_dist)
V2 BE@0.5R      = earlier trigger at +0.5R
V3 BE+1pt @1R   = V1 but lock 1pt profit (sp = entry + 1pt for long)
V4 BE@1.5R      = later trigger, only after solid move
V5 TRAIL-step   = V1 trigger + then trail SL with running extreme each bar
V6 BE@box-edge  = move SL to BE when price crosses opposite box edge

Conservative order of ops: BE trigger detected at bar i-1, applied at bar i
(1-bar lag) to avoid same-bar ambiguity.

Output: per-variant aggregate comparison (PnL closed, WR, PF, worst trade,
trade count, BE-save count, would-have-won-but-BE count).
"""
from __future__ import annotations
import json, sys
from datetime import date as date_t
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT / "scripts"))
from ptbox_engine_e37 import load_data, build_date_groups, E37_CONFIG
from run_e38_v12_iteration import compute_daily_atr

CSV = "/Users/irfanprimaputra.b/Downloads/XAUUSD_M1_2021_-_2026.csv"


def is_pin(o, h, l, c, dir_):
    rng = h - l
    if rng <= 0: return False
    body = abs(c - o)
    if body / rng > 0.30: return False
    if dir_ == 1: return (min(o,c) - l) / rng >= 0.50
    return (h - max(o,c)) / rng >= 0.50


def is_engulf(po, pc, o, c, dir_):
    if dir_ == 1: return pc < po and c > o and o <= pc and c >= po
    return pc > po and c < o and o >= pc and c <= po


def run_pullback_with_be(dg, dates, sess_name, atr_pass, be_variant,
                         max_attempts=5, retest_tolerance=3.0, sl_buffer=2.0,
                         tp_mult=2.0, max_wait_bars=60):
    """e44 PB engine + per-variant BE-trail logic.

    be_variant string, one of: 'V0','V1','V2','V3','V4','V5','V6'
    """
    overrides = {
        "Asia":   {**E37_CONFIG['asia'],   "box_start_h": 19},
        "London": {**E37_CONFIG['london']},
        "NY":     {**E37_CONFIG['ny'],     "session_end_h": 13},
    }
    cfg = overrides[sess_name]
    BS = cfg["box_start_h"]*60 + cfg["box_start_m"]
    BE_min = BS + cfg["box_dur"]
    SE = 24*60 if cfg["session_end_h"] == 24 else cfg["session_end_h"]*60
    delay = 25 if sess_name == 'NY' else 0

    pnl_c = 0.0
    n = w = l = 0
    worst = 0
    sl_distances = []
    be_saves = 0  # counts trades where BE-exit prevented full -SL loss
    be_premature = 0  # counts trades where BE-exit but original SL not hit AND TP eventually reachable

    for day in dates:
        if day not in dg: continue
        if atr_pass is not None and day not in atr_pass: continue
        g = dg[day]
        tm = g['tm'].values
        H = g['high'].values; L = g['low'].values
        C = g['close'].values; O = g['open'].values

        bk = (tm >= BS) & (tm < BE_min)
        if bk.sum() == 0: continue
        bx_hi = float(H[bk].max()); bx_lo = float(L[bk].min())
        bw = bx_hi - bx_lo
        if bw < 1: continue

        tr = (tm >= BE_min+delay) & (tm < SE)
        if tr.sum() < 5: continue
        Hi = H[tr]; Lo = L[tr]; Cl = C[tr]; Op = O[tr]; Tm = tm[tr]

        attempts = 0
        in_trade = False
        ed = 0; sp = tp_ = ep = 0.0
        sl_orig = 0.0
        be_triggered = False
        be_armed_for_next_bar = False
        running_extreme = 0.0  # for V5 trail
        state = 0
        breakout_dir = 0
        breakout_idx = -1
        retest_extreme = 0
        cur_entry_idx = -1

        for i in range(1, len(Cl)):
            ch = Hi[i]; cl_ = Lo[i]; cc = Cl[i]; co = Op[i]
            ph = Hi[i-1]; pl = Lo[i-1]; pc = Cl[i-1]; po = Op[i-1]

            if in_trade:
                # ─── Apply BE trigger from PRIOR bar (1-bar lag) ───
                if be_armed_for_next_bar:
                    if ed == 1:
                        new_sp = ep if be_variant in ('V1','V2','V4','V5') else (ep + 1.0 if be_variant == 'V3' else ep)
                        if be_variant == 'V6': new_sp = ep
                        sp = max(sp, new_sp)  # never lower SL for long
                    else:
                        new_sp = ep if be_variant in ('V1','V2','V4','V5') else (ep - 1.0 if be_variant == 'V3' else ep)
                        if be_variant == 'V6': new_sp = ep
                        sp = min(sp, new_sp)  # never raise SL for short
                    be_triggered = True
                    be_armed_for_next_bar = False

                # ─── V5: continue trailing after BE ───
                if be_variant == 'V5' and be_triggered:
                    if ed == 1:
                        running_extreme = max(running_extreme, Hi[i-1])
                        new_trail_sp = running_extreme - (ep - sl_orig)  # trail by sl_dist
                        sp = max(sp, new_trail_sp)
                    else:
                        running_extreme = min(running_extreme, Lo[i-1])
                        new_trail_sp = running_extreme + (sl_orig - ep)
                        sp = min(sp, new_trail_sp)

                # ─── Exit checks ───
                exit_now = False; exit_px = 0.0; exit_reason = ''
                if ed == 1:
                    if cl_ <= sp:
                        exit_now = True; exit_px = sp
                        exit_reason = 'BE' if be_triggered and abs(sp - ep) < 1.5 else 'SL'
                    elif ch >= tp_:
                        exit_now = True; exit_px = tp_; exit_reason = 'TP'
                else:
                    if ch >= sp:
                        exit_now = True; exit_px = sp
                        exit_reason = 'BE' if be_triggered and abs(sp - ep) < 1.5 else 'SL'
                    elif cl_ <= tp_:
                        exit_now = True; exit_px = tp_; exit_reason = 'TP'

                if exit_now:
                    pnl = (exit_px - ep) if ed == 1 else (ep - exit_px)
                    pnl_c += pnl
                    if pnl < 0: worst = min(worst, pnl)
                    n += 1
                    if pnl > 0: w += 1
                    else: l += 1

                    # Track BE-save: original SL would have hit (by checking forward for original sl_orig)
                    if exit_reason == 'BE':
                        # Look forward (within session) — does price hit sl_orig later?
                        sl_would_hit = False
                        tp_would_hit = False
                        for j in range(i, len(Cl)):
                            if ed == 1:
                                if Lo[j] <= sl_orig: sl_would_hit = True; break
                                if Hi[j] >= tp_:   tp_would_hit = True; break
                            else:
                                if Hi[j] >= sl_orig: sl_would_hit = True; break
                                if Lo[j] <= tp_:   tp_would_hit = True; break
                        if sl_would_hit: be_saves += 1
                        if tp_would_hit: be_premature += 1

                    in_trade = False; state = 0; be_triggered = False
                    be_armed_for_next_bar = False; running_extreme = 0
                    continue

                # ─── BE trigger check at end of CURRENT bar (arm for NEXT bar) ───
                if not be_triggered:
                    sl_dist = abs(ep - sl_orig)
                    if be_variant == 'V1' and ed == 1 and ch >= ep + 1.0 * sl_dist:
                        be_armed_for_next_bar = True; running_extreme = ch
                    elif be_variant == 'V1' and ed == -1 and cl_ <= ep - 1.0 * sl_dist:
                        be_armed_for_next_bar = True; running_extreme = cl_
                    elif be_variant == 'V2' and ed == 1 and ch >= ep + 0.5 * sl_dist:
                        be_armed_for_next_bar = True; running_extreme = ch
                    elif be_variant == 'V2' and ed == -1 and cl_ <= ep - 0.5 * sl_dist:
                        be_armed_for_next_bar = True; running_extreme = cl_
                    elif be_variant == 'V3' and ed == 1 and ch >= ep + 1.0 * sl_dist:
                        be_armed_for_next_bar = True; running_extreme = ch
                    elif be_variant == 'V3' and ed == -1 and cl_ <= ep - 1.0 * sl_dist:
                        be_armed_for_next_bar = True; running_extreme = cl_
                    elif be_variant == 'V4' and ed == 1 and ch >= ep + 1.5 * sl_dist:
                        be_armed_for_next_bar = True; running_extreme = ch
                    elif be_variant == 'V4' and ed == -1 and cl_ <= ep - 1.5 * sl_dist:
                        be_armed_for_next_bar = True; running_extreme = cl_
                    elif be_variant == 'V5' and ed == 1 and ch >= ep + 1.0 * sl_dist:
                        be_armed_for_next_bar = True; running_extreme = ch
                    elif be_variant == 'V5' and ed == -1 and cl_ <= ep - 1.0 * sl_dist:
                        be_armed_for_next_bar = True; running_extreme = cl_
                    elif be_variant == 'V6' and ed == 1 and ch >= bx_hi + 0.5 * bw:
                        # opposite-box-edge proxy: long, reach mid-above-box
                        be_armed_for_next_bar = True; running_extreme = ch
                    elif be_variant == 'V6' and ed == -1 and cl_ <= bx_lo - 0.5 * bw:
                        be_armed_for_next_bar = True; running_extreme = cl_

                continue

            if attempts >= max_attempts: continue

            # ─── Pullback state machine entry (same as e44 baseline) ───
            if state == 0:
                if cc > bx_hi:
                    breakout_dir = 1; breakout_idx = i
                    state = 1; retest_extreme = cl_
                elif cc < bx_lo:
                    breakout_dir = -1; breakout_idx = i
                    state = 1; retest_extreme = ch
                continue
            if state == 1:
                if i - breakout_idx > max_wait_bars: state = 0; continue
                if breakout_dir == 1:
                    retest_extreme = min(retest_extreme, cl_)
                    if cl_ <= bx_hi + retest_tolerance: state = 2
                else:
                    retest_extreme = max(retest_extreme, ch)
                    if ch >= bx_lo - retest_tolerance: state = 2
                continue
            if state == 2:
                if i - breakout_idx > max_wait_bars: state = 0; continue
                if breakout_dir == 1:
                    retest_extreme = min(retest_extreme, cl_)
                    if cl_ < bx_lo: state = 0; continue
                    if is_pin(co, ch, cl_, cc, 1) or is_engulf(po, pc, co, cc, 1):
                        ep = float(cc); ed = 1
                        sp = retest_extreme - sl_buffer
                        sl_dist = ep - sp
                        if sl_dist <= 0: state = 0; continue
                        tp_ = ep + tp_mult * sl_dist
                        sl_orig = sp
                        sl_distances.append(sl_dist)
                        in_trade = True; attempts += 1
                        cur_entry_idx = i
                        be_triggered = False; be_armed_for_next_bar = False
                        running_extreme = ep
                else:
                    retest_extreme = max(retest_extreme, ch)
                    if ch > bx_hi: state = 0; continue
                    if is_pin(co, ch, cl_, cc, -1) or is_engulf(po, pc, co, cc, -1):
                        ep = float(cc); ed = -1
                        sp = retest_extreme + sl_buffer
                        sl_dist = sp - ep
                        if sl_dist <= 0: state = 0; continue
                        tp_ = ep - tp_mult * sl_dist
                        sl_orig = sp
                        sl_distances.append(sl_dist)
                        in_trade = True; attempts += 1
                        cur_entry_idx = i
                        be_triggered = False; be_armed_for_next_bar = False
                        running_extreme = ep

    return {
        'pnl_closed': pnl_c, 'n': n, 'wins': w, 'losses': l,
        'wr': 100*w/n if n else 0, 'worst': worst,
        'avg_sl': float(np.mean(sl_distances)) if sl_distances else 0,
        'be_saves': be_saves, 'be_premature': be_premature,
    }


def aggregate_session(dg, dates, atr_pass, be_variant):
    total = {'pnl_closed':0, 'n':0, 'wins':0, 'losses':0, 'worst':0,
             'be_saves':0, 'be_premature':0, 'sl_dists':[]}
    per = {}
    for sess in ['Asia','London','NY']:
        r = run_pullback_with_be(dg, dates, sess, atr_pass, be_variant)
        per[sess] = r
        total['pnl_closed'] += r['pnl_closed']
        total['n'] += r['n']; total['wins'] += r['wins']; total['losses'] += r['losses']
        total['worst'] = min(total['worst'], r['worst'])
        total['be_saves'] += r['be_saves']
        total['be_premature'] += r['be_premature']
        if r['avg_sl'] > 0: total['sl_dists'].append(r['avg_sl'])
    total['wr'] = 100*total['wins']/total['n'] if total['n'] else 0
    total['avg_sl'] = float(np.mean(total['sl_dists'])) if total['sl_dists'] else 0
    return per, total


def main():
    print("Loading 5y XAUUSD M1...")
    df = load_data(CSV)
    dg, dates = build_date_groups(df)
    print(f"  {len(dates)} ET trading days\n")

    atr_ctx = compute_daily_atr(dg, dates, lookback=30)
    sorted_d = sorted(atr_ctx.keys()); history = []
    e38_pass = set()
    for d in sorted_d:
        if len(history) < 30: e38_pass.add(d)
        else:
            if atr_ctx[d]['atr'] >= float(np.percentile(history[-30:], 30)): e38_pass.add(d)
        history.append(atr_ctx[d]['atr'])

    print(f"  e38 ATR pass-set: {len(e38_pass)} / {len(dates)}\n")

    variants = [
        ('V0', 'BASELINE (no BE)'),
        ('V1', 'BE @ +1R (move SL to entry)'),
        ('V2', 'BE @ +0.5R (early trigger)'),
        ('V3', 'BE+1pt @ +1R (lock 1pt profit)'),
        ('V4', 'BE @ +1.5R (later trigger)'),
        ('V5', 'TRAIL-step @ +1R then trail'),
        ('V6', 'BE @ opposite-box-edge'),
    ]

    print("Running 7 variants × 3 sessions × 5y data...\n")
    results = []
    for code, label in variants:
        per, tot = aggregate_session(dg, dates, e38_pass, code)
        results.append({'code': code, 'label': label, 'per': per, 'tot': tot})
        # Compute PF
        # Reconstruct from per-session
        gross_p = sum(t['pnl_closed'] for t in per.values() if t['pnl_closed'] > 0) or 0
        # Need win/loss separately — re-compute from sl_distances + worst not available
        # Approximate PF via wr × tp / (1-wr) × avg_sl (rough)
        wr = tot['wr'] / 100
        avg_w_est = 0  # need sum of pos pnl / wins; not tracked. Skip for now.
        print(f"{code} {label:<35} | n={tot['n']:>4} | pnl={tot['pnl_closed']:>+7.0f} | wr={tot['wr']:>4.1f}% | worst={tot['worst']:>+5.1f} | BE-saves={tot['be_saves']:>4} | BE-premature={tot['be_premature']:>4}")

    print("\n" + "="*100)
    print("SUMMARY DELTA (vs V0 BASELINE)")
    print("="*100)
    base_pnl = results[0]['tot']['pnl_closed']
    base_wr = results[0]['tot']['wr']
    base_worst = results[0]['tot']['worst']
    base_n = results[0]['tot']['n']
    print(f"{'Variant':<8} | {'Δ PnL':>9} | {'Δ WR':>7} | {'Δ worst':>9} | {'Δ trades':>8} | {'BE-saves':>8} | {'BE-prem':>7} | {'Net BE':>7}")
    print("-"*100)
    for r in results:
        t = r['tot']
        d_pnl = t['pnl_closed'] - base_pnl
        d_wr  = t['wr'] - base_wr
        d_worst = t['worst'] - base_worst
        d_n = t['n'] - base_n
        net_be = t['be_saves'] - t['be_premature']  # positive = BE net helpful
        print(f"{r['code']:<8} | {d_pnl:>+9.0f} | {d_wr:>+6.1f}% | {d_worst:>+9.1f} | {d_n:>+8} | {t['be_saves']:>8} | {t['be_premature']:>7} | {net_be:>+7}")

    # Per-session detail for best variant
    print("\n" + "="*100)
    print("PER-SESSION DETAIL (all variants)")
    print("="*100)
    for r in results:
        print(f"\n── {r['code']} {r['label']} ──")
        for sess in ['Asia','London','NY']:
            x = r['per'][sess]
            print(f"  {sess:<8} n={x['n']:>4} pnl={x['pnl_closed']:>+7.0f} wr={x['wr']:>4.1f}% worst={x['worst']:>+5.1f} avgSL={x['avg_sl']:>4.1f} BE-save={x['be_saves']:>3} BE-prem={x['be_premature']:>3}")

    # Save JSON
    out = ROOT / 'data' / 'phase17_be_trail_sweep.json'
    with open(out, 'w') as f:
        json.dump([{'code':r['code'],'label':r['label'],'tot':r['tot'],
                    'per':{s:{k:v for k,v in r['per'][s].items() if k != 'sl_dists'} for s in r['per']}} for r in results],
                  f, indent=2, default=str)
    print(f"\n[saved] {out}")


if __name__ == "__main__":
    main()
