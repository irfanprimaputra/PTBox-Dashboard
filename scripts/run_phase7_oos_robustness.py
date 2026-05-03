"""Phase 7 OOS Robustness Test — TRUE out-of-sample validation.

Method:
  1. Optimize e16b config on 2021-2023 ONLY (train period, ~3 yrs)
  2. LOCK parameters per session
  3. Apply locked params to 2024-2026 (pure unseen test, ~2.3 yrs)
  4. Compare locked-static OOS PnL vs walk-forward dynamic PnL

If locked static OOS still positive AND consistent with walk-forward
→ real edge, robust to regime
If locked static OOS regresses massively
→ walk-forward was masking via re-optimization (overfit signal)
"""
import os, sys, json, datetime, time
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT / "scripts"))

from ptbox_quarterly_v3 import CONFIG, load_data, build_date_groups, PATTERN_VARIANTS
from ptbox_quarterly_v4 import ASIA_MEANREV_VARIANTS

from run_phase7_e16_naked_forex import (
    backtest_direct_breakout, _bt_dispatch, optimize_session,
    filter_allow_all, base_config,
)

TRAIN_END = datetime.date(2023, 12, 31)
TEST_START = datetime.date(2024, 1, 1)


def optimize_locked_params(df_train, sess_config):
    """Optimize once on full train period, return best params per session."""
    print("\n  Optimizing on TRAIN (2021-2023)...")
    tg, td = build_date_groups(df_train)
    locked = {}
    for sess in ["Asia", "London", "NY"]:
        cfg = sess_config[sess]
        fine = optimize_session(
            tg, td, sess, cfg["variant"], cfg["model_type"], cfg["window"],
            filter_allow_all, cfg["adaptive"], cfg.get("pattern_at_breakout"),
        )
        if not fine:
            print(f"    {sess}: NO valid params"); locked[sess] = None
            continue
        best = max(fine, key=lambda r: r["pnl"])
        locked[sess] = {
            "bh": best["bh"], "bm": best["bm"], "dur": best["dur"],
            "train_pnl": best["pnl"], "train_trades": best.get("trades"), "train_wr": best.get("winrate"),
        }
        print(f"    {sess}: bh={best['bh']:>2} bm={best['bm']:>2} dur={best['dur']} "
              f"train_pnl={best['pnl']:+.1f} trades={best.get('trades')} wr={best.get('winrate')}%")
    return locked


def apply_locked_to_test(df_test, locked, sess_config):
    """Apply locked params to test period — STATIC, no re-optimization."""
    print("\n  Applying LOCKED params to TEST (2024-2026)...")
    tg, td = build_date_groups(df_test)
    results = {}
    for sess in ["Asia", "London", "NY"]:
        if locked.get(sess) is None: continue
        cfg = sess_config[sess]
        p = locked[sess]
        tps = CONFIG["tp_per_session"][sess]
        r = _bt_dispatch(
            cfg["model_type"], cfg["variant"], tg, td,
            p["bh"], p["bm"], p["dur"], tps["tp1"], tps["tp2"],
            filter_allow_all, sess, cfg["adaptive"], cfg.get("pattern_at_breakout"),
        )
        if r:
            results[sess] = {
                "test_pnl": r["pnl"], "test_trades": r["trades"], "test_wr": r["winrate"],
                **p,
            }
            print(f"    {sess}: test_pnl={r['pnl']:+.1f} trades={r['trades']} wr={r['winrate']}%")
        else:
            print(f"    {sess}: NO valid trades")
    return results


def compare_oos_vs_walkforward(oos_results, walkforward_recent):
    """Side-by-side comparison."""
    print("\n" + "═" * 72)
    print(" OOS vs WALK-FORWARD (recent 2024+) COMPARISON")
    print("═" * 72)
    print(f"\n  {'Session':<8} {'Locked OOS':>14} {'WF Recent':>14} {'Δ':>10} {'Verdict'}")
    print(f"  {'-' * 8} {'-' * 14} {'-' * 14} {'-' * 10} {'-' * 30}")
    for sess in ["Asia", "London", "NY"]:
        oos = oos_results.get(sess, {}).get("test_pnl", 0)
        wf = walkforward_recent.get(sess, 0)
        delta = oos - wf
        verdict = "✅ ROBUST" if oos >= 0 and abs(delta) < abs(wf) * 0.5 else (
            "⚠️ DECAY" if oos < wf and oos < 0 else "✓ OK"
        )
        print(f"  {sess:<8} {oos:>+12.1f}    {wf:>+12.1f}    {delta:>+8.1f}    {verdict}")
    total_oos = sum(r.get("test_pnl", 0) for r in oos_results.values())
    total_wf = sum(walkforward_recent.values())
    print(f"  {'TOTAL':<8} {total_oos:>+12.1f}    {total_wf:>+12.1f}    {total_oos - total_wf:>+8.1f}")
    return total_oos, total_wf


def main():
    print("═" * 72)
    print(" Phase 7 OOS Robustness Test · e16b config locked on 2021-2023")
    print("═" * 72)

    csv = "/Users/irfanprimaputra.b/Downloads/XAUUSD_M1_2021_-_2026.csv"
    df = load_data(csv)
    df_train = df[df["date_et"] <= TRAIN_END].copy()
    df_test  = df[df["date_et"] >= TEST_START].copy()
    print(f"\n  Train: {df_train['date_et'].min()} → {df_train['date_et'].max()}  ({len(df_train):,} bars)")
    print(f"  Test:  {df_test['date_et'].min()} → {df_test['date_et'].max()}  ({len(df_test):,} bars)")

    # e16b config
    cfg = base_config()
    cfg["NY"]["model_type"] = "direct_breakout"
    cfg["NY"]["pattern_at_breakout"] = "any"

    locked = optimize_locked_params(df_train, cfg)
    oos_results = apply_locked_to_test(df_test, locked, cfg)

    # Walk-forward recent reference (from e16b run)
    wf_recent = {"Asia": 141.8, "London": 468.0, "NY": 186.9}  # from e16b recent 2y
    total_oos, total_wf = compare_oos_vs_walkforward(oos_results, wf_recent)

    print("\n" + "═" * 72)
    print(" 🎯 OOS ROBUSTNESS VERDICT")
    print("═" * 72)
    if total_oos > 0:
        retention = total_oos / total_wf * 100 if total_wf > 0 else 0
        print(f"\n  ✅ LOCKED STATIC OOS: {total_oos:+.1f} pts (vs walk-forward dynamic {total_wf:+.1f})")
        print(f"  Retention: {retention:.1f}% of walk-forward signal preserved without re-optimization")
        if retention >= 60:
            print(f"  → REAL EDGE — strategy survives without per-quarter re-tuning")
        elif retention >= 30:
            print(f"  → MODERATE — walk-forward adds value, static still positive")
        else:
            print(f"  → WEAK — most edge comes from re-optimization, not static rules")
    else:
        print(f"\n  ⚠️  LOCKED STATIC OOS: {total_oos:+.1f} pts (NEGATIVE)")
        print(f"  Strategy fails when not re-tuned per quarter.")
        print(f"  → STRONG OVERFIT EVIDENCE — walk-forward masks via adaptive timing")

    # Save
    out = {
        "generated": datetime.datetime.now().isoformat(),
        "train_period": [str(df_train["date_et"].min()), str(df_train["date_et"].max())],
        "test_period": [str(df_test["date_et"].min()), str(df_test["date_et"].max())],
        "locked_params": {k: v for k, v in locked.items() if v},
        "oos_results": oos_results,
        "walkforward_recent_reference": wf_recent,
        "total_oos": total_oos,
        "total_walkforward_recent": total_wf,
    }
    with open(ROOT / "data" / "phase7_oos_robustness.json", "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\n  Saved: data/phase7_oos_robustness.json")


if __name__ == "__main__":
    main()
