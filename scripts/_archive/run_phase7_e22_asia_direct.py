"""Phase 7 e22 — Test Asia direct breakout model (mirror NY win mechanism).

Hypothesis: Asia mean-rev ceiling ~+182. NY went -117 → +308 with direct
breakout + pattern-at-breakout. Test if Asia gets similar boost.

Variants:
  e22a — Asia direct breakout, full window 19-23 ET, NO pattern
  e22b — Asia direct breakout, full window, + pattern-at-breakout (mirror NY)
  e22c — Asia direct breakout, late 21-23 ET, + pattern (combine e20d window)
  e22d — Asia direct breakout, Tokyo open 19-21 ET, + pattern (test early window)
"""
import os, sys, json, datetime, time
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT / "scripts"))

from ptbox_quarterly_v3 import CONFIG, load_data, PATTERN_VARIANTS

from run_phase7_e16_naked_forex import walk_forward_e16, base_config


def run_variant(label, df, asia_model, asia_window, asia_pattern=None):
    cfg = base_config()
    # Asia override
    cfg["Asia"]["model_type"] = asia_model
    cfg["Asia"]["window"] = asia_window
    cfg["Asia"]["adaptive"] = False  # direct breakout doesn't use adaptive
    if asia_pattern:
        cfg["Asia"]["pattern_at_breakout"] = asia_pattern
    cfg["Asia"]["variant"] = PATTERN_VARIANTS["dyn_sl_tp_baseline"]  # use breakout config
    # NY (e16b winner)
    cfg["NY"]["model_type"] = "direct_breakout"
    cfg["NY"]["pattern_at_breakout"] = "any"

    print(f"\n{'═' * 72}\n {label}\n Asia: model={asia_model}, window={asia_window}, pattern={asia_pattern}\n{'═' * 72}")
    t0 = time.time()
    results = walk_forward_e16(df, cfg)
    elapsed = time.time() - t0
    df_r = pd.DataFrame(results)
    total = df_r["val_pnl"].sum() if len(df_r) else 0
    by_sess = df_r.groupby("session")["val_pnl"].sum() if len(df_r) else pd.Series()
    df_r["q_year"] = df_r["quarter"].str[:4].astype(int)
    recent = df_r[df_r["q_year"] >= 2024]
    recent_total = recent["val_pnl"].sum() if len(recent) else 0
    asia_pnl = by_sess.get("Asia", 0)
    print(f"  Elapsed: {elapsed:.1f}s")
    print(f"  Total 19Q: {total:+.1f} (Δ vs e20d +976 = {total - 976:+.1f})")
    print(f"  Asia      {asia_pnl:>+8.1f} (e20d ref +182, Δ {asia_pnl - 182:+.0f}) ⭐")
    print(f"  London    {by_sess.get('London', 0):>+8.1f}")
    print(f"  NY        {by_sess.get('NY', 0):>+8.1f}")
    print(f"  Recent 24+: {recent_total:+.1f}")
    return {"label": label, "total_19q": total, "asia_pnl": float(asia_pnl),
            "asia_delta_e20d": float(asia_pnl - 182),
            "total_recent": recent_total,
            "by_session": {s: float(by_sess.get(s, 0)) for s in ['Asia','London','NY']}}


def main():
    csv = "/Users/irfanprimaputra.b/Downloads/XAUUSD_M1_2021_-_2026.csv"
    df = load_data(csv)
    summaries = []

    FULL_WIN = (1140, 1380)   # 19:00-23:00 ET
    LATE_WIN = (1260, 1380)   # 21:00-23:00 ET
    TOKYO_WIN = (1140, 1260)  # 19:00-21:00 ET

    # e22a — Asia direct breakout, full window, NO pattern
    summaries.append(run_variant("e22a · Asia direct breakout (full window, no pattern)",
                                  df, "direct_breakout", FULL_WIN, asia_pattern=None))

    # e22b — Asia direct breakout, full window, + pattern (mirror NY win)
    summaries.append(run_variant("e22b · Asia direct + pattern-at-breakout (full window)",
                                  df, "direct_breakout", FULL_WIN, asia_pattern="any"))

    # e22c — Asia direct breakout, late 21-23 ET, + pattern
    summaries.append(run_variant("e22c · Asia direct + pattern (late 21-23 ET)",
                                  df, "direct_breakout", LATE_WIN, asia_pattern="any"))

    # e22d — Asia direct breakout, Tokyo open 19-21 ET, + pattern
    summaries.append(run_variant("e22d · Asia direct + pattern (Tokyo open 19-21 ET)",
                                  df, "direct_breakout", TOKYO_WIN, asia_pattern="any"))

    out = ROOT / "data" / "phase7_e22_results.json"
    with open(out, 'w') as f:
        json.dump({'generated': datetime.datetime.now().isoformat(),
                   'e20d_baseline_asia': 182.0, 'target_asia': 300.0,
                   'variants': summaries}, f, indent=2)

    print("\n" + "═" * 72)
    print(" SUMMARY · e22 Asia Direct Breakout (target +300)")
    print("═" * 72)
    print(f"  {'Variant':<55} {'Asia':>9} {'Δ e20d':>9} {'19Q':>9}")
    print(f"  {'─' * 55} {'─' * 9} {'─' * 9} {'─' * 9}")
    for s in summaries:
        ok = "⭐" if s["asia_pnl"] >= 300 else ("✅" if s["asia_delta_e20d"] > 0 else "❌")
        print(f"  {s['label']:<55} {s['asia_pnl']:>+8.1f} {s['asia_delta_e20d']:>+9.1f} {s['total_19q']:>+8.1f} {ok}")
    print(f"\n  Saved: {out}")


if __name__ == "__main__":
    main()
