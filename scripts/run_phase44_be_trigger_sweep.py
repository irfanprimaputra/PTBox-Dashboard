"""
Phase 44 — BE Trigger R Sweep (full engine).

Phase 43 hinted BE trigger 1.5R might beat 1.0R. Test with FULL engine
(ATR filter + TP boost + NY delay + session params).

Sweep be_trigger_r values: 0.75, 1.0 (current), 1.25, 1.5, 1.75, 2.0
"""
import sys
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT / "scripts"))
from ptbox_engine_e37 import load_data, build_date_groups, E37_CONFIG, compute_atr_filter_dates
from run_be_trail_sweep import run_pullback_with_be

CSV = "/Users/irfanprimaputra.b/Downloads/XAUUSD_M1_2021_-_2026.csv"


def patch_v5_be_trigger(be_trigger_r):
    """Monkey-patch run_be_trail_sweep V5 logic with custom be_trigger_r."""
    import run_be_trail_sweep as bs
    original = bs.run_pullback_with_be

    def patched(dg, dates, sess_name, atr_pass, be_variant, **kw):
        return _run_pullback_custom_be(dg, dates, sess_name, atr_pass, be_trigger_r, **kw)

    return patched


def _run_pullback_custom_be(dg, dates, sess_name, atr_pass, be_trigger_r,
                              max_attempts=5, retest_tolerance=3.0, sl_buffer=2.0,
                              tp_mult=2.0, max_wait_bars=60):
    """Full e44 PB engine + V5 trail with custom be_trigger_r."""
    cfg_raw = {
        "Asia":   {**E37_CONFIG['asia'],   "box_start_h": 19},
        "London": {**E37_CONFIG['london']},
        "NY":     {**E37_CONFIG['ny']},
    }[sess_name]
    cfg = {
        'box_start_h': cfg_raw['box_start_h'],
        'box_start_m': cfg_raw.get('box_start_m', 0),
        'box_dur_min': cfg_raw.get('box_dur', cfg_raw.get('box_dur_min', 60)),
        'session_end_h': cfg_raw.get('session_end_h', 24),
        'entry_delay_min': cfg_raw.get('entry_delay_min', 25 if sess_name == 'NY' else 0),
    }

    pnl_closed = 0.0
    n = w = l = be_saves = be_premature = 0
    worst = 0.0
    sl_distances = []
    trail_exits = 0
    tp_hits = 0
    sl_hits = 0

    for d in dates:
        if d not in dg: continue
        if d not in atr_pass: continue
        g = dg[d]

        BS = cfg['box_start_h'] * 60 + cfg.get('box_start_m', 0)
        BE_min = BS + cfg['box_dur_min']
        SE = cfg.get('session_end_h_eff', cfg['session_end_h'])
        if SE == 24: SE = 1439
        else: SE = SE * 60 - 1

        tm = g['tm'].values
        H = g['high'].values; L_ = g['low'].values; C = g['close'].values; O = g['open'].values
        box_mask = (tm >= BS) & (tm < BE_min)
        if box_mask.sum() < 5: continue
        bx_hi = H[box_mask].max(); bx_lo = L_[box_mask].min()
        bw = bx_hi - bx_lo
        if bw < 1: continue

        delay = cfg.get('entry_delay_min', 0)
        tr = (tm >= BE_min + delay) & (tm < SE)
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
                # BE Trail V5 with custom trigger
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
                        pnl_closed += pnl_t; n += 1
                        if pnl_t > 0: w += 1
                        else: l += 1
                        if pnl_t < worst: worst = pnl_t
                        if be_triggered:
                            if abs(sp - ep) <= 0.5: be_saves += 1
                            else: trail_exits += 1
                        else:
                            sl_hits += 1
                        be_triggered = False
                        continue
                    elif ch >= tp_:
                        pnl_t = tp_ - ep; in_trade = False
                        pnl_closed += pnl_t; n += 1; w += 1; tp_hits += 1
                        if be_triggered and abs(sp - ep) <= 0.5: be_premature += 1
                        be_triggered = False
                        continue
                else:
                    if ch >= sp:
                        pnl_t = ep - sp; in_trade = False
                        pnl_closed += pnl_t; n += 1
                        if pnl_t > 0: w += 1
                        else: l += 1
                        if pnl_t < worst: worst = pnl_t
                        if be_triggered:
                            if abs(sp - ep) <= 0.5: be_saves += 1
                            else: trail_exits += 1
                        else:
                            sl_hits += 1
                        be_triggered = False
                        continue
                    elif cl_ <= tp_:
                        pnl_t = ep - tp_; in_trade = False
                        pnl_closed += pnl_t; n += 1; w += 1; tp_hits += 1
                        if be_triggered and abs(sp - ep) <= 0.5: be_premature += 1
                        be_triggered = False
                        continue
                continue

            if attempts >= max_attempts: continue

            # PB state machine
            if state == 0:
                if cc > bx_hi:
                    state = 1; bk_dir = 1; bk_idx = i
                elif cc < bx_lo:
                    state = 1; bk_dir = -1; bk_idx = i
            elif state == 1:
                if i - bk_idx > max_wait_bars:
                    state = 0; bk_dir = 0
                    continue
                if bk_dir == 1 and cl_ <= bx_hi + retest_tolerance: state = 2
                elif bk_dir == -1 and ch >= bx_lo - retest_tolerance: state = 2
            elif state == 2:
                # Pattern detection (bull/bear pin or engulf)
                rng = ch - cl_
                if bk_dir == 1:
                    bull = (rng > 0 and (cc - cl_) / rng > 0.6 and cc > co) or (cc > po and co < pc and cc > co)
                    if cl_ >= bx_hi - retest_tolerance and bull:
                        sl_px = min(cl_, pl) - sl_buffer
                        sl_d = cc - sl_px
                        if 0 < sl_d <= 30:
                            tp_eff = tp_mult * (cfg.get('tp_boost_mult', 1.0) if cfg.get('tp_boost_pctile') else 1.0)
                            tp_px = cc + tp_eff * sl_d
                            ep = cc; sp = sl_px; sl_orig = sl_px; tp_ = tp_px; ed = 1
                            in_trade = True; attempts += 1; state = 0
                            be_triggered = False
                            sl_distances.append(sl_d)
                        else: attempts += 1; state = 0
                else:
                    bear = (rng > 0 and (ch - cc) / rng > 0.6 and cc < co) or (cc < po and co > pc and cc < co)
                    if ch <= bx_lo + retest_tolerance and bear:
                        sl_px = max(ch, ph) + sl_buffer
                        sl_d = sl_px - cc
                        if 0 < sl_d <= 30:
                            tp_eff = tp_mult
                            tp_px = cc - tp_eff * sl_d
                            ep = cc; sp = sl_px; sl_orig = sl_px; tp_ = tp_px; ed = -1
                            in_trade = True; attempts += 1; state = 0
                            be_triggered = False
                            sl_distances.append(sl_d)
                        else: attempts += 1; state = 0

    wr = 100 * w / n if n else 0
    avg_sl = float(np.mean(sl_distances)) if sl_distances else 0
    return {
        'pnl_closed': round(pnl_closed, 2),
        'n': n, 'wins': w, 'losses': l,
        'worst': round(worst, 2),
        'be_saves': be_saves, 'be_premature': be_premature,
        'trail_exits': trail_exits, 'tp_hits': tp_hits, 'sl_hits': sl_hits,
        'wr': round(wr, 2), 'avg_sl': round(avg_sl, 2),
    }


def main():
    print("Loading data...")
    df = load_data(CSV)
    dg, all_dates = build_date_groups(df)
    atr_pass_set = compute_atr_filter_dates(dg, all_dates, lookback=30, percentile=30)
    # Convert set to dict for .get() compatibility
    atr_pass = {d: True for d in atr_pass_set}
    print(f"  {len(dg)} days · ATR pass: {len(atr_pass_set)}/{len(all_dates)}\n")

    print("=" * 110)
    print("PHASE 44 — BE TRIGGER R SWEEP (full engine + ATR filter)")
    print("=" * 110)

    triggers = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
    all_results = {}

    for be_r in triggers:
        print(f'\n--- BE Trigger {be_r}R ---')
        sess_results = {}
        total_pnl = 0; total_n = 0; total_w = 0; total_be = 0; total_trail = 0; total_tp = 0; worst_overall = 0

        for sess in ['Asia', 'London', 'NY']:
            r = _run_pullback_custom_be(dg, all_dates, sess, atr_pass, be_r)
            sess_results[sess] = r
            total_pnl += r['pnl_closed']; total_n += r['n']; total_w += r['wins']
            total_be += r['be_saves']; total_trail += r['trail_exits']; total_tp += r['tp_hits']
            if r['worst'] < worst_overall: worst_overall = r['worst']
            print(f"  {sess:<8} | PnL {r['pnl_closed']:>+8.2f} | n={r['n']:>4} | WR {r['wr']:>5.1f}% | BE={r['be_saves']:>3} | Trail={r['trail_exits']:>3} | TP={r['tp_hits']:>3} | worst {r['worst']:>+6.2f}")

        all_results[be_r] = {
            'sessions': sess_results,
            'total_pnl': round(total_pnl, 2),
            'usd_per_yr_002': round(total_pnl * 2 / 5, 2),
            'total_n': total_n,
            'total_wr': round(100 * total_w / total_n, 2) if total_n else 0,
            'be_saves': total_be,
            'trail_exits': total_trail,
            'tp_hits': total_tp,
            'worst': round(worst_overall, 2),
        }
        marker = ' ⭐ CURRENT' if be_r == 1.0 else ''
        print(f"  TOTAL    | PnL {total_pnl:>+8.2f} | $/yr {total_pnl*2/5:>+7.0f} | n={total_n:>4} | WR {100*total_w/total_n if total_n else 0:>5.1f}%{marker}")

    # Summary table
    print('\n' + '=' * 110)
    print("SUMMARY TABLE")
    print('=' * 110)
    print(f'{"BE Trigger":>12} | {"PnL pts":>10} | {"$/yr@0.02":>10} | {"trades":>7} | {"WR%":>6} | {"BE":>4} | {"TR":>4} | {"TP":>4} | {"worst":>7}')
    print('-' * 95)
    for be_r in triggers:
        r = all_results[be_r]
        marker = ' ⭐' if be_r == 1.0 else ''
        print(f'{be_r:>10.2f}R{marker:<3} | {r["total_pnl"]:>+10.2f} | {r["usd_per_yr_002"]:>+10.0f} | {r["total_n"]:>7} | {r["total_wr"]:>6.2f} | {r["be_saves"]:>4} | {r["trail_exits"]:>4} | {r["tp_hits"]:>4} | {r["worst"]:>+7.2f}')

    # Verdict
    best = max(all_results.items(), key=lambda x: x[1]['total_pnl'])
    current = all_results[1.0]
    delta_pnl = best[1]['total_pnl'] - current['total_pnl']
    delta_usd_yr = (best[1]['total_pnl'] - current['total_pnl']) * 2 / 5

    print('\n' + '=' * 110)
    print("VERDICT")
    print('=' * 110)
    print(f"Current (1.0R):  PnL ${current['total_pnl']:.0f} | $/yr {current['usd_per_yr_002']:+.0f} | WR {current['total_wr']:.1f}%")
    print(f"BEST ({best[0]}R):    PnL ${best[1]['total_pnl']:.0f} | $/yr {best[1]['usd_per_yr_002']:+.0f} | WR {best[1]['total_wr']:.1f}%")
    print(f"Delta:           +${delta_pnl:.0f} ({delta_usd_yr:+.0f}/yr)")

    if best[0] != 1.0 and delta_usd_yr > 100:
        print(f"\n✅ DEPLOY: change beTriggerR from 1.0 to {best[0]} in Pine v15")
    elif best[0] == 1.0:
        print(f"\n✅ CURRENT OPTIMAL: keep beTriggerR = 1.0")
    else:
        print(f"\n⚠️  MARGINAL: improvement <$100/yr, not worth deploy risk")

    # Save
    out = ROOT / 'data' / 'phase44_be_trigger_sweep.json'
    with open(out, 'w') as f:
        json.dump({'triggers': triggers, 'results': {str(k): v for k, v in all_results.items()}}, f, indent=2)
    print(f'\n[saved] {out}')


if __name__ == '__main__':
    main()
