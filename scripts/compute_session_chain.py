"""Inter-session state chain analysis.

Build transition probability matrices:
  NY[t-1] → Asia[t]
  Asia[t] → London[t]
  London[t] → NY[t]

Plus full-chain probability (NY[t-1] state → NY[t] outcome).

Output:
  data/session_chain_transitions.csv — pairwise transition probabilities
  data/session_chain_full.csv — full 4-state chain (NY[-1]→Asia→London→NY)
"""
from pathlib import Path
import pandas as pd
import numpy as np
from collections import Counter

DATA_DIR = Path(__file__).parent.parent / "data"
SESS_FILE = DATA_DIR / "session_behavior.csv"
OUT_TRANS = DATA_DIR / "session_chain_transitions.csv"
OUT_FULL = DATA_DIR / "session_chain_full.csv"

STATES = ["TREND_UP", "TREND_DOWN", "V_UP", "V_DOWN", "RANGE", "EXPANSION_UP", "EXPANSION_DN"]


def main():
    print("═" * 72)
    print(" Inter-Session State Chain Analysis")
    print("═" * 72)

    sess = pd.read_csv(SESS_FILE)
    sess["date"] = pd.to_datetime(sess["date"])
    sess = sess.sort_values(["date", "session"]).reset_index(drop=True)

    # Pivot to wide format: 1 row per date, columns Asia/London/NY state
    print("\nPivoting per-date session states...")
    wide = sess.pivot(index="date", columns="session", values="state").reset_index()
    wide = wide[["date", "Asia", "London", "NY"]].dropna()
    print(f"  {len(wide):,} dates with all 3 sessions")

    # Add NY of previous date
    wide = wide.sort_values("date").reset_index(drop=True)
    wide["NY_prev"] = wide["NY"].shift(1)
    wide = wide.dropna(subset=["NY_prev"]).reset_index(drop=True)
    print(f"  {len(wide):,} dates with NY[t-1] available")

    # ─────────────────────────────────────────────────────────────
    # PAIRWISE TRANSITIONS
    # ─────────────────────────────────────────────────────────────
    transitions = []
    for from_col, to_col, label in [
        ("NY_prev", "Asia",  "NY[t-1] → Asia[t]"),
        ("Asia",    "London", "Asia[t] → London[t]"),
        ("London",  "NY",    "London[t] → NY[t]"),
    ]:
        ct = pd.crosstab(wide[from_col], wide[to_col], normalize="index") * 100
        ct = ct.round(1)
        cnt = pd.crosstab(wide[from_col], wide[to_col])

        for from_state in ct.index:
            for to_state in ct.columns:
                transitions.append({
                    "transition": label,
                    "from_state": from_state,
                    "to_state": to_state,
                    "count": int(cnt.loc[from_state, to_state]),
                    "pct": float(ct.loc[from_state, to_state]),
                })

    trans_df = pd.DataFrame(transitions)
    trans_df.to_csv(OUT_TRANS, index=False)

    # Print pairwise summary
    for label in ["NY[t-1] → Asia[t]", "Asia[t] → London[t]", "London[t] → NY[t]"]:
        print(f"\n{'─' * 72}")
        print(f"📈 {label}")
        print(f"{'─' * 72}")
        sub = trans_df[trans_df["transition"] == label]
        # Highlight strongest transitions (highest pct from each from_state)
        for from_state in sub["from_state"].unique():
            row = sub[sub["from_state"] == from_state].sort_values("pct", ascending=False)
            top = row.iloc[0]
            n_total = row["count"].sum()
            print(f"  {from_state:<13} (n={n_total:>3}) → {top['to_state']:<13} {top['pct']:>5.1f}%  "
                  + (f"(2nd: {row.iloc[1]['to_state']} {row.iloc[1]['pct']:.1f}%)" if len(row) > 1 else ""))

    # ─────────────────────────────────────────────────────────────
    # FULL CHAIN: NY[t-1] → Asia → London → NY
    # ─────────────────────────────────────────────────────────────
    print(f"\n{'─' * 72}")
    print(f"🔗 FULL CHAIN: NY[t-1] → Asia[t] → London[t] → NY[t]")
    print(f"{'─' * 72}")

    chain_data = wide.groupby(["NY_prev", "Asia", "London", "NY"]).size().reset_index(name="count")
    chain_data["pct_of_total"] = chain_data["count"] / chain_data["count"].sum() * 100

    # Conditional NY outcome given prev 3 states
    chain_data["chain_prefix"] = chain_data["NY_prev"] + " → " + chain_data["Asia"] + " → " + chain_data["London"]
    grouped = chain_data.groupby("chain_prefix").apply(
        lambda g: g.assign(pct_NY_outcome=g["count"] / g["count"].sum() * 100)
    ).reset_index(drop=True)
    grouped = grouped.sort_values(["chain_prefix", "count"], ascending=[True, False])
    grouped[["NY_prev", "Asia", "London", "NY", "count", "pct_NY_outcome", "pct_of_total"]].to_csv(OUT_FULL, index=False)

    # Top 10 most predictive chains (highest count + high NY outcome concentration)
    print(f"\n  Top 10 chains by frequency (count >= 10):")
    print(f"  {'CHAIN':<55} {'Top NY':<14} {'Prob':>6} {'Count':>6}")
    top = []
    for prefix, g in grouped.groupby("chain_prefix"):
        total = g["count"].sum()
        if total < 10:
            continue
        top_outcome = g.iloc[0]
        top.append({
            "chain": prefix,
            "top_NY": top_outcome["NY"],
            "prob": top_outcome["pct_NY_outcome"],
            "total": total,
        })
    top_df = pd.DataFrame(top).sort_values("prob", ascending=False).head(15)
    for _, r in top_df.iterrows():
        bar = "█" * int(r["prob"] / 5)
        print(f"  {r['chain']:<55} {r['top_NY']:<14} {r['prob']:>5.1f}% {r['total']:>5} {bar}")

    print(f"\n  Saved transitions: {OUT_TRANS}")
    print(f"  Saved full chain:  {OUT_FULL}")

    # Sanity: distribution of NY[t-1] alone
    print(f"\n  Baseline NY state distribution (no conditioning):")
    base = wide["NY"].value_counts(normalize=True) * 100
    for st, pct in base.items():
        print(f"    {st:<14} {pct:>5.1f}%")


if __name__ == "__main__":
    main()
