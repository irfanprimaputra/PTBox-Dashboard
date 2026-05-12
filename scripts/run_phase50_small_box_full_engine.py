"""
Phase 50 — Small Box + Break-Only Sweep WITH FULL ENGINE.

Phase 49 missing ATR filter (e38) + TP boost (e39) = invalid comparison.
Phase 50 REUSES full engine from Phase 44 (BE Trigger sweep base) and adds:
- Box duration parameter (was hardcoded 90/60/60)
- Entry mode toggle (pullback / breakout / breakout_strong)
- BE Trigger 1.5R (Phase 46 cross-era winner)

Apples-to-apples vs Phase 46 baseline ($1,494/yr Trump era).
"""
import sys
import json
from pathlib import Path
import numpy as np
from datetime import date

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT / "scripts"))
from ptbox_engine_e37 import load_data, build_date_groups, E37_CONFIG, compute_atr_filter_dates, compute_atr_rank_map

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
    return (dir_ == 1 and c > o) or (dir_ == -1 and c < o)


def run_session_full(dg, dates, sess_name, atr_pass, atr_rank, *,
                    box_dur, entry_mode, be_trigger_r=1.5, tp_mult=2.0,
                    use_tp_boost=True, tp_boost_pctile=72, tp_boost_mult=1.30,
                    pb_retest_tol=3.0, pb_sl_buffer=2.0,
                    max_attempts=5, max_wait_bars=60):
    """Full e44 PB engine with ATR filter + TP boost + custom box_dur + entry mode."""
    cfg_map = {
        'Asia':   {'box_start_h': 19, 'session_end_h': 24, 'entry_delay_min': 0},
        'London': {'box_start_h': 0,  'session_end_h': 8,  'entry_delay_min': 0},
        'NY':     {'box_start_h': 7,  'session_end_h': 13, 'entry_delay_min': 25},
    }
    cfg = cfg_map[sess_name]

    pnl_closed = 0.0
    n = w = l = be_saves = trail_exits = tp_hits = 0
    worst = 0.0

    for d in dates:
        if d not in dg: continue
        if d not in atr_pass: continue
        g = dg[d]
        if len(g) < 50: continue

        BS = cfg['box_start_h'] * 60
        BE_min = BS + box_dur
        SE = 1439 if cfg['session_end_h'] == 24 else cfg['session_end_h'] * 60 - 1

        tm = g['tm'].values
        H = g['high'].values; L_ = g['low'].values; C = g['close'].values; O = g['open'].values
        box_mask = (tm >= BS) & (tm < BE_min)
        if box_mask.sum() < max(2, box_dur // 5): continue
        bx_hi = H[box_mask].max(); bx_lo = L_[box_mask].min()
        bw = bx_hi - bx_lo
        if bw < 0.5: continue

        delay = cfg['entry_delay_min']
        tr = (tm >= BE_min + delay) & (tm < SE)
        if tr.sum() < 5: continue
        Hi = H[tr]; Lo = L_[tr]; Cl = C[tr]; Op = O[tr]

        # TP boost active for this day?
        atr_rank_today = atr_rank.get(d, 0.5)
        tp_eff = tp_mult * (tp_boost_mult if (use_tp_boost and atr_rank_today >= tp_boost_pctile / 100) else 1.0)

        attempts = 0; in_trade = False
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
                        pnl_t = sp - ep; pnl_closed += pnl_t; n += 1; in_trade = False
                        if pnl_t > 0: w += 1
                        else: l += 1
                        if pnl_t < worst: worst = pnl_t
                        if be_triggered:
                            if abs(sp - ep) <= 0.5: be_saves += 1
                            else: trail_exits += 1
                        be_triggered = False
                        continue
                    elif ch >= tp_:
                        pnl_closed += tp_ - ep; n += 1; w += 1; tp_hits += 1; in_trade = False
                        be_triggered = False
                        continue
                else:
                    if ch >= sp:
                        pnl_t = ep - sp; pnl_closed += pnl_t; n += 1; in_trade = False
                        if pnl_t > 0: w += 1
                        else: l += 1
                        if pnl_t < worst: worst = pnl_t
                        if be_triggered:
                            if abs(sp - ep) <= 0.5: be_saves += 1
                            else: trail_exits += 1
                        be_triggered = False
                        continue
                    elif cl_ <= tp_:
                        pnl_closed += ep - tp_; n += 1; w += 1; tp_hits += 1; in_trade = False
                        be_triggered = False
                        continue
                continue

            if attempts >= max_attempts: continue

            if entry_mode == 'breakout':
                if cc > bx_hi:
                    sl_d = max(2.0, pb_sl_buffer + bw * 0.3)
                    sl_px = cc - sl_d
                    tp_px = cc + tp_eff * sl_d
                    ep = cc; sp = sl_px; sl_orig = sl_px; tp_ = tp_px; ed = 1
                    in_trade = True; attempts += 1; be_triggered = False
                elif cc < bx_lo:
                    sl_d = max(2.0, pb_sl_buffer + bw * 0.3)
                    sl_px = cc + sl_d
                    tp_px = cc - tp_eff * sl_d
                    ep = cc; sp = sl_px; sl_orig = sl_px; tp_ = tp_px; ed = -1
                    in_trade = True; attempts += 1; be_triggered = False

            elif entry_mode == 'breakout_strong':
                if cc > bx_hi and is_strong_body(co, ch, cl_, cc, 1):
                    sl_d = max(2.0, pb_sl_buffer + bw * 0.3)
                    sl_px = cc - sl_d
                    tp_px = cc + tp_eff * sl_d
                    ep = cc; sp = sl_px; sl_orig = sl_px; tp_ = tp_px; ed = 1
                    in_trade = True; attempts += 1; be_triggered = False
                elif cc < bx_lo and is_strong_body(co, ch, cl_, cc, -1):
                    sl_d = max(2.0, pb_sl_buffer + bw * 0.3)
                    sl_px = cc + sl_d
                    tp_px = cc - tp_eff * sl_d
                    ep = cc; sp = sl_px; sl_orig = sl_px; tp_ = tp_px; ed = -1
                    in_trade = True; attempts += 1; be_triggered = False

            elif entry_mode == 'pullback':
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
                            tp_px = cc + tp_eff * sl_d
                            ep = cc; sp = sl_px; sl_orig = sl_px; tp_ = tp_px; ed = 1
                            in_trade = True; attempts += 1; state = 0; be_triggered = False
                        else: attempts += 1; state = 0
                    elif bk_dir == -1 and ch <= bx_lo + pb_retest_tol and (is_pin(co, ch, cl_, cc, -1) or is_engulf(po, pc, co, cc, -1)):
                        sl_px = max(ch, ph) + pb_sl_buffer
                        sl_d = sl_px - cc
                        if 0 < sl_d <= 30:
                            tp_px = cc - tp_eff * sl_d
                            ep = cc; sp = sl_px; sl_orig = sl_px; tp_ = tp_px; ed = -1
                            in_trade = True; attempts += 1; state = 0; be_triggered = False
                        else: attempts += 1; state = 0

    wr = round(100 * w / n, 2) if n else 0
    return {
        'pnl': round(pnl_closed, 2),
        'n': n, 'wr': wr,
        'be_saves': be_saves, 'trail_exits': trail_exits, 'tp_hits': tp_hits,
        'worst': round(worst, 2),
    }


def main():
    print("Loading 5y data...")
    df = load_data(CSV)
    dg, all_dates = build_date_groups(df)
    trump_dates = [d for d in all_dates if d >= TRUMP_START]
    print(f"  Trump-2 era: {len(trump_dates)} days")

    atr_full_set = compute_atr_filter_dates(dg, all_dates, lookback=30, percentile=30)
    atr_pass_trump = {d: True for d in atr_full_set if d >= TRUMP_START}
    atr_rank_map = compute_atr_rank_map(dg, all_dates, lookback=30)
    print(f"  ATR pass Trump: {len(atr_pass_trump)}/{len(trump_dates)}\n")

    print("=" * 130)
    print("PHASE 50 — Small Box + Entry Mode Sweep (FULL ENGINE: ATR + TP boost + BE 1.5R)")
    print("=" * 130)

    # Sweep: Box × Entry Mode (full engine)
    print("\n### SWEEP: Box Duration × Entry Mode (Trump-only, FULL features) ###")
    print(f'{"Variant":<35} | {"PnL pts":>9} | {"$/yr@002":>9} | {"trades":>6} | {"WR%":>5} | {"TP":>4} | {"BE":>4} | {"TR":>4} | {"worst":>7}')
    print('-' * 130)

    all_results = []
    for box_dur in [5, 10, 15, 30, 60, 90, 120]:
        for mode in ['breakout', 'breakout_strong', 'pullback']:
            total_pnl = 0; total_n = 0; total_w = 0; total_be = 0; total_trail = 0; total_tp = 0; worst_overall = 0
            for sess in ['Asia', 'London', 'NY']:
                r = run_session_full(dg, trump_dates, sess, atr_pass_trump, atr_rank_map,
                                       box_dur=box_dur, entry_mode=mode)
                total_pnl += r['pnl']; total_n += r['n']; total_w += r['wins'] if 'wins' in r else 0
                total_be += r['be_saves']; total_trail += r['trail_exits']; total_tp += r['tp_hits']
                if r['worst'] < worst_overall: worst_overall = r['worst']
                if 'wins' not in r: total_w += (1 if r['wr'] > 0 else 0) * r['n'] * r['wr'] / 100
            total_w = int(total_w) if total_w else 0
            wr = round(100 * total_w / total_n, 2) if total_n else 0
            usd_yr = round(total_pnl * 2 / 1.33, 2)
            res = {
                'box_dur': box_dur, 'entry_mode': mode,
                'pnl_pts': round(total_pnl, 2), 'usd_per_yr': usd_yr,
                'n': total_n, 'wr': wr, 'be': total_be, 'trail': total_trail,
                'tp': total_tp, 'worst': round(worst_overall, 2),
            }
            all_results.append(res)
            name = f"box={box_dur}min · {mode}"
            print(f'{name:<35} | {total_pnl:>+9.0f} | {usd_yr:>+9.0f} | {total_n:>6} | {wr:>5.1f} | {total_tp:>4} | {total_be:>4} | {total_trail:>4} | {worst_overall:>+7.0f}')

    best = max(all_results, key=lambda x: x['pnl_pts'])
    print(f"\n>>> BEST: box={best['box_dur']}min · {best['entry_mode']} → ${best['usd_per_yr']:+.0f}/yr <<<")

    # Compare to Phase 46 baseline
    baseline_usd_yr = 1494  # Phase 46 90min PB + ATR + TP boost + BE 1.75R
    delta = best['usd_per_yr'] - baseline_usd_yr
    print(f"\nPhase 46 baseline (90min PB + BE 1.75R): $1,494/yr")
    print(f"Phase 50 best: ${best['usd_per_yr']:+.0f}/yr | Δ {delta:+.0f}/yr ({100*delta/baseline_usd_yr:+.1f}%)")

    if delta > 200:
        print(f"\n✅ DEPLOY recommendation: box={best['box_dur']}min · {best['entry_mode']}")
    elif delta > 0:
        print(f"\n⚠️ MARGINAL improvement, may not justify mechanic change")
    else:
        print(f"\n❌ Existing Pine v15 BEATS small-box variants. STAY 90min + pullback.")

    out = ROOT / 'data' / 'phase50_small_box_full_engine.json'
    with open(out, 'w') as f:
        json.dump({'all_results': all_results, 'best': best, 'baseline_usd_yr': baseline_usd_yr, 'delta_usd_yr': delta}, f, indent=2, default=str)
    print(f'\n[saved] {out}')


if __name__ == '__main__':
    main()
