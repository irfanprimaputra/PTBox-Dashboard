"""Capture per-session OHLC + behavior state per trading day.

Session windows (ET, matches PT Box engine):
  Asia:   19:00-23:00 ET (UTC-4) → 23:00-03:00 UTC, span across midnight
  London: 01:00-05:00 ET → 05:00-09:00 UTC
  NY:     08:00-12:00 ET → 12:00-16:00 UTC

State classification per session:
  TREND_UP      : close>open AND close in upper 30% of range
  TREND_DOWN    : close<open AND close in lower 30% of range
  V_UP          : low extreme touched (>50% range below open) BUT close>open
  V_DOWN        : high extreme touched (>50% range above open) BUT close<open
  RANGE         : |close-open| < 30% of range AND close near middle
  EXPANSION_UP  : range > 1.5× rolling 20-day avg AND close>open
  EXPANSION_DN  : range > 1.5× rolling 20-day avg AND close<open

Output: data/session_behavior.csv
        columns: date, session, open, close, high, low, range_pts, body_pts, state, ...
"""
from pathlib import Path
import pandas as pd
import numpy as np

DATA_FILE = Path("/Users/irfanprimaputra.b/Downloads/XAUUSD_M1_2021_-_2026.csv")
OUT_FILE = Path(__file__).parent.parent / "data" / "session_behavior.csv"

# Session windows in MINUTES of day (ET)
SESSIONS = {
    "Asia":   (19*60, 23*60),     # 19:00 - 23:00 ET
    "London": (1*60,  5*60),      # 01:00 - 05:00 ET
    "NY":     (8*60,  12*60),     # 08:00 - 12:00 ET
}
TZ_OFFSET_HOURS = 4  # data is UTC; subtract 4 to get ET


def load_m1():
    print(f"Loading {DATA_FILE.name}...")
    df = pd.read_csv(DATA_FILE, sep="\t")
    df.columns = [c.strip("<>").lower() for c in df.columns]
    df["datetime"] = (
        pd.to_datetime(df["date"] + " " + df["time"], format="%Y.%m.%d %H:%M:%S")
        - pd.Timedelta(hours=TZ_OFFSET_HOURS)
    )
    df = df.sort_values("datetime").drop_duplicates("datetime").reset_index(drop=True)
    df["date_et"] = df["datetime"].dt.date
    df["min_of_day"] = df["datetime"].dt.hour * 60 + df["datetime"].dt.minute
    df["weekday"] = df["datetime"].dt.weekday
    df = df[df["weekday"] < 5].reset_index(drop=True)
    print(f"  {len(df):,} M1 bars · {df['date_et'].min()} → {df['date_et'].max()}")
    return df


def classify_state(open_p, close_p, high_p, low_p, avg_range):
    """Returns one of: TREND_UP, TREND_DOWN, V_UP, V_DOWN, RANGE, EXPANSION_UP, EXPANSION_DN"""
    rng = high_p - low_p
    if rng == 0:
        return "RANGE"
    body = close_p - open_p
    body_abs = abs(body)
    body_pct = body_abs / rng

    upper_third = high_p - rng * 0.3
    lower_third = low_p + rng * 0.3
    middle_low  = low_p + rng * 0.35
    middle_high = high_p - rng * 0.35

    is_expansion = rng > avg_range * 1.5 if avg_range > 0 else False
    open_distance_to_high = (high_p - open_p) / rng
    open_distance_to_low  = (open_p - low_p) / rng

    # V reversals: extreme excursion away from open, then close opposite direction
    if open_distance_to_low > 0.5 and body > 0:
        return "V_UP"
    if open_distance_to_high > 0.5 and body < 0:
        return "V_DOWN"

    # Expansion + direction
    if is_expansion and body > 0:
        return "EXPANSION_UP"
    if is_expansion and body < 0:
        return "EXPANSION_DN"

    # Trend
    if body > 0 and close_p >= upper_third:
        return "TREND_UP"
    if body < 0 and close_p <= lower_third:
        return "TREND_DOWN"

    # Range — close near middle, body small
    if middle_low <= close_p <= middle_high and body_pct < 0.3:
        return "RANGE"

    # Mild directional fallback
    return "TREND_UP" if body > 0 else "TREND_DOWN"


def aggregate_session(group, sess_name):
    if group.empty:
        return None
    open_p = group.iloc[0]["open"]
    close_p = group.iloc[-1]["close"]
    high_p = group["high"].max()
    low_p = group["low"].min()
    open_time = group.iloc[0]["datetime"]
    close_time = group.iloc[-1]["datetime"]
    return {
        "session": sess_name,
        "open": open_p,
        "close": close_p,
        "high": high_p,
        "low": low_p,
        "range_pts": high_p - low_p,
        "body_pts": close_p - open_p,
        "open_time": open_time,
        "close_time": close_time,
        "bars": len(group),
    }


def main():
    print("═" * 72)
    print(" Session Behavior Analyzer · 2021-2026 XAUUSD M1")
    print("═" * 72)

    df = load_m1()

    # Build session table per date
    print("\nAggregating per-session per-day...")
    rows = []
    dates = df["date_et"].unique()
    for i, d in enumerate(dates):
        if i % 500 == 0:
            print(f"  {i}/{len(dates)} dates processed...")
        day_df = df[df["date_et"] == d]
        for sess_name, (start_min, end_min) in SESSIONS.items():
            mask = (day_df["min_of_day"] >= start_min) & (day_df["min_of_day"] < end_min)
            sess_df = day_df[mask]
            agg = aggregate_session(sess_df, sess_name)
            if agg is not None:
                agg["date"] = d
                rows.append(agg)

    sess = pd.DataFrame(rows)
    sess["date"] = pd.to_datetime(sess["date"])
    sess = sess.sort_values(["date", "session"]).reset_index(drop=True)
    print(f"  → {len(sess):,} session-days captured")

    # Compute rolling 20-day avg range per session for expansion classification
    print("\nComputing rolling avg range + state classification...")
    for sess_name in SESSIONS.keys():
        m = sess["session"] == sess_name
        sess.loc[m, "avg_range_20d"] = sess.loc[m, "range_pts"].rolling(20, min_periods=5).mean().shift(1)
    sess["avg_range_20d"] = sess["avg_range_20d"].fillna(sess.groupby("session")["range_pts"].transform("median"))

    # Classify state
    sess["state"] = sess.apply(
        lambda r: classify_state(r["open"], r["close"], r["high"], r["low"], r["avg_range_20d"]),
        axis=1,
    )

    # Save
    sess["body_pct_range"] = (sess["body_pts"] / sess["range_pts"]).round(3)
    out_cols = [
        "date", "session", "open", "close", "high", "low",
        "range_pts", "body_pts", "body_pct_range",
        "avg_range_20d", "state", "open_time", "close_time", "bars",
    ]
    sess[out_cols].to_csv(OUT_FILE, index=False)

    # Summary
    print("\n" + "═" * 72)
    print(" STATE DISTRIBUTION per SESSION")
    print("═" * 72)
    for sess_name in SESSIONS.keys():
        s = sess[sess["session"] == sess_name]
        print(f"\n🔸 {sess_name} ({len(s):,} session-days)")
        print(f"   Avg range: {s['range_pts'].mean():.2f} pts | Median: {s['range_pts'].median():.2f}")
        print(f"   State breakdown:")
        sd = s["state"].value_counts(normalize=True) * 100
        for st_, pct in sd.items():
            cnt = int((s["state"] == st_).sum())
            bar = "█" * int(pct / 2)
            print(f"     {st_:<14} {cnt:>5} ({pct:5.1f}%) {bar}")

    print(f"\n  Saved: {OUT_FILE}")


if __name__ == "__main__":
    main()
