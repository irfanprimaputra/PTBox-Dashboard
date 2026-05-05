"""Phase 7 e16 Series — Naked Forex direct breakout + pattern-at-breakout.

User ideas applied:
  1. Direct breakout entry (skip pullback wait)
  2. Naked Forex pattern at BREAKOUT candle (not pullback)
  3. Combine variants

Variants:
  e16a — NY direct breakout entry (no pullback)
  e16b — NY breakout + pattern-at-breakout (pin/engulfing on breakout candle)
  e16c — London breakout + pattern-at-breakout (test better than pullback pattern)
  e16d — Combo: NY Silver Bullet timing + direct breakout + pattern confirm

Reports BOTH 5-yr walk-forward AND recent 2024-2026 performance.
"""
import os, sys, json, datetime, time
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT / "scripts"))

from ptbox_quarterly_v3 import (
    CONFIG, load_data, build_date_groups, _check_pattern, _is_pin_bar,
    _is_engulfing, _is_inside_bar, PATTERN_VARIANTS,
)
from ptbox_quarterly_v4 import ASIA_MEANREV_VARIANTS

from run_engine_with_filters import (
    backtest_meanrev_fail_filtered, generate_quarters,
)


# ───────────────────────────────────────────────────────────────────
# 🆕 NEW BACKTEST: Direct breakout entry + pattern-at-breakout
# ───────────────────────────────────────────────────────────────────

def backtest_direct_breakout(date_groups, all_dates, bh, bm, dur, tp1, tp2,
                              variant, allowed_fn=None, session_name="",
                              adaptive=False, pattern_at_breakout=None):
    """Direct breakout entry — enter at breakout candle close, no pullback wait.

    pattern_at_breakout: None (no filter) | "pin_bar" | "engulfing" | "any"
        Checks pattern on breakout candle itself (Naked Forex confirmation).
    """
    SL_FIXED = CONFIG['sl_pts']
    MAX_ATT = 5 if adaptive else CONFIG['max_attempts']
    BS = bh * 60 + bm
    BE = BS + dur
    tw = tl = t1c = t2c = 0
    pnl_list = []

    skip_box_gt = variant.get('skip_box_gt')
    sl_box_mult = variant.get('sl_box_mult')
    tp_box_mult = variant.get('tp_box_mult')
    min_sl = variant.get('min_sl', 3.0)

    if allowed_fn is None:
        allowed_fn = lambda d, s, dr: True

    for day in all_dates:
        if day not in date_groups:
            pnl_list.append(0.); continue

        g  = date_groups[day]
        tm = g['tm'].values
        H  = g['high'].values; L  = g['low'].values
        C  = g['close'].values; O  = g['open'].values

        bk = (tm >= BS) & (tm < BE)
        if bk.sum() == 0:
            pnl_list.append(0.); continue
        bx_hi = H[bk].max(); bx_lo = L[bk].min()
        box_width = bx_hi - bx_lo
        if skip_box_gt is not None and box_width > skip_box_gt:
            pnl_list.append(0.); continue

        SL = max(min_sl, sl_box_mult * box_width) if sl_box_mult is not None else SL_FIXED
        if tp_box_mult is not None:
            tp1_use = tp_box_mult[0] * SL
            tp2_use = tp_box_mult[1] * SL
        else:
            tp1_use = tp1; tp2_use = tp2

        tr = tm >= BE
        if tr.sum() < 3:
            pnl_list.append(0.); continue

        Hi = H[tr]; Lo = L[tr]; Cl = C[tr]; Op = O[tr]

        att = bkd = 0
        ep = sp = t1p = t2p = 0.
        itr = False; done = False; st = None
        dp = 0.; dw = dl = d1 = d2 = 0
        pending = None
        day_wins = 0; day_losses = 0

        for i in range(len(Cl)):
            ch = Hi[i]; cl = Lo[i]; cc = Cl[i]; co = Op[i]

            if adaptive and (day_losses >= 2 or day_wins >= 1):
                done = True

            # Pending entry → enter at this bar's open
            if pending is not None and not itr:
                ed, breakout_close, breakout_low, breakout_high = pending
                pending = None
                if not allowed_fn(day, session_name, ed):
                    continue
                ep = co
                att += 1; itr = True; bkd = ed
                if ed == 1:
                    sp  = bx_lo - SL  # SL below box (cleaner than breakout low - SL)
                    t1p = ep + tp1_use
                    t2p = ep + tp2_use
                else:
                    sp  = bx_hi + SL
                    t1p = ep - tp1_use
                    t2p = ep - tp2_use

            if itr:
                if (bkd==1 and ch>=t2p) or (bkd==-1 and cl<=t2p):
                    dw+=1; d2+=1; dp+=tp2_use; itr=False; done=True; day_wins+=1; continue
                if (bkd==1 and ch>=t1p) or (bkd==-1 and cl<=t1p):
                    dw+=1; d1+=1; dp+=tp1_use; itr=False; done=True; day_wins+=1; continue
                if (bkd==1 and cl<=sp) or (bkd==-1 and ch>=sp):
                    dl+=1; dp-=abs(ep-sp); itr=False; bkd=0; st=i; day_losses+=1
                    if att >= MAX_ATT: done=True
                    continue

            if done or itr or att >= MAX_ATT: continue
            if pending is not None: continue
            if st is not None and i <= st: continue

            # Detect breakout candle (close beyond box edge)
            is_up_breakout   = bkd != 1  and cc > bx_hi
            is_down_breakout = bkd != -1 and cc < bx_lo

            if is_up_breakout or is_down_breakout:
                direction = 1 if is_up_breakout else -1
                # Pattern check at breakout candle itself
                pattern_ok = True
                if pattern_at_breakout is not None and i > 0:
                    prev_oh = (Op[i-1], Hi[i-1], Lo[i-1], Cl[i-1])
                    curr_oh = (co, ch, cl, cc)
                    pattern_ok = _check_pattern(prev_oh, curr_oh, direction, pattern_at_breakout)

                if pattern_ok:
                    # Direct entry at next bar's open
                    pending = (direction, cc, cl, ch)
                    bkd = direction

        tw += dw; tl += dl; t1c += d1; t2c += d2
        pnl_list.append(dp)

    tt = tw + tl
    if tt < CONFIG['min_trades']:
        return None

    return {
        'bh': bh, 'bm': bm, 'dur': dur,
        'trades': tt, 'wins': tw, 'losses': tl,
        'winrate': round(tw/tt*100, 1),
        'pnl': round(sum(pnl_list), 1),
        'tp1': t1c, 'tp2': t2c,
    }


# ───────────────────────────────────────────────────────────────────
# 🎯 Walk-forward orchestrator — flexible per-session model
# ───────────────────────────────────────────────────────────────────

def _bt_dispatch(model_type, variant, date_groups, all_dates, bh, bm, dur, tp1, tp2,
                 allowed_fn, session_name, adaptive, pattern_at_breakout=None):
    if model_type == "mean_rev_fail":
        return backtest_meanrev_fail_filtered(date_groups, all_dates, bh, bm, dur,
                                               variant, allowed_fn, session_name, adaptive)
    if model_type == "direct_breakout":
        return backtest_direct_breakout(date_groups, all_dates, bh, bm, dur, tp1, tp2,
                                         variant, allowed_fn, session_name, adaptive, pattern_at_breakout)
    # Default: breakout-pullback (existing v3 backtest)
    from run_engine_with_filters import backtest_filtered
    return backtest_filtered(date_groups, all_dates, bh, bm, dur, tp1, tp2,
                             variant, allowed_fn, session_name, adaptive)


def optimize_session(date_groups, all_dates, sess_name, variant, model_type,
                      window, allowed_fn, adaptive, pattern_at_breakout=None):
    s, e = window
    tps = CONFIG['tp_per_session'][sess_name]
    tp1, tp2 = tps['tp1'], tps['tp2']
    durs = CONFIG['durations']
    step = CONFIG['coarse_step']
    fw = CONFIG['fine_window']

    coarse = []
    for bmt in range(s, e, step):
        bh = bmt // 60; bm = bmt % 60
        for dur in durs:
            if bmt + dur >= e: continue
            r = _bt_dispatch(model_type, variant, date_groups, all_dates, bh, bm, dur, tp1, tp2,
                             allowed_fn, sess_name, adaptive, pattern_at_breakout)
            if r: coarse.append(r)
    if not coarse: return []
    df_c = pd.DataFrame(coarse)
    top_centers = df_c.nlargest(5, 'pnl')[['bh','bm']].values

    seen = set(); fine = []
    for bh, bm in top_centers:
        center = int(bh)*60 + int(bm)
        for bmt in range(max(s, center-fw), min(e, center+fw+1)):
            if bmt in seen: continue
            seen.add(bmt)
            fh = bmt//60; fm = bmt%60
            for dur in durs:
                if bmt + dur >= e: continue
                r = _bt_dispatch(model_type, variant, date_groups, all_dates, fh, fm, dur, tp1, tp2,
                                 allowed_fn, sess_name, adaptive, pattern_at_breakout)
                if r: fine.append(r)
    return fine


def filter_allow_all(d, s, dr): return True


def walk_forward_e16(df, sess_config):
    """sess_config: dict per session with model_type, variant, window, adaptive, pattern_at_breakout."""
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
            cfg = sess_config[sess]
            fine = optimize_session(
                tg, td, sess, cfg['variant'], cfg['model_type'], cfg['window'],
                filter_allow_all, cfg['adaptive'], cfg.get('pattern_at_breakout'),
            )
            if not fine: continue
            best = max(fine, key=lambda r: r['pnl'])
            tps = CONFIG['tp_per_session'][sess]
            r_val = _bt_dispatch(
                cfg['model_type'], cfg['variant'], vg, vd, best['bh'], best['bm'], best['dur'],
                tps['tp1'], tps['tp2'], filter_allow_all, sess, cfg['adaptive'], cfg.get('pattern_at_breakout'),
            )
            val_pnl = r_val['pnl'] if r_val else 0
            val_trades = r_val['trades'] if r_val else 0
            val_wr = r_val['winrate'] if r_val else 0
            results.append({
                'quarter': qlabel, 'session': sess,
                'val_pnl': val_pnl, 'val_trades': val_trades, 'val_winrate': val_wr,
            })
    return results


# ───────────────────────────────────────────────────────────────────
# 🚀 Variants
# ───────────────────────────────────────────────────────────────────

# e14d baseline session config
def base_config():
    return {
        "Asia": {
            "model_type": "mean_rev_fail",
            "variant": ASIA_MEANREV_VARIANTS["asia_a2_fail"],
            "window": (CONFIG['sessions']['Asia']['start_min'], CONFIG['sessions']['Asia']['end_min']),
            "adaptive": True,
        },
        "London": {
            "model_type": "breakout_pullback",
            "variant": PATTERN_VARIANTS["any_pattern"],
            "window": (CONFIG['sessions']['London']['start_min'], CONFIG['sessions']['London']['end_min']),
            "adaptive": False,
        },
        "NY": {
            "model_type": "breakout_pullback",
            "variant": PATTERN_VARIANTS["dyn_sl_tp_baseline"],
            "window": (CONFIG['sessions']['NY']['start_min'], CONFIG['sessions']['NY']['end_min']),
            "adaptive": False,
        },
    }


def run_variant(label, df, cfg):
    print(f"\n{'═' * 72}")
    print(f" {label}")
    print(f"{'═' * 72}")
    t0 = time.time()
    results = walk_forward_e16(df, cfg)
    elapsed = time.time() - t0
    df_r = pd.DataFrame(results)

    total = df_r["val_pnl"].sum() if len(df_r) else 0
    by_sess = df_r.groupby("session")["val_pnl"].sum() if len(df_r) else pd.Series()

    # Recent: 2024Q1 onwards
    df_r["q_year"] = df_r["quarter"].str[:4].astype(int)
    recent = df_r[df_r["q_year"] >= 2024]
    recent_total = recent["val_pnl"].sum() if len(recent) else 0
    recent_by_sess = recent.groupby("session")["val_pnl"].sum() if len(recent) else pd.Series()

    print(f"  Elapsed: {elapsed:.1f}s")
    print(f"  Total 19Q (5y) PnL: {total:+.1f} (Δ vs e14d +549 = {total - 549:+.1f})")
    for sess in ['Asia','London','NY']:
        v = by_sess.get(sess, 0)
        e14d_ref = {"Asia": 151, "London": 486, "NY": -88}[sess]
        print(f"    {sess:<7} {v:>+8.1f} (e14d ref {e14d_ref:+d}, Δ {v - e14d_ref:+.0f})")
    print(f"  Recent (2024+): {recent_total:+.1f} ({len(recent)//3} quarters)")
    for sess in ['Asia','London','NY']:
        v = recent_by_sess.get(sess, 0)
        print(f"    {sess:<7} {v:>+8.1f}")

    return {
        "label": label,
        "total_19q": total,
        "total_recent": recent_total,
        "by_session": {s: float(by_sess.get(s, 0)) for s in ['Asia','London','NY']},
        "recent_by_session": {s: float(recent_by_sess.get(s, 0)) for s in ['Asia','London','NY']},
    }


def main():
    csv = "/Users/irfanprimaputra.b/Downloads/XAUUSD_M1_2021_-_2026.csv"
    df = load_data(csv)
    summaries = []

    # e16a — NY direct breakout entry (no pullback)
    cfg = base_config()
    cfg["NY"]["model_type"] = "direct_breakout"
    summaries.append(run_variant("e16a · NY direct breakout entry (no pullback)", df, cfg))

    # e16b — NY direct breakout + pattern at breakout candle
    cfg = base_config()
    cfg["NY"]["model_type"] = "direct_breakout"
    cfg["NY"]["pattern_at_breakout"] = "any"
    summaries.append(run_variant("e16b · NY direct + pattern-at-breakout (any)", df, cfg))

    # e16c — London direct breakout (test if better than current)
    cfg = base_config()
    cfg["London"]["model_type"] = "direct_breakout"
    summaries.append(run_variant("e16c · London direct breakout", df, cfg))

    # e16d — Combo: NY Silver Bullet window + direct breakout + pattern
    cfg = base_config()
    cfg["NY"]["model_type"] = "direct_breakout"
    cfg["NY"]["pattern_at_breakout"] = "any"
    cfg["NY"]["window"] = (615, 660)  # 10:15-11:00 EST
    summaries.append(run_variant("e16d · NY Silver Bullet + direct + pattern", df, cfg))

    out = ROOT / "data" / "phase7_e16_results.json"
    with open(out, 'w') as f:
        json.dump({
            'generated': datetime.datetime.now().isoformat(),
            'e14d_baseline': 549.0,
            'variants': summaries,
        }, f, indent=2)

    print("\n" + "═" * 72)
    print(" SUMMARY · e16 Series (Naked Forex direct breakout)")
    print("═" * 72)
    print(f"  {'Variant':<55} {'19Q':>9} {'Recent24+':>11} {'NY':>9}")
    print(f"  {'─' * 55} {'─' * 9} {'─' * 11} {'─' * 9}")
    for s in summaries:
        print(f"  {s['label']:<55} {s['total_19q']:>+8.1f} {s['total_recent']:>+10.1f} {s['by_session']['NY']:>+9.1f}")
    print(f"\n  e14d baseline: 19Q +549, NY -88")
    print(f"  Saved: {out}")


if __name__ == "__main__":
    main()
