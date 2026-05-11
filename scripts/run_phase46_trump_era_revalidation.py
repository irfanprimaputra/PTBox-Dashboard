"""
Phase 46 — Trump-Era Only Re-Validation.

User question: backtest full 5y mixes Biden chop + Trump volatile regimes.
Should we focus Trump-era (2025-2026) only as relevant validation?

Test:
1. Re-run BE Trigger R sweep (Phase 44) on Trump-only data
2. Compare optimal Trump-only vs full 5y optimal
3. Re-validate key params on Trump-only data
4. Verdict: same optimal? OR Trump regime needs different config?
"""
import sys
import json
from pathlib import Path
import numpy as np
import pandas as pd
from datetime import date

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT / "scripts"))
from ptbox_engine_e37 import load_data, build_date_groups, E37_CONFIG, compute_atr_filter_dates
from run_phase44_be_trigger_sweep import _run_pullback_custom_be

CSV = "/Users/irfanprimaputra.b/Downloads/XAUUSD_M1_2021_-_2026.csv"

TRUMP_START = date(2025, 1, 1)
BIDEN_END = date(2024, 12, 31)


def main():
    print("Loading 5y data...")
    df = load_data(CSV)
    dg, all_dates = build_date_groups(df)

    # Split dates by era
    biden_dates = [d for d in all_dates if d <= BIDEN_END]
    trump_dates = [d for d in all_dates if d >= TRUMP_START]

    print(f"  Biden era (2021-2024): {len(biden_dates)} days")
    print(f"  Trump-2 era (2025-2026): {len(trump_dates)} days")

    # ATR filter sets
    print("\nComputing ATR filter...")
    atr_full_set = compute_atr_filter_dates(dg, all_dates, lookback=30, percentile=30)
    atr_pass_full = {d: True for d in atr_full_set}
    atr_pass_biden = {d: True for d in atr_full_set if d <= BIDEN_END}
    atr_pass_trump = {d: True for d in atr_full_set if d >= TRUMP_START}
    print(f"  ATR pass Biden: {len(atr_pass_biden)}/{len(biden_dates)} = {100*len(atr_pass_biden)/len(biden_dates):.1f}%")
    print(f"  ATR pass Trump: {len(atr_pass_trump)}/{len(trump_dates)} = {100*len(atr_pass_trump)/len(trump_dates):.1f}%")

    triggers = [0.75, 1.0, 1.25, 1.5, 1.75, 2.0]

    print("\n" + "=" * 110)
    print("PHASE 46 — BE Trigger R Sweep Per Era")
    print("=" * 110)

    eras = [
        ('Biden 2021-2024', biden_dates, atr_pass_biden, 4.0),
        ('Trump-2 2025-2026', trump_dates, atr_pass_trump, 1.33),
    ]

    all_results = {}
    for era_name, era_dates, era_atr, years in eras:
        print(f"\n### {era_name} ({years} years) ###")
        print(f'{"BE Trigger":>12} | {"PnL pts":>9} | {"$/yr@002":>9} | {"trades":>6} | {"WR%":>5} | {"BE":>4} | {"TR":>4} | {"TP":>4} | {"worst":>7}')
        print('-' * 95)

        era_results = {}
        for be_r in triggers:
            total_pnl = 0; total_n = 0; total_w = 0; total_be = 0; total_trail = 0; total_tp = 0; worst_overall = 0
            for sess in ['Asia', 'London', 'NY']:
                r = _run_pullback_custom_be(dg, era_dates, sess, era_atr, be_r)
                total_pnl += r['pnl_closed']; total_n += r['n']; total_w += r['wins']
                total_be += r['be_saves']; total_trail += r['trail_exits']; total_tp += r['tp_hits']
                if r['worst'] < worst_overall: worst_overall = r['worst']

            wr = round(100 * total_w / total_n, 2) if total_n else 0
            usd_yr = round(total_pnl * 2 / years, 2)
            era_results[be_r] = {
                'pnl_pts': round(total_pnl, 2), 'usd_per_yr': usd_yr,
                'n': total_n, 'wr': wr, 'be': total_be, 'trail': total_trail,
                'tp': total_tp, 'worst': round(worst_overall, 2),
            }
            marker = ' ⭐' if be_r == 1.0 else ''
            print(f'{be_r:>10.2f}R{marker:<3} | {total_pnl:>+9.0f} | {usd_yr:>+9.0f} | {total_n:>6} | {wr:>5.1f} | {total_be:>4} | {total_trail:>4} | {total_tp:>4} | {worst_overall:>+7.0f}')

        all_results[era_name] = era_results

    # Comparison
    print('\n' + '=' * 110)
    print("CROSS-ERA COMPARISON")
    print('=' * 110)

    biden_results = all_results['Biden 2021-2024']
    trump_results = all_results['Trump-2 2025-2026']
    biden_best = max(biden_results.items(), key=lambda x: x[1]['pnl_pts'])
    trump_best = max(trump_results.items(), key=lambda x: x[1]['pnl_pts'])

    print(f"\nBiden 2021-2024 BEST: BE Trigger {biden_best[0]}R = {biden_best[1]['pnl_pts']:.0f}pts, ${biden_best[1]['usd_per_yr']:+.0f}/yr")
    print(f"Trump-2 2025-2026 BEST: BE Trigger {trump_best[0]}R = {trump_best[1]['pnl_pts']:.0f}pts, ${trump_best[1]['usd_per_yr']:+.0f}/yr")

    if biden_best[0] != trump_best[0]:
        print(f"\n🚨 DIFFERENT OPTIMAL between eras!")
        print(f"   Biden likes BE Trigger {biden_best[0]}R")
        print(f"   Trump likes BE Trigger {trump_best[0]}R")
        print(f"   → If user trades current era (Trump), tune to Trump optimal")
    else:
        print(f"\n✅ SAME OPTIMAL across eras: BE Trigger {biden_best[0]}R")
        print(f"   Robust across regime shifts")

    # Income comparison
    biden_yr_at_optimal = biden_best[1]['usd_per_yr']
    trump_yr_at_optimal = trump_best[1]['usd_per_yr']
    print(f"\nIncome scale Biden → Trump-2: ${biden_yr_at_optimal:.0f}/yr → ${trump_yr_at_optimal:.0f}/yr = {trump_yr_at_optimal/biden_yr_at_optimal if biden_yr_at_optimal != 0 else 0:.1f}× boost")

    # Save
    out = ROOT / 'data' / 'phase46_trump_era_revalidation.json'
    with open(out, 'w') as f:
        json.dump({'eras': {k: {str(r): v for r, v in vs.items()} for k, vs in all_results.items()},
                   'biden_best': {'be_r': biden_best[0], **biden_best[1]},
                   'trump_best': {'be_r': trump_best[0], **trump_best[1]}}, f, indent=2)
    print(f'\n[saved] {out}')


if __name__ == '__main__':
    main()
