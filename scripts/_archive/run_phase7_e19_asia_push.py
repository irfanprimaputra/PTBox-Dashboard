"""Phase 7 e19 — Push Asia from +151 to 300+ pts.

Variants to test:
  e19a — Asia + pattern-at-fade-entry (Naked Forex mirror of NY win)
  e19b — Asia + min_displacement filter (skip weak fakeouts)
  e19c — Asia + box-width adaptive TP (TP scales with box width)
  e19d — Asia COMBO: pattern + min_displacement + adaptive TP

Inherits e16b London + NY config.
"""
import os, sys, json, datetime, time
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT / "scripts"))

from ptbox_quarterly_v3 import (
    CONFIG, load_data, build_date_groups, _check_pattern,
    PATTERN_VARIANTS,
)
from ptbox_quarterly_v4 import ASIA_MEANREV_VARIANTS

from run_phase7_e16_naked_forex import (
    walk_forward_e16, base_config, _bt_dispatch, optimize_session,
    filter_allow_all, backtest_direct_breakout,
)
from run_engine_with_filters import backtest_meanrev_fail_filtered, generate_quarters


# ───────────────────────────────────────────────────────────────────
# 🆕 NEW: Asia mean-rev with pattern + min_displacement + dynamic TP
# ───────────────────────────────────────────────────────────────────

def backtest_meanrev_advanced(date_groups, all_dates, bh, bm, dur, variant,
                                allowed_fn=None, session_name="Asia", adaptive=True,
                                pattern_at_fade=None, min_displacement_pct=None,
                                tp_strategy="box_mid"):
    """Asia mean-rev with advanced filters.

    pattern_at_fade: None | "pin_bar" | "engulfing" | "any"
        Check pattern on the fade candle (when close re-enters box).
    min_displacement_pct: None | 0.0-1.0
        Only fade if breakout extreme reached >= this fraction of box width
        beyond box edge. E.g., 0.5 = wait until breakout reaches 50% box width
        beyond edge before considering fade.
    tp_strategy:
        "box_mid"      — TP at midpoint (default)
        "opposite"     — TP at opposite box edge (wider)
        "0.7_mid"      — TP at 70% to midpoint (tighter, faster exit)
        "1.5_mid"      — TP at 150% (overshoot midpoint, capture continuation)
    """
    SL_BUFFER = variant.get('sl_buffer', 1.0)
    MIN_SL = variant.get('min_sl', 1.0)
    MIN_BW = variant.get('min_box_width', 1.0)
    MAX_ATT = 5 if adaptive else CONFIG['max_attempts']
    BS = bh * 60 + bm
    BE = BS + dur

    if allowed_fn is None:
        allowed_fn = lambda d, s, dr: True

    tw = tl = 0
    pnl_list = []

    for day in all_dates:
        if day not in date_groups:
            pnl_list.append(0.); continue

        g = date_groups[day]
        tm = g['tm'].values
        H = g['high'].values; L = g['low'].values
        C = g['close'].values; O = g['open'].values

        bk = (tm >= BS) & (tm < BE)
        if bk.sum() == 0:
            pnl_list.append(0.); continue
        bx_hi = H[bk].max(); bx_lo = L[bk].min()
        box_width = bx_hi - bx_lo
        if box_width < MIN_BW:
            pnl_list.append(0.); continue
        box_mid = (bx_hi + bx_lo) / 2.0

        tr = tm >= BE
        if tr.sum() < 3:
            pnl_list.append(0.); continue

        Hi = H[tr]; Lo = L[tr]; Cl = C[tr]; Op = O[tr]

        att = 0; in_trade = False
        bk_dir = 0; bk_extreme = None
        pending = None
        ep = sp = tp_ = 0.; ed = 0
        dp = 0.; dw = dl = 0
        st = None; done = False
        day_wins = 0; day_losses = 0

        for i in range(len(Cl)):
            ch = Hi[i]; cl = Lo[i]; cc = Cl[i]; co = Op[i]

            if adaptive and (day_losses >= 2 or day_wins >= 1):
                done = True

            if pending is not None and not in_trade:
                ent_dir, extreme = pending
                pending = None
                if not allowed_fn(day, session_name, ent_dir):
                    in_trade = False; bk_dir = 0; bk_extreme = None
                    continue

                # min_displacement filter: was breakout strong enough?
                if min_displacement_pct is not None:
                    if ent_dir == 1:
                        # Fade long after up-fail: breakout was UP
                        # extreme = highest point of upbreak
                        displacement = extreme - bx_hi
                    else:
                        # Fade short after down-fail: breakout was DOWN
                        displacement = bx_lo - extreme
                    if displacement < min_displacement_pct * box_width:
                        in_trade = False; bk_dir = 0; bk_extreme = None
                        continue  # weak breakout, skip fade

                # Pattern at fade-entry candle (current bar i)
                if pattern_at_fade is not None and i > 0:
                    prev_oh = (Op[i-1], Hi[i-1], Lo[i-1], Cl[i-1])
                    curr_oh = (co, ch, cl, cc)
                    if not _check_pattern(prev_oh, curr_oh, ent_dir, pattern_at_fade):
                        in_trade = False; bk_dir = 0; bk_extreme = None
                        continue

                ep = co; ed = ent_dir
                # SL based on extreme
                if ed == 1:
                    sp = extreme - SL_BUFFER
                else:
                    sp = extreme + SL_BUFFER

                # TP strategy
                if tp_strategy == "box_mid":
                    tp_ = box_mid
                elif tp_strategy == "opposite":
                    tp_ = bx_lo if ed == 1 else bx_hi
                elif tp_strategy == "0.7_mid":
                    diff = box_mid - ep
                    tp_ = ep + 0.7 * diff
                elif tp_strategy == "1.5_mid":
                    diff = box_mid - ep
                    tp_ = ep + 1.5 * diff
                else:
                    tp_ = box_mid

                sl_dist = abs(ep - sp); tp_dist = abs(tp_ - ep)
                degenerate = (
                    sl_dist < MIN_SL or tp_dist < 0.5 or
                    (ed == 1 and tp_ <= ep) or (ed == -1 and tp_ >= ep) or
                    (ed == 1 and sp >= ep) or (ed == -1 and sp <= ep)
                )
                if degenerate:
                    in_trade = False; bk_dir = 0; bk_extreme = None; continue
                in_trade = True; att += 1

            if in_trade:
                if ed == 1:
                    if cl <= sp:
                        dl += 1; dp -= (ep - sp); in_trade = False
                        bk_dir = 0; bk_extreme = None; st = i; day_losses += 1
                        if att >= MAX_ATT: done = True
                        continue
                    if ch >= tp_:
                        dw += 1; dp += (tp_ - ep); in_trade = False
                        bk_dir = 0; bk_extreme = None; st = i; day_wins += 1
                        if att >= MAX_ATT: done = True
                        continue
                else:
                    if ch >= sp:
                        dl += 1; dp -= (sp - ep); in_trade = False
                        bk_dir = 0; bk_extreme = None; st = i; day_losses += 1
                        if att >= MAX_ATT: done = True
                        continue
                    if cl <= tp_:
                        dw += 1; dp += (ep - tp_); in_trade = False
                        bk_dir = 0; bk_extreme = None; st = i; day_wins += 1
                        if att >= MAX_ATT: done = True
                        continue

            if done or in_trade or att >= MAX_ATT: continue
            if pending is not None: continue
            if st is not None and i <= st: continue

            if bk_dir == 0:
                if cc > bx_hi: bk_dir = 1; bk_extreme = ch
                elif cc < bx_lo: bk_dir = -1; bk_extreme = cl
            elif bk_dir == 1:
                if ch > bk_extreme: bk_extreme = ch
                if cc < bx_lo: bk_dir = -1; bk_extreme = cl
                elif bx_lo < cc < bx_hi: pending = (-1, bk_extreme)
            elif bk_dir == -1:
                if cl < bk_extreme: bk_extreme = cl
                if cc > bx_hi: bk_dir = 1; bk_extreme = ch
                elif bx_lo < cc < bx_hi: pending = (1, bk_extreme)

        tw += dw; tl += dl
        pnl_list.append(dp)

    tt = tw + tl
    if tt < CONFIG['min_trades']:
        return None

    return {
        'bh': bh, 'bm': bm, 'dur': dur,
        'trades': tt, 'wins': tw, 'losses': tl,
        'winrate': round(tw/tt*100, 1) if tt else 0,
        'pnl': round(sum(pnl_list), 1),
    }


# ───────────────────────────────────────────────────────────────────
# 🎯 Walk-forward with custom Asia model
# ───────────────────────────────────────────────────────────────────

def walk_forward_asia_advanced(df, asia_kwargs, london_cfg, ny_cfg):
    """asia_kwargs: dict with pattern_at_fade, min_displacement_pct, tp_strategy."""
    sess_variants = {
        "Asia": ASIA_MEANREV_VARIANTS["asia_a2_fail"],
        "London": london_cfg["variant"],
        "NY": ny_cfg["variant"],
    }
    sess_windows = {
        "Asia": (CONFIG['sessions']['Asia']['start_min'], CONFIG['sessions']['Asia']['end_min']),
        "London": london_cfg["window"],
        "NY": ny_cfg["window"],
    }
    sess_models = {
        "Asia": "mean_rev_advanced",
        "London": london_cfg["model_type"],
        "NY": ny_cfg["model_type"],
    }
    sess_pattern = {
        "London": london_cfg.get("pattern_at_breakout"),
        "NY": ny_cfg.get("pattern_at_breakout"),
    }

    data_start = df['date_et'].min()
    data_end = df['date_et'].max()
    quarters = generate_quarters(data_start, data_end)
    results = []

    for idx, (train_s, train_e, val_s, val_e, qlabel) in enumerate(quarters, 1):
        df_train = df[(df['date_et']>=train_s)&(df['date_et']<=train_e)]
        df_val = df[(df['date_et']>=val_s)&(df['date_et']<=val_e)]
        tg, td = build_date_groups(df_train)
        vg, vd = build_date_groups(df_val)
        if len(td) < 15 or len(vd) < 10: continue

        for sess in ['Asia','London','NY']:
            sv = sess_variants[sess]
            sw = sess_windows[sess]
            model = sess_models[sess]

            # Optimize window
            tps = CONFIG['tp_per_session'][sess]
            tp1, tp2 = tps['tp1'], tps['tp2']
            durs = CONFIG['durations']
            step = CONFIG['coarse_step']

            def dispatch(date_groups_, all_dates_, bh, bm, dur):
                if model == "mean_rev_advanced":
                    return backtest_meanrev_advanced(
                        date_groups_, all_dates_, bh, bm, dur, sv,
                        filter_allow_all, sess, adaptive=True,
                        **asia_kwargs,
                    )
                elif model == "direct_breakout":
                    return backtest_direct_breakout(
                        date_groups_, all_dates_, bh, bm, dur, tp1, tp2, sv,
                        filter_allow_all, sess, False, sess_pattern.get(sess),
                    )
                else:
                    from run_engine_with_filters import backtest_filtered
                    return backtest_filtered(
                        date_groups_, all_dates_, bh, bm, dur, tp1, tp2, sv,
                        filter_allow_all, sess, False,
                    )

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
                    seen.add(bmt)
                    fh = bmt//60; fm = bmt%60
                    for dur in durs:
                        if bmt + dur >= sw[1]: continue
                        r = dispatch(tg, td, fh, fm, dur)
                        if r: fine.append(r)
            if not fine: continue
            best = max(fine, key=lambda r: r['pnl'])

            r_val = dispatch(vg, vd, best['bh'], best['bm'], best['dur'])
            val_pnl = r_val['pnl'] if r_val else 0
            val_trades = r_val['trades'] if r_val else 0
            val_wr = r_val['winrate'] if r_val else 0
            results.append({
                'quarter': qlabel, 'session': sess,
                'val_pnl': val_pnl, 'val_trades': val_trades, 'val_winrate': val_wr,
            })
    return results


def run_variant(label, df, asia_kwargs):
    cfg = base_config()
    cfg["NY"]["model_type"] = "direct_breakout"
    cfg["NY"]["pattern_at_breakout"] = "any"
    london_cfg = cfg["London"]
    ny_cfg = cfg["NY"]

    print(f"\n{'═' * 72}")
    print(f" {label}")
    print(f" Asia kwargs: {asia_kwargs}")
    print(f"{'═' * 72}")
    t0 = time.time()
    results = walk_forward_asia_advanced(df, asia_kwargs, london_cfg, ny_cfg)
    elapsed = time.time() - t0
    df_r = pd.DataFrame(results)
    total = df_r["val_pnl"].sum() if len(df_r) else 0
    by_sess = df_r.groupby("session")["val_pnl"].sum() if len(df_r) else pd.Series()
    df_r["q_year"] = df_r["quarter"].str[:4].astype(int)
    recent = df_r[df_r["q_year"] >= 2024]
    recent_total = recent["val_pnl"].sum() if len(recent) else 0

    asia_pnl = by_sess.get("Asia", 0)
    print(f"  Elapsed: {elapsed:.1f}s")
    print(f"  Total 19Q: {total:+.1f} (Δ vs e16b +945 = {total - 945:+.1f})")
    print(f"  Asia      {asia_pnl:>+8.1f} (e16b ref +151, Δ {asia_pnl - 151:+.0f}) ⭐")
    print(f"  London    {by_sess.get('London', 0):>+8.1f}")
    print(f"  NY        {by_sess.get('NY', 0):>+8.1f}")
    print(f"  Recent 24+: {recent_total:+.1f}")

    return {
        "label": label, "total_19q": total, "total_recent": recent_total,
        "asia_pnl": float(asia_pnl), "asia_delta": float(asia_pnl - 151),
        "by_session": {s: float(by_sess.get(s, 0)) for s in ['Asia','London','NY']},
    }


def main():
    csv = "/Users/irfanprimaputra.b/Downloads/XAUUSD_M1_2021_-_2026.csv"
    df = load_data(csv)
    summaries = []

    # e19a — Pattern at fade entry (Naked Forex mirror of NY win)
    summaries.append(run_variant("e19a · Asia + pattern-at-fade-entry (any)", df,
        {"pattern_at_fade": "any", "min_displacement_pct": None, "tp_strategy": "box_mid"}))

    # e19b — Min displacement filter (skip weak fakeouts)
    summaries.append(run_variant("e19b · Asia + min_displacement 0.5", df,
        {"pattern_at_fade": None, "min_displacement_pct": 0.5, "tp_strategy": "box_mid"}))

    # e19c — TP variation: tighter
    summaries.append(run_variant("e19c · Asia + TP=0.7×mid (tighter)", df,
        {"pattern_at_fade": None, "min_displacement_pct": None, "tp_strategy": "0.7_mid"}))

    # e19d — TP variation: wider (overshoot)
    summaries.append(run_variant("e19d · Asia + TP=1.5×mid (overshoot)", df,
        {"pattern_at_fade": None, "min_displacement_pct": None, "tp_strategy": "1.5_mid"}))

    # e19e — Combo: pattern + min_displacement
    summaries.append(run_variant("e19e · Asia COMBO: pattern + min_disp 0.3", df,
        {"pattern_at_fade": "any", "min_displacement_pct": 0.3, "tp_strategy": "box_mid"}))

    out = ROOT / "data" / "phase7_e19_results.json"
    with open(out, 'w') as f:
        json.dump({
            'generated': datetime.datetime.now().isoformat(),
            'e16b_baseline_asia': 151.0,
            'target_asia': 300.0,
            'variants': summaries,
        }, f, indent=2)

    print("\n" + "═" * 72)
    print(" SUMMARY · e19 Asia Push (target +300, current +151)")
    print("═" * 72)
    print(f"  {'Variant':<55} {'Asia':>9} {'Δ Asia':>9} {'19Q':>9}")
    print(f"  {'─' * 55} {'─' * 9} {'─' * 9} {'─' * 9}")
    for s in summaries:
        ok = "⭐" if s["asia_pnl"] >= 300 else ("✅" if s["asia_delta"] > 0 else "❌")
        print(f"  {s['label']:<55} {s['asia_pnl']:>+8.1f} {s['asia_delta']:>+9.1f} {s['total_19q']:>+8.1f} {ok}")
    print(f"\n  e16b baseline Asia: +151\n  Target: +300+\n  Saved: {out}")


if __name__ == "__main__":
    main()
