"""Apply combined filters to PT Box historical trades.

Tests:
  Filter A — Macro Bias Score (X-9): skip counter-bias trades
  Filter B — Session State Chain: skip trades against predicted session state
  Filter C — Combined (A + B): both must agree

For each trade in ptbox_v6_trades.csv:
  1. Lookup macro bias score for that date
  2. Lookup session state chain prediction
  3. Mark trade as KEEP / SKIP per filter
  4. Compute filtered PnL + WR vs baseline
"""
from pathlib import Path
import pandas as pd
import numpy as np

DATA_DIR = Path(__file__).parent.parent / "data"
TRADES = DATA_DIR / "ptbox_v6_trades.csv"
MACRO  = DATA_DIR / "macro" / "daily_bias_score.csv"
SESS   = DATA_DIR / "session_behavior.csv"

# Predictive signal: chains with WR > 50% at top NY outcome (from chain analysis)
# Format: (chain_prefix) → predicted_direction
HIGH_CONVICTION_CHAINS = {
    # NY[t-1] → Asia[t] → London[t] → predicted next NY direction
    ("TREND_DOWN", "TREND_DOWN", "V_UP"):       "UP",     # 63.6%
    ("V_UP",       "TREND_DOWN", "TREND_DOWN"): "UP",     # 60.0%
    ("RANGE",      "TREND_UP",   "TREND_UP"):   "DOWN",   # 58.8%
    ("RANGE",      "TREND_DOWN", "TREND_UP"):   "DOWN",   # 50.0%
    ("TREND_DOWN", "RANGE",      "TREND_DOWN"): "DOWN",   # 50.0%
    ("V_DOWN",     "TREND_UP",   "TREND_DOWN"): "DOWN",   # 50.0%
    ("TREND_DOWN", "TREND_DOWN", "TREND_UP"):   "UP",     # 50.0%
}


def load_data():
    print("Loading trades, macro, session behavior...")
    trades = pd.read_csv(TRADES)
    trades["date"] = pd.to_datetime(trades["date"])

    macro = pd.read_csv(MACRO)
    macro["date"] = pd.to_datetime(macro["date"])
    macro = macro[["date", "bias_score", "bias_label"]]

    sess = pd.read_csv(SESS)
    sess["date"] = pd.to_datetime(sess["date"])

    # Pivot session state to wide
    sess_wide = sess.pivot(index="date", columns="session", values="state").reset_index()
    sess_wide.columns.name = None
    sess_wide = sess_wide.sort_values("date").reset_index(drop=True)
    sess_wide["NY_prev"] = sess_wide["NY"].shift(1)

    print(f"  trades: {len(trades):,} | macro: {len(macro):,} | sess: {len(sess_wide):,}")
    return trades, macro, sess_wide


def apply_macro_filter(trades_macro):
    """Filter A: Skip if direction counter to macro bias.
    Score >= +1 → skip SHORT trades
    Score <= -1 → skip LONG trades
    """
    def keep(row):
        if pd.isna(row["bias_score"]):
            return True  # no data, keep
        s = row["bias_score"]
        d = row["direction"]
        if s >= 1 and d == "short":
            return False
        if s <= -1 and d == "long":
            return False
        return True

    trades_macro["filter_macro_keep"] = trades_macro.apply(keep, axis=1)
    return trades_macro


def apply_chain_filter(trades_full):
    """Filter B: Skip if direction counter to inter-session chain prediction.
    Only triggers for NY trades when chain matches HIGH_CONVICTION_CHAINS.
    Other sessions: keep all (no chain prediction available).
    """
    def keep(row):
        if row["session"] != "NY":
            return True  # only NY chain predicts NY direction
        chain = (row.get("NY_prev"), row.get("Asia"), row.get("London"))
        if pd.isna(chain[0]) or pd.isna(chain[1]) or pd.isna(chain[2]):
            return True
        pred = HIGH_CONVICTION_CHAINS.get(chain)
        if pred is None:
            return True  # no high-conviction signal → keep
        d = row["direction"]
        # Pred=UP, direction=long → keep | pred=DOWN, direction=short → keep | else skip
        if pred == "UP" and d == "short":
            return False
        if pred == "DOWN" and d == "long":
            return False
        return True

    trades_full["filter_chain_keep"] = trades_full.apply(keep, axis=1)
    return trades_full


def summarize(trades, mask, label):
    kept = trades[mask]
    skipped = trades[~mask]
    n_total = len(trades)
    n_kept = len(kept)
    n_skip = len(skipped)
    pnl_kept = kept["pnl_pts"].sum()
    pnl_skip = skipped["pnl_pts"].sum()
    pnl_full = trades["pnl_pts"].sum()
    wr_kept = (kept["pnl_pts"] > 0).sum() / n_kept * 100 if n_kept else 0
    wr_full = (trades["pnl_pts"] > 0).sum() / n_total * 100 if n_total else 0
    avg_full = pnl_full / n_total if n_total else 0
    avg_kept = pnl_kept / n_kept if n_kept else 0

    print(f"\n  {label}")
    print(f"    Trades:    {n_kept:>5} kept / {n_skip:>5} skipped (of {n_total})")
    print(f"    PnL kept:  {pnl_kept:>+8.1f} pts  (was {pnl_full:+.1f} unfiltered)")
    print(f"    PnL skip:  {pnl_skip:>+8.1f} pts  (avoided)")
    print(f"    Δ vs full: {pnl_kept - pnl_full:>+8.1f} pts  ({(pnl_kept - pnl_full) / abs(pnl_full) * 100 if pnl_full else 0:+.1f}%)")
    print(f"    WR:        {wr_kept:>5.1f}%  (was {wr_full:.1f}%)")
    print(f"    Avg/trade: {avg_kept:>+5.2f}  (was {avg_full:+.2f})")
    return {
        "label": label,
        "n_kept": n_kept,
        "n_skip": n_skip,
        "pnl_kept": pnl_kept,
        "pnl_skip": pnl_skip,
        "wr_kept": wr_kept,
        "delta_vs_full": pnl_kept - pnl_full,
    }


def main():
    print("═" * 72)
    print(" Apply Filters to PT Box Historical Trades")
    print("═" * 72)

    trades, macro, sess = load_data()

    # Merge
    print("\nMerging trades + macro + session state...")
    df = trades.merge(macro, on="date", how="left")
    df = df.merge(sess[["date", "Asia", "London", "NY", "NY_prev"]], on="date", how="left")
    print(f"  Merged: {len(df):,} trades")
    print(f"  With macro bias data: {df['bias_score'].notna().sum():,}")
    print(f"  With session chain data: {df['NY_prev'].notna().sum():,}")

    # Apply filters
    df = apply_macro_filter(df)
    df = apply_chain_filter(df)

    # Combined filter
    df["filter_both_keep"] = df["filter_macro_keep"] & df["filter_chain_keep"]

    # ─────────────────────────────────────────────────────────────
    print("\n" + "═" * 72)
    print(" RESULTS — Filter Performance vs Unfiltered Baseline")
    print("═" * 72)

    results = []
    for sess_name in ["Asia", "London", "NY", "ALL"]:
        if sess_name == "ALL":
            sub = df.copy()
        else:
            sub = df[df["session"] == sess_name].copy()

        print(f"\n{'━' * 72}")
        print(f"📍 SESSION: {sess_name}  (n={len(sub):,} trades)")
        print(f"{'━' * 72}")
        print(f"  Baseline (no filter): PnL = {sub['pnl_pts'].sum():+.1f} pts, "
              f"WR = {(sub['pnl_pts'] > 0).sum() / len(sub) * 100:.1f}%")

        results.append(summarize(sub, sub["filter_macro_keep"], f"FILTER A · Macro Bias"))
        results.append(summarize(sub, sub["filter_chain_keep"], f"FILTER B · Session Chain"))
        results.append(summarize(sub, sub["filter_both_keep"], f"FILTER A+B · Both"))

    # Save filter outcomes
    out_file = DATA_DIR / "trades_with_filters.csv"
    df.to_csv(out_file, index=False)
    print(f"\n  Saved: {out_file}")


if __name__ == "__main__":
    main()
