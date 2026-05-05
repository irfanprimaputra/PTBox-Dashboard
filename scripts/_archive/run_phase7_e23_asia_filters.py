"""Phase 7 e23 — Asia day-of-week + NY[t-1] direction filters.

Findings from analyze_asia_dow_and_chain.py (on v6 fixed-config trades):
  - Thursday catastrophic (-87), Tue/Wed best
  - RANGE NY_prev days: 80% WR, +0.44/trade (vs +0.04 full average)

e23 variants (apply to walk-forward engine):
  e23a — Skip Thursday Asia entirely
  e23b — Asia only on RANGE NY_prev days
  e23c — Asia skip Thursday + RANGE NY_prev (combo)
  e23d — Asia skip Thursday + Friday (defensive Friday-skip)
"""
import os, sys, json, datetime, time
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT / "scripts"))

from ptbox_quarterly_v3 import CONFIG, load_data, build_date_groups, PATTERN_VARIANTS
from ptbox_quarterly_v4 import ASIA_MEANREV_VARIANTS

from run_phase7_e16_naked_forex import base_config, backtest_direct_breakout
from run_engine_with_filters import backtest_filtered, backtest_meanrev_fail_filtered
from run_phase7_e19_asia_push import generate_quarters

# Pre-compute NY_prev direction map
def build_ny_prev_dir_map():
    sess = pd.read_csv(ROOT / "data" / "session_behavior.csv")
    sess["date"] = pd.to_datetime(sess["date"]).dt.date
    sess_wide = sess.pivot(index="date", columns="session", values="state")
    sess_wide = sess_wide.sort_index()
    sess_wide["NY_prev"] = sess_wide["NY"].shift(1)
    BULLISH = ["TREND_UP", "V_UP", "EXPANSION_UP"]
    BEARISH = ["TREND_DOWN", "V_DOWN", "EXPANSION_DN"]

    def classify(state):
        if state in BULLISH: return "BULLISH"
        if state in BEARISH: return "BEARISH"
        return "RANGE"
    sess_wide["NY_prev_dir"] = sess_wide["NY_prev"].apply(classify)
    return dict(zip(sess_wide.index, sess_wide["NY_prev_dir"]))


# Build allowed_fn per filter
def make_filter(skip_dow=None, only_ny_prev=None, ny_prev_map=None):
    """skip_dow: list of dayofweek ints (0=Mon, 4=Fri)
       only_ny_prev: list like ['RANGE'] to allow only those NY_prev directions
    """
    def allowed(date, session, direction):
        if session != "Asia":
            return True  # only filter Asia
        # Day-of-week filter
        if skip_dow:
            dow = date.weekday()
            if dow in skip_dow:
                return False
        # NY_prev direction filter
        if only_ny_prev and ny_prev_map:
            ny_dir = ny_prev_map.get(date)
            if ny_dir is None:
                return False  # no data, skip conservatively
            if ny_dir not in only_ny_prev:
                return False
        return True
    return allowed


def filter_allow_all(d, s, dr): return True


def walk_forward_e23(df, allowed_fn_asia):
    """Walk-forward with Asia filter, London/NY default e16b."""
    cfg = base_config()
    cfg["NY"]["model_type"] = "direct_breakout"
    cfg["NY"]["pattern_at_breakout"] = "any"

    sess_variants = {
        "Asia": ASIA_MEANREV_VARIANTS["asia_a2_fail"],
        "London": cfg["London"]["variant"],
        "NY": cfg["NY"]["variant"],
    }
    # e20d: Asia late-window 21-23 ET
    sess_windows = {
        "Asia": (1260, 1380),  # late-window
        "London": cfg["London"]["window"],
        "NY": cfg["NY"]["window"],
    }
    sess_models = {
        "Asia": "mean_rev_fail",
        "London": cfg["London"]["model_type"],
        "NY": cfg["NY"]["model_type"],
    }

    data_start = df['date_et'].min(); data_end = df['date_et'].max()
    quarters = generate_quarters(data_start, data_end)
    results = []

    for idx, (train_s, train_e, val_s, val_e, qlabel) in enumerate(quarters, 1):
        df_train = df[(df['date_et']>=train_s)&(df['date_et']<=train_e)]
        df_val = df[(df['date_et']>=val_s)&(df['date_et']<=val_e)]
        tg, td = build_date_groups(df_train); vg, vd = build_date_groups(df_val)
        if len(td) < 15 or len(vd) < 10: continue

        for sess in ['Asia','London','NY']:
            sv = sess_variants[sess]; sw = sess_windows[sess]
            tps = CONFIG['tp_per_session'][sess]
            tp1, tp2 = tps['tp1'], tps['tp2']

            def dispatch(date_groups_, all_dates_, bh, bm, dur):
                if sess == "Asia":
                    return backtest_meanrev_fail_filtered(
                        date_groups_, all_dates_, bh, bm, dur, sv,
                        allowed_fn_asia, sess, adaptive=True,
                    )
                elif sess == "NY":
                    return backtest_direct_breakout(
                        date_groups_, all_dates_, bh, bm, dur, tp1, tp2, sv,
                        filter_allow_all, sess, False, "any",
                    )
                else:  # London
                    return backtest_filtered(
                        date_groups_, all_dates_, bh, bm, dur, tp1, tp2, sv,
                        filter_allow_all, sess, False,
                    )

            durs = CONFIG['durations']; step = CONFIG['coarse_step']
            coarse = []
            for bmt in range(sw[0], sw[1], step):
                bh = bmt // 60; bm = bmt % 60
                for dur in durs:
                    if bmt + dur >= sw[1]: continue
                    r = dispatch(tg, td, bh, bm, dur)
                    if r: coarse.append(r)
            if not coarse: continue
            df_c = pd.DataFrame(coarse)
            top_centers = df_c.nlargest(5, 'pnl')[['bh','bm']].values
            seen = set(); fine = []
            for bh, bm in top_centers:
                center = int(bh)*60 + int(bm)
                for bmt in range(max(sw[0], center-CONFIG['fine_window']),
                                  min(sw[1], center+CONFIG['fine_window']+1)):
                    if bmt in seen: continue
                    seen.add(bmt); fh = bmt//60; fm = bmt%60
                    for dur in durs:
                        if bmt + dur >= sw[1]: continue
                        r = dispatch(tg, td, fh, fm, dur)
                        if r: fine.append(r)
            if not fine: continue
            best = max(fine, key=lambda r: r['pnl'])
            r_val = dispatch(vg, vd, best['bh'], best['bm'], best['dur'])
            val_pnl = r_val['pnl'] if r_val else 0
            results.append({
                'quarter': qlabel, 'session': sess, 'val_pnl': val_pnl,
                'val_trades': r_val.get('trades', 0) if r_val else 0,
                'val_winrate': r_val.get('winrate', 0) if r_val else 0,
            })
    return results


def run_variant(label, df, allowed_fn):
    print(f"\n{'═' * 72}\n {label}\n{'═' * 72}")
    t0 = time.time()
    results = walk_forward_e23(df, allowed_fn)
    elapsed = time.time() - t0
    df_r = pd.DataFrame(results)
    total = df_r["val_pnl"].sum() if len(df_r) else 0
    by_sess = df_r.groupby("session")["val_pnl"].sum() if len(df_r) else pd.Series()
    df_r["q_year"] = df_r["quarter"].str[:4].astype(int)
    recent = df_r[df_r["q_year"] >= 2024]
    recent_total = recent["val_pnl"].sum() if len(recent) else 0
    asia_pnl = by_sess.get("Asia", 0)
    asia_trades = df_r[df_r["session"] == "Asia"]["val_trades"].sum() if len(df_r) else 0
    print(f"  Elapsed: {elapsed:.1f}s")
    print(f"  Total 19Q: {total:+.1f} (Δ vs e20d +976 = {total - 976:+.1f})")
    print(f"  Asia      {asia_pnl:>+8.1f} ({asia_trades} trades, e20d ref +182, Δ {asia_pnl - 182:+.0f})")
    print(f"  Recent 24+: {recent_total:+.1f}")
    return {"label": label, "total_19q": total, "asia_pnl": float(asia_pnl),
            "asia_trades": int(asia_trades), "asia_delta": float(asia_pnl - 182),
            "total_recent": recent_total,
            "by_session": {s: float(by_sess.get(s, 0)) for s in ['Asia','London','NY']}}


def main():
    csv = "/Users/irfanprimaputra.b/Downloads/XAUUSD_M1_2021_-_2026.csv"
    df = load_data(csv)
    ny_prev_map = build_ny_prev_dir_map()

    summaries = []

    # e23a — Skip Thursday Asia (dayofweek=3 = Thursday in ET, which = Friday WIB)
    summaries.append(run_variant("e23a · Skip Thursday Asia", df,
        make_filter(skip_dow=[3])))

    # e23b — Asia only on RANGE NY_prev days
    summaries.append(run_variant("e23b · Asia only RANGE NY_prev", df,
        make_filter(only_ny_prev=["RANGE"], ny_prev_map=ny_prev_map)))

    # e23c — Combo: skip Thursday + RANGE NY_prev
    summaries.append(run_variant("e23c · Skip Thursday + RANGE NY_prev", df,
        make_filter(skip_dow=[3], only_ny_prev=["RANGE"], ny_prev_map=ny_prev_map)))

    # e23d — Defensive: skip Thursday + Friday (4 = Friday)
    summaries.append(run_variant("e23d · Skip Thursday + Friday", df,
        make_filter(skip_dow=[3, 4])))

    out = ROOT / "data" / "phase7_e23_results.json"
    with open(out, 'w') as f:
        json.dump({'generated': datetime.datetime.now().isoformat(),
                   'e20d_baseline_asia': 182.0, 'target_asia': 300.0,
                   'variants': summaries}, f, indent=2)

    print("\n" + "═" * 72)
    print(" SUMMARY · e23 Asia Filters (vs e20d Asia +182)")
    print("═" * 72)
    print(f"  {'Variant':<55} {'Asia':>9} {'Trades':>7} {'Δ Asia':>9} {'19Q':>9}")
    print(f"  {'─' * 55} {'─' * 9} {'─' * 7} {'─' * 9} {'─' * 9}")
    for s in summaries:
        ok = "⭐" if s["asia_pnl"] >= 300 else ("✅" if s["asia_delta"] > 0 else "❌")
        print(f"  {s['label']:<55} {s['asia_pnl']:>+8.1f} {s['asia_trades']:>7} {s['asia_delta']:>+9.1f} {s['total_19q']:>+8.1f} {ok}")
    print(f"\n  Saved: {out}")


if __name__ == "__main__":
    main()
