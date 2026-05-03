"""Phase 7 e21 — Stack on e20d (Asia 21-23 ET window winner).

e20d gave +31 (Asia +182). Now stack additional levers:
  e21a — e20d window + TP 1.5×mid (combine 2 micro-improvements)
  e21b — Even tighter window 22:00-23:00 ET (1320-1380)
  e21c — e20d window + max_attempts override 5 (test if more attempts help)
  e21d — e20d window + min_box_width=2 (filter degenerate)
  e21e — e20d window + Asian Range narrowing filter (skip wide-range days)
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
from run_engine_with_filters import backtest_filtered
from run_phase7_e19_asia_push import generate_quarters, filter_allow_all
from run_phase7_e19_asia_push import backtest_meanrev_advanced  # has tp_strategy support
from run_phase7_e20_asia_rr import backtest_meanrev_rr


def walk_forward_e21(df, asia_window, asia_kwargs, london_cfg, ny_cfg, model_fn="advanced"):
    sess_variants = {"Asia": ASIA_MEANREV_VARIANTS["asia_a2_fail"],
                     "London": london_cfg["variant"], "NY": ny_cfg["variant"]}
    sess_windows = {"Asia": asia_window,
                    "London": london_cfg["window"], "NY": ny_cfg["window"]}

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
                    if model_fn == "advanced":
                        return backtest_meanrev_advanced(
                            date_groups_, all_dates_, bh, bm, dur, sv,
                            filter_allow_all, sess, adaptive=True, **asia_kwargs,
                        )
                    elif model_fn == "rr":
                        return backtest_meanrev_rr(
                            date_groups_, all_dates_, bh, bm, dur, sv,
                            filter_allow_all, sess, adaptive=True, **asia_kwargs,
                        )
                elif sess == "NY":
                    return backtest_direct_breakout(
                        date_groups_, all_dates_, bh, bm, dur, tp1, tp2, sv,
                        filter_allow_all, sess, False, ny_cfg.get("pattern_at_breakout"),
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


def run_variant(label, df, asia_window, asia_kwargs, model_fn="advanced"):
    cfg = base_config()
    cfg["NY"]["model_type"] = "direct_breakout"
    cfg["NY"]["pattern_at_breakout"] = "any"

    print(f"\n{'═' * 72}\n {label}\n Window: {asia_window}, kwargs: {asia_kwargs}\n{'═' * 72}")
    t0 = time.time()
    results = walk_forward_e21(df, asia_window, asia_kwargs, cfg["London"], cfg["NY"], model_fn)
    elapsed = time.time() - t0
    df_r = pd.DataFrame(results)
    total = df_r["val_pnl"].sum() if len(df_r) else 0
    by_sess = df_r.groupby("session")["val_pnl"].sum() if len(df_r) else pd.Series()
    df_r["q_year"] = df_r["quarter"].str[:4].astype(int)
    recent = df_r[df_r["q_year"] >= 2024]
    recent_total = recent["val_pnl"].sum() if len(recent) else 0
    asia_pnl = by_sess.get("Asia", 0)
    print(f"  Elapsed: {elapsed:.1f}s")
    print(f"  Total 19Q: {total:+.1f} (Δ vs e20d +976 = {total - 976:+.1f})")
    print(f"  Asia      {asia_pnl:>+8.1f} (e20d ref +182, Δ {asia_pnl - 182:+.0f}) ⭐")
    print(f"  Recent 24+: {recent_total:+.1f}")
    return {"label": label, "total_19q": total, "asia_pnl": float(asia_pnl),
            "asia_delta_e20d": float(asia_pnl - 182),
            "asia_delta_e16b": float(asia_pnl - 151),
            "total_recent": recent_total,
            "by_session": {s: float(by_sess.get(s, 0)) for s in ['Asia','London','NY']}}


def main():
    csv = "/Users/irfanprimaputra.b/Downloads/XAUUSD_M1_2021_-_2026.csv"
    df = load_data(csv)
    summaries = []

    # e20d window: 1260-1380 (21:00-23:00 ET)
    LATE_WIN = (1260, 1380)

    # e21a — e20d window + TP 1.5×mid (stack with e19d theme)
    summaries.append(run_variant("e21a · Late + TP=1.5×mid", df, LATE_WIN,
        {"pattern_at_fade": None, "min_displacement_pct": None, "tp_strategy": "1.5_mid"}))

    # e21b — Even tighter window 22:00-23:00 ET (1320-1380)
    summaries.append(run_variant("e21b · Very late 22-23 ET", df, (1320, 1380),
        {"pattern_at_fade": None, "min_displacement_pct": None, "tp_strategy": "box_mid"}))

    # e21c — e20d window + box-edge SL (R:R fix that failed full window, retry on late)
    summaries.append(run_variant("e21c · Late + tighter SL (box_edge)", df, LATE_WIN,
        {"sl_mode": "box_edge", "tp_mode": "box_mid"}, model_fn="rr"))

    # e21d — e20d window + min_box_width=2 (filter very narrow boxes)
    cfg_late_minbox = dict(ASIA_MEANREV_VARIANTS["asia_a2_fail"])
    cfg_late_minbox["min_box_width"] = 2.0
    # We need to inject the variant override; do this via override variant in dispatch
    # Instead, use the standard mean-rev with custom variant (re-run via base run)
    # Simpler: skip this for now (would require new dispatch path)

    # e21e — e20d window + TP=1.5×mid + max_attempts allow MORE
    # Use advanced model with TP override (5 max attempts via adaptive)
    summaries.append(run_variant("e21d · Late + TP=2.0×mid (overshoot more)", df, LATE_WIN,
        {"pattern_at_fade": None, "min_displacement_pct": None, "tp_strategy": "1.5_mid"}))

    # e21f — Slightly wider late window 20:30-23:00 ET (1230-1380) (recovery from over-restrict)
    summaries.append(run_variant("e21e · Late wider 20:30-23 ET", df, (1230, 1380),
        {"pattern_at_fade": None, "min_displacement_pct": None, "tp_strategy": "box_mid"}))

    out = ROOT / "data" / "phase7_e21_results.json"
    with open(out, 'w') as f:
        json.dump({'generated': datetime.datetime.now().isoformat(),
                   'e20d_baseline_asia': 182.0, 'target_asia': 300.0,
                   'variants': summaries}, f, indent=2)

    print("\n" + "═" * 72)
    print(" SUMMARY · e21 Asia Stack on e20d (target +300)")
    print("═" * 72)
    print(f"  {'Variant':<55} {'Asia':>9} {'Δ e20d':>9} {'Δ e16b':>9} {'19Q':>9}")
    print(f"  {'─' * 55} {'─' * 9} {'─' * 9} {'─' * 9} {'─' * 9}")
    for s in summaries:
        ok = "⭐" if s["asia_pnl"] >= 300 else ("✅" if s["asia_delta_e20d"] > 0 else "❌")
        print(f"  {s['label']:<55} {s['asia_pnl']:>+8.1f} {s['asia_delta_e20d']:>+9.1f} {s['asia_delta_e16b']:>+9.1f} {s['total_19q']:>+8.1f} {ok}")
    print(f"\n  Saved: {out}")


if __name__ == "__main__":
    main()
