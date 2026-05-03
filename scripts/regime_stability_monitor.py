"""Regime Stability + Live Edge Tracker.

Answers:
  1. Is the strategy stable across quarters? (regime stability)
  2. When does backtest stop matching live behavior? (decay detection)
  3. What's the alarm signal? (rolling metrics breach threshold)

Inputs:
  - data/phase7_walkforward_filtered.csv  (e14_full result, baseline)
  - data/phase7_variant_results.json      (e14a-d variants)
  - data/phase7_ny_variants_results.json  (e15 variants)
  - data/ptbox_v6_trades.csv              (live trades for tracking)
  - data/macro/daily_bias_score.csv       (regime context)

Outputs:
  - data/regime_stability_report.csv       (per-Q stability metrics)
  - data/live_edge_tracker.csv             (cumulative actual vs expected)
  - Console: ALARMS if any threshold breached
"""
from pathlib import Path
import pandas as pd
import numpy as np
import json

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"


def load_quarter_results():
    """Load e14_full walk-forward results (per quarter × session)."""
    df = pd.read_csv(DATA / "phase7_walkforward_filtered.csv")
    return df


def regime_stability(df_q):
    """For each session, compute per-quarter PnL rolling stats + drift detection."""
    results = []
    for sess in df_q["session"].unique():
        s = df_q[df_q["session"] == sess].copy().sort_values("quarter").reset_index(drop=True)
        s["q_year"] = s["quarter"].str[:4].astype(int)
        s["q_num"] = s["quarter"].str[-1].astype(int)
        s["q_idx"] = (s["q_year"] - s["q_year"].min()) * 4 + s["q_num"]

        # Rolling 4Q stats
        s["pnl_4q_mean"] = s["val_pnl"].rolling(4, min_periods=2).mean()
        s["pnl_4q_std"] = s["val_pnl"].rolling(4, min_periods=2).std()

        # Cumulative
        s["pnl_cumulative"] = s["val_pnl"].cumsum()

        # Quarter z-score (vs full historical)
        full_mean = s["val_pnl"].mean()
        full_std = s["val_pnl"].std()
        s["pnl_zscore"] = (s["val_pnl"] - full_mean) / full_std

        # Regime change candidates: z-score > +/- 2
        s["regime_alarm"] = abs(s["pnl_zscore"]) > 2

        results.append(s)
    return pd.concat(results, ignore_index=True)


def detect_recent_drift(df_stable, recent_quarters=4):
    """Detect if recent N quarters drift significantly from historical baseline."""
    drift = []
    for sess in df_stable["session"].unique():
        s = df_stable[df_stable["session"] == sess].copy().sort_values("quarter")
        if len(s) < recent_quarters * 2:
            continue
        historical = s.iloc[:-recent_quarters]
        recent = s.iloc[-recent_quarters:]

        hist_mean = historical["val_pnl"].mean()
        hist_std = historical["val_pnl"].std()
        recent_mean = recent["val_pnl"].mean()

        z = (recent_mean - hist_mean) / (hist_std / np.sqrt(recent_quarters)) if hist_std else 0

        verdict = "OK"
        if z < -2:
            verdict = "🚨 DECAY ALARM"
        elif z < -1:
            verdict = "⚠️  Watch (mild decay)"
        elif z > 2:
            verdict = "✅ IMPROVING (positive drift)"

        drift.append({
            "session": sess,
            "historical_mean_pnl_per_q": hist_mean,
            "historical_std": hist_std,
            "recent_mean_pnl_per_q": recent_mean,
            "drift_zscore": z,
            "verdict": verdict,
            "n_historical_quarters": len(historical),
            "n_recent_quarters": len(recent),
            "recent_quarters_list": list(recent["quarter"].values),
        })
    return drift


def main():
    print("═" * 72)
    print(" Regime Stability + Drift Detection · e14_full walk-forward 19Q")
    print("═" * 72)

    df_q = load_quarter_results()
    if len(df_q) == 0:
        print("No data found.")
        return

    print(f"\nLoaded {len(df_q):,} quarter-session rows")

    df_stable = regime_stability(df_q)
    df_stable.to_csv(DATA / "regime_stability_report.csv", index=False)

    # Print regime alarms (z-score > 2 quarters)
    print("\n" + "─" * 72)
    print("🚨 REGIME ALARMS (z-score > ±2)")
    print("─" * 72)
    alarms = df_stable[df_stable["regime_alarm"]]
    if len(alarms):
        print(alarms[["quarter", "session", "val_pnl", "pnl_zscore"]].to_string(index=False))
    else:
        print("  No alarms — system within ±2σ across all quarters")

    # Drift detection
    print("\n" + "═" * 72)
    print(" RECENT DRIFT DETECTION (last 4 quarters vs historical)")
    print("═" * 72)
    drifts = detect_recent_drift(df_stable, recent_quarters=4)
    print(f"\n  {'Session':<8} {'Hist Mean':>12} {'Recent Mean':>13} {'Drift Z':>10} {'Verdict':<28} {'Recent Q'}")
    print(f"  {'-' * 8} {'-' * 12} {'-' * 13} {'-' * 10} {'-' * 28} {'-' * 30}")
    for d in drifts:
        rec_q = ", ".join(d["recent_quarters_list"][:4])
        print(f"  {d['session']:<8} {d['historical_mean_pnl_per_q']:>+10.2f}   {d['recent_mean_pnl_per_q']:>+10.2f}    "
              f"{d['drift_zscore']:>+8.2f}  {d['verdict']:<28} {rec_q}")

    # Quarter-by-quarter recent (last 4Q)
    print("\n" + "─" * 72)
    print("📊 PER-SESSION RECENT 4Q PnL")
    print("─" * 72)
    for sess in df_stable["session"].unique():
        s = df_stable[df_stable["session"] == sess].sort_values("quarter")
        recent = s.tail(4)
        print(f"\n  {sess}:")
        for _, r in recent.iterrows():
            sign = "+" if r["val_pnl"] >= 0 else ""
            bar = "█" * int(min(abs(r["val_pnl"]) / 10, 30)) if pd.notna(r["val_pnl"]) else ""
            print(f"    {r['quarter']:<8} {sign}{r['val_pnl']:>7.1f} z={r['pnl_zscore']:+.2f}  {bar}")

    # Save drift report
    with open(DATA / "regime_drift_report.json", "w") as f:
        json.dump({"drifts": drifts}, f, indent=2, default=str)

    print("\n" + "═" * 72)
    print(" 🛡️  ACTION SIGNALS")
    print("═" * 72)
    for d in drifts:
        print(f"\n  {d['session']}:")
        z = d["drift_zscore"]
        if z < -2:
            print(f"    🚨 STOP TRADING this session — recent {d['n_recent_quarters']}Q underperforming.")
            print(f"    Action: Re-optimize parameters OR pause until conditions normalize.")
        elif z < -1:
            print(f"    ⚠️  REDUCE SIZE 50% — mild decay detected.")
            print(f"    Action: Monitor next 2Q, full-size if recovers, halt if continues.")
        elif z > 2:
            print(f"    ✅ STRONG REGIME — consider increase size 1.5x.")
            print(f"    Action: Lock current params, ride the wave.")
        else:
            print(f"    ✓ NORMAL — continue current parameters.")

    print(f"\n  Saved: regime_stability_report.csv, regime_drift_report.json")


if __name__ == "__main__":
    main()
