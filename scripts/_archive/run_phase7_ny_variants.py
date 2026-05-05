"""Phase 7 NY Recovery — e15 series.

Baseline: e14d (+549 pts) = e013 deploy + Adaptive max_attempts on Asia ONLY
NY currently: -88 pts (biggest drag remaining)

Test variants:
  e15a — NY timing shift: 10:15-11:00 EST (Silver Bullet, Anthia method)
  e15b — NY day-of-week skip: skip Friday NY (positions squaring)
  e15c — NY restrict 09:30-10:30 EST (Anthia First Candle Range window)

Each variant inherits e14d Asia + London config, only NY changes.
"""
import os, sys, json, datetime, time
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT / "scripts"))

from run_engine_with_filters import (
    backtest_filtered, backtest_meanrev_fail_filtered, generate_quarters,
)
from ptbox_quarterly_v3 import CONFIG, load_data, build_date_groups, PATTERN_VARIANTS
from ptbox_quarterly_v4 import ASIA_MEANREV_VARIANTS


# ───────────────────────────────────────────────────────────────────
# 🛡️ Filter functions per variant
# ───────────────────────────────────────────────────────────────────

def filter_allow_all(date, session, direction):
    return True


def filter_skip_friday_ny(date, session, direction):
    if session == "NY" and date.weekday() == 4:  # Friday
        return False
    return True


# ───────────────────────────────────────────────────────────────────
# 🎯 Walk-forward with PER-SESSION custom timing window + filter
# ───────────────────────────────────────────────────────────────────

def _bt_dispatch(variant, date_groups, all_dates, bh, bm, dur, tp1, tp2,
                 allowed_fn, session_name, adaptive=False):
    model = variant.get('model', 'breakout_pullback')
    if model == 'mean_rev_fail':
        return backtest_meanrev_fail_filtered(date_groups, all_dates, bh, bm, dur,
                                               variant, allowed_fn, session_name, adaptive)
    return backtest_filtered(date_groups, all_dates, bh, bm, dur, tp1, tp2,
                             variant, allowed_fn, session_name, adaptive)


def optimize_session_custom_window(date_groups, all_dates, sess_name, variant,
                                     start_min, end_min, allowed_fn, adaptive):
    tps = CONFIG['tp_per_session'][sess_name]
    tp1, tp2 = tps['tp1'], tps['tp2']
    durs = CONFIG['durations']
    step = CONFIG['coarse_step']
    fw = CONFIG['fine_window']

    coarse = []
    for bmt in range(start_min, end_min, step):
        bh = bmt // 60; bm = bmt % 60
        for dur in durs:
            if bmt + dur >= end_min: continue
            r = _bt_dispatch(variant, date_groups, all_dates, bh, bm, dur, tp1, tp2,
                             allowed_fn, sess_name, adaptive)
            if r: coarse.append(r)

    if not coarse: return []
    df_c = pd.DataFrame(coarse)
    top_centers = df_c.nlargest(5, 'pnl')[['bh','bm']].values

    seen = set(); fine = []
    for bh, bm in top_centers:
        center = int(bh)*60 + int(bm)
        for bmt in range(max(start_min, center-fw), min(end_min, center+fw+1)):
            if bmt in seen: continue
            seen.add(bmt)
            fh = bmt//60; fm = bmt%60
            for dur in durs:
                if bmt + dur >= end_min: continue
                r = _bt_dispatch(variant, date_groups, all_dates, fh, fm, dur, tp1, tp2,
                                 allowed_fn, sess_name, adaptive)
                if r: fine.append(r)
    return fine


def walk_forward_with_ny_config(df, ny_window=None, ny_filter=None, ny_adaptive=False, label=""):
    """ny_window: (start_min, end_min) tuple, or None for default 480-720
       ny_filter: filter function or None
       ny_adaptive: bool
    """
    sess_variants = {
        "Asia":   ASIA_MEANREV_VARIANTS["asia_a2_fail"],
        "London": PATTERN_VARIANTS["any_pattern"],
        "NY":     PATTERN_VARIANTS["dyn_sl_tp_baseline"],
    }
    sess_windows = {
        "Asia":   (CONFIG['sessions']['Asia']['start_min'], CONFIG['sessions']['Asia']['end_min']),
        "London": (CONFIG['sessions']['London']['start_min'], CONFIG['sessions']['London']['end_min']),
        "NY":     ny_window if ny_window else (CONFIG['sessions']['NY']['start_min'], CONFIG['sessions']['NY']['end_min']),
    }
    sess_filter = {"Asia": filter_allow_all, "London": filter_allow_all, "NY": ny_filter or filter_allow_all}
    sess_adaptive = {"Asia": True, "London": False, "NY": ny_adaptive}  # e14d baseline: adaptive Asia only

    data_start = df['date_et'].min()
    data_end   = df['date_et'].max()
    quarters   = generate_quarters(data_start, data_end)
    results = []

    for idx, (train_s, train_e, val_s, val_e, qlabel) in enumerate(quarters, 1):
        df_train = df[(df['date_et']>=train_s)&(df['date_et']<=train_e)]
        df_val   = df[(df['date_et']>=val_s)  &(df['date_et']<=val_e)]
        tg, td = build_date_groups(df_train)
        vg, vd = build_date_groups(df_val)
        if len(td) < 15 or len(vd) < 10: continue

        for sess in ['Asia','London','NY']:
            sv = sess_variants[sess]
            sw_start, sw_end = sess_windows[sess]
            sf = sess_filter[sess]
            sa = sess_adaptive[sess]
            fine = optimize_session_custom_window(tg, td, sess, sv, sw_start, sw_end, sf, sa)
            if not fine: continue
            best = max(fine, key=lambda r: r['pnl'])
            tps = CONFIG['tp_per_session'][sess]
            r_val = _bt_dispatch(sv, vg, vd, best['bh'], best['bm'], best['dur'],
                                 tps['tp1'], tps['tp2'], sf, sess, sa)
            val_pnl = r_val['pnl'] if r_val else 0
            val_trades = r_val['trades'] if r_val else 0
            val_wr = r_val['winrate'] if r_val else 0
            results.append({
                'quarter': qlabel, 'session': sess,
                'best_bh': best['bh'], 'best_bm': best['bm'], 'best_dur': best['dur'],
                'val_pnl': val_pnl, 'val_trades': val_trades, 'val_winrate': val_wr,
            })
    return results


def run_variant(label, df, **kwargs):
    print(f"\n{'═' * 72}")
    print(f" {label}")
    print(f"{'═' * 72}")
    t0 = time.time()
    results = walk_forward_with_ny_config(df, label=label, **kwargs)
    elapsed = time.time() - t0
    df_r = pd.DataFrame(results)
    total = df_r["val_pnl"].sum() if len(df_r) else 0
    by_sess = df_r.groupby("session")["val_pnl"].sum() if len(df_r) else pd.Series()

    print(f"  Elapsed: {elapsed:.1f}s")
    print(f"  Total PnL: {total:+.1f} pts (Δ vs e14d +549 = {total - 549:+.1f})")
    for sess in ['Asia','London','NY']:
        v = by_sess.get(sess, 0)
        e14d_ref = {"Asia": 151, "London": 486, "NY": -88}[sess]
        print(f"    {sess:<7} {v:>+8.1f} (e14d ref {e14d_ref:+d}, Δ {v - e14d_ref:+.0f})")
    return {
        "label": label,
        "total": total,
        "by_session": {s: float(by_sess.get(s, 0)) for s in ['Asia','London','NY']},
        "elapsed_s": elapsed,
    }


def main():
    csv = "/Users/irfanprimaputra.b/Downloads/XAUUSD_M1_2021_-_2026.csv"
    df = load_data(csv)

    summaries = []

    # e15a — NY Silver Bullet (10:15-11:00 EST = 615-660 min)
    summaries.append(run_variant(
        "e15a · NY Silver Bullet (10:15-11:00 EST)",
        df, ny_window=(615, 660),
    ))

    # e15b — NY skip Friday (default window, just filter Friday)
    summaries.append(run_variant(
        "e15b · NY skip Friday",
        df, ny_filter=filter_skip_friday_ny,
    ))

    # e15c — NY First Candle Range window (09:30-10:30 EST = 570-630 min)
    summaries.append(run_variant(
        "e15c · NY First Candle Range (09:30-10:30 EST)",
        df, ny_window=(570, 630),
    ))

    # e15d — Combined: Silver Bullet + Friday skip
    summaries.append(run_variant(
        "e15d · NY Silver Bullet + Friday skip",
        df, ny_window=(615, 660), ny_filter=filter_skip_friday_ny,
    ))

    out = ROOT / "data" / "phase7_ny_variants_results.json"
    with open(out, 'w') as f:
        json.dump({
            'generated': datetime.datetime.now().isoformat(),
            'e14d_baseline': 549.0,
            'variants': summaries,
        }, f, indent=2)

    print("\n" + "═" * 72)
    print(" SUMMARY · NY Recovery Variants (vs e14d +549)")
    print("═" * 72)
    print(f"  {'Variant':<55} {'Total':>9} {'Δ e14d':>9} {'NY':>9}")
    print(f"  {'─' * 55} {'─' * 9} {'─' * 9} {'─' * 9}")
    for s in summaries:
        delta = s["total"] - 549
        print(f"  {s['label']:<55} {s['total']:>+8.1f} {delta:>+9.1f} {s['by_session']['NY']:>+9.1f}")
    print(f"\n  e14d reference: +549.0  Asia +151  London +486  NY -88")
    print(f"\n  Saved: {out}")


if __name__ == "__main__":
    main()
