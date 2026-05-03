"""
╔══════════════════════════════════════════════════════════════════════╗
║  PT BOX v6 — TRADE-LEVEL EXPORT SIMULATOR                            ║
║  Fixed deploy config (current production), per-trade CSV output      ║
║  Supports full 2015-2026 dataset for day/week/month analytics        ║
╚══════════════════════════════════════════════════════════════════════╝

Purpose:
   - Replay PT Box logic across full historic data
   - Emit per-trade CSV (date, time, session, direction, entry/exit, SL/TP, hit, PnL)
   - Enables day-of-week, weekly, monthly aggregations in dashboard

DEPLOY CONFIG (matches current b0_ny_no_pattern setup, e013):
   Asia:   mean-rev A2-fail @ 19:23 UTC-4 dur=7m, SL=extreme+1, TP=box_mid
   London: breakout-pullback @ 01:43 UTC-4 dur=3m, dyn_sl_tp + any_pattern
   NY:     breakout-pullback @ 09:03 UTC-4 dur=5m, dyn_sl_tp NO pattern

Usage:
   python3 ptbox_v6_trade_export.py [csv_path]
   (defaults to ~/Downloads/XAUUSD_M1_2015 - 2026.csv)

Output:
   ~/Downloads/ptbox_v6_trades.csv  (per-trade rows, ready for dashboard)
"""

import os, sys, datetime, time
from pathlib import Path
import pandas as pd
import numpy as np

# ═══════════════════════════════════════════════════════════════
# ⚙️  CONFIG — fixed deploy parameters (matches e013)
# ═══════════════════════════════════════════════════════════════

DEPLOY = {
    "Asia": {
        "model": "mean_rev_fail",
        "bh": 19, "bm": 23, "dur": 7,
        "sl_buffer": 1.0, "min_sl": 1.0, "min_box_width": 1.0,
    },
    "London": {
        "model": "breakout_pullback",
        "bh": 1, "bm": 43, "dur": 3,
        "sl_box_mult": 0.5, "tp_box_mult": (3.0, 6.0), "min_sl": 3.0,
        "pattern_filter": "any",
    },
    "NY": {
        "model": "breakout_pullback",
        "bh": 9, "bm": 3, "dur": 5,
        "sl_box_mult": 0.5, "tp_box_mult": (3.0, 6.0), "min_sl": 3.0,
        "pattern_filter": None,  # B0 finding: pattern hurts NY
    },
}

MAX_ATTEMPTS = 3
TZ_OFFSET_HOURS = 4   # UTC-4 (NY time)


# ═══════════════════════════════════════════════════════════════
# 📥 DATA LOADING
# ═══════════════════════════════════════════════════════════════

def load_data(filepath):
    print(f"Loading: {filepath}")
    df = pd.read_csv(filepath, sep='\t')
    df.columns = [c.strip('<>').lower() for c in df.columns]

    # Parse datetime (broker UTC) + convert to ET
    df['dt_utc'] = pd.to_datetime(df['date'] + ' ' + df['time'], format='%Y.%m.%d %H:%M:%S')
    df['dt_et'] = df['dt_utc'] - pd.Timedelta(hours=TZ_OFFSET_HOURS)
    df['date_et'] = df['dt_et'].dt.date
    df['tm'] = df['dt_et'].dt.hour * 60 + df['dt_et'].dt.minute

    df = df.sort_values(['date_et', 'tm']).reset_index(drop=True)
    print(f"  → {len(df):,} bars · {df['date_et'].min()} to {df['date_et'].max()}")
    return df


def build_date_groups(df):
    groups = {}
    for date, g in df.groupby('date_et'):
        groups[date] = {
            'tm': g['tm'].values,
            'high': g['high'].values,
            'low': g['low'].values,
            'close': g['close'].values,
            'open': g['open'].values,
        }
    return groups, sorted(groups.keys())


# ═══════════════════════════════════════════════════════════════
# 🕯️  PATTERN DETECTION (lifted from v3)
# ═══════════════════════════════════════════════════════════════

def _is_pin_bar(o, h, l, c, dir_):
    body = abs(c - o)
    rng = h - l
    if rng <= 0:
        return False
    if dir_ == 1:  # bullish pin (long lower wick)
        lower_wick = min(o, c) - l
        return lower_wick >= 0.6 * rng and body <= 0.3 * rng
    else:  # bearish pin (long upper wick)
        upper_wick = h - max(o, c)
        return upper_wick >= 0.6 * rng and body <= 0.3 * rng


def _is_engulfing(prev, curr, dir_):
    po, ph, pl, pc = prev
    co, ch, cl, cc = curr
    if dir_ == 1:  # bullish engulfing
        return pc < po and cc > co and cc >= po and co <= pc
    else:  # bearish engulfing
        return pc > po and cc < co and cc <= po and co >= pc


def _is_inside_bar(prev, curr):
    po, ph, pl, pc = prev
    co, ch, cl, cc = curr
    return ch <= ph and cl >= pl


def _check_pattern(prev, curr, dir_, kind):
    if kind == "pin_bar":
        return _is_pin_bar(*curr, dir_)
    if kind == "engulfing":
        return _is_engulfing(prev, curr, dir_)
    if kind == "inside_bar":
        return _is_inside_bar(prev, curr)
    if kind == "any":
        return _is_pin_bar(*curr, dir_) or _is_engulfing(prev, curr, dir_) or _is_inside_bar(prev, curr)
    return True


# ═══════════════════════════════════════════════════════════════
# 🔁 BACKTEST: BREAKOUT-PULLBACK (London + NY) — emits trades
# ═══════════════════════════════════════════════════════════════

def simulate_breakout_pullback(date_groups, all_dates, session_name, cfg):
    """Run breakout-pullback logic, return list of trade dicts."""
    bh, bm, dur = cfg['bh'], cfg['bm'], cfg['dur']
    sl_box_mult = cfg.get('sl_box_mult', 0.5)
    tp_box_mult = cfg.get('tp_box_mult', (3.0, 6.0))
    min_sl = cfg.get('min_sl', 3.0)
    pattern_filter = cfg.get('pattern_filter')
    BS = bh * 60 + bm
    BE = BS + dur

    trades = []

    for day in all_dates:
        if day not in date_groups:
            continue
        g = date_groups[day]
        tm, H, L, C, O = g['tm'], g['high'], g['low'], g['close'], g['open']

        bk = (tm >= BS) & (tm < BE)
        if bk.sum() == 0:
            continue
        bx_hi = float(H[bk].max())
        bx_lo = float(L[bk].min())
        box_width = bx_hi - bx_lo
        if box_width <= 0:
            continue

        SL = max(min_sl, sl_box_mult * box_width) if sl_box_mult else min_sl
        tp1_use = tp_box_mult[0] * SL if tp_box_mult else 9.0
        tp2_use = tp_box_mult[1] * SL if tp_box_mult else 18.0

        tr = tm >= BE
        if tr.sum() < 3:
            continue

        Hi, Lo, Cl, Op = H[tr], L[tr], C[tr], O[tr]
        Tm_in_trade = tm[tr]

        att = bkd = 0
        bi = -1
        itr = False
        ep = sp = t1p = t2p = 0.
        ed = 0
        entry_tm_min = 0
        bk_low = bk_high = 0.
        done = False
        st = None
        pending = None

        for i in range(len(Cl)):
            ch = float(Hi[i]); cl = float(Lo[i]); cc = float(Cl[i]); co = float(Op[i])

            if pending is not None and not itr:
                ed_p, pl_, ph_ = pending
                pending = None
                ep = co
                ed = ed_p
                att += 1
                itr = True
                bkd = ed_p
                bi = -1
                entry_tm_min = int(Tm_in_trade[i])
                if ed == 1:
                    sp = pl_ - SL
                    t1p = ep + tp1_use
                    t2p = ep + tp2_use
                else:
                    sp = ph_ + SL
                    t1p = ep - tp1_use
                    t2p = ep - tp2_use

            if itr:
                exit_type = None
                exit_price = None
                pnl = None
                if (ed == 1 and ch >= t2p) or (ed == -1 and cl <= t2p):
                    exit_type = "TP2"
                    exit_price = t2p
                    pnl = tp2_use
                elif (ed == 1 and ch >= t1p) or (ed == -1 and cl <= t1p):
                    exit_type = "TP1"
                    exit_price = t1p
                    pnl = tp1_use
                elif (ed == 1 and cl <= sp) or (ed == -1 and ch >= sp):
                    exit_type = "SL"
                    exit_price = sp
                    pnl = -abs(ep - sp)

                if exit_type is not None:
                    trades.append({
                        'date': str(day),
                        'session': session_name,
                        'model': 'breakout_pullback',
                        'direction': 'long' if ed == 1 else 'short',
                        'entry_time': f"{entry_tm_min // 60:02d}:{entry_tm_min % 60:02d}",
                        'exit_time': f"{int(Tm_in_trade[i]) // 60:02d}:{int(Tm_in_trade[i]) % 60:02d}",
                        'entry_price': round(ep, 3),
                        'exit_price': round(exit_price, 3),
                        'sl_price': round(sp, 3),
                        'tp1_price': round(t1p, 3),
                        'tp2_price': round(t2p, 3),
                        'box_width': round(box_width, 2),
                        'sl_distance': round(SL, 2),
                        'hit_type': exit_type,
                        'pnl_pts': round(pnl, 2),
                        'attempt': att,
                    })
                    itr = False
                    bkd = 0
                    bi = -1
                    st = i
                    if att >= MAX_ATTEMPTS:
                        done = True
                    if exit_type in ("TP1", "TP2"):
                        done = True   # take profit and stop attempts (matches v3 behavior)
                    continue

            if done or itr or att >= MAX_ATTEMPTS:
                continue
            if pending is not None:
                continue
            if st is not None and i <= st:
                continue

            if bkd != 1 and cc > bx_hi:
                bkd = 1; bi = i
            elif bkd != -1 and cc < bx_lo:
                bkd = -1; bi = i

            if bkd != 0 and bi >= 0 and i > bi and i + 1 < len(Cl):
                pattern_ok = True
                if pattern_filter is not None:
                    if i > 0:
                        prev_oh = (float(Op[i-1]), float(Hi[i-1]), float(Lo[i-1]), float(Cl[i-1]))
                        curr_oh = (co, ch, cl, cc)
                        if bkd == 1 and cc > bx_hi and cl <= bx_hi:
                            pattern_ok = _check_pattern(prev_oh, curr_oh, 1, pattern_filter)
                        elif bkd == -1 and cc < bx_lo and ch >= bx_lo:
                            pattern_ok = _check_pattern(prev_oh, curr_oh, -1, pattern_filter)

                if bkd == 1 and cc > bx_hi and cl <= bx_hi and pattern_ok:
                    pending = (1, cl, ch); bi = -1
                elif bkd == -1 and cc < bx_lo and ch >= bx_lo and pattern_ok:
                    pending = (-1, cl, ch); bi = -1

    return trades


# ═══════════════════════════════════════════════════════════════
# 🔄 BACKTEST: MEAN-REV FAIL (Asia) — emits trades
# ═══════════════════════════════════════════════════════════════

def simulate_meanrev_fail(date_groups, all_dates, session_name, cfg):
    bh, bm, dur = cfg['bh'], cfg['bm'], cfg['dur']
    SL_BUFFER = cfg.get('sl_buffer', 1.0)
    MIN_SL = cfg.get('min_sl', 1.0)
    MIN_BW = cfg.get('min_box_width', 1.0)
    BS = bh * 60 + bm
    BE = BS + dur

    trades = []

    for day in all_dates:
        if day not in date_groups:
            continue
        g = date_groups[day]
        tm, H, L, C, O = g['tm'], g['high'], g['low'], g['close'], g['open']

        bk = (tm >= BS) & (tm < BE)
        if bk.sum() == 0:
            continue
        bx_hi = float(H[bk].max())
        bx_lo = float(L[bk].min())
        box_width = bx_hi - bx_lo
        if box_width < MIN_BW:
            continue
        box_mid = (bx_hi + bx_lo) / 2.0

        tr = tm >= BE
        if tr.sum() < 3:
            continue
        Hi, Lo, Cl, Op = H[tr], L[tr], C[tr], O[tr]
        Tm_in_trade = tm[tr]

        att = 0
        in_trade = False
        bk_dir = 0
        bk_extreme = None
        pending = None
        ep = sp = tp_ = 0.
        ed = 0
        entry_tm_min = 0
        st = None
        done = False

        for i in range(len(Cl)):
            ch = float(Hi[i]); cl = float(Lo[i]); cc = float(Cl[i]); co = float(Op[i])

            if pending is not None and not in_trade:
                ent_dir, extreme = pending
                pending = None
                ep = co
                ed = ent_dir
                entry_tm_min = int(Tm_in_trade[i])
                if ed == 1:
                    sp = extreme - SL_BUFFER
                    tp_ = box_mid
                else:
                    sp = extreme + SL_BUFFER
                    tp_ = box_mid

                sl_dist = abs(ep - sp)
                tp_dist = abs(tp_ - ep)
                degenerate = (
                    sl_dist < MIN_SL or
                    tp_dist < 0.5 or
                    (ed == 1 and tp_ <= ep) or
                    (ed == -1 and tp_ >= ep) or
                    (ed == 1 and sp >= ep) or
                    (ed == -1 and sp <= ep)
                )
                if degenerate:
                    in_trade = False
                    bk_dir = 0
                    bk_extreme = None
                    continue
                in_trade = True
                att += 1

            if in_trade:
                exit_type = None
                exit_price = None
                pnl = None
                if ed == 1:
                    if cl <= sp:
                        exit_type = "SL"; exit_price = sp; pnl = -(ep - sp)
                    elif ch >= tp_:
                        exit_type = "TP"; exit_price = tp_; pnl = tp_ - ep
                else:
                    if ch >= sp:
                        exit_type = "SL"; exit_price = sp; pnl = -(sp - ep)
                    elif cl <= tp_:
                        exit_type = "TP"; exit_price = tp_; pnl = ep - tp_

                if exit_type is not None:
                    trades.append({
                        'date': str(day),
                        'session': session_name,
                        'model': 'mean_rev_fail',
                        'direction': 'long' if ed == 1 else 'short',
                        'entry_time': f"{entry_tm_min // 60:02d}:{entry_tm_min % 60:02d}",
                        'exit_time': f"{int(Tm_in_trade[i]) // 60:02d}:{int(Tm_in_trade[i]) % 60:02d}",
                        'entry_price': round(ep, 3),
                        'exit_price': round(exit_price, 3),
                        'sl_price': round(sp, 3),
                        'tp1_price': round(tp_, 3),
                        'tp2_price': round(tp_, 3),
                        'box_width': round(box_width, 2),
                        'sl_distance': round(abs(ep - sp), 2),
                        'hit_type': exit_type,
                        'pnl_pts': round(pnl, 2),
                        'attempt': att,
                    })
                    in_trade = False
                    bk_dir = 0
                    bk_extreme = None
                    st = i
                    if att >= MAX_ATTEMPTS:
                        done = True
                    continue

            if done or in_trade or att >= MAX_ATTEMPTS:
                continue
            if pending is not None:
                continue
            if st is not None and i <= st:
                continue

            if bk_dir == 0:
                if cc > bx_hi:
                    bk_dir = 1; bk_extreme = ch
                elif cc < bx_lo:
                    bk_dir = -1; bk_extreme = cl
            elif bk_dir == 1:
                if ch > bk_extreme:
                    bk_extreme = ch
                if cc < bx_lo:
                    bk_dir = -1; bk_extreme = cl
                elif bx_lo < cc < bx_hi:
                    pending = (-1, bk_extreme)
            elif bk_dir == -1:
                if cl < bk_extreme:
                    bk_extreme = cl
                if cc > bx_hi:
                    bk_dir = 1; bk_extreme = ch
                elif bx_lo < cc < bx_hi:
                    pending = (1, bk_extreme)

    return trades


# ═══════════════════════════════════════════════════════════════
# 🚀 MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    args = sys.argv[1:]
    default_csv = str(Path.home() / "Downloads/XAUUSD_M1_2015 - 2026.csv")
    csv_path = args[0] if args else default_csv
    if not os.path.exists(csv_path):
        # Fallback to 2021-2026 dataset if 2015 not available
        fallback = str(Path.home() / "Downloads/XAUUSD_M1_2021_-_2026.csv")
        if os.path.exists(fallback):
            print(f"⚠️  2015 dataset not found, using fallback: {fallback}")
            csv_path = fallback
        else:
            print(f"❌ Neither dataset found.")
            sys.exit(1)

    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║  PT BOX v6 — TRADE-LEVEL EXPORT                                  ║")
    print("║  Fixed deploy config (matches e013) · per-trade CSV output       ║")
    print("╚══════════════════════════════════════════════════════════════════╝\n")

    df = load_data(csv_path)
    date_groups, all_dates = build_date_groups(df)
    print(f"  → {len(all_dates):,} unique trading days\n")

    all_trades = []
    t_start = time.time()

    for sess_name, cfg in DEPLOY.items():
        t0 = time.time()
        print(f"Simulating {sess_name} ({cfg['model']}) @ {cfg['bh']:02d}:{cfg['bm']:02d} dur={cfg['dur']}m...")
        if cfg['model'] == 'mean_rev_fail':
            trades = simulate_meanrev_fail(date_groups, all_dates, sess_name, cfg)
        else:
            trades = simulate_breakout_pullback(date_groups, all_dates, sess_name, cfg)
        elapsed = time.time() - t0
        wins = sum(1 for t in trades if t['pnl_pts'] > 0)
        losses = sum(1 for t in trades if t['pnl_pts'] < 0)
        total_pnl = sum(t['pnl_pts'] for t in trades)
        print(f"  → {len(trades)} trades · {wins}W / {losses}L · WR {wins/len(trades)*100:.1f}% · Total {total_pnl:+.0f} pts · {elapsed:.1f}s")
        all_trades.extend(trades)

    print(f"\nTotal: {len(all_trades)} trades, {time.time()-t_start:.1f}s elapsed")

    # Save
    df_out = pd.DataFrame(all_trades)
    df_out['date'] = pd.to_datetime(df_out['date'])
    df_out['day_of_week'] = df_out['date'].dt.day_name()
    df_out['week'] = df_out['date'].dt.to_period('W').astype(str)
    df_out['month'] = df_out['date'].dt.to_period('M').astype(str)
    df_out['quarter'] = df_out['date'].dt.to_period('Q').astype(str)
    df_out['year'] = df_out['date'].dt.year

    out_path = Path.home() / "Downloads/ptbox_v6_trades.csv"
    df_out.to_csv(out_path, index=False)
    print(f"\n✅ Saved: {out_path}")
    print(f"   Columns: {list(df_out.columns)}")

    # Quick summary
    print(f"\n{'='*60}")
    print("Summary:")
    summary = df_out.groupby('session').agg(
        trades=('pnl_pts', 'count'),
        wins=('pnl_pts', lambda x: (x > 0).sum()),
        losses=('pnl_pts', lambda x: (x < 0).sum()),
        wr=('pnl_pts', lambda x: (x > 0).sum() / len(x) * 100),
        total_pnl=('pnl_pts', 'sum'),
        avg_pnl=('pnl_pts', 'mean'),
    )
    print(summary.round(1).to_string())

    print(f"\nDay-of-week sneak peek:")
    dow = df_out.groupby('day_of_week')['pnl_pts'].agg(['count', 'sum', 'mean']).round(2)
    print(dow.to_string())


if __name__ == '__main__':
    main()
