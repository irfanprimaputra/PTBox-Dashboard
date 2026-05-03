"""Simulate adaptive max_attempts rule + stack with macro + chain filters.

Adaptive rule (per Anthia "2L or 1W = stop"):
  Within each (date × session):
    - Walk through trades chronologically
    - Stop session if: cumulative_losses >= 2 OR cumulative_wins >= 1
    - Trades after stop signal = SKIP

Compare 5 variants:
  V0  Baseline (no filter, max 3 attempts)
  V1  Adaptive (max_attempts replaced by 2L-or-1W rule)
  V2  Macro filter only (X-9)
  V3  Adaptive + Macro
  V4  Adaptive + Macro + Chain (full stack)
"""
from pathlib import Path
import pandas as pd
import numpy as np

DATA_DIR = Path(__file__).parent.parent / "data"
TRADES_F = DATA_DIR / "trades_with_filters.csv"

# High-conviction chains (from compute_session_chain.py)
HIGH_CONVICTION_CHAINS = {
    ("TREND_DOWN", "TREND_DOWN", "V_UP"):       "UP",
    ("V_UP",       "TREND_DOWN", "TREND_DOWN"): "UP",
    ("RANGE",      "TREND_UP",   "TREND_UP"):   "DOWN",
    ("RANGE",      "TREND_DOWN", "TREND_UP"):   "DOWN",
    ("TREND_DOWN", "RANGE",      "TREND_DOWN"): "DOWN",
    ("V_DOWN",     "TREND_UP",   "TREND_DOWN"): "DOWN",
    ("TREND_DOWN", "TREND_DOWN", "TREND_UP"):   "UP",
}


def apply_adaptive_max_attempts(trades_df):
    """Per (date, session), walk chronologically.

    Stop if losses >= 2 OR wins >= 1.

    Adds column 'keep_adaptive' = True if trade taken under rule.
    """
    trades_df = trades_df.sort_values(["date", "session", "entry_time"]).reset_index(drop=True)
    trades_df["keep_adaptive"] = False

    for (d, s), group in trades_df.groupby(["date", "session"], sort=False):
        wins = 0
        losses = 0
        for idx in group.index:
            # Decision: take this trade?
            if losses >= 2 or wins >= 1:
                # Stop signal hit, skip
                continue
            # Take the trade
            trades_df.at[idx, "keep_adaptive"] = True
            pnl = trades_df.at[idx, "pnl_pts"]
            if pnl > 0:
                wins += 1
            elif pnl < 0:
                losses += 1
            # zero = neutral, no count change

    return trades_df


def summarize(df, mask_col, label):
    kept = df[df[mask_col]] if mask_col else df
    n = len(df)
    nk = len(kept)
    pnl = kept["pnl_pts"].sum()
    pnl_full = df["pnl_pts"].sum()
    wr = (kept["pnl_pts"] > 0).sum() / nk * 100 if nk else 0
    avg = pnl / nk if nk else 0
    delta = pnl - pnl_full
    pct = delta / abs(pnl_full) * 100 if pnl_full else 0
    return {
        "label": label,
        "n_kept": nk,
        "n_total": n,
        "pnl": pnl,
        "delta": delta,
        "pct": pct,
        "wr": wr,
        "avg": avg,
    }


def print_table(rows, header):
    print(f"\n{'━' * 88}")
    print(f" {header}")
    print(f"{'━' * 88}")
    print(f"  {'Variant':<35} {'Kept':>6}/{'Total':<6}  {'PnL':>9}  {'Delta':>9}  {'WR':>6}  {'Avg':>6}")
    print(f"  {'─' * 35} {'─' * 6} {'─' * 6}  {'─' * 9}  {'─' * 9}  {'─' * 6}  {'─' * 6}")
    for r in rows:
        wr_str = f"{r['wr']:.1f}%"
        delta_str = f"{r['delta']:+.1f}" if r['label'] != "V0 Baseline" else "—"
        pct_str = f"({r['pct']:+.1f}%)" if r['label'] != "V0 Baseline" else ""
        print(f"  {r['label']:<35} {r['n_kept']:>6}/{r['n_total']:<6}  {r['pnl']:>+8.1f}  {delta_str:>9} {pct_str:>10}  {wr_str:>6}  {r['avg']:>+5.2f}")


def main():
    print("═" * 88)
    print(" Adaptive max_attempts Simulation + Filter Stack")
    print(" Rule: stop after 2 losses OR 1 win per (date × session)")
    print("═" * 88)

    df = pd.read_csv(TRADES_F)
    df["date"] = pd.to_datetime(df["date"])
    print(f"\nLoaded: {len(df):,} trades · {df['date'].min().date()} → {df['date'].max().date()}")

    # Apply adaptive max_attempts
    print("\nSimulating adaptive max_attempts (2L-or-1W rule)...")
    df = apply_adaptive_max_attempts(df)
    print(f"  Adaptive rule kept: {df['keep_adaptive'].sum():,} of {len(df):,} ({df['keep_adaptive'].mean() * 100:.1f}%)")

    # Combined columns
    df["keep_v3_adaptive_macro"]       = df["keep_adaptive"] & df["filter_macro_keep"]
    df["keep_v4_adaptive_macro_chain"] = df["keep_adaptive"] & df["filter_macro_keep"] & df["filter_chain_keep"]

    # ─────────────────────────────────────
    # Per-session breakdown
    # ─────────────────────────────────────
    for sess_name in ["Asia", "London", "NY", "ALL"]:
        sub = df.copy() if sess_name == "ALL" else df[df["session"] == sess_name].copy()
        baseline = sub["pnl_pts"].sum()

        rows = [
            {"label": "V0 Baseline", "n_kept": len(sub), "n_total": len(sub), "pnl": baseline, "delta": 0, "pct": 0,
             "wr": (sub["pnl_pts"] > 0).sum() / len(sub) * 100 if len(sub) else 0,
             "avg": baseline / len(sub) if len(sub) else 0},
            summarize(sub, "keep_adaptive",                "V1 Adaptive only"),
            summarize(sub, "filter_macro_keep",            "V2 Macro only"),
            summarize(sub, "keep_v3_adaptive_macro",       "V3 Adaptive + Macro"),
            summarize(sub, "keep_v4_adaptive_macro_chain", "V4 Adaptive + Macro + Chain"),
        ]
        print_table(rows, f"📍 {sess_name}  (n={len(sub):,} trades, baseline {baseline:+.1f} pts)")

    # ─────────────────────────────────────
    # Save updated trades
    # ─────────────────────────────────────
    out = DATA_DIR / "trades_with_filters.csv"
    df.to_csv(out, index=False)
    print(f"\n  Saved updated: {out}")

    # ─────────────────────────────────────
    # Highlight key insight
    # ─────────────────────────────────────
    all_baseline = df["pnl_pts"].sum()
    v4_pnl = df[df["keep_v4_adaptive_macro_chain"]]["pnl_pts"].sum()
    v4_delta = v4_pnl - all_baseline
    print(f"\n{'═' * 88}")
    print(f" 🎯 HEADLINE FULL STACK")
    print(f"{'═' * 88}")
    print(f"   Baseline PnL: {all_baseline:+.1f} pts ({len(df):,} trades, fixed-config)")
    print(f"   V4 Full Stack: {v4_pnl:+.1f} pts ({df['keep_v4_adaptive_macro_chain'].sum():,} kept)")
    print(f"   Δ saved:      {v4_delta:+.1f} pts ({v4_delta / abs(all_baseline) * 100:+.1f}% damage reduction)")


if __name__ == "__main__":
    main()
