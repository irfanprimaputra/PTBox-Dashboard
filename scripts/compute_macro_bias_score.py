"""Compute daily macro bias score for XAUUSD from 6 sentiment sources.

Score model: -6 to +6 (sum of 6 components, each ±1 or 0).

Component                    | +1                 | -1                 | 0
─────────────────────────────┼────────────────────┼────────────────────┼─────────
DXY direction (5d MA slope)  | down               | up                 | flat
10Y yield direction (5d MA)  | down               | up                 | flat
2Y yield direction (5d MA)   | down               | up                 | flat
VIX level                    | >20                | <15                | 15-20
GLD flow (5d MA slope)       | rising             | falling            | flat
RRP direction (5d trend)     | falling            | rising             | flat

Output: data/macro/daily_bias_score.csv
"""
from pathlib import Path
import pandas as pd
import numpy as np

DATA_DIR = Path(__file__).parent.parent / "data" / "macro"
OUT_FILE = DATA_DIR / "daily_bias_score.csv"

FLAT_THRESHOLD = 0.001  # slope < this = flat


def load_series(file: str, value_col: str) -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / file)
    df["date"] = pd.to_datetime(df["date"])
    df = df[["date", value_col]].dropna().sort_values("date").reset_index(drop=True)
    return df


def slope_5d(series: pd.Series) -> pd.Series:
    """5-day MA slope, sign indicates direction."""
    ma = series.rolling(5, min_periods=3).mean()
    return ma.diff(5) / ma.shift(5)  # 5-day pct change of MA


def directional_score(slope: pd.Series, invert: bool = False) -> pd.Series:
    """slope > threshold = +1 (up), < -threshold = -1 (down), else 0.

    invert=True → flip sign (e.g., DXY up = bad for gold)
    """
    score = pd.Series(0, index=slope.index, dtype=int)
    score[slope > FLAT_THRESHOLD] = 1
    score[slope < -FLAT_THRESHOLD] = -1
    if invert:
        score = -score
    return score


def vix_level_score(vix: pd.Series) -> pd.Series:
    """VIX >20 = +1 (risk-off favors gold), <15 = -1 (complacency), else 0."""
    score = pd.Series(0, index=vix.index, dtype=int)
    score[vix > 20] = 1
    score[vix < 15] = -1
    return score


def main():
    print("═" * 70)
    print(" Compute Macro Daily Bias Score · XAUUSD")
    print("═" * 70)

    # Load each series
    print("\nLoading 6 macro series...")
    dxy   = load_series("dxy_daily.csv", "Close")
    gld   = load_series("gld_daily.csv", "Close")
    y10y  = load_series("us_10y_yield.csv", "yield_10y_pct")
    y2y   = load_series("us_2y_yield.csv", "yield_2y_pct")
    vix   = load_series("vix_daily.csv", "Close")
    rrp   = load_series("rrp_daily.csv", "rrp_billion_usd")

    # Rename for merge
    dxy   = dxy.rename(columns={"Close": "dxy"})
    gld   = gld.rename(columns={"Close": "gld"})
    vix   = vix.rename(columns={"Close": "vix"})

    # Merge on date (outer to keep all dates)
    print("Merging series...")
    df = dxy.merge(gld, on="date", how="outer")
    df = df.merge(y10y, on="date", how="outer")
    df = df.merge(y2y, on="date", how="outer")
    df = df.merge(vix, on="date", how="outer")
    df = df.merge(rrp, on="date", how="outer")
    df = df.sort_values("date").reset_index(drop=True)

    # Forward-fill weekend/holiday gaps (yields, RRP often have gaps)
    df = df.ffill()
    df = df.dropna(subset=["dxy", "gld", "yield_10y_pct", "yield_2y_pct", "vix"])

    print(f"Merged: {len(df):,} rows ({df['date'].min().date()} → {df['date'].max().date()})")

    # Compute slopes
    print("\nComputing 5-day MA slopes...")
    df["dxy_slope"]  = slope_5d(df["dxy"])
    df["gld_slope"]  = slope_5d(df["gld"])
    df["y10y_slope"] = slope_5d(df["yield_10y_pct"])
    df["y2y_slope"]  = slope_5d(df["yield_2y_pct"])
    df["rrp_slope"]  = slope_5d(df["rrp_billion_usd"].fillna(0))

    # Directional scores (each ±1 or 0)
    # DXY UP = bad for gold → invert
    # GLD UP = good for gold → no invert (rising = +1)
    # 10Y UP = bad → invert
    # 2Y UP = bad → invert
    # RRP UP = bad → invert (rising RRP = liquidity withdrawal = USD strong)
    print("Computing directional scores...")
    df["score_dxy"]  = directional_score(df["dxy_slope"], invert=True)
    df["score_gld"]  = directional_score(df["gld_slope"], invert=False)
    df["score_10y"]  = directional_score(df["y10y_slope"], invert=True)
    df["score_2y"]   = directional_score(df["y2y_slope"], invert=True)
    df["score_rrp"]  = directional_score(df["rrp_slope"], invert=True)
    df["score_vix"]  = vix_level_score(df["vix"])

    # Total score
    df["bias_score"] = (
        df["score_dxy"] + df["score_gld"] + df["score_10y"]
        + df["score_2y"] + df["score_rrp"] + df["score_vix"]
    )

    # Bias label
    def label(s):
        if s >= 4: return "STRONG_BULLISH"
        if s >= 1: return "BULLISH_LEAN"
        if s == 0: return "NEUTRAL"
        if s >= -3: return "BEARISH_LEAN"
        return "STRONG_BEARISH"

    df["bias_label"] = df["bias_score"].apply(label)

    # Save
    out_cols = [
        "date", "dxy", "gld", "yield_10y_pct", "yield_2y_pct", "vix", "rrp_billion_usd",
        "score_dxy", "score_gld", "score_10y", "score_2y", "score_rrp", "score_vix",
        "bias_score", "bias_label",
    ]
    df[out_cols].dropna(subset=["bias_score"]).to_csv(OUT_FILE, index=False)

    # Summary stats
    print("\n" + "═" * 70)
    print(" BIAS SCORE DISTRIBUTION (2015-2026)")
    print("═" * 70)
    valid = df.dropna(subset=["bias_score"])
    print(f"Total trading days scored: {len(valid):,}")
    print(f"Mean score:                {valid['bias_score'].mean():+.2f}")
    print(f"Median score:              {int(valid['bias_score'].median()):+d}")

    print("\nLabel distribution:")
    label_counts = valid["bias_label"].value_counts()
    for lbl, cnt in label_counts.items():
        pct = cnt / len(valid) * 100
        print(f"  {lbl:<18} {cnt:>5,} days ({pct:5.1f}%)")

    print("\nScore histogram:")
    hist = valid["bias_score"].value_counts().sort_index()
    max_count = hist.max()
    for score, cnt in hist.items():
        bar = "█" * int(cnt / max_count * 40)
        print(f"  {int(score):+d}  {cnt:>5,} {bar}")

    # Last 10 days sample
    print("\nLast 10 trading days sample:")
    print(valid.tail(10)[["date", "bias_score", "bias_label"]].to_string(index=False))

    print(f"\n  Saved: {OUT_FILE}")


if __name__ == "__main__":
    main()
