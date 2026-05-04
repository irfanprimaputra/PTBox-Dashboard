"""Asia day-of-week PnL + NY[t-1] → Asia[t] behavior analysis.

User questions:
  1. Hari apa Asia paling profit/loss? Bar chart Mon-Fri.
  2. NY hari sebelumnya gimana → Asia hari ini gimana?
     (Liquidity grab theory: Asia first moves opposite of NY close direction)

Output:
  data/asia_dow_analysis.csv
  data/asia_ny_prev_chain.csv
  Print bar charts inline
"""
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"


def load_data():
    trades = pd.read_csv(DATA / "ptbox_v6_trades.csv")
    trades["date"] = pd.to_datetime(trades["date"])
    trades["dow"] = trades["date"].dt.day_name()
    trades["dow_num"] = trades["date"].dt.dayofweek

    sess = pd.read_csv(DATA / "session_behavior.csv")
    sess["date"] = pd.to_datetime(sess["date"])
    return trades, sess


def asia_dow_analysis(trades):
    print("═" * 72)
    print(" ASIA — Day of Week PnL Analysis")
    print("═" * 72)

    asia = trades[trades["session"] == "Asia"].copy()
    if len(asia) == 0:
        print("  No Asia trades in v6 export.")
        return None

    print(f"\n  Total Asia trades: {len(asia):,}")
    print(f"  Date range: {asia['date'].min().date()} → {asia['date'].max().date()}")
    print(f"  Total PnL: {asia['pnl_pts'].sum():+.1f} pts")
    print(f"  Win rate: {(asia['pnl_pts'] > 0).sum() / len(asia) * 100:.1f}%")

    print("\n  Per-Day-of-Week breakdown:")
    print(f"  {'Day':<10} {'Trades':>7} {'Total PnL':>11} {'Avg/trade':>10} {'WR %':>7} {'BAR'}")
    print(f"  {'─' * 10} {'─' * 7} {'─' * 11} {'─' * 10} {'─' * 7}")

    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    rows = []
    for day in days_order:
        sub = asia[asia["dow"] == day]
        if len(sub) == 0:
            continue
        total = sub["pnl_pts"].sum()
        avg = total / len(sub)
        wr = (sub["pnl_pts"] > 0).sum() / len(sub) * 100
        bar_len = int(min(abs(total) / 5, 30))
        bar = ("+" * bar_len) if total > 0 else ("-" * bar_len)
        rows.append({
            "day": day, "trades": len(sub), "total_pnl": total,
            "avg": avg, "wr": wr,
        })
        print(f"  {day:<10} {len(sub):>7} {total:>+10.1f}  {avg:>+9.2f} {wr:>6.1f}%   {bar}")

    df_dow = pd.DataFrame(rows)
    df_dow.to_csv(DATA / "asia_dow_analysis.csv", index=False)

    # Identify best/worst days
    best = df_dow.loc[df_dow["total_pnl"].idxmax()]
    worst = df_dow.loc[df_dow["total_pnl"].idxmin()]
    print(f"\n  ⭐ Best:  {best['day']} ({best['total_pnl']:+.1f} pts, WR {best['wr']:.1f}%)")
    print(f"  💀 Worst: {worst['day']} ({worst['total_pnl']:+.1f} pts, WR {worst['wr']:.1f}%)")

    # Suggest skip rules if any day clearly worst
    if worst["total_pnl"] < 0:
        skip_pnl = asia[asia["dow"] != worst["day"]]["pnl_pts"].sum()
        full_pnl = asia["pnl_pts"].sum()
        print(f"\n  💡 If skip {worst['day']} entirely:")
        print(f"     PnL: {full_pnl:+.1f} → {skip_pnl:+.1f} (Δ {skip_pnl - full_pnl:+.1f})")

    return df_dow


def asia_ny_prev_chain(trades, sess):
    print("\n" + "═" * 72)
    print(" ASIA vs NY[t-1] CLOSE — Liquidity Grab Theory")
    print("═" * 72)

    # Pivot session behavior wide
    sess_wide = sess.pivot(index="date", columns="session", values="state")
    sess_wide = sess_wide.sort_index()
    sess_wide["NY_prev"] = sess_wide["NY"].shift(1)

    # Compute NY prev "directional bias" using state
    # TREND_UP / V_UP / EXPANSION_UP = bullish close
    # TREND_DOWN / V_DOWN / EXPANSION_DN = bearish close
    # RANGE = neutral
    bullish_states = ["TREND_UP", "V_UP", "EXPANSION_UP"]
    bearish_states = ["TREND_DOWN", "V_DOWN", "EXPANSION_DN"]

    def classify_dir(state):
        if state in bullish_states: return "BULLISH"
        if state in bearish_states: return "BEARISH"
        return "RANGE"

    sess_wide["NY_prev_dir"] = sess_wide["NY_prev"].apply(classify_dir)
    sess_wide["asia_dir"] = sess_wide["Asia"].apply(classify_dir)

    # For each NY_prev direction, what's Asia's behavior?
    # Theory: NY bullish prev → Asia first moves DOWN (liquidity grab) → mean-rev fade SHORT works
    # NY bearish prev → Asia first moves UP → mean-rev fade LONG works

    print(f"\n  NY[t-1] → Asia[t] direction transition matrix:")
    sess_clean = sess_wide.dropna(subset=["NY_prev_dir", "asia_dir"]).reset_index()
    matrix = pd.crosstab(sess_clean["NY_prev_dir"], sess_clean["asia_dir"], normalize="index") * 100
    cnt = pd.crosstab(sess_clean["NY_prev_dir"], sess_clean["asia_dir"])

    print(f"\n  {'NY_prev':<10} {'→ BULLISH':>10} {'→ BEARISH':>10} {'→ RANGE':>10} {'(n)':>6}")
    print(f"  {'─' * 10} {'─' * 10} {'─' * 10} {'─' * 10} {'─' * 6}")
    for dir_prev in matrix.index:
        bull = matrix.loc[dir_prev, "BULLISH"] if "BULLISH" in matrix.columns else 0
        bear = matrix.loc[dir_prev, "BEARISH"] if "BEARISH" in matrix.columns else 0
        rng = matrix.loc[dir_prev, "RANGE"] if "RANGE" in matrix.columns else 0
        n = cnt.loc[dir_prev].sum()
        print(f"  {dir_prev:<10} {bull:>9.1f}% {bear:>9.1f}% {rng:>9.1f}% {n:>5}")

    # Test liquidity grab theory: link Asia trade outcome to NY_prev direction
    asia_trades = trades[trades["session"] == "Asia"].copy()
    asia_trades["date_only"] = asia_trades["date"]
    sess_clean_dates = sess_clean[["date", "NY_prev_dir"]].rename(columns={"date": "date_only"})
    merged = asia_trades.merge(sess_clean_dates, on="date_only", how="left")

    print(f"\n  Asia trades grouped by NY[t-1] direction (n={len(merged):,}):")
    print(f"  {'NY_prev':<10} {'Trades':>7} {'Total PnL':>11} {'Avg':>8} {'WR%':>6}")
    print(f"  {'─' * 10} {'─' * 7} {'─' * 11} {'─' * 8} {'─' * 6}")
    chain_rows = []
    for dir_ in ["BULLISH", "BEARISH", "RANGE"]:
        sub = merged[merged["NY_prev_dir"] == dir_]
        if len(sub) == 0:
            continue
        total = sub["pnl_pts"].sum()
        avg = total / len(sub)
        wr = (sub["pnl_pts"] > 0).sum() / len(sub) * 100
        chain_rows.append({"ny_prev_dir": dir_, "trades": len(sub), "total_pnl": total, "avg": avg, "wr": wr})
        print(f"  {dir_:<10} {len(sub):>7} {total:>+10.1f}  {avg:>+7.2f} {wr:>5.1f}%")

    # Direction-specific test: Asia LONG vs SHORT trades, separated by NY_prev_dir
    print(f"\n  Asia LONG vs SHORT split by NY[t-1]:")
    print(f"  {'NY_prev':<10} {'Direction':<10} {'Trades':>7} {'PnL':>9} {'WR%':>6}")
    print(f"  {'─' * 10} {'─' * 10} {'─' * 7} {'─' * 9} {'─' * 6}")
    for dir_prev in ["BULLISH", "BEARISH", "RANGE"]:
        for d in ["long", "short"]:
            sub = merged[(merged["NY_prev_dir"] == dir_prev) & (merged["direction"] == d)]
            if len(sub) == 0:
                continue
            total = sub["pnl_pts"].sum()
            wr = (sub["pnl_pts"] > 0).sum() / len(sub) * 100
            print(f"  {dir_prev:<10} {d:<10} {len(sub):>7} {total:>+8.1f} {wr:>5.1f}%")

    # Save
    pd.DataFrame(chain_rows).to_csv(DATA / "asia_ny_prev_chain.csv", index=False)

    # Liquidity grab interpretation
    print(f"\n  💡 LIQUIDITY GRAB THEORY CHECK:")
    print(f"     If theory true: Asia trade direction OPPOSITE of NY_prev should win more")
    if len(merged) > 0:
        # NY bullish prev + Asia SHORT = should win (liquidity grab down)
        bull_short = merged[(merged["NY_prev_dir"] == "BULLISH") & (merged["direction"] == "short")]
        bear_long = merged[(merged["NY_prev_dir"] == "BEARISH") & (merged["direction"] == "long")]

        if len(bull_short):
            print(f"     NY_BULL → Asia SHORT: WR {(bull_short['pnl_pts']>0).sum()/len(bull_short)*100:.1f}%, PnL {bull_short['pnl_pts'].sum():+.1f}")
        if len(bear_long):
            print(f"     NY_BEAR → Asia LONG: WR {(bear_long['pnl_pts']>0).sum()/len(bear_long)*100:.1f}%, PnL {bear_long['pnl_pts'].sum():+.1f}")


def main():
    trades, sess = load_data()
    asia_dow_analysis(trades)
    asia_ny_prev_chain(trades, sess)


if __name__ == "__main__":
    main()
