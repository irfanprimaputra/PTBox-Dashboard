"""Phase 7 e17 (London) + e18 (Asia) — push pillars belum di-amplify.

London variants (e17): keep e16b NY+Asia, vary London
  e17a — London with stricter pattern (pin_bar only, no inside_bar)
  e17b — London with longer boxes [10, 15, 20] durations
  e17c — London restricted to killzone (02:00-04:00 ET)
  e17d — London with engulfing-only pattern

Asia variants (e18): keep e16b London+NY, vary Asia
  e18a — Asia restricted Tokyo open (19:00-21:00 ET)
  e18b — Asia min_box_width=3 (filter degenerate)
  e18c — Asia min_box_width=5 (stricter)

Each variant inherits e16b base, only target session changes.
"""
import os, sys, json, datetime, time
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT / "scripts"))

from ptbox_quarterly_v3 import CONFIG, load_data, PATTERN_VARIANTS
from ptbox_quarterly_v4 import ASIA_MEANREV_VARIANTS

from run_phase7_e16_naked_forex import (
    walk_forward_e16, base_config,
)


def base_e16b():
    """e16b config: e14d + NY direct + pattern."""
    cfg = base_config()
    cfg["NY"]["model_type"] = "direct_breakout"
    cfg["NY"]["pattern_at_breakout"] = "any"
    return cfg


def run_variant(label, df, cfg):
    print(f"\n{'═' * 72}")
    print(f" {label}")
    print(f"{'═' * 72}")
    t0 = time.time()
    results = walk_forward_e16(df, cfg)
    elapsed = time.time() - t0
    df_r = pd.DataFrame(results)
    total = df_r["val_pnl"].sum() if len(df_r) else 0
    by_sess = df_r.groupby("session")["val_pnl"].sum() if len(df_r) else pd.Series()

    df_r["q_year"] = df_r["quarter"].str[:4].astype(int)
    recent = df_r[df_r["q_year"] >= 2024]
    recent_total = recent["val_pnl"].sum() if len(recent) else 0
    recent_by_sess = recent.groupby("session")["val_pnl"].sum() if len(recent) else pd.Series()

    print(f"  Elapsed: {elapsed:.1f}s")
    print(f"  19Q (5y): {total:+.1f} (Δ vs e16b +945 = {total - 945:+.1f})")
    for sess in ['Asia','London','NY']:
        v = by_sess.get(sess, 0)
        e16b_ref = {"Asia": 151, "London": 486, "NY": 308}[sess]
        print(f"    {sess:<7} {v:>+8.1f} (e16b ref {e16b_ref:+d}, Δ {v - e16b_ref:+.0f})")
    print(f"  Recent (2024+): {recent_total:+.1f}")
    return {
        "label": label, "total_19q": total, "total_recent": recent_total,
        "by_session": {s: float(by_sess.get(s, 0)) for s in ['Asia','London','NY']},
        "recent_by_session": {s: float(recent_by_sess.get(s, 0)) for s in ['Asia','London','NY']},
    }


def make_pattern_variant(base_variant, pattern_filter):
    v = dict(base_variant)
    v["pattern_filter"] = pattern_filter
    return v


def main():
    csv = "/Users/irfanprimaputra.b/Downloads/XAUUSD_M1_2021_-_2026.csv"
    df = load_data(csv)
    summaries = []

    # ─── LONDON variants (e17) ───
    # e17a: London pin_bar only (stricter)
    cfg = base_e16b()
    cfg["London"]["variant"] = make_pattern_variant(PATTERN_VARIANTS["pin_bar_only"], "pin_bar")
    summaries.append(run_variant("e17a · London pin_bar only", df, cfg))

    # e17b: London engulfing only
    cfg = base_e16b()
    cfg["London"]["variant"] = make_pattern_variant(PATTERN_VARIANTS["engulfing_only"], "engulfing")
    summaries.append(run_variant("e17b · London engulfing only", df, cfg))

    # e17c: London killzone (02:00-04:00 ET = 120-240 min)
    cfg = base_e16b()
    cfg["London"]["window"] = (120, 240)
    summaries.append(run_variant("e17c · London killzone 02:00-04:00 ET", df, cfg))

    # e17d: London direct breakout + pattern (test if combo works)
    cfg = base_e16b()
    cfg["London"]["model_type"] = "direct_breakout"
    cfg["London"]["pattern_at_breakout"] = "any"
    summaries.append(run_variant("e17d · London direct + pattern-at-breakout", df, cfg))

    # ─── ASIA variants (e18) ───
    # e18a: Asia Tokyo open only (19:00-21:00 ET = 1140-1260 min)
    cfg = base_e16b()
    cfg["Asia"]["window"] = (1140, 1260)
    summaries.append(run_variant("e18a · Asia Tokyo open only (19:00-21:00 ET)", df, cfg))

    # e18b: Asia min_box_width=3
    cfg = base_e16b()
    asia_v = dict(ASIA_MEANREV_VARIANTS["asia_a2_fail"])
    asia_v["min_box_width"] = 3.0
    cfg["Asia"]["variant"] = asia_v
    summaries.append(run_variant("e18b · Asia min_box_width=3", df, cfg))

    # e18c: Asia min_box_width=5 (stricter)
    cfg = base_e16b()
    asia_v = dict(ASIA_MEANREV_VARIANTS["asia_a2_fail"])
    asia_v["min_box_width"] = 5.0
    cfg["Asia"]["variant"] = asia_v
    summaries.append(run_variant("e18c · Asia min_box_width=5", df, cfg))

    out = ROOT / "data" / "phase7_e17_e18_results.json"
    with open(out, 'w') as f:
        json.dump({
            'generated': datetime.datetime.now().isoformat(),
            'e16b_baseline': 945.0,
            'variants': summaries,
        }, f, indent=2)

    print("\n" + "═" * 72)
    print(" SUMMARY · e17 (London) + e18 (Asia) — vs e16b +945")
    print("═" * 72)
    print(f"  {'Variant':<55} {'19Q':>9} {'Recent24+':>11} {'Δ e16b':>9}")
    print(f"  {'─' * 55} {'─' * 9} {'─' * 11} {'─' * 9}")
    for s in summaries:
        delta = s["total_19q"] - 945
        print(f"  {s['label']:<55} {s['total_19q']:>+8.1f} {s['total_recent']:>+10.1f} {delta:>+8.1f}")
    print(f"\n  e16b baseline: 19Q +945, recent24 +797")
    print(f"  Saved: {out}")


if __name__ == "__main__":
    main()
