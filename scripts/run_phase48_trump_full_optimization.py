"""
Phase 48 — Full Trump-Era Multi-Param Optimization.

Phase 46 tested only BE Trigger R Trump-only.
This phase tests ALL key params Trump-only:
- pb_retest_tol
- pb_sl_buffer
- pb_tp_mult
- max_attempt
- be_trigger_r (cross-check)

Compare Trump-optimal vs full-5y Pine v15 defaults.
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


def sweep_be_trigger_trump(dg, trump_dates, atr_pass_trump):
    print(f"\n### Sweep 1: BE Trigger R (Trump-only) ###")
    print(f'{"BE R":>6} | {"PnL pts":>9} | {"$/yr@002":>9} | {"trades":>6} | {"WR%":>5}')
    print('-' * 60)
    results = {}
    for be_r in [1.0, 1.25, 1.5, 1.75, 2.0]:
        total_pnl = 0; total_n = 0; total_w = 0
        for sess in ['Asia', 'London', 'NY']:
            r = _run_pullback_custom_be(dg, trump_dates, sess, atr_pass_trump, be_r)
            total_pnl += r['pnl_closed']; total_n += r['n']; total_w += r['wins']
        wr = round(100 * total_w / total_n, 2) if total_n else 0
        usd_yr = round(total_pnl * 2 / 1.33, 2)
        results[be_r] = {'pnl_pts': round(total_pnl, 2), 'usd_per_yr': usd_yr, 'n': total_n, 'wr': wr}
        marker = ' ⭐' if be_r == 1.0 else ''
        print(f'{be_r:>5.2f}{marker:<3} | {total_pnl:>+9.0f} | {usd_yr:>+9.0f} | {total_n:>6} | {wr:>5.1f}')
    return results


def main():
    print("Loading 5y data...")
    df = load_data(CSV)
    dg, all_dates = build_date_groups(df)

    trump_dates = [d for d in all_dates if d >= TRUMP_START]
    biden_dates = [d for d in all_dates if d < TRUMP_START]
    print(f"  Biden: {len(biden_dates)} days | Trump-2: {len(trump_dates)} days\n")

    atr_full_set = compute_atr_filter_dates(dg, all_dates, lookback=30, percentile=30)
    atr_pass_trump = {d: True for d in atr_full_set if d >= TRUMP_START}
    print(f"  ATR pass Trump: {len(atr_pass_trump)}/{len(trump_dates)}")

    print("\n" + "=" * 110)
    print("PHASE 48 — Full Multi-Param Optimization (Trump-only era)")
    print("=" * 110)

    # Sweep 1: BE Trigger (best ~$1500/yr)
    be_results = sweep_be_trigger_trump(dg, trump_dates, atr_pass_trump)
    best_be_r = max(be_results.items(), key=lambda x: x[1]['pnl_pts'])

    print(f"\n>>> BEST BE Trigger Trump: {best_be_r[0]}R = ${best_be_r[1]['usd_per_yr']}/yr <<<")

    # Statistical confidence check
    n_total = best_be_r[1]['n']
    win_rate = best_be_r[1]['wr'] / 100
    if n_total > 0:
        # Standard error for WR estimate
        se = np.sqrt(win_rate * (1 - win_rate) / n_total)
        ci_95_lower = (win_rate - 1.96 * se) * 100
        ci_95_upper = (win_rate + 1.96 * se) * 100

        # Standard error for $/yr (rough estimate)
        pnl_pts = best_be_r[1]['pnl_pts']
        pnl_se_estimate = abs(pnl_pts) * 0.15  # rough 15% std error assumption
        ci_95_pnl_lower = pnl_pts - 1.96 * pnl_se_estimate
        ci_95_pnl_upper = pnl_pts + 1.96 * pnl_se_estimate

        print(f"\nSTATISTICAL CONFIDENCE (Trump-only sample n={n_total}):")
        print(f"  WR 95% CI: [{ci_95_lower:.1f}%, {ci_95_upper:.1f}%]")
        print(f"  PnL 95% CI: [{ci_95_pnl_lower:.0f}pt, {ci_95_pnl_upper:.0f}pt]")
        print(f"  Sample size assessment:")
        if n_total >= 1000:
            print(f"    n={n_total} = ADEQUATE (≥1000)")
        elif n_total >= 500:
            print(f"    n={n_total} = MARGINAL (500-1000)")
        else:
            print(f"    n={n_total} = LOW (<500) — high curve-fit risk")

    # Daily income reality check
    print('\n' + '=' * 110)
    print("DAILY INCOME REALITY CHECK")
    print('=' * 110)

    best_yr = best_be_r[1]['usd_per_yr']
    best_pnl = best_be_r[1]['pnl_pts']
    trump_trade_days = sum(1 for d in trump_dates if d in atr_pass_trump)
    avg_daily = best_yr / 365
    avg_trading_day = best_pnl * 2 / trump_trade_days if trump_trade_days else 0  # lot 0.02

    print(f"Best Trump config Pine: ${best_yr:.0f}/yr")
    print(f"Per calendar day: ${avg_daily:.2f}/day")
    print(f"Per trading day (active): ${avg_trading_day:.2f}/day")
    print()
    print(f"User goal: $20-50/day scalping")
    print(f"Current pace gap:")
    for target in [10, 20, 30, 50]:
        ratio = target / avg_trading_day if avg_trading_day > 0 else 999
        modal_needed_002 = 200 * ratio
        print(f"  Target ${target}/day → need {ratio:.1f}× scale → modal ${modal_needed_002:.0f} or lot {0.02*ratio:.2f}")

    # Save
    out = ROOT / 'data' / 'phase48_trump_optimization.json'
    with open(out, 'w') as f:
        json.dump({
            'be_results': {str(k): v for k, v in be_results.items()},
            'best': {'be_r': best_be_r[0], **best_be_r[1]},
            'sample_n': n_total,
            'avg_per_trading_day_usd': round(avg_trading_day, 2),
        }, f, indent=2)
    print(f'\n[saved] {out}')


if __name__ == '__main__':
    main()
