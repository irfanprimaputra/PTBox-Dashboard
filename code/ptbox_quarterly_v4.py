"""
╔══════════════════════════════════════════════════════════════════════╗
║      PT BOX QUARTERLY ENGINE v4 — Phase 5 Asia Mean-Reversion       ║
║      Per-session variant routing (Asia=meanrev, London/NY=existing) ║
╚══════════════════════════════════════════════════════════════════════╝

CHANGES vs v3:
1. ✅ Per-session variant config (different model per session)
2. ✅ Mean-reversion backtest engine (A2-fail flavor): fade failed breakout
3. ✅ Reuse v3 internals via import (load_data, generate_quarters, backtest, etc.)
4. ✅ Append to same experiment registry (continuity with Phase 4)

CARA PAKAI:
   python3 ptbox_quarterly_v4.py --phase5-asia-fail [csv]

OUTPUT:
   - ptbox_phase5_asia_meanrev_results.csv (per quarter × variant × session)
   - ptbox_phase5_asia_meanrev_summary.json
   - APPEND ke ptbox_phase4_experiments.csv (registry continuity)

CONSTRAINT (per Irfan 2026-04-27):
   - Asia ONLY swap to mean-rev model
   - London + NY MUST keep any_pattern (proven, don't regress London +468 edge)
   - Time window keep current (19:23 dur=7m default search) — isolate model variable
"""

import os, sys, json, datetime, time
import pandas as pd
import numpy as np

# Import v3 internals (library reuse)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ptbox_quarterly_v3 import (
    CONFIG, load_data, build_date_groups, generate_quarters,
    backtest, PATTERN_VARIANTS, EXPERIMENT_LOG,
)


# ═══════════════════════════════════════════════════════════════
# 🎴 PHASE 5 — ASIA MEAN-REVERSION VARIANTS
# ═══════════════════════════════════════════════════════════════

ASIA_MEANREV_VARIANTS = {
    "asia_a2_fail": {
        "label": "Asia A2-fail: fade failed breakout (SL=extreme+1pt buffer, TP=box midpoint)",
        "model": "mean_rev_fail",
        "sl_buffer": 1.0,        # buffer beyond breakout extreme
        "min_sl": 1.0,           # absolute floor SL distance
        "min_box_width": 1.0,    # skip degenerate boxes
        # Compatibility fields (unused by meanrev path, kept for shared code)
        "skip_box_gt": None, "sl_box_mult": None, "tp_box_mult": None,
        "pattern_filter": None,
    },
}

# Per-session variant combos for Phase 5
PHASE5_VARIANTS = {
    "phase5_sanity_any_pattern": {
        "label": "Sanity: any_pattern across all sessions (replicates e010 ~-562 pts)",
        "sessions": {
            "Asia":   PATTERN_VARIANTS["any_pattern"],
            "London": PATTERN_VARIANTS["any_pattern"],
            "NY":     PATTERN_VARIANTS["any_pattern"],
        },
    },
    "asia_a2_fail": {
        "label": "Asia A2-fail mean-rev + London/NY any_pattern (isolate Asia model swap)",
        "sessions": {
            "Asia":   ASIA_MEANREV_VARIANTS["asia_a2_fail"],
            "London": PATTERN_VARIANTS["any_pattern"],
            "NY":     PATTERN_VARIANTS["any_pattern"],
        },
    },
}


# ═══════════════════════════════════════════════════════════════
# 🔄 BACKTEST — MEAN-REVERSION (A2-FAIL FLAVOR)
# ═══════════════════════════════════════════════════════════════

def backtest_meanrev_fail(date_groups, all_dates, bh, bm, dur, variant):
    """
    A2-fail mean reversion: fade failed breakout.

    Logic per day:
      1. Box period [BS, BE) → compute bx_hi, bx_lo, box_mid, box_width
      2. Post-box bars:
         - Detect breakout: close beyond box edge
         - Track breakout extreme (highest high if up, lowest low if down)
         - Detect FAIL: close re-enters box (bx_lo < close < bx_hi)
         - On fail → ENTER opposite direction at NEXT bar open
      3. Trade mgmt:
         - SL = breakout_extreme ± SL_BUFFER (location-based)
         - TP = box midpoint
         - SL checked first on tie (conservative)
      4. Cooldown after SL (skip current bar), max attempts per day
      5. After SL/TP exit, reset breakout state — new fade can form same day

    Edge cases handled:
      - Cross-through: close goes from > bx_hi to < bx_lo without fail-stop
        → reset bk_dir to opposite, track new extreme
      - Degenerate boxes (width < min) → skip day
      - Degenerate trades (TP on wrong side of entry) → skip
    """
    SL_BUFFER = variant.get('sl_buffer', 1.0)
    MIN_SL = variant.get('min_sl', 1.0)
    MIN_BW = variant.get('min_box_width', 1.0)
    MAX_ATT = CONFIG['max_attempts']
    BS = bh * 60 + bm
    BE = BS + dur

    tw = tl = 0
    pnl_list = []
    box_widths = []

    for day in all_dates:
        if day not in date_groups:
            pnl_list.append(0.); continue

        g = date_groups[day]
        tm = g['tm'].values
        H = g['high'].values
        L = g['low'].values
        C = g['close'].values
        O = g['open'].values

        bk = (tm >= BS) & (tm < BE)
        if bk.sum() == 0:
            pnl_list.append(0.); continue
        bx_hi = H[bk].max()
        bx_lo = L[bk].min()
        box_width = bx_hi - bx_lo
        if box_width < MIN_BW:
            pnl_list.append(0.); continue
        box_mid = (bx_hi + bx_lo) / 2.0
        box_widths.append(box_width)

        tr = tm >= BE
        if tr.sum() < 3:
            pnl_list.append(0.); continue

        Hi = H[tr]; Lo = L[tr]; Cl = C[tr]; Op = O[tr]

        att = 0
        in_trade = False
        bk_dir = 0
        bk_extreme = None
        pending = None
        ep = sp = tp_ = 0.
        ed = 0
        dp = 0.
        dw = dl = 0
        st = None
        done = False

        for i in range(len(Cl)):
            ch = Hi[i]; cl = Lo[i]; cc = Cl[i]; co = Op[i]

            # --- Enter pending trade at this bar's open ---
            if pending is not None and not in_trade:
                ent_dir, extreme = pending
                pending = None
                ep = co
                ed = ent_dir
                if ed == 1:  # long fade after down-fail
                    sp = extreme - SL_BUFFER
                    tp_ = box_mid
                else:        # short fade after up-fail
                    sp = extreme + SL_BUFFER
                    tp_ = box_mid

                # Sanity: skip degenerate (TP must be on profitable side, SL min distance)
                sl_dist = abs(ep - sp)
                tp_dist = abs(tp_ - ep)
                degenerate = (
                    sl_dist < MIN_SL or
                    tp_dist < 0.5 or
                    (ed == 1 and tp_ <= ep) or
                    (ed == -1 and tp_ >= ep) or
                    (ed == 1 and sp >= ep) or
                    (ed == -1 and sp <= ep)
                )
                if degenerate:
                    in_trade = False; bk_dir = 0; bk_extreme = None
                    continue
                in_trade = True
                att += 1

            # --- In-trade SL/TP check ---
            if in_trade:
                if ed == 1:
                    if cl <= sp:  # SL first (conservative)
                        dl += 1; dp -= (ep - sp); in_trade = False
                        bk_dir = 0; bk_extreme = None; st = i
                        if att >= MAX_ATT: done = True
                        continue
                    if ch >= tp_:
                        dw += 1; dp += (tp_ - ep); in_trade = False
                        bk_dir = 0; bk_extreme = None; st = i
                        if att >= MAX_ATT: done = True
                        continue
                else:  # ed == -1
                    if ch >= sp:
                        dl += 1; dp -= (sp - ep); in_trade = False
                        bk_dir = 0; bk_extreme = None; st = i
                        if att >= MAX_ATT: done = True
                        continue
                    if cl <= tp_:
                        dw += 1; dp += (ep - tp_); in_trade = False
                        bk_dir = 0; bk_extreme = None; st = i
                        if att >= MAX_ATT: done = True
                        continue

            if done or in_trade or att >= MAX_ATT: continue
            if pending is not None: continue
            if st is not None and i <= st: continue

            # --- Detect / update breakout state ---
            if bk_dir == 0:
                if cc > bx_hi:
                    bk_dir = 1; bk_extreme = ch
                elif cc < bx_lo:
                    bk_dir = -1; bk_extreme = cl
            elif bk_dir == 1:
                if ch > bk_extreme:
                    bk_extreme = ch
                if cc < bx_lo:
                    # Cross all the way → flip to down-breakout
                    bk_dir = -1; bk_extreme = cl
                elif bx_lo < cc < bx_hi:
                    # Up breakout failed → fade short next bar
                    pending = (-1, bk_extreme)
            elif bk_dir == -1:
                if cl < bk_extreme:
                    bk_extreme = cl
                if cc > bx_hi:
                    bk_dir = 1; bk_extreme = ch
                elif bx_lo < cc < bx_hi:
                    # Down breakout failed → fade long next bar
                    pending = (1, bk_extreme)

        tw += dw; tl += dl
        pnl_list.append(dp)

    tt = tw + tl
    if tt < CONFIG['min_trades']:
        return None

    arr = np.cumsum(pnl_list)
    mdd = float((arr - np.maximum.accumulate(arr)).min())
    avg_box_w = round(float(np.mean(box_widths)), 2) if box_widths else 0

    return {
        'bh': bh, 'bm': bm, 'dur': dur,
        'trades': tt, 'wins': tw, 'losses': tl,
        'winrate': round(tw/tt*100, 1) if tt else 0,
        'pnl': round(sum(pnl_list), 1),
        'max_dd': round(mdd, 1),
        'tp1': 0, 'tp2': 0,
        'tp1_rate': 0, 'tp2_rate': 0,
        'pnl_list': pnl_list,
        'avg_box_width': avg_box_w,
        'pattern_skipped': 0,
    }


# ═══════════════════════════════════════════════════════════════
# 🎯 BACKTEST DISPATCH (route to correct engine per variant)
# ═══════════════════════════════════════════════════════════════

def _bt_dispatch(variant, date_groups, all_dates, bh, bm, dur, tp1, tp2):
    model = variant.get('model', 'breakout_pullback')
    if model == 'mean_rev_fail':
        return backtest_meanrev_fail(date_groups, all_dates, bh, bm, dur, variant)
    return backtest(date_groups, all_dates, bh, bm, dur, tp1, tp2, variant=variant)


def optimize_session_v4(date_groups, all_dates, sess_name, variant):
    cfg = CONFIG['sessions'][sess_name]
    tps = CONFIG['tp_per_session'][sess_name]
    s, e = cfg['start_min'], cfg['end_min']
    tp1, tp2 = tps['tp1'], tps['tp2']
    durs = CONFIG['durations']
    step = CONFIG['coarse_step']
    fw = CONFIG['fine_window']

    coarse = []
    for bmt in range(s, e, step):
        bh = bmt // 60; bm = bmt % 60
        for dur in durs:
            if bmt + dur >= e: continue
            r = _bt_dispatch(variant, date_groups, all_dates, bh, bm, dur, tp1, tp2)
            if r: coarse.append(r)

    if not coarse:
        return []

    df_c = pd.DataFrame(coarse)
    top_centers = df_c.nlargest(5, 'pnl')[['bh','bm']].values

    seen = set(); fine = []
    for bh, bm in top_centers:
        center = int(bh)*60 + int(bm)
        for bmt in range(max(s, center-fw), min(e, center+fw+1)):
            if bmt in seen: continue
            seen.add(bmt)
            fh = bmt//60; fm = bmt%60
            for dur in durs:
                if bmt + dur >= e: continue
                r = _bt_dispatch(variant, date_groups, all_dates, fh, fm, dur, tp1, tp2)
                if r: fine.append(r)

    return fine


# ═══════════════════════════════════════════════════════════════
# 📊 PHASE 5 WALK-FORWARD (per-session variant routing)
# ═══════════════════════════════════════════════════════════════

def walk_forward_phase5(df, phase5_key, phase5_variant):
    print(f"\n{'─'*70}")
    print(f"PHASE 5 VARIANT: {phase5_key}")
    print(f"  {phase5_variant['label']}")
    for s, v in phase5_variant['sessions'].items():
        model = v.get('model', 'breakout_pullback')
        print(f"  · {s:<6} → model={model}, label={v.get('label', '(unnamed)')[:60]}")
    print(f"{'─'*70}")

    data_start = df['date_et'].min()
    data_end   = df['date_et'].max()
    quarters   = generate_quarters(data_start, data_end)
    results = []

    sess_variants = phase5_variant['sessions']

    for idx, (train_s, train_e, val_s, val_e, label) in enumerate(quarters, 1):
        df_train = df[(df['date_et']>=train_s)&(df['date_et']<=train_e)]
        df_val   = df[(df['date_et']>=val_s)  &(df['date_et']<=val_e)]
        tg, td = build_date_groups(df_train)
        vg, vd = build_date_groups(df_val)
        if len(td) < 15 or len(vd) < 10:
            continue

        q_total = 0
        sess_summary = []
        for sess in ['Asia','London','NY']:
            sv = sess_variants[sess]
            tps = CONFIG['tp_per_session'][sess]
            tp1, tp2 = tps['tp1'], tps['tp2']
            fine = optimize_session_v4(tg, td, sess, sv)
            if not fine:
                sess_summary.append(f"{sess}-")
                continue
            best = pd.DataFrame(fine).nlargest(1,'pnl').iloc[0]
            bh, bm, dur = int(best.bh), int(best.bm), int(best.dur)
            vr = _bt_dispatch(sv, vg, vd, bh, bm, dur, tp1, tp2)
            if vr:
                q_total += vr['pnl']
                results.append({
                    'phase5_variant': phase5_key,
                    'quarter': label,
                    'session': sess,
                    'session_model': sv.get('model', 'breakout_pullback'),
                    'train_time': f"{bh:02d}:{bm:02d}",
                    'train_dur': dur,
                    'val_pnl': vr['pnl'],
                    'val_wr':  vr['winrate'],
                    'val_trades': vr['trades'],
                    'val_max_dd': vr['max_dd'],
                    'avg_box_width': vr.get('avg_box_width', 0),
                    'pass': vr['pnl'] > 0,
                })
                ind = "✓" if vr['pnl']>0 else "✗"
                sess_summary.append(f"{sess}{ind}{vr['pnl']:+.0f}")
            else:
                sess_summary.append(f"{sess}-")
        print(f"  [{idx:2d}/{len(quarters)}] {label}: Total {q_total:+.0f} | " + " ".join(sess_summary))

    return results


def aggregate_phase5(results, phase5_key):
    df_r = pd.DataFrame([r for r in results if r['phase5_variant']==phase5_key])
    if len(df_r) == 0: return None
    agg = {
        'phase5_variant': phase5_key,
        'session_quarters': len(df_r),
        'total_pnl': round(float(df_r['val_pnl'].sum()), 1),
        'avg_winrate': round(float(df_r['val_wr'].mean()), 1),
        'quarters_tested': int(df_r['quarter'].nunique()),
        'sessions': {},
    }
    for sess in ['Asia','London','NY']:
        sd = df_r[df_r['session']==sess]
        if len(sd)==0:
            agg['sessions'][sess] = None
            continue
        agg['sessions'][sess] = {
            'total_pnl': round(float(sd['val_pnl'].sum()), 1),
            'n_quarters': int(len(sd)),
            'n_pass': int(sd['pass'].sum()),
            'pass_rate_pct': round(float(sd['pass'].sum()/len(sd)*100), 1),
            'avg_pnl_per_q': round(float(sd['val_pnl'].mean()), 1),
            'avg_winrate': round(float(sd['val_wr'].mean()), 1),
            'avg_box_width': round(float(sd['avg_box_width'].mean()), 2),
            'model': sd.iloc[0]['session_model'],
        }
    return agg


# ═══════════════════════════════════════════════════════════════
# 📝 EXPERIMENT REGISTRY APPEND (Phase 5 entries)
# ═══════════════════════════════════════════════════════════════

def append_phase5_log(phase5_key, phase5_variant, agg, baseline_pnl, verdict, notes=""):
    config_summary = {
        'sessions': {
            s: {k: v for k, v in cv.items() if k != 'label'}
            for s, cv in phase5_variant['sessions'].items()
        },
    }
    row = {
        'experiment_id': '',
        'date_run': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
        'angle': 'Phase 5 #A2',
        'variant_name': phase5_key,
        'variant_label': phase5_variant['label'],
        'config_json': json.dumps(config_summary),
        'quarters_tested': agg['quarters_tested'],
        'session_quarters': agg['session_quarters'],
        'total_pnl': agg['total_pnl'],
        'asia_pnl':   agg['sessions']['Asia']['total_pnl']   if agg['sessions']['Asia']   else None,
        'london_pnl': agg['sessions']['London']['total_pnl'] if agg['sessions']['London'] else None,
        'ny_pnl':     agg['sessions']['NY']['total_pnl']     if agg['sessions']['NY']     else None,
        'asia_pass_rate':   agg['sessions']['Asia']['pass_rate_pct']   if agg['sessions']['Asia']   else None,
        'london_pass_rate': agg['sessions']['London']['pass_rate_pct'] if agg['sessions']['London'] else None,
        'ny_pass_rate':     agg['sessions']['NY']['pass_rate_pct']     if agg['sessions']['NY']     else None,
        'avg_winrate': agg['avg_winrate'],
        'vs_baseline_delta': round(agg['total_pnl'] - baseline_pnl, 1),
        'vs_baseline_pct': round((agg['total_pnl'] - baseline_pnl) / abs(baseline_pnl) * 100, 1) if baseline_pnl else 0,
        'verdict': verdict,
        'notes': notes,
    }
    if os.path.exists(EXPERIMENT_LOG):
        df_log = pd.read_csv(EXPERIMENT_LOG)
        next_id = len(df_log) + 1
    else:
        df_log = pd.DataFrame()
        next_id = 1
    row['experiment_id'] = f"e{next_id:03d}"
    df_new = pd.DataFrame([row])
    df_log = pd.concat([df_log, df_new], ignore_index=True)
    df_log.to_csv(EXPERIMENT_LOG, index=False)
    print(f"  ✅ Logged as {row['experiment_id']} → {EXPERIMENT_LOG}")
    return row['experiment_id']


# ═══════════════════════════════════════════════════════════════
# 🚀 MAIN — PHASE 5 ASIA MEAN-REVERSION
# ═══════════════════════════════════════════════════════════════

def main_phase5_asia_meanrev(csv_path):
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║   PT BOX ENGINE v4 — PHASE 5 #A2 ASIA MEAN-REVERSION            ║")
    print("║   (A2-fail: fade failed breakout, Asia ONLY)                    ║")
    print("║   London + NY keep any_pattern (don't regress London edge)      ║")
    print("╚══════════════════════════════════════════════════════════════════╝\n")

    df = load_data(csv_path)

    PHASE1_BASELINE   = -2498.4   # original control (e001)
    P4_2_REGISTRY_BEST = -562.3   # e010 any_pattern (cited "current best")

    all_results = []
    all_aggs = []

    t_total = time.time()
    for vkey, vdef in PHASE5_VARIANTS.items():
        t0 = time.time()
        results = walk_forward_phase5(df, vkey, vdef)
        elapsed = time.time() - t0
        print(f"\n  [{vkey}] runtime: {elapsed:.1f}s, {len(results)} session-quarters")
        agg = aggregate_phase5(results, vkey)
        if agg:
            all_results.extend(results)
            all_aggs.append(agg)

    print(f"\n{'='*92}")
    print(f"TOTAL ELAPSED: {time.time()-t_total:.1f}s")
    print(f"{'='*92}")

    print(f"\n{'PHASE5 VARIANT':<32} {'PnL':>10} {'Δ vs e010':>12} {'Asia':>10} {'London':>10} {'NY':>10}")
    print('─' * 92)
    for agg in all_aggs:
        delta_e010 = agg['total_pnl'] - P4_2_REGISTRY_BEST
        a = agg['sessions']['Asia']['total_pnl']   if agg['sessions']['Asia']   else 0
        l = agg['sessions']['London']['total_pnl'] if agg['sessions']['London'] else 0
        n = agg['sessions']['NY']['total_pnl']     if agg['sessions']['NY']     else 0
        print(f"{agg['phase5_variant']:<32} {agg['total_pnl']:>+10.1f} {delta_e010:>+12.1f} "
              f"{a:>+10.1f} {l:>+10.1f} {n:>+10.1f}")

    # Save raw results
    df_out = pd.DataFrame(all_results)
    df_out.to_csv('ptbox_phase5_asia_meanrev_results.csv', index=False)
    print(f"\n✅ Raw results: ptbox_phase5_asia_meanrev_results.csv")

    # Save summary JSON
    summary = {
        'generated': datetime.datetime.now().isoformat(),
        'angle': 'Phase 5 #A2 — Asia A2-fail mean-reversion',
        'phase1_baseline_reference': PHASE1_BASELINE,
        'p4_2_registry_best_reference': P4_2_REGISTRY_BEST,
        'variants': all_aggs,
    }
    with open('ptbox_phase5_asia_meanrev_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"✅ Summary: ptbox_phase5_asia_meanrev_summary.json")

    # Append to experiment registry
    print(f"\nAppending to experiment registry...")
    sanity_pnl = next(
        (a['total_pnl'] for a in all_aggs if a['phase5_variant']=='phase5_sanity_any_pattern'),
        P4_2_REGISTRY_BEST
    )
    E010_ASIA_REF = -740.0  # e010 Asia component (for delta tracking)
    for agg in all_aggs:
        delta_e010 = agg['total_pnl'] - P4_2_REGISTRY_BEST
        delta_sanity = agg['total_pnl'] - sanity_pnl
        if agg['phase5_variant'] == 'phase5_sanity_any_pattern':
            verdict = 'sanity_check'
            notes = f'Sanity replication of e010 any_pattern. Δ vs e010: {delta_e010:+.0f} pts (expected ~0)'
        else:
            asia_now = agg['sessions']['Asia']['total_pnl'] if agg['sessions']['Asia'] else 0
            asia_change = asia_now - E010_ASIA_REF
            if delta_e010 > 500:
                verdict = 'promising'
            elif delta_e010 > 100:
                verdict = 'marginal_improve'
            elif delta_e010 > -100:
                verdict = 'no_change'
            else:
                verdict = 'reject_worse'
            notes = (
                f'Δ vs e010 (any_pattern total): {delta_e010:+.0f}. '
                f'Δ vs Phase 5 sanity: {delta_sanity:+.0f}. '
                f'Asia component change vs e010 Asia (-740): {asia_change:+.0f}'
            )
        append_phase5_log(
            agg['phase5_variant'], PHASE5_VARIANTS[agg['phase5_variant']],
            agg, PHASE1_BASELINE, verdict, notes
        )

    print()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    csv_path = args[0] if args else CONFIG['m1_file']
    if not os.path.exists(csv_path):
        print(f"❌ File not found: {csv_path}")
        print("   Usage:")
        print("     python3 ptbox_quarterly_v4.py --phase5-asia-fail [csv]")
        sys.exit(1)

    if '--phase5-asia-fail' in sys.argv or '--phase5-asia-meanrev' in sys.argv:
        main_phase5_asia_meanrev(csv_path)
    else:
        print("Usage:")
        print("  python3 ptbox_quarterly_v4.py --phase5-asia-fail [csv]")
        sys.exit(0)


if __name__ == '__main__':
    main()
