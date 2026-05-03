"""Phase 7 — Engine integration: walk-forward 19Q with V4 filter active.

Wraps existing v3+v4 backtest functions, injects pre-computed filter mask
from macro bias + session chain. Compares filtered walk-forward vs e013
baseline (+375 pts).

Usage:
    python3 scripts/run_engine_with_filters.py [csv_path]

Output:
    data/phase7_walkforward_filtered.csv  — per-Q × session × variant
    data/phase7_summary.json
"""
import os, sys, json, datetime, time
from pathlib import Path
import pandas as pd
import numpy as np

# Add code dir to path so we can import v3/v4
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "code"))

from ptbox_quarterly_v3 import (
    CONFIG, load_data, build_date_groups, BOX_QUALITY_VARIANTS,
    PATTERN_VARIANTS, _check_pattern, _is_pin_bar,
)
from ptbox_quarterly_v4 import (
    ASIA_MEANREV_VARIANTS,
)


# ───────────────────────────────────────────────────────────────────
# 🛡️ FILTER MASK PRE-COMPUTATION
# ───────────────────────────────────────────────────────────────────

# High-conviction chains (from compute_session_chain.py, WR ≥50%)
HIGH_CONVICTION_CHAINS = {
    ("TREND_DOWN", "TREND_DOWN", "V_UP"):       "UP",
    ("V_UP",       "TREND_DOWN", "TREND_DOWN"): "UP",
    ("RANGE",      "TREND_UP",   "TREND_UP"):   "DOWN",
    ("RANGE",      "TREND_DOWN", "TREND_UP"):   "DOWN",
    ("TREND_DOWN", "RANGE",      "TREND_DOWN"): "DOWN",
    ("V_DOWN",     "TREND_UP",   "TREND_DOWN"): "DOWN",
    ("TREND_DOWN", "TREND_DOWN", "TREND_UP"):   "UP",
}


def build_filter_masks():
    """Returns dict: (date, session, direction) → True/False (allowed)."""
    print("Pre-computing filter masks...")

    macro = pd.read_csv(ROOT / "data" / "macro" / "daily_bias_score.csv")
    macro["date"] = pd.to_datetime(macro["date"]).dt.date
    macro_map = dict(zip(macro["date"], macro["bias_score"]))

    sess = pd.read_csv(ROOT / "data" / "session_behavior.csv")
    sess["date"] = pd.to_datetime(sess["date"]).dt.date
    sess_wide = sess.pivot(index="date", columns="session", values="state")

    chain_pred = {}  # date → predicted NY direction (or None)
    dates_sorted = sorted(sess_wide.index)
    for i, d in enumerate(dates_sorted):
        if i == 0:
            continue
        prev = dates_sorted[i-1]
        try:
            ny_prev = sess_wide.loc[prev, "NY"]
            asia    = sess_wide.loc[d, "Asia"]
            london  = sess_wide.loc[d, "London"]
            chain_pred[d] = HIGH_CONVICTION_CHAINS.get((ny_prev, asia, london))
        except (KeyError, ValueError):
            chain_pred[d] = None

    # Filter mask: (date, direction) → True/False
    # direction: 1 = long, -1 = short
    macro_skip_long  = lambda d: macro_map.get(d, 0) <= -1
    macro_skip_short = lambda d: macro_map.get(d, 0) >= 1

    chain_skip_long  = lambda d: chain_pred.get(d) == "DOWN"
    chain_skip_short = lambda d: chain_pred.get(d) == "UP"

    def allowed(date, session, direction):
        # direction: 1 long, -1 short
        if direction == 1:
            if macro_skip_long(date):  return False
            if session == "NY" and chain_skip_long(date): return False
        elif direction == -1:
            if macro_skip_short(date): return False
            if session == "NY" and chain_skip_short(date): return False
        return True

    print(f"  Macro coverage: {len(macro_map):,} dates")
    print(f"  Chain coverage: {sum(1 for v in chain_pred.values() if v is not None):,} dates with prediction")
    return allowed


# ───────────────────────────────────────────────────────────────────
# 🔁 FILTERED BACKTEST FUNCTIONS (wrap v3.backtest, v4.backtest_meanrev_fail)
# ───────────────────────────────────────────────────────────────────

def backtest_filtered(date_groups, all_dates, bh, bm, dur, tp1, tp2,
                       variant, allowed_fn, session_name, adaptive=True):
    """Wraps v3.backtest with filter + adaptive max_attempts.

    Filter: skip trade if allowed_fn(date, session, direction) == False
    Adaptive: stop session if cumulative wins>=1 OR losses>=2
    """
    if variant is None:
        variant = BOX_QUALITY_VARIANTS["control"]

    SL_FIXED = CONFIG['sl_pts']
    MAX_ATT = 5 if adaptive else CONFIG['max_attempts']  # adaptive uses 2L/1W rule, allow more raw attempts
    BS = bh * 60 + bm
    BE = BS + dur
    tw = tl = t1c = t2c = 0
    pnl_list = []

    skip_box_gt = variant.get('skip_box_gt')
    sl_box_mult = variant.get('sl_box_mult')
    tp_box_mult = variant.get('tp_box_mult')
    min_sl = variant.get('min_sl', 3.0)
    pattern_filter = variant.get('pattern_filter')

    for day in all_dates:
        if day not in date_groups:
            pnl_list.append(0.); continue

        g  = date_groups[day]
        tm = g['tm'].values
        H  = g['high'].values
        L  = g['low'].values
        C  = g['close'].values
        O  = g['open'].values

        bk = (tm >= BS) & (tm < BE)
        if bk.sum() == 0:
            pnl_list.append(0.); continue
        bx_hi = H[bk].max()
        bx_lo = L[bk].min()
        box_width = bx_hi - bx_lo

        if skip_box_gt is not None and box_width > skip_box_gt:
            pnl_list.append(0.); continue

        SL = max(min_sl, sl_box_mult * box_width) if sl_box_mult is not None else SL_FIXED
        if tp_box_mult is not None:
            tp1_use = tp_box_mult[0] * SL
            tp2_use = tp_box_mult[1] * SL
        else:
            tp1_use = tp1
            tp2_use = tp2

        tr = tm >= BE
        if tr.sum() < 3:
            pnl_list.append(0.); continue

        Hi = H[tr]; Lo = L[tr]; Cl = C[tr]; Op = O[tr]

        att = bkd = 0; bi = -1; itr = False
        ep = sp = t1p = t2p = 0.
        done = False; st = None; dp = 0.
        dw = dl = d1 = d2 = 0
        pending = None

        # Adaptive tracking
        day_wins = 0
        day_losses = 0

        for i in range(len(Cl)):
            ch = Hi[i]; cl = Lo[i]; cc = Cl[i]; co = Op[i]

            # Adaptive: stop if 2L or 1W
            if adaptive and (day_losses >= 2 or day_wins >= 1):
                done = True

            if pending is not None and not itr:
                ed, pl_, ph_ = pending
                pending = None

                # ✨ FILTER CHECK — gate trade entry
                if not allowed_fn(day, session_name, ed):
                    # Skip this trade entirely, reset
                    bkd = 0; bi = -1
                    continue

                ep  = co
                att += 1; itr = True; bkd = ed; bi = -1
                if ed == 1:
                    sp  = pl_ - SL
                    t1p = ep + tp1_use
                    t2p = ep + tp2_use
                else:
                    sp  = ph_ + SL
                    t1p = ep - tp1_use
                    t2p = ep - tp2_use

            if itr:
                if (bkd==1 and ch>=t2p) or (bkd==-1 and cl<=t2p):
                    dw+=1; d2+=1; dp+=tp2_use; itr=False; done=True; day_wins += 1; continue
                if (bkd==1 and ch>=t1p) or (bkd==-1 and cl<=t1p):
                    dw+=1; d1+=1; dp+=tp1_use; itr=False; done=True; day_wins += 1; continue
                if (bkd==1 and cl<=sp)  or (bkd==-1 and ch>=sp):
                    dl+=1; dp-=abs(ep-sp); itr=False; bkd=0; bi=-1; st=i; day_losses += 1
                    if att >= MAX_ATT: done=True
                    continue

            if done or itr or att >= MAX_ATT: continue
            if pending is not None: continue
            if st is not None and i <= st: continue

            if bkd != 1  and cc > bx_hi: bkd=1;  bi=i
            elif bkd != -1 and cc < bx_lo: bkd=-1; bi=i

            if bkd != 0 and bi >= 0 and i > bi and i+1 < len(Cl):
                pattern_ok = True
                if pattern_filter is not None:
                    if i > 0:
                        prev_oh = (Op[i-1], Hi[i-1], Lo[i-1], Cl[i-1])
                        curr_oh = (co, ch, cl, cc)
                        if bkd==1  and cc > bx_hi and cl <= bx_hi:
                            pattern_ok = _check_pattern(prev_oh, curr_oh, 1, pattern_filter)
                        elif bkd==-1 and cc < bx_lo and ch >= bx_lo:
                            pattern_ok = _check_pattern(prev_oh, curr_oh, -1, pattern_filter)

                if bkd==1  and cc > bx_hi and cl <= bx_hi:
                    if pattern_ok:
                        pending = (1,  cl, ch); bi=-1
                elif bkd==-1 and cc < bx_lo and ch >= bx_lo:
                    if pattern_ok:
                        pending = (-1, cl, ch); bi=-1

        tw += dw; tl += dl; t1c += d1; t2c += d2
        pnl_list.append(dp)

    tt = tw + tl
    if tt < CONFIG['min_trades']:
        return None

    arr = np.cumsum(pnl_list)
    mdd = float((arr - np.maximum.accumulate(arr)).min())

    return {
        'bh': bh, 'bm': bm, 'dur': dur,
        'trades': tt, 'wins': tw, 'losses': tl,
        'winrate': round(tw/tt*100, 1),
        'pnl': round(sum(pnl_list), 1),
        'max_dd': round(mdd, 1),
        'tp1': t1c, 'tp2': t2c,
        'tp1_rate': round(t1c/tw*100, 1) if tw else 0,
        'tp2_rate': round(t2c/tw*100, 1) if tw else 0,
    }


def backtest_meanrev_fail_filtered(date_groups, all_dates, bh, bm, dur,
                                    variant, allowed_fn, session_name, adaptive=True):
    """Wraps v4.backtest_meanrev_fail with filter + adaptive."""
    SL_BUFFER = variant.get('sl_buffer', 1.0)
    MIN_SL = variant.get('min_sl', 1.0)
    MIN_BW = variant.get('min_box_width', 1.0)
    MAX_ATT = 5 if adaptive else CONFIG['max_attempts']
    BS = bh * 60 + bm
    BE = BS + dur

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

                # ✨ FILTER CHECK
                if not allowed_fn(day, session_name, ent_dir):
                    in_trade = False; bk_dir = 0; bk_extreme = None
                    continue

                ep = co; ed = ent_dir
                if ed == 1:
                    sp = extreme - SL_BUFFER; tp_ = box_mid
                else:
                    sp = extreme + SL_BUFFER; tp_ = box_mid
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
# 🎯 OPTIMIZER + WALK-FORWARD (filtered)
# ───────────────────────────────────────────────────────────────────

def _bt_dispatch_filtered(variant, date_groups, all_dates, bh, bm, dur, tp1, tp2,
                          allowed_fn, session_name, adaptive=True):
    model = variant.get('model', 'breakout_pullback')
    if model == 'mean_rev_fail':
        return backtest_meanrev_fail_filtered(date_groups, all_dates, bh, bm, dur,
                                               variant, allowed_fn, session_name, adaptive)
    return backtest_filtered(date_groups, all_dates, bh, bm, dur, tp1, tp2,
                             variant, allowed_fn, session_name, adaptive)


def optimize_session_filtered(date_groups, all_dates, sess_name, variant, allowed_fn, adaptive=True):
    cfg = CONFIG['sessions'][sess_name]
    tps = CONFIG['tp_per_session'][sess_name]
    s, e = cfg['start_min'], cfg['end_min']
    tp1, tp2 = tps['tp1'], tps['tp2']
    durs = CONFIG['durations']
    step = CONFIG['coarse_step']
    fw = CONFIG['fine_window']

    coarse = []
    for bmt in range(s, e, step):
        bh = bmt // 60; bm = bmt % 60
        for dur in durs:
            if bmt + dur >= e: continue
            r = _bt_dispatch_filtered(variant, date_groups, all_dates, bh, bm, dur, tp1, tp2,
                                       allowed_fn, sess_name, adaptive)
            if r: coarse.append(r)

    if not coarse:
        return []

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
                r = _bt_dispatch_filtered(variant, date_groups, all_dates, fh, fm, dur, tp1, tp2,
                                           allowed_fn, sess_name, adaptive)
                if r: fine.append(r)

    return fine


def generate_quarters(start_date, end_date):
    quarters = []
    y = start_date.year
    while True:
        for qn, (m1, m2, m3) in enumerate([(1,2,3),(4,5,6),(7,8,9),(10,11,12)], 1):
            train_end = datetime.date(y, m3, 28)
            try:
                train_end = datetime.date(y, m3 + 1, 1) - datetime.timedelta(days=1)
            except ValueError:
                train_end = datetime.date(y, 12, 31)
            train_start = datetime.date(y, m1, 1)
            val_start = train_end + datetime.timedelta(days=1)
            val_end = val_start + datetime.timedelta(days=89)
            if val_end > end_date:
                return quarters
            quarters.append((train_start, train_end, val_start, val_end, f"{y}Q{qn}"))
        y += 1


def walk_forward_filtered(df, variant_def, allowed_fn, adaptive=True):
    print(f"\n{'─'*70}")
    print(f"  Walk-forward FILTERED · adaptive={adaptive}")
    print(f"{'─'*70}")

    data_start = df['date_et'].min()
    data_end   = df['date_et'].max()
    quarters   = generate_quarters(data_start, data_end)
    results = []

    for idx, (train_s, train_e, val_s, val_e, label) in enumerate(quarters, 1):
        df_train = df[(df['date_et']>=train_s)&(df['date_et']<=train_e)]
        df_val   = df[(df['date_et']>=val_s)  &(df['date_et']<=val_e)]
        tg, td = build_date_groups(df_train)
        vg, vd = build_date_groups(df_val)
        if len(td) < 15 or len(vd) < 10:
            continue

        q_total = 0
        sess_summary = []
        for sess in ['Asia','London','NY']:
            sv = variant_def['sessions'][sess]

            # Train: optimize timing on training period (with filter active)
            fine = optimize_session_filtered(tg, td, sess, sv, allowed_fn, adaptive)
            if not fine:
                continue
            best = max(fine, key=lambda r: r['pnl'])

            # Validate: apply best timing on validation period (with filter)
            tps = CONFIG['tp_per_session'][sess]
            r_val = _bt_dispatch_filtered(
                sv, vg, vd, best['bh'], best['bm'], best['dur'],
                tps['tp1'], tps['tp2'], allowed_fn, sess, adaptive,
            )
            val_pnl = r_val['pnl'] if r_val else 0
            val_trades = r_val['trades'] if r_val else 0
            val_wr = r_val['winrate'] if r_val else 0

            results.append({
                'quarter': label, 'session': sess,
                'best_bh': best['bh'], 'best_bm': best['bm'], 'best_dur': best['dur'],
                'train_pnl': best['pnl'], 'val_pnl': val_pnl,
                'val_trades': val_trades, 'val_winrate': val_wr,
            })
            q_total += val_pnl
            sess_summary.append(f"{sess[:3]}={val_pnl:+.1f}")

        print(f"  Q{idx:>2} {label}  total={q_total:+8.1f}  ({' '.join(sess_summary)})")

    return results


# ───────────────────────────────────────────────────────────────────
# 🚀 MAIN
# ───────────────────────────────────────────────────────────────────

VARIANT_E013_FILTERED = {
    "label": "e014: e013 + V4 filter (Macro + Chain + Adaptive)",
    "sessions": {
        "Asia":   ASIA_MEANREV_VARIANTS["asia_a2_fail"],
        "London": PATTERN_VARIANTS["any_pattern"],
        "NY":     PATTERN_VARIANTS["dyn_sl_tp_baseline"],
    },
}


def main(csv_path):
    print("═" * 72)
    print(" PT BOX PHASE 7 · Engine Integration · Walk-forward + V4 Filter")
    print("═" * 72)

    df = load_data(csv_path)
    allowed_fn = build_filter_masks()

    t0 = time.time()
    print("\n Running walk-forward 19Q with FILTER ACTIVE (Macro + Chain + Adaptive)...")
    results = walk_forward_filtered(df, VARIANT_E013_FILTERED, allowed_fn, adaptive=True)
    elapsed = time.time() - t0
    print(f"\n  Walk-forward elapsed: {elapsed:.1f}s")

    # Aggregate
    df_r = pd.DataFrame(results)
    out_csv = ROOT / "data" / "phase7_walkforward_filtered.csv"
    df_r.to_csv(out_csv, index=False)

    total_pnl = df_r["val_pnl"].sum()
    total_trades = df_r["val_trades"].sum()

    print("\n" + "═" * 72)
    print(f" 🎯 PHASE 7 RESULT")
    print("═" * 72)
    print(f"  Total walk-forward PnL (filtered): {total_pnl:+.1f} pts")
    print(f"  Total trades: {total_trades:,}")
    print(f"  e013 baseline (no filter):  +375.0 pts (reference)")
    print(f"  Δ vs e013 baseline:         {total_pnl - 375:+.1f} pts")

    # Per-session breakdown
    print("\n  Per-session breakdown:")
    for sess in ['Asia', 'London', 'NY']:
        s = df_r[df_r['session'] == sess]
        if len(s):
            print(f"    {sess:<7} {s['val_pnl'].sum():+8.1f} pts ({s['val_trades'].sum():>4} trades, "
                  f"WR mean {s['val_winrate'].mean():.1f}%)")

    # Summary JSON
    summary = {
        'generated': datetime.datetime.now().isoformat(),
        'experiment_id': 'e014_filtered',
        'description': 'e013 deploy config + V4 filter (Macro + Chain + Adaptive) walk-forward 19Q',
        'total_pnl': total_pnl,
        'total_trades': int(total_trades),
        'e013_baseline': 375.0,
        'delta_vs_e013': total_pnl - 375.0,
        'per_session': {
            sess: {
                'pnl': float(df_r[df_r['session']==sess]['val_pnl'].sum()),
                'trades': int(df_r[df_r['session']==sess]['val_trades'].sum()),
                'avg_wr': float(df_r[df_r['session']==sess]['val_winrate'].mean()),
            }
            for sess in ['Asia', 'London', 'NY']
        },
    }
    with open(ROOT / "data" / "phase7_summary.json", 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\n  Saved: {out_csv}")
    print(f"  Saved: {ROOT / 'data' / 'phase7_summary.json'}")


if __name__ == "__main__":
    csv = sys.argv[1] if len(sys.argv) > 1 else "/Users/irfanprimaputra.b/Downloads/XAUUSD_M1_2021_-_2026.csv"
    main(csv)
