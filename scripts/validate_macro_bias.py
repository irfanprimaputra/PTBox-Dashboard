"""Sanity-check: does macro bias score predict next-day XAUUSD direction?

Pull XAU/USD daily price (GC=F gold futures), correlate with bias_score.
If high score → high prob of next-day positive return → model is real.
"""
from pathlib import Path
import pandas as pd
import yfinance as yf

DATA_DIR = Path(__file__).parent.parent / "data" / "macro"
SCORE_FILE = DATA_DIR / "daily_bias_score.csv"


def main():
    print("═" * 70)
    print(" Validate Macro Bias Score vs XAUUSD Daily Returns")
    print("═" * 70)

    # Load bias scores
    print("\nLoading bias scores...")
    bias = pd.read_csv(SCORE_FILE)
    bias["date"] = pd.to_datetime(bias["date"])
    print(f"  Bias scores: {len(bias):,} rows")

    # Pull GC=F (gold futures) daily
    print("\nPulling GC=F (gold futures) daily 2015-2026...")
    gc = yf.download("GC=F", start="2015-01-01", end="2026-05-03", progress=False, auto_adjust=False)
    if isinstance(gc.columns, pd.MultiIndex):
        gc.columns = [c[0] if isinstance(c, tuple) else c for c in gc.columns]
    gc.index.name = "date"
    gc = gc.reset_index()
    gc["date"] = pd.to_datetime(gc["date"])
    gc["xau_return_next"] = gc["Close"].pct_change().shift(-1) * 100  # next-day return %
    gc = gc[["date", "Close", "xau_return_next"]].rename(columns={"Close": "xau_close"})
    print(f"  XAU prices: {len(gc):,} rows ({gc['date'].min().date()} → {gc['date'].max().date()})")

    # Merge
    df = bias.merge(gc, on="date", how="inner")
    df = df.dropna(subset=["bias_score", "xau_return_next"])
    print(f"  Merged: {len(df):,} rows for analysis")

    # Aggregate next-day returns per bias bucket
    print("\n" + "═" * 70)
    print(" NEXT-DAY XAU RETURN per BIAS SCORE BUCKET")
    print("═" * 70)
    print(f"{'Bias Score':<12} {'Days':>6} {'Avg Return':>12} {'Win Rate':>10} {'Median':>10}")
    print("-" * 60)
    for score in sorted(df["bias_score"].unique()):
        bucket = df[df["bias_score"] == score]["xau_return_next"]
        if len(bucket) < 5:
            continue
        avg = bucket.mean()
        wr = (bucket > 0).sum() / len(bucket) * 100
        med = bucket.median()
        bar = ("+" if avg > 0 else "-") * min(int(abs(avg) * 30), 20)
        print(f"  {int(score):+d}        {len(bucket):>6} {avg:>+10.3f}% {wr:>8.1f}% {med:>+9.3f}% {bar}")

    print("\n" + "═" * 70)
    print(" AGGREGATED — Bullish vs Bearish vs Neutral")
    print("═" * 70)
    bullish = df[df["bias_score"] >= 1]["xau_return_next"]
    bearish = df[df["bias_score"] <= -1]["xau_return_next"]
    strong_bull = df[df["bias_score"] >= 4]["xau_return_next"]
    strong_bear = df[df["bias_score"] <= -4]["xau_return_next"]
    neutral = df[df["bias_score"] == 0]["xau_return_next"]

    print(f"\n{'Group':<20} {'Days':>6} {'Avg Return %':>14} {'Win Rate %':>12} {'Median %':>10}")
    print("-" * 64)
    for label, grp in [
        ("STRONG_BULLISH(+4+)", strong_bull),
        ("BULLISH(+1+)", bullish),
        ("NEUTRAL(0)", neutral),
        ("BEARISH(-1-)", bearish),
        ("STRONG_BEARISH(-4-)", strong_bear),
    ]:
        if len(grp) > 0:
            wr = (grp > 0).sum() / len(grp) * 100
            print(f"  {label:<20} {len(grp):>6} {grp.mean():>+12.3f}%  {wr:>10.1f}%  {grp.median():>+8.3f}%")

    # Correlation
    corr = df["bias_score"].corr(df["xau_return_next"])
    spearman = df["bias_score"].corr(df["xau_return_next"], method="spearman")
    print(f"\nCorrelations:")
    print(f"  Pearson  bias_score × next-day return: {corr:+.4f}")
    print(f"  Spearman bias_score × next-day return: {spearman:+.4f}")
    if abs(corr) > 0.05:
        print(f"  → Signal detected (|corr| > 0.05)")
    else:
        print(f"  → Weak/no signal at single-day horizon")

    # Multi-day forward
    print("\n" + "═" * 70)
    print(" MULTI-DAY FORWARD RETURN per BIAS BUCKET (5-day forward)")
    print("═" * 70)
    gc2 = gc.copy()
    gc2["xau_return_5d"] = gc2["xau_close"].pct_change(5).shift(-5) * 100
    df2 = bias.merge(gc2[["date", "xau_close", "xau_return_5d"]], on="date", how="inner").dropna()

    print(f"\n{'Group':<20} {'Days':>6} {'Avg 5d Return %':>16} {'Win Rate %':>12}")
    print("-" * 60)
    for label, mask in [
        ("STRONG_BULLISH(+4+)", df2["bias_score"] >= 4),
        ("BULLISH(+1+)",        df2["bias_score"] >= 1),
        ("NEUTRAL(0)",          df2["bias_score"] == 0),
        ("BEARISH(-1-)",        df2["bias_score"] <= -1),
        ("STRONG_BEARISH(-4-)", df2["bias_score"] <= -4),
    ]:
        grp = df2[mask]["xau_return_5d"]
        if len(grp) > 0:
            wr = (grp > 0).sum() / len(grp) * 100
            print(f"  {label:<20} {len(grp):>6} {grp.mean():>+14.3f}%  {wr:>10.1f}%")

    corr5 = df2["bias_score"].corr(df2["xau_return_5d"])
    print(f"\n  Pearson  bias_score × 5-day return:  {corr5:+.4f}")


if __name__ == "__main__":
    main()
