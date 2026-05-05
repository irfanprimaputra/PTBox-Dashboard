"""Phase 7 Variants — decompose filter to find what works.

Tests 4 variants to identify which component regressed London:
  e14a — Macro only (no chain, no adaptive)
  e14b — Adaptive only
  e14c — Per-session: filter ON for NY+Asia, OFF for London
  e14d — Per-session: Adaptive ON for Asia only, raw London/NY
"""
import os, sys, json, datetime, time
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT / "scripts"))

# Reuse all the heavy lifting from run_engine_with_filters
from run_engine_with_filters import (
    HIGH_CONVICTION_CHAINS, build_filter_masks,
    backtest_filtered, backtest_meanrev_fail_filtered,
    optimize_session_filtered, generate_quarters,
    VARIANT_E013_FILTERED,
)
from ptbox_quarterly_v3 import CONFIG, load_data, build_date_groups
from ptbox_quarterly_v4 import ASIA_MEANREV_VARIANTS
from ptbox_quarterly_v3 import PATTERN_VARIANTS


def build_variant_filter(macro_on=True, chain_on=True, sessions_to_filter=("Asia","London","NY")):
    """Build allowed_fn matching variant rules.

    sessions_to_filter: tuple of sessions where filter applies.
        Other sessions: always allowed (no filter).
    """
    macro = pd.read_csv(ROOT / "data" / "macro" / "daily_bias_score.csv")
    macro["date"] = pd.to_datetime(macro["date"]).dt.date
    macro_map = dict(zip(macro["date"], macro["bias_score"]))

    sess = pd.read_csv(ROOT / "data" / "session_behavior.csv")
    sess["date"] = pd.to_datetime(sess["date"]).dt.date
    sess_wide = sess.pivot(index="date", columns="session", values="state")

    chain_pred = {}
    dates_sorted = sorted(sess_wide.index)
    for i, d in enumerate(dates_sorted):
        if i == 0: continue
        prev = dates_sorted[i-1]
        try:
            ny_prev = sess_wide.loc[prev, "NY"]
            asia    = sess_wide.loc[d, "Asia"]
            london  = sess_wide.loc[d, "London"]
            chain_pred[d] = HIGH_CONVICTION_CHAINS.get((ny_prev, asia, london))
        except (KeyError, ValueError):
            chain_pred[d] = None

    def allowed(date, session, direction):
        # If session not in filter list, allow everything
        if session not in sessions_to_filter:
            return True
        if direction == 1:  # long
            if macro_on and macro_map.get(date, 0) <= -1: return False
            if chain_on and session == "NY" and chain_pred.get(date) == "DOWN": return False
        elif direction == -1:  # short
            if macro_on and macro_map.get(date, 0) >= 1: return False
            if chain_on and session == "NY" and chain_pred.get(date) == "UP": return False
        return True

    return allowed


def _bt_dispatch_filtered(variant, date_groups, all_dates, bh, bm, dur, tp1, tp2,
                          allowed_fn, session_name, adaptive=True):
    model = variant.get('model', 'breakout_pullback')
    if model == 'mean_rev_fail':
        return backtest_meanrev_fail_filtered(date_groups, all_dates, bh, bm, dur,
                                               variant, allowed_fn, session_name, adaptive)
    return backtest_filtered(date_groups, all_dates, bh, bm, dur, tp1, tp2,
                             variant, allowed_fn, session_name, adaptive)


def walk_forward_variant(df, variant_def, allowed_fn, adaptive_per_session=None):
    """Run walk-forward. adaptive_per_session: dict like {"Asia": True, "London": False, "NY": True}.
    If None, all True."""
    if adaptive_per_session is None:
        adaptive_per_session = {"Asia": True, "London": True, "NY": True}

    data_start = df['date_et'].min()
    data_end   = df['date_et'].max()
    quarters   = generate_quarters(data_start, data_end)
    results = []

    for idx, (train_s, train_e, val_s, val_e, label) in enumerate(quarters, 1):
        df_train = df[(df['date_et']>=train_s)&(df['date_et']<=train_e)]
        df_val   = df[(df['date_et']>=val_s)  &(df['date_et']<=val_e)]
        tg, td = build_date_groups(df_train)
        vg, vd = build_date_groups(df_val)
        if len(td) < 15 or len(vd) < 10:
            continue

        for sess in ['Asia','London','NY']:
            sv = variant_def['sessions'][sess]
            adaptive = adaptive_per_session.get(sess, True)
            fine = optimize_session_filtered(tg, td, sess, sv, allowed_fn, adaptive)
            if not fine: continue
            best = max(fine, key=lambda r: r['pnl'])
            tps = CONFIG['tp_per_session'][sess]
            r_val = _bt_dispatch_filtered(
                sv, vg, vd, best['bh'], best['bm'], best['dur'],
                tps['tp1'], tps['tp2'], allowed_fn, sess, adaptive,
            )
            val_pnl = r_val['pnl'] if r_val else 0
            val_trades = r_val['trades'] if r_val else 0
            val_wr = r_val['winrate'] if r_val else 0
            results.append({
                'quarter': label, 'session': sess,
                'val_pnl': val_pnl, 'val_trades': val_trades, 'val_winrate': val_wr,
            })
    return results


def run_variant(label, df, allowed_fn, adaptive_per_session, variant_def):
    print(f"\n{'═' * 72}")
    print(f" {label}")
    print(f"{'═' * 72}")
    t0 = time.time()
    results = walk_forward_variant(df, variant_def, allowed_fn, adaptive_per_session)
    elapsed = time.time() - t0
    df_r = pd.DataFrame(results)
    total = df_r["val_pnl"].sum() if len(df_r) else 0
    by_sess = df_r.groupby("session")["val_pnl"].sum() if len(df_r) else pd.Series()

    print(f"  Elapsed: {elapsed:.1f}s")
    print(f"  Total PnL: {total:+.1f} pts (Δ vs e013 +375 = {total - 375:+.1f})")
    for sess in ['Asia','London','NY']:
        v = by_sess.get(sess, 0)
        e013_ref = {"Asia": 24, "London": 468, "NY": -117}[sess]
        print(f"    {sess:<7} {v:>+8.1f} (e013 ref {e013_ref:+d}, Δ {v - e013_ref:+.0f})")
    return {
        "label": label,
        "total": total,
        "by_session": {s: float(by_sess.get(s, 0)) for s in ['Asia','London','NY']},
        "elapsed_s": elapsed,
    }


def main():
    csv = "/Users/irfanprimaputra.b/Downloads/XAUUSD_M1_2021_-_2026.csv"
    print(f"Loading {csv}...")
    df = load_data(csv)
    variant_def = VARIANT_E013_FILTERED

    summaries = []

    # e14a — Macro only (no chain, no adaptive)
    f = build_variant_filter(macro_on=True, chain_on=False, sessions_to_filter=("Asia","London","NY"))
    summaries.append(run_variant("e14a · Macro only (no chain, no adaptive)", df, f,
                                  {"Asia": False, "London": False, "NY": False}, variant_def))

    # e14b — Adaptive only (no macro, no chain)
    f = build_variant_filter(macro_on=False, chain_on=False, sessions_to_filter=())  # no macro/chain skip
    summaries.append(run_variant("e14b · Adaptive only (no macro, no chain)", df, f,
                                  {"Asia": True, "London": True, "NY": True}, variant_def))

    # e14c — Per-session: filter NY+Asia, London raw
    f = build_variant_filter(macro_on=True, chain_on=True, sessions_to_filter=("Asia","NY"))
    summaries.append(run_variant("e14c · Filter on NY+Asia ONLY (London raw)", df, f,
                                  {"Asia": True, "London": False, "NY": True}, variant_def))

    # e14d — Adaptive on Asia only, raw London/NY
    f = build_variant_filter(macro_on=False, chain_on=False, sessions_to_filter=())
    summaries.append(run_variant("e14d · Adaptive on Asia ONLY", df, f,
                                  {"Asia": True, "London": False, "NY": False}, variant_def))

    # Save summary
    out = ROOT / "data" / "phase7_variant_results.json"
    with open(out, 'w') as f:
        json.dump({
            'generated': datetime.datetime.now().isoformat(),
            'e013_baseline': 375.0,
            'variants': summaries,
        }, f, indent=2)

    print("\n" + "═" * 72)
    print(" SUMMARY")
    print("═" * 72)
    print(f"  {'Variant':<48} {'Total':>9} {'Δ e013':>9} {'Asia':>8} {'London':>9} {'NY':>8}")
    print(f"  {'─' * 48} {'─' * 9} {'─' * 9} {'─' * 8} {'─' * 9} {'─' * 8}")
    for s in summaries:
        delta = s["total"] - 375
        print(f"  {s['label']:<48} {s['total']:>+8.1f} {delta:>+9.1f} "
              f"{s['by_session']['Asia']:>+8.1f} {s['by_session']['London']:>+9.1f} {s['by_session']['NY']:>+8.1f}")
    print(f"\n  e013 reference (no filter): +375.0  Asia +24  London +468  NY -117")
    print(f"\n  Saved: {out}")


if __name__ == "__main__":
    main()
