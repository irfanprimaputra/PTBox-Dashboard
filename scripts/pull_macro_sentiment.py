"""Pull macro sentiment data 2015-2026 untuk PT Box X-9 daily bias filter.

Sources:
1. FRED RRPONTSYD — Reverse Repo Operations (via pandas-datareader, no key needed)
2. Yahoo GLD — SPDR Gold ETF (yfinance)
3. DXY — US Dollar Index (yfinance: DX-Y.NYB)
4. US 2Y yield — FRED DGS2 (via pandas-datareader)
5. US 10Y yield — yfinance ^TNX (or FRED DGS10)
6. VIX — yfinance ^VIX

Output: PTBox-Dashboard/data/macro/*.csv
"""
import os
import time
from pathlib import Path
import pandas as pd
import yfinance as yf
from pandas_datareader import data as pdr

START = "2015-01-01"
END   = "2026-05-03"
OUT_DIR = Path(__file__).parent.parent / "data" / "macro"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def pull_yfinance(ticker: str, label: str) -> pd.DataFrame:
    print(f"  Pulling {label} ({ticker}) from yfinance...", end=" ", flush=True)
    try:
        df = yf.download(ticker, start=START, end=END, progress=False, auto_adjust=False)
        if df.empty:
            print(f"❌ EMPTY")
            return pd.DataFrame()
        # Flatten MultiIndex columns if needed
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df.index.name = "date"
        df.reset_index(inplace=True)
        print(f"✅ {len(df):,} rows ({df['date'].min().date()} → {df['date'].max().date()})")
        return df
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return pd.DataFrame()


def pull_fred(series: str, label: str) -> pd.DataFrame:
    print(f"  Pulling {label} ({series}) from FRED...", end=" ", flush=True)
    try:
        df = pdr.DataReader(series, "fred", START, END)
        df.index.name = "date"
        df.reset_index(inplace=True)
        print(f"✅ {len(df):,} rows ({df['date'].min().date()} → {df['date'].max().date()})")
        return df
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return pd.DataFrame()


def main():
    print("═" * 70)
    print(" PT Box Macro Sentiment Data Pull · 2015-01-01 → 2026-05-03")
    print("═" * 70)

    results = {}

    # 1. RRP — FRED RRPONTSYD
    print("\n[1/6] Reverse Repo Operations (RRPONTSYD)")
    rrp = pull_fred("RRPONTSYD", "RRP daily")
    if not rrp.empty:
        rrp.columns = ["date", "rrp_billion_usd"]
        rrp.to_csv(OUT_DIR / "rrp_daily.csv", index=False)
        results["RRP"] = rrp

    # 2. GLD — Yahoo
    print("\n[2/6] SPDR Gold Shares ETF (GLD)")
    gld = pull_yfinance("GLD", "GLD ETF")
    if not gld.empty:
        gld.to_csv(OUT_DIR / "gld_daily.csv", index=False)
        results["GLD"] = gld

    # 3. DXY — Yahoo
    print("\n[3/6] US Dollar Index (DX-Y.NYB)")
    dxy = pull_yfinance("DX-Y.NYB", "DXY")
    if dxy.empty:
        # Fallback: ^DXY ticker
        dxy = pull_yfinance("^DXY", "DXY (fallback)")
    if not dxy.empty:
        dxy.to_csv(OUT_DIR / "dxy_daily.csv", index=False)
        results["DXY"] = dxy

    # 4. US 2Y yield — FRED DGS2
    print("\n[4/6] US 2-Year Treasury Yield (DGS2)")
    y2y = pull_fred("DGS2", "US 2Y yield")
    if not y2y.empty:
        y2y.columns = ["date", "yield_2y_pct"]
        y2y.to_csv(OUT_DIR / "us_2y_yield.csv", index=False)
        results["2Y"] = y2y

    # 5. US 10Y yield — Yahoo ^TNX (yield × 10) atau FRED DGS10
    print("\n[5/6] US 10-Year Treasury Yield")
    y10y = pull_fred("DGS10", "US 10Y yield")
    if y10y.empty:
        # Fallback: ^TNX yfinance (close = yield × 10, divide by 10)
        tnx = pull_yfinance("^TNX", "10Y via TNX")
        if not tnx.empty:
            y10y = tnx[["date", "Close"]].copy()
            y10y.columns = ["date", "yield_10y_pct"]
    else:
        y10y.columns = ["date", "yield_10y_pct"]
    if not y10y.empty:
        y10y.to_csv(OUT_DIR / "us_10y_yield.csv", index=False)
        results["10Y"] = y10y

    # 6. VIX — Yahoo
    print("\n[6/6] VIX Volatility Index (^VIX)")
    vix = pull_yfinance("^VIX", "VIX")
    if not vix.empty:
        vix.to_csv(OUT_DIR / "vix_daily.csv", index=False)
        results["VIX"] = vix

    # Summary
    print("\n" + "═" * 70)
    print(" SUMMARY")
    print("═" * 70)
    print(f"{'Source':<12} {'Rows':>10} {'Date Range':<30} {'File'}")
    print("-" * 70)
    for label, df in results.items():
        date_col = "date" if "date" in df.columns else df.columns[0]
        rng = f"{pd.to_datetime(df[date_col]).min().date()} → {pd.to_datetime(df[date_col]).max().date()}"
        print(f"{label:<12} {len(df):>10,} {rng:<30}")
    print(f"\n  Output dir: {OUT_DIR}")
    print(f"  Total sources: {len(results)}/6")


if __name__ == "__main__":
    main()
