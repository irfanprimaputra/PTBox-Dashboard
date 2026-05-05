"""
╔══════════════════════════════════════════════════════════════════════╗
║      PT BOX QUARTERLY ENGINE v5 — Phase 5 B-Series (NY angles)      ║
║      B0: Diagnose pattern filter damage on NY (revert NY to raw)    ║
╚══════════════════════════════════════════════════════════════════════╝

CHANGES vs v4:
1. ✅ B0 variant: NY pattern_filter=None (revert to dyn_sl_tp_baseline)
2. ✅ Reuse v4 internals via import (walk_forward_phase5, aggregate, append_log)
3. ✅ Append to same experiment registry (continuity e013+)

CARA PAKAI:
   python3 ptbox_quarterly_v5.py --b0 [csv]

OUTPUT:
   - ptbox_phase5b_results.csv (per quarter × variant × session)
   - ptbox_phase5b_summary.json
   - APPEND ke ptbox_phase4_experiments.csv (registry continuity)

HYPOTHESIS B0:
   Pattern filter (any_pattern) HURT NY in e010 (raw -117 → filtered -290 = -173 pts damage).
   B0 reverts NY to no-pattern; expected total ≈ +375 pts (+24 Asia, +468 London, -117 NY).
   If hit → confirms pattern damage diagnosed correctly → unlocks B3 (EMA H1 trend gate).
   If miss → investigate timing-search interaction effects before layering B3.
"""

import os, sys, json, datetime, time
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ptbox_quarterly_v3 import (
    CONFIG, load_data, PATTERN_VARIANTS, EXPERIMENT_LOG,
)
from ptbox_quarterly_v4 import (
    ASIA_MEANREV_VARIANTS,
    walk_forward_phase5, aggregate_phase5, append_phase5_log,
)


# ═══════════════════════════════════════════════════════════════
# 🎴 PHASE 5 B-SERIES — NY angle variants
# ═══════════════════════════════════════════════════════════════

PHASE5B_VARIANTS = {
    "b0_ny_no_pattern": {
        "label": "B0: Asia A2-fail + London any_pattern + NY dyn_sl_tp_baseline (NO pattern) — diagnose pattern damage on NY",
        "sessions": {
            "Asia":   ASIA_MEANREV_VARIANTS["asia_a2_fail"],
            "London": PATTERN_VARIANTS["any_pattern"],
            "NY":     PATTERN_VARIANTS["dyn_sl_tp_baseline"],
        },
    },
}


# ═══════════════════════════════════════════════════════════════
# 🚀 MAIN
# ═══════════════════════════════════════════════════════════════

def main_phase5b(csv_path):
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║   PT BOX ENGINE v5 — PHASE 5 B-SERIES (NY angles)               ║")
    print("║   B0: Revert NY to dyn_sl_tp_baseline (no pattern filter)       ║")
    print("║   Asia + London unchanged (don't regress confirmed edges)       ║")
    print("╚══════════════════════════════════════════════════════════════════╝\n")

    df = load_data(csv_path)

    PHASE1_BASELINE     = -2498.4   # e001
    P4_2_REGISTRY_BEST  = -562.3    # e010
    P5_A2_REGISTRY_BEST = +202.0    # e012 (current best)

    all_results = []
    all_aggs = []

    t_total = time.time()
    for vkey, vdef in PHASE5B_VARIANTS.items():
        t0 = time.time()
        results = walk_forward_phase5(df, vkey, vdef)
        elapsed = time.time() - t0
        print(f"\n  [{vkey}] runtime: {elapsed:.1f}s, {len(results)} session-quarters")
        agg = aggregate_phase5(results, vkey)
        if agg:
            all_results.extend(results)
            all_aggs.append(agg)

    print(f"\n{'='*98}")
    print(f"TOTAL ELAPSED: {time.time()-t_total:.1f}s")
    print(f"{'='*98}")

    print(f"\n{'PHASE5B VARIANT':<32} {'PnL':>10} {'Δ e012':>10} {'Asia':>10} {'London':>10} {'NY':>10}")
    print('─' * 98)
    for agg in all_aggs:
        delta_e012 = agg['total_pnl'] - P5_A2_REGISTRY_BEST
        a = agg['sessions']['Asia']['total_pnl']   if agg['sessions']['Asia']   else 0
        l = agg['sessions']['London']['total_pnl'] if agg['sessions']['London'] else 0
        n = agg['sessions']['NY']['total_pnl']     if agg['sessions']['NY']     else 0
        print(f"{agg['phase5_variant']:<32} {agg['total_pnl']:>+10.1f} {delta_e012:>+10.1f} "
              f"{a:>+10.1f} {l:>+10.1f} {n:>+10.1f}")

    # Save raw results
    df_out = pd.DataFrame(all_results)
    df_out.to_csv('ptbox_phase5b_results.csv', index=False)
    print(f"\n✅ Raw results: ptbox_phase5b_results.csv")

    # Save summary JSON
    summary = {
        'generated': datetime.datetime.now().isoformat(),
        'angle': 'Phase 5 B-Series — NY angles',
        'phase1_baseline_reference': PHASE1_BASELINE,
        'p4_2_registry_best_reference': P4_2_REGISTRY_BEST,
        'p5_a2_registry_best_reference': P5_A2_REGISTRY_BEST,
        'variants': all_aggs,
    }
    with open('ptbox_phase5b_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"✅ Summary: ptbox_phase5b_summary.json")

    # Append to experiment registry (e013+)
    print(f"\nAppending to experiment registry...")
    E012_NY_REF = -290.0  # e012 NY component
    for agg in all_aggs:
        delta_e012 = agg['total_pnl'] - P5_A2_REGISTRY_BEST
        ny_now = agg['sessions']['NY']['total_pnl'] if agg['sessions']['NY'] else 0
        ny_change = ny_now - E012_NY_REF
        if delta_e012 > 100:
            verdict = 'promising'
        elif delta_e012 > 25:
            verdict = 'marginal_improve'
        elif delta_e012 > -25:
            verdict = 'no_change'
        else:
            verdict = 'reject_worse'
        notes = (
            f'B0 diagnostic: NY pattern_filter=None. '
            f'Δ vs e012 (current best): {delta_e012:+.0f}. '
            f'NY component change vs e012 NY (-290): {ny_change:+.0f}. '
            f'Predicted ≈ +375 total / NY ~-117.'
        )
        # Override angle label for B-series tracking
        variant_def = dict(PHASE5B_VARIANTS[agg['phase5_variant']])
        eid = append_phase5_log(
            agg['phase5_variant'], variant_def,
            agg, PHASE1_BASELINE, verdict, notes
        )
        # Patch angle field in registry (append_phase5_log hardcodes 'Phase 5 #A2')
        if os.path.exists(EXPERIMENT_LOG):
            df_log = pd.read_csv(EXPERIMENT_LOG)
            df_log.loc[df_log['experiment_id']==eid, 'angle'] = 'Phase 5 #B0'
            df_log.to_csv(EXPERIMENT_LOG, index=False)

    print()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    csv_path = args[0] if args else CONFIG['m1_file']
    if not os.path.exists(csv_path):
        print(f"❌ File not found: {csv_path}")
        print("   Usage:")
        print("     python3 ptbox_quarterly_v5.py --b0 [csv]")
        sys.exit(1)

    if '--b0' in sys.argv or '--phase5b' in sys.argv:
        main_phase5b(csv_path)
    else:
        print("Usage:")
        print("  python3 ptbox_quarterly_v5.py --b0 [csv]")
        sys.exit(0)


if __name__ == '__main__':
    main()
