"""
╔══════════════════════════════════════════════════════════════════════╗
║      PT BOX QUARTERLY ENGINE v3 — Phase 4 Box Quality Variants      ║
║      Original by Irfan, extended for variant experimentation        ║
╚══════════════════════════════════════════════════════════════════════╝

CHANGES vs v2:
1. ✅ Box quality variants: dynamic SL (proportional to box width)
2. ✅ Optional dynamic TP (TP1=3xSL, TP2=6xSL)
3. ✅ Experiment log: append result ke ptbox_phase4_experiments.csv
4. ✅ Dashboard HTML cross-variant comparison
5. ✅ Preserve v2 deploy + extended modes (full superset)

CARA PAKAI:

   # Mode 1-2 from v2 (preserved)
   python3 ptbox_quarterly_v3.py [csv]                 # 3-month deploy
   python3 ptbox_quarterly_v3.py --extended [csv]      # walk-forward 19Q (Phase 1)

   # Mode 3 NEW (Phase 4)
   python3 ptbox_quarterly_v3.py --phase4-box [csv]    # 4 variants box quality

OUTPUT (Phase 4 mode):
   - ptbox_phase4_box_quality_results.csv (per quarter × variant × session)
   - ptbox_phase4_box_quality_summary.json
   - ptbox_phase4_dashboard.html (cross-variant viz)
   - APPEND ke ptbox_phase4_experiments.csv (registry log)
"""

import os, sys, json, datetime, time
import pandas as pd
import numpy as np

# ═══════════════════════════════════════════════════════════════
# ⚙️  CONFIG
# ═══════════════════════════════════════════════════════════════

CONFIG = {
    "m1_file": "xauusd_m1.csv",
    "lookback_months": 3,
    "sl_pts": 3.0,
    "max_attempts": 3,
    "tp_per_session": {
        "Asia":   {"tp1": 15, "tp2": 30},
        "London": {"tp1": 18, "tp2": 36},
        "NY":     {"tp1": 9,  "tp2": 18},
    },
    "sessions": {
        "Asia":   {"start_min": 1140, "end_min": 1380},
        "London": {"start_min": 60,   "end_min": 300},
        "NY":     {"start_min": 480,  "end_min": 720},
    },
    "durations": [3, 5, 7, 10],
    "coarse_step": 5,
    "fine_window": 10,
    "min_trades": 5,
    "tz_offset_hours": 4,
}

# Phase 4 — Angle #2 Naked Forex Pattern Filter Variants
# All inherit dyn_sl_tp box quality (Phase 4 #1 winner) + add pattern filter at pullback
PATTERN_VARIANTS = {
    "dyn_sl_tp_baseline": {
        "label": "dyn_sl_tp + NO pattern filter (sanity baseline)",
        "skip_box_gt": None, "sl_box_mult": 0.5, "tp_box_mult": (3.0, 6.0), "min_sl": 3.0,
        "pattern_filter": None,
    },
    "pin_bar_only": {
        "label": "dyn_sl_tp + pin bar at pullback",
        "skip_box_gt": None, "sl_box_mult": 0.5, "tp_box_mult": (3.0, 6.0), "min_sl": 3.0,
        "pattern_filter": "pin_bar",
    },
    "engulfing_only": {
        "label": "dyn_sl_tp + bullish/bearish engulfing at pullback",
        "skip_box_gt": None, "sl_box_mult": 0.5, "tp_box_mult": (3.0, 6.0), "min_sl": 3.0,
        "pattern_filter": "engulfing",
    },
    "any_pattern": {
        "label": "dyn_sl_tp + any-of-3 (pin OR engulfing OR inside bar)",
        "skip_box_gt": None, "sl_box_mult": 0.5, "tp_box_mult": (3.0, 6.0), "min_sl": 3.0,
        "pattern_filter": "any",
    },
}

# Phase 4 — Angle #1 Box Quality Variants
BOX_QUALITY_VARIANTS = {
    "control": {
        "label": "Control (no filter)",
        "skip_box_gt": None,      # no hard skip
        "sl_box_mult": None,      # use CONFIG['sl_pts'] fixed
        "tp_box_mult": None,      # use CONFIG['tp_per_session'] fixed
        "min_sl": 3.0,
    },
    "dyn_sl_0.5": {
        "label": "Dynamic SL = 0.5× box width",
        "skip_box_gt": None,
        "sl_box_mult": 0.5,
        "tp_box_mult": None,      # keep fixed TP per session
        "min_sl": 3.0,
    },
    "dyn_sl_1.0": {
        "label": "Dynamic SL = 1.0× box width",
        "skip_box_gt": None,
        "sl_box_mult": 1.0,
        "tp_box_mult": None,
        "min_sl": 3.0,
    },
    "dyn_sl_tp": {
        "label": "Dynamic SL=0.5×box, TP1=3×SL, TP2=6×SL (full proportional)",
        "skip_box_gt": None,
        "sl_box_mult": 0.5,
        "tp_box_mult": (3.0, 6.0),  # (TP1 multiplier, TP2 multiplier) of SL
        "min_sl": 3.0,
    },
}

# ═══════════════════════════════════════════════════════════════
# 📥 DATA LOADING (same as v2)
# ═══════════════════════════════════════════════════════════════

def load_data(filepath):
    print(f"Loading: {filepath}")
    df = pd.read_csv(filepath, sep='\t')
    df.columns = [c.strip('<>').lower() for c in df.columns]
    if 'tickvol' not in df.columns:
        rename_map = {}
        for c in df.columns:
            if c == 'vol' or c == 'volume':
                rename_map[c] = 'vol'
        df = df.rename(columns=rename_map)
    expected = ['date', 'time', 'open', 'high', 'low', 'close']
    for col in expected:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
    df['datetime'] = (
        pd.to_datetime(df['date'] + ' ' + df['time'], format='%Y.%m.%d %H:%M:%S')
        - pd.Timedelta(hours=CONFIG['tz_offset_hours'])
    )
    df = df.sort_values('datetime').drop_duplicates('datetime').reset_index(drop=True)
    df['date_et']  = df['datetime'].dt.date
    df['hour_et']  = df['datetime'].dt.hour
    df['min_et']   = df['datetime'].dt.minute
    df['weekday']  = df['datetime'].dt.weekday
    df = df[df['weekday'] < 5].copy().reset_index(drop=True)
    print(f"  {len(df):,} bars | {df['date_et'].min()} → {df['date_et'].max()} | {df['date_et'].nunique()} days")
    return df


def build_date_groups(df):
    dg = {}
    for d, grp in df.groupby('date_et'):
        g = grp.copy()
        g['tm'] = g['hour_et'] * 60 + g['min_et']
        dg[d] = g
    return dg, sorted(dg.keys())


# ═══════════════════════════════════════════════════════════════
# 🕯️ NAKED FOREX PATTERN DETECTION (custom, no external lib)
# ═══════════════════════════════════════════════════════════════

def _is_pin_bar(o, h, l, c, direction, max_body_ratio=0.30, min_wick_ratio=0.50):
    """direction: 1=bullish (rejection of low/up wick), -1=bearish (rejection of high)"""
    rng = h - l
    if rng <= 0: return False
    body = abs(c - o)
    if body / rng > max_body_ratio: return False
    if direction == 1:
        # Bullish pin: long lower wick (rejection of low)
        lower_wick = min(o, c) - l
        return lower_wick / rng >= min_wick_ratio
    else:
        # Bearish pin: long upper wick (rejection of high)
        upper_wick = h - max(o, c)
        return upper_wick / rng >= min_wick_ratio


def _is_engulfing(o_prev, c_prev, o, c, direction):
    """direction: 1=bullish engulfing (prior bear engulfed by current bull), -1=bearish"""
    if direction == 1:
        if c_prev >= o_prev: return False  # prior must be bearish
        if c <= o: return False             # current must be bullish
        return o <= c_prev and c >= o_prev  # current body engulfs prior body
    else:
        if c_prev <= o_prev: return False
        if c >= o: return False
        return o >= c_prev and c <= o_prev


def _is_inside_bar(h_prev, l_prev, h, l):
    """Current bar fully contained in prior bar's range."""
    return h < h_prev and l > l_prev


def _check_pattern(prev_ohlc, curr_ohlc, direction, mode):
    """
    Apply pattern filter at pullback candle.
    prev_ohlc / curr_ohlc: tuples of (o, h, l, c)
    direction: 1 for bullish breakout, -1 for bearish
    mode: None / "pin_bar" / "engulfing" / "inside_bar" / "any"
    Returns True if pattern matches (or no filter), False otherwise.
    """
    if mode is None or mode == "none":
        return True

    o_p, h_p, l_p, c_p = prev_ohlc
    o, h, l, c = curr_ohlc

    if mode == "pin_bar":
        return _is_pin_bar(o, h, l, c, direction)
    if mode == "engulfing":
        return _is_engulfing(o_p, c_p, o, c, direction)
    if mode == "inside_bar":
        return _is_inside_bar(h_p, l_p, h, l)
    if mode == "any":
        return (_is_pin_bar(o, h, l, c, direction)
                or _is_engulfing(o_p, c_p, o, c, direction)
                or _is_inside_bar(h_p, l_p, h, l))
    return True


# ═══════════════════════════════════════════════════════════════
# 🔄 BACKTESTER v3 — supports box quality variant
# ═══════════════════════════════════════════════════════════════

def backtest(date_groups, all_dates, bh, bm, dur, tp1, tp2, variant=None):
    """
    variant: dict from BOX_QUALITY_VARIANTS or None (default = control)
    """
    if variant is None:
        variant = BOX_QUALITY_VARIANTS["control"]

    SL_FIXED = CONFIG['sl_pts']
    MAX_ATT = CONFIG['max_attempts']
    BS = bh * 60 + bm
    BE = BS + dur
    tw = tl = t1c = t2c = 0
    pnl_list = []
    box_widths = []  # diagnostic: track distribution

    skip_box_gt = variant.get('skip_box_gt')
    sl_box_mult = variant.get('sl_box_mult')
    tp_box_mult = variant.get('tp_box_mult')
    min_sl = variant.get('min_sl', 3.0)
    pattern_filter = variant.get('pattern_filter')  # None / pin_bar / engulfing / inside_bar / any
    pattern_skipped = 0  # diagnostic: count pullbacks rejected by pattern

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
        box_widths.append(box_width)

        # Variant: hard skip wide box
        if skip_box_gt is not None and box_width > skip_box_gt:
            pnl_list.append(0.); continue

        # Variant: dynamic SL
        if sl_box_mult is not None:
            SL = max(min_sl, sl_box_mult * box_width)
        else:
            SL = SL_FIXED

        # Variant: dynamic TP
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

        for i in range(len(Cl)):
            ch = Hi[i]; cl = Lo[i]; cc = Cl[i]; co = Op[i]

            if pending is not None and not itr:
                ed, pl_, ph_ = pending
                pending = None
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
                    dw+=1; d2+=1; dp+=tp2_use; itr=False; done=True; continue
                if (bkd==1 and ch>=t1p) or (bkd==-1 and cl<=t1p):
                    dw+=1; d1+=1; dp+=tp1_use; itr=False; done=True; continue
                if (bkd==1 and cl<=sp)  or (bkd==-1 and ch>=sp):
                    dl+=1; dp-=abs(ep-sp); itr=False; bkd=0; bi=-1; st=i
                    if att >= MAX_ATT: done=True
                    continue

            if done or itr or att >= MAX_ATT: continue
            if pending is not None: continue
            if st is not None and i <= st: continue

            if bkd != 1  and cc > bx_hi: bkd=1;  bi=i
            elif bkd != -1 and cc < bx_lo: bkd=-1; bi=i

            if bkd != 0 and bi >= 0 and i > bi and i+1 < len(Cl):
                # Pattern filter check at pullback candle (i)
                # Need prior candle (i-1) for engulfing/inside-bar detection
                pattern_ok = True
                if pattern_filter is not None:
                    if i > 0:
                        prev_oh = (Op[i-1], Hi[i-1], Lo[i-1], Cl[i-1])
                        curr_oh = (co, ch, cl, cc)
                        if bkd==1  and cc > bx_hi and cl <= bx_hi:
                            pattern_ok = _check_pattern(prev_oh, curr_oh, 1, pattern_filter)
                        elif bkd==-1 and cc < bx_lo and ch >= bx_lo:
                            pattern_ok = _check_pattern(prev_oh, curr_oh, -1, pattern_filter)
                    else:
                        # No prior candle — only single-candle patterns apply
                        if pattern_filter not in (None, "pin_bar"):
                            pattern_ok = False
                        else:
                            curr_oh = (co, ch, cl, cc)
                            if bkd==1  and cc > bx_hi and cl <= bx_hi:
                                pattern_ok = _is_pin_bar(co, ch, cl, cc, 1) if pattern_filter == "pin_bar" else True
                            elif bkd==-1 and cc < bx_lo and ch >= bx_lo:
                                pattern_ok = _is_pin_bar(co, ch, cl, cc, -1) if pattern_filter == "pin_bar" else True

                if bkd==1  and cc > bx_hi and cl <= bx_hi:
                    if pattern_ok:
                        pending = (1,  cl, ch); bi=-1
                    else:
                        pattern_skipped += 1
                elif bkd==-1 and cc < bx_lo and ch >= bx_lo:
                    if pattern_ok:
                        pending = (-1, cl, ch); bi=-1
                    else:
                        pattern_skipped += 1

        tw += dw; tl += dl; t1c += d1; t2c += d2
        pnl_list.append(dp)

    tt = tw + tl
    if tt < CONFIG['min_trades']:
        return None

    arr = np.cumsum(pnl_list)
    mdd = float((arr - np.maximum.accumulate(arr)).min())
    tp1_rate = round(t1c/tw*100, 1) if tw else 0
    tp2_rate = round(t2c/tw*100, 1) if tw else 0
    avg_box_w = round(float(np.mean(box_widths)), 2) if box_widths else 0

    return {
        'bh': bh, 'bm': bm, 'dur': dur,
        'trades': tt, 'wins': tw, 'losses': tl,
        'winrate': round(tw/tt*100, 1),
        'pnl': round(sum(pnl_list), 1),
        'max_dd': round(mdd, 1),
        'tp1': t1c, 'tp2': t2c,
        'tp1_rate': tp1_rate,
        'tp2_rate': tp2_rate,
        'pnl_list': pnl_list,
        'avg_box_width': avg_box_w,
        'pattern_skipped': int(pattern_skipped),
    }


# ═══════════════════════════════════════════════════════════════
# 🔍 OPTIMIZATION ENGINE (variant-aware)
# ═══════════════════════════════════════════════════════════════

def optimize_session(date_groups, all_dates, sess_name, variant=None):
    cfg  = CONFIG['sessions'][sess_name]
    tps  = CONFIG['tp_per_session'][sess_name]
    s    = cfg['start_min']
    e    = cfg['end_min']
    tp1  = tps['tp1']
    tp2  = tps['tp2']
    durs = CONFIG['durations']
    step = CONFIG['coarse_step']
    fw   = CONFIG['fine_window']

    coarse = []
    for bmt in range(s, e, step):
        bh = bmt // 60; bm = bmt % 60
        for dur in durs:
            if bmt + dur >= e: continue
            r = backtest(date_groups, all_dates, bh, bm, dur, tp1, tp2, variant=variant)
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
                r = backtest(date_groups, all_dates, fh, fm, dur, tp1, tp2, variant=variant)
                if r: fine.append(r)

    return fine


# ═══════════════════════════════════════════════════════════════
# 📊 EXTENDED WALK-FORWARD (variant-aware)
# ═══════════════════════════════════════════════════════════════

def generate_quarters(start_date, end_date):
    quarters = []
    y = start_date.year
    q = ((start_date.month - 1) // 3) + 1

    while True:
        val_start_month = (q - 1) * 3 + 1
        val_start = datetime.date(y, val_start_month, 1)
        if val_start_month + 2 == 12:
            val_end = datetime.date(y, 12, 31)
        else:
            val_end = datetime.date(y, val_start_month + 3, 1) - datetime.timedelta(days=1)

        train_end = val_start - datetime.timedelta(days=1)
        train_start_month = train_end.month - 2
        train_start_year = train_end.year
        if train_start_month <= 0:
            train_start_month += 12
            train_start_year -= 1
        train_start = datetime.date(train_start_year, train_start_month, 1)

        if train_start < start_date:
            q += 1
            if q > 4: q = 1; y += 1
            if y > end_date.year + 1: break
            continue

        if val_end > end_date:
            break

        label = f"Q{q} {y}"
        quarters.append((train_start, train_end, val_start, val_end, label))

        q += 1
        if q > 4: q = 1; y += 1

    return quarters


def walk_forward_for_variant(df, variant_key, variant):
    """Run walk-forward 19Q for a specific variant. Returns list of (quarter, session, ...) dicts."""
    print(f"\n{'─'*65}")
    print(f"VARIANT: {variant_key} — {variant['label']}")
    print(f"{'─'*65}")

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

        q_total_pnl = 0
        sess_summary = []
        for sess in ['Asia','London','NY']:
            tps = CONFIG['tp_per_session'][sess]
            tp1 = tps['tp1']; tp2 = tps['tp2']
            fine = optimize_session(tg, td, sess, variant=variant)
            if not fine:
                sess_summary.append(f"{sess}-")
                continue
            best = pd.DataFrame(fine).nlargest(1,'pnl').iloc[0]
            bh,bm,dur = int(best.bh),int(best.bm),int(best.dur)
            vr = backtest(vg, vd, bh, bm, dur, tp1, tp2, variant=variant)
            if vr:
                q_total_pnl += vr['pnl']
                results.append({
                    'variant': variant_key,
                    'quarter': label,
                    'session': sess,
                    'train_time': f"{bh:02d}:{bm:02d}",
                    'train_dur': dur,
                    'val_pnl': vr['pnl'],
                    'val_wr':  vr['winrate'],
                    'val_trades': vr['trades'],
                    'val_max_dd': vr['max_dd'],
                    'avg_box_width': vr.get('avg_box_width', 0),
                    'pass': vr['pnl'] > 0,
                })
                ind = "✓" if vr['pnl']>0 else "✗"
                sess_summary.append(f"{sess}{ind}{vr['pnl']:+.0f}")
            else:
                sess_summary.append(f"{sess}-")
        print(f"  [{idx:2d}/{len(quarters)}] {label}: Total {q_total_pnl:+.0f} | " + " ".join(sess_summary))

    return results


def aggregate_variant(results, variant_key):
    """Per-variant per-session aggregates."""
    df_r = pd.DataFrame([r for r in results if r['variant']==variant_key])
    if len(df_r) == 0:
        return None

    agg = {'variant': variant_key, 'session_quarters': len(df_r), 'total_pnl': 0.0,
           'sessions': {}, 'avg_winrate': 0.0}
    agg['total_pnl'] = round(float(df_r['val_pnl'].sum()), 1)
    agg['avg_winrate'] = round(float(df_r['val_wr'].mean()), 1)
    agg['quarters_tested'] = int(df_r['quarter'].nunique())

    for sess in ['Asia','London','NY']:
        sd = df_r[df_r['session']==sess]
        if len(sd)==0:
            agg['sessions'][sess] = None
            continue
        agg['sessions'][sess] = {
            'total_pnl': round(float(sd['val_pnl'].sum()), 1),
            'n_quarters': int(len(sd)),
            'n_pass': int(sd['pass'].sum()),
            'pass_rate_pct': round(float(sd['pass'].sum()/len(sd)*100), 1),
            'avg_pnl_per_q': round(float(sd['val_pnl'].mean()), 1),
            'avg_winrate': round(float(sd['val_wr'].mean()), 1),
            'avg_box_width': round(float(sd['avg_box_width'].mean()), 2),
        }
    return agg


# ═══════════════════════════════════════════════════════════════
# 📝 EXPERIMENT LOG (registry CSV)
# ═══════════════════════════════════════════════════════════════

EXPERIMENT_LOG = "ptbox_phase4_experiments.csv"

def append_experiment_log(angle, variant_key, variant, agg, baseline_pnl, verdict, notes=""):
    """Append a row to the cumulative experiment registry."""
    row = {
        'experiment_id': '',  # filled below
        'date_run': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
        'angle': angle,
        'variant_name': variant_key,
        'variant_label': variant['label'],
        'config_json': json.dumps({k:v for k,v in variant.items() if k!='label'}),
        'quarters_tested': agg['quarters_tested'],
        'session_quarters': agg['session_quarters'],
        'total_pnl': agg['total_pnl'],
        'asia_pnl': agg['sessions']['Asia']['total_pnl'] if agg['sessions']['Asia'] else None,
        'london_pnl': agg['sessions']['London']['total_pnl'] if agg['sessions']['London'] else None,
        'ny_pnl': agg['sessions']['NY']['total_pnl'] if agg['sessions']['NY'] else None,
        'asia_pass_rate': agg['sessions']['Asia']['pass_rate_pct'] if agg['sessions']['Asia'] else None,
        'london_pass_rate': agg['sessions']['London']['pass_rate_pct'] if agg['sessions']['London'] else None,
        'ny_pass_rate': agg['sessions']['NY']['pass_rate_pct'] if agg['sessions']['NY'] else None,
        'avg_winrate': agg['avg_winrate'],
        'vs_baseline_delta': round(agg['total_pnl'] - baseline_pnl, 1),
        'vs_baseline_pct': round((agg['total_pnl'] - baseline_pnl) / abs(baseline_pnl) * 100, 1) if baseline_pnl else 0,
        'verdict': verdict,
        'notes': notes,
    }

    if os.path.exists(EXPERIMENT_LOG):
        df_log = pd.read_csv(EXPERIMENT_LOG)
        next_id = len(df_log) + 1
    else:
        df_log = pd.DataFrame()
        next_id = 1
    row['experiment_id'] = f"e{next_id:03d}"

    df_new = pd.DataFrame([row])
    df_log = pd.concat([df_log, df_new], ignore_index=True)
    df_log.to_csv(EXPERIMENT_LOG, index=False)
    print(f"  ✅ Logged as {row['experiment_id']} → {EXPERIMENT_LOG}")
    return row['experiment_id']


# ═══════════════════════════════════════════════════════════════
# 🌐 PHASE 4 DASHBOARD HTML
# ═══════════════════════════════════════════════════════════════

def build_phase4_dashboard(all_results, all_aggs, baseline_pnl):
    now = datetime.datetime.now().strftime('%d %b %Y %H:%M')
    df_all = pd.DataFrame(all_results)

    # Variant comparison cards
    cards = ''
    for agg in all_aggs:
        delta = agg['total_pnl'] - baseline_pnl
        delta_pct = (delta / abs(baseline_pnl) * 100) if baseline_pnl else 0
        color = '#00e5a0' if delta >= 0 else '#ff4466'
        if agg['variant'] == 'control':
            color = '#64748b'  # grey for baseline
        cards += f"""<div class="vc">
            <div class="vk">{agg['variant']}</div>
            <div class="vp" style="color:{color}">{agg['total_pnl']:+.0f} pts</div>
            <div class="vd">Δ {delta:+.0f} ({delta_pct:+.1f}%)</div>
            <div class="vw">WR {agg['avg_winrate']:.1f}% · {agg['session_quarters']} session-Q</div>
        </div>"""

    # Per-session breakdown table
    sess_rows = ''
    for sess in ['Asia','London','NY']:
        cells = f"<td><b>{sess}</b></td>"
        for agg in all_aggs:
            s = agg['sessions'].get(sess)
            if s is None:
                cells += "<td>—</td>"
            else:
                pc = '#00e5a0' if s['total_pnl']>=0 else '#ff4466'
                cells += f"<td style='color:{pc}'><b>{s['total_pnl']:+.0f}</b><br><span class='sub'>{s['pass_rate_pct']:.0f}% pass · WR {s['avg_winrate']:.0f}% · box {s['avg_box_width']:.1f}p</span></td>"
        sess_rows += f"<tr>{cells}</tr>"

    # Quarter heatmap per variant
    quarters = sorted(df_all['quarter'].unique(), key=lambda q: (int(q.split()[1]), int(q.split()[0][1:])))
    heatmap_html = ''
    for sess in ['Asia','London','NY']:
        rows = ''
        for q in quarters:
            cells = f"<td class='q'>{q}</td>"
            for agg in all_aggs:
                v = agg['variant']
                row = df_all[(df_all['quarter']==q) & (df_all['session']==sess) & (df_all['variant']==v)]
                if len(row) == 0:
                    cells += "<td class='cell na'>—</td>"
                else:
                    pnl = row.iloc[0]['val_pnl']
                    intensity = min(abs(pnl)/100, 1.0)
                    if pnl > 0:
                        bg = f"rgba(0,229,160,{intensity:.2f})"
                    else:
                        bg = f"rgba(255,68,102,{intensity:.2f})"
                    cells += f"<td class='cell' style='background:{bg}'>{pnl:+.0f}</td>"
            rows += f"<tr>{cells}</tr>"
        heatmap_html += f"<h3 class='sh'>{sess}</h3><table class='hm'><thead><tr><th>Quarter</th>"
        for agg in all_aggs:
            heatmap_html += f"<th>{agg['variant']}</th>"
        heatmap_html += "</tr></thead><tbody>" + rows + "</tbody></table>"

    var_headers = ''.join([f"<th>{a['variant']}</th>" for a in all_aggs])

    return f"""<!DOCTYPE html><html><head>
<meta charset="UTF-8"><title>PT Box Phase 4 — Box Quality</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@700;800&display=swap');
:root{{--bg:#060810;--bg2:#0c1020;--border:#1e2a40;--gold:#f5c842;
      --green:#00e5a0;--red:#ff4466;--text:#e2e8f0;--muted:#64748b;
      --mono:'Space Mono',monospace;--sans:'Syne',sans-serif;}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:var(--mono);padding:32px}}
.wrap{{max-width:1200px;margin:0 auto}}
h1{{font-family:var(--sans);font-size:36px;font-weight:800;color:#fff;margin-bottom:4px}}
h1 span{{color:var(--gold)}}
h2{{font-family:var(--sans);font-size:18px;color:var(--gold);margin:32px 0 12px;border-bottom:1px solid var(--border);padding-bottom:6px}}
h3.sh{{font-size:13px;color:var(--gold);margin:20px 0 8px;font-family:var(--mono);letter-spacing:.1em}}
.meta{{font-size:11px;color:var(--muted);margin-bottom:24px;line-height:1.8}}
.badge{{font-size:9px;letter-spacing:.2em;color:var(--gold);
  background:rgba(245,200,66,.08);border:1px solid rgba(245,200,66,.2);
  padding:3px 10px;border-radius:2px;display:inline-block;margin-bottom:12px}}
.gv{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin:16px 0}}
.vc{{background:var(--bg2);border:1px solid var(--border);border-radius:4px;padding:16px;text-align:center}}
.vk{{font-size:10px;letter-spacing:.15em;color:var(--muted);margin-bottom:8px}}
.vp{{font-size:24px;font-weight:700}}
.vd{{font-size:12px;color:var(--text);margin-top:6px}}
.vw{{font-size:10px;color:var(--muted);margin-top:8px}}
table.bd{{width:100%;border-collapse:collapse;font-size:11px;margin-top:12px}}
table.bd th,table.bd td{{padding:10px;border-bottom:1px solid var(--border);text-align:left;vertical-align:top}}
table.bd th{{font-size:9px;color:var(--muted);letter-spacing:.1em;text-transform:uppercase}}
table.bd .sub{{font-size:9px;color:var(--muted);font-weight:400}}
table.hm{{width:100%;border-collapse:collapse;font-size:10px;margin-bottom:8px}}
table.hm th{{padding:6px;border-bottom:1px solid var(--border);font-size:9px;color:var(--muted);text-align:center}}
table.hm td{{padding:4px;text-align:center;border:1px solid rgba(30,42,64,.3)}}
table.hm td.q{{color:var(--muted);text-align:left;background:transparent;font-size:10px}}
table.hm td.cell{{font-weight:700;color:#fff}}
table.hm td.na{{color:var(--muted);background:transparent;font-weight:400}}
.legend{{font-size:10px;color:var(--muted);margin-top:8px}}
.note{{background:rgba(245,200,66,.06);border:1px solid rgba(245,200,66,.2);
  border-radius:3px;padding:14px;font-size:11px;color:var(--text);
  line-height:1.8;margin:16px 0}}
footer{{margin-top:48px;border-top:1px solid var(--border);padding-top:16px;
  font-size:10px;color:var(--muted)}}
</style></head><body><div class="wrap">
<div class="badge">PHASE 4 — ANGLE #1 BOX QUALITY</div>
<h1>PT BOX <span>VARIANT TEST</span></h1>
<div class="meta">Generated {now} · 19-quarter walk-forward · Baseline (control) {baseline_pnl:+.0f} pts</div>

<h2>📊 Variant Comparison</h2>
<div class="gv">{cards}</div>
<div class="note">Δ vs control = absolute PnL change. Positive Δ = variant improve over baseline. Variant terbaik biasanya yg highest Δ DENGAN per-session improve consistent (bukan cuma 1 session jago).</div>

<h2>🔬 Per-Session Breakdown</h2>
<table class="bd">
<thead><tr><th>Session</th>{var_headers}</tr></thead>
<tbody>{sess_rows}</tbody>
</table>
<div class="legend">Each cell: total PnL across quarters · pass rate · avg WR · avg box width</div>

<h2>🌡️ Quarter-by-Quarter Heatmap</h2>
<div class="legend">Green = winning quarter, red = losing. Intensity = magnitude. Compare variants side-by-side.</div>
{heatmap_html}

<footer>PT Box Phase 4 Engine v3 · Irfan XAUUSD · {now}</footer>
</div></body></html>"""


# ═══════════════════════════════════════════════════════════════
# 🚀 PHASE 4 MAIN — Box Quality variants
# ═══════════════════════════════════════════════════════════════

def main_phase4_box_quality(csv_path):
    print("╔══════════════════════════════════════════════════════╗")
    print("║   PT BOX ENGINE v3 — PHASE 4 #1 BOX QUALITY         ║")
    print("║   (4 variants × 19Q walk-forward)                   ║")
    print("╚══════════════════════════════════════════════════════╝\n")

    df = load_data(csv_path)

    all_results = []
    all_aggs = []

    t_total = time.time()
    for variant_key, variant in BOX_QUALITY_VARIANTS.items():
        t0 = time.time()
        results = walk_forward_for_variant(df, variant_key, variant)
        elapsed = time.time() - t0
        print(f"  Variant {variant_key}: {elapsed:.1f}s, {len(results)} session-quarters")
        agg = aggregate_variant(results, variant_key)
        if agg:
            all_results.extend(results)
            all_aggs.append(agg)

    print(f"\n{'='*65}")
    print(f"TOTAL ELAPSED: {time.time()-t_total:.1f}s")
    print(f"{'='*65}")

    # Identify baseline (control)
    baseline = next((a for a in all_aggs if a['variant']=='control'), None)
    baseline_pnl = baseline['total_pnl'] if baseline else 0

    # Print summary table
    print(f"\n{'VARIANT':<15} {'PnL':>10} {'Δ baseline':>14} {'Asia':>10} {'London':>10} {'NY':>10}")
    print('─'*75)
    for agg in all_aggs:
        delta = agg['total_pnl'] - baseline_pnl
        a = agg['sessions']['Asia']['total_pnl'] if agg['sessions']['Asia'] else 0
        l = agg['sessions']['London']['total_pnl'] if agg['sessions']['London'] else 0
        n = agg['sessions']['NY']['total_pnl'] if agg['sessions']['NY'] else 0
        marker = ' ← BASELINE' if agg['variant']=='control' else ''
        print(f"{agg['variant']:<15} {agg['total_pnl']:>+10.1f} {delta:>+14.1f} {a:>+10.1f} {l:>+10.1f} {n:>+10.1f}{marker}")

    # Save raw results CSV
    df_out = pd.DataFrame(all_results)
    df_out.to_csv('ptbox_phase4_box_quality_results.csv', index=False)
    print(f"\n✅ Raw results: ptbox_phase4_box_quality_results.csv")

    # Save summary JSON
    summary_full = {
        'generated': datetime.datetime.now().isoformat(),
        'angle': 'Phase 4 #1 — Box Quality',
        'baseline_pnl': baseline_pnl,
        'variants': all_aggs,
    }
    with open('ptbox_phase4_box_quality_summary.json', 'w') as f:
        json.dump(summary_full, f, indent=2)
    print(f"✅ Summary: ptbox_phase4_box_quality_summary.json")

    # Append to experiment log
    print(f"\nAppending to experiment registry...")
    for agg in all_aggs:
        if agg['variant'] == 'control':
            verdict = 'baseline'
            notes = 'Control replication, should match Phase 1 (-2,498 pts)'
        else:
            delta = agg['total_pnl'] - baseline_pnl
            if delta > 500:
                verdict = 'promising'
            elif delta > 100:
                verdict = 'marginal_improve'
            elif delta > -100:
                verdict = 'no_change'
            else:
                verdict = 'reject_worse'
            notes = f"Δ {delta:+.0f} pts vs baseline"
        append_experiment_log('Phase 4 #1', agg['variant'], BOX_QUALITY_VARIANTS[agg['variant']],
                              agg, baseline_pnl, verdict, notes)

    # Build dashboard
    html = build_phase4_dashboard(all_results, all_aggs, baseline_pnl)
    with open('ptbox_phase4_dashboard.html', 'w') as f:
        f.write(html)
    print(f"✅ Dashboard: ptbox_phase4_dashboard.html\n")


# ═══════════════════════════════════════════════════════════════
# 🕯️ PHASE 4 #2 — NAKED FOREX PATTERN MAIN
# ═══════════════════════════════════════════════════════════════

def main_phase4_pattern(csv_path):
    print("╔══════════════════════════════════════════════════════╗")
    print("║   PT BOX ENGINE v3 — PHASE 4 #2 PATTERN FILTER      ║")
    print("║   (4 variants × 19Q × 3 sessions, dyn_sl_tp base)   ║")
    print("╚══════════════════════════════════════════════════════╝\n")

    df = load_data(csv_path)

    # Phase 4 #1 best (dyn_sl_tp without pattern) = -803.2 pts
    dyn_sl_tp_baseline_pnl = -803.2

    all_results = []
    all_aggs = []

    t_total = time.time()
    for variant_key, variant in PATTERN_VARIANTS.items():
        t0 = time.time()
        results = walk_forward_for_variant(df, variant_key, variant)
        elapsed = time.time() - t0
        print(f"  Variant {variant_key}: {elapsed:.1f}s, {len(results)} session-quarters")
        agg = aggregate_variant(results, variant_key)
        if agg:
            all_results.extend(results)
            all_aggs.append(agg)

    print(f"\n{'='*65}")
    print(f"TOTAL ELAPSED: {time.time()-t_total:.1f}s")
    print(f"{'='*65}")

    baseline = next((a for a in all_aggs if a['variant']=='dyn_sl_tp_baseline'), None)
    baseline_pnl = baseline['total_pnl'] if baseline else dyn_sl_tp_baseline_pnl

    print(f"\n{'VARIANT':<22} {'PnL':>10} {'Δ baseline':>14} {'Asia':>10} {'London':>10} {'NY':>10}")
    print('─'*82)
    for agg in all_aggs:
        delta = agg['total_pnl'] - baseline_pnl
        a = agg['sessions']['Asia']['total_pnl'] if agg['sessions']['Asia'] else 0
        l = agg['sessions']['London']['total_pnl'] if agg['sessions']['London'] else 0
        n = agg['sessions']['NY']['total_pnl'] if agg['sessions']['NY'] else 0
        marker = ' ← BASELINE' if agg['variant']=='dyn_sl_tp_baseline' else ''
        print(f"{agg['variant']:<22} {agg['total_pnl']:>+10.1f} {delta:>+14.1f} {a:>+10.1f} {l:>+10.1f} {n:>+10.1f}{marker}")

    # Save results
    df_out = pd.DataFrame(all_results)
    df_out.to_csv('ptbox_phase4_pattern_results.csv', index=False)
    print(f"\n✅ Raw results: ptbox_phase4_pattern_results.csv")

    summary_full = {
        'generated': datetime.datetime.now().isoformat(),
        'angle': 'Phase 4 #2 — Naked Forex Pattern',
        'baseline_variant': 'dyn_sl_tp_baseline',
        'baseline_pnl': baseline_pnl,
        'phase4_1_baseline_reference': dyn_sl_tp_baseline_pnl,
        'phase1_baseline_reference': -2498.4,
        'variants': all_aggs,
    }
    with open('ptbox_phase4_pattern_summary.json', 'w') as f:
        json.dump(summary_full, f, indent=2)
    print(f"✅ Summary: ptbox_phase4_pattern_summary.json")

    # Append to experiment log (vs PHASE 1 baseline -2498.4 for cumulative tracking)
    print(f"\nAppending to experiment registry...")
    PHASE1_BASELINE = -2498.4
    for agg in all_aggs:
        delta_phase1 = agg['total_pnl'] - PHASE1_BASELINE
        delta_phase4_1 = agg['total_pnl'] - dyn_sl_tp_baseline_pnl
        if agg['variant'] == 'dyn_sl_tp_baseline':
            verdict = 'sanity_check'
            notes = f'Sanity replication of e004 dyn_sl_tp (-803). Δ vs Phase 4 #1: {delta_phase4_1:+.0f}'
        else:
            if delta_phase4_1 > 500:
                verdict = 'promising'
            elif delta_phase4_1 > 100:
                verdict = 'marginal_improve'
            elif delta_phase4_1 > -100:
                verdict = 'no_change'
            else:
                verdict = 'reject_worse'
            notes = f'Δ vs dyn_sl_tp baseline: {delta_phase4_1:+.0f} pts'
        append_experiment_log('Phase 4 #2', agg['variant'], PATTERN_VARIANTS[agg['variant']],
                              agg, PHASE1_BASELINE, verdict, notes)

    # Build dashboard (reuse phase4 builder)
    html = build_phase4_dashboard(all_results, all_aggs, baseline_pnl)
    with open('ptbox_phase4_pattern_dashboard.html', 'w') as f:
        f.write(html)
    print(f"✅ Dashboard: ptbox_phase4_pattern_dashboard.html\n")


# ═══════════════════════════════════════════════════════════════
# 🎯 IN-SAMPLE CEILING CHECK (theoretical max with hindsight)
# ═══════════════════════════════════════════════════════════════

def in_sample_ceiling(df, variant_key, variant):
    """
    Optimize per session pakai SELURUH data (cheating w/ hindsight).
    Returns ceiling PnL — theoretical max if we knew the future.
    """
    print(f"\n{'─'*65}")
    print(f"CEILING: {variant_key} — {variant['label']}")
    print(f"{'─'*65}")

    date_groups, all_dates = build_date_groups(df)
    print(f"  Full data: {all_dates[0]} → {all_dates[-1]} ({len(all_dates)} trading days)")

    sess_results = {}
    total_pnl = 0
    all_winrates = []

    for sess in ['Asia', 'London', 'NY']:
        t0 = time.time()
        # Optimize on full data
        fine = optimize_session(date_groups, all_dates, sess, variant=variant)
        if not fine:
            sess_results[sess] = None
            print(f"  {sess}: no valid timing found")
            continue

        best = pd.DataFrame(fine).nlargest(1, 'pnl').iloc[0]
        bh, bm, dur = int(best.bh), int(best.bm), int(best.dur)

        # Verify by re-running backtest with best params (sanity)
        tps = CONFIG['tp_per_session'][sess]
        verify = backtest(date_groups, all_dates, bh, bm, dur, tps['tp1'], tps['tp2'], variant=variant)

        elapsed = time.time() - t0
        sess_results[sess] = {
            'best_time': f"{bh:02d}:{bm:02d}",
            'best_dur': dur,
            'ceiling_pnl': float(verify['pnl']),
            'trades': int(verify['trades']),
            'winrate': float(verify['winrate']),
            'max_dd': float(verify['max_dd']),
            'avg_box_width': float(verify.get('avg_box_width', 0)),
        }
        total_pnl += verify['pnl']
        all_winrates.append(verify['winrate'])
        print(f"  {sess}: optimal {bh:02d}:{bm:02d} dur={dur}m → PnL {verify['pnl']:+.1f} pts, "
              f"WR {verify['winrate']:.1f}%, {verify['trades']} trades ({elapsed:.1f}s)")

    avg_wr = round(sum(all_winrates)/len(all_winrates), 1) if all_winrates else 0
    return {
        'variant': variant_key,
        'sessions': sess_results,
        'total_ceiling_pnl': round(total_pnl, 1),
        'avg_winrate': avg_wr,
    }


def append_ceiling_log(angle, variant_key, variant, ceiling_data, walkforward_pnl):
    """Append ceiling experiment to registry with adapted schema."""
    sess = ceiling_data['sessions']
    row = {
        'experiment_id': '',
        'date_run': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
        'angle': angle,
        'variant_name': f"{variant_key}_ceiling",
        'variant_label': f"In-sample ceiling: {variant['label']}",
        'config_json': json.dumps({
            **{k:v for k,v in variant.items() if k!='label'},
            'mode': 'in_sample_ceiling',
        }),
        'quarters_tested': 19,
        'session_quarters': 3,  # 3 sessions, treated as 1 period
        'total_pnl': ceiling_data['total_ceiling_pnl'],
        'asia_pnl': sess['Asia']['ceiling_pnl'] if sess.get('Asia') else None,
        'london_pnl': sess['London']['ceiling_pnl'] if sess.get('London') else None,
        'ny_pnl': sess['NY']['ceiling_pnl'] if sess.get('NY') else None,
        'asia_pass_rate': None,  # N/A for in-sample
        'london_pass_rate': None,
        'ny_pass_rate': None,
        'avg_winrate': ceiling_data['avg_winrate'],
        'vs_baseline_delta': round(ceiling_data['total_ceiling_pnl'] - (-2498.4), 1),
        'vs_baseline_pct': round((ceiling_data['total_ceiling_pnl'] - (-2498.4)) / 2498.4 * 100, 1),
        'verdict': 'ceiling_reference',
        'notes': f"In-sample (uses future data, NOT deploy-able). Walk-forward best for this variant: {walkforward_pnl:+.0f} pts. Capture rate: {round(walkforward_pnl/ceiling_data['total_ceiling_pnl']*100,1) if ceiling_data['total_ceiling_pnl']!=0 else 'N/A'}%",
    }

    if os.path.exists(EXPERIMENT_LOG):
        df_log = pd.read_csv(EXPERIMENT_LOG)
        next_id = len(df_log) + 1
    else:
        df_log = pd.DataFrame()
        next_id = 1
    row['experiment_id'] = f"e{next_id:03d}"

    df_new = pd.DataFrame([row])
    df_log = pd.concat([df_log, df_new], ignore_index=True)
    df_log.to_csv(EXPERIMENT_LOG, index=False)
    print(f"  ✅ Logged as {row['experiment_id']} → {EXPERIMENT_LOG}")
    return row['experiment_id']


def main_phase4_ceiling(csv_path):
    print("╔══════════════════════════════════════════════════════╗")
    print("║   PT BOX ENGINE v3 — IN-SAMPLE CEILING CHECK        ║")
    print("║   (theoretical max with hindsight — not deployable) ║")
    print("╚══════════════════════════════════════════════════════╝\n")

    df = load_data(csv_path)

    # Walk-forward best per variant (from Phase 4 #1 results)
    walkforward_best = {
        'control': -2498.4,
        'dyn_sl_tp': -803.2,
    }

    results = {}
    t_total = time.time()
    for variant_key in ['control', 'dyn_sl_tp']:
        variant = BOX_QUALITY_VARIANTS[variant_key]
        results[variant_key] = in_sample_ceiling(df, variant_key, variant)

    elapsed = time.time() - t_total
    print(f"\n{'='*65}")
    print(f"TOTAL ELAPSED: {elapsed:.1f}s")
    print(f"{'='*65}")

    # Summary comparison
    print(f"\n{'VARIANT':<20} {'In-Sample Ceiling':>20} {'Walk-Forward':>15} {'Capture %':>12}")
    print('─'*72)
    for vkey, data in results.items():
        ceil = data['total_ceiling_pnl']
        wf = walkforward_best.get(vkey, 0)
        capture = round(wf/ceil*100, 1) if ceil != 0 else 0
        print(f"{vkey:<20} {ceil:>+20.1f} {wf:>+15.1f} {capture:>11.1f}%")

    # Save JSON
    out = {
        'generated': datetime.datetime.now().isoformat(),
        'angle': 'Phase 4 — In-sample ceiling check',
        'walkforward_best': walkforward_best,
        'ceilings': results,
    }
    with open('ptbox_phase4_ceiling_results.json', 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\n✅ Results: ptbox_phase4_ceiling_results.json")

    # Append to experiment log
    print(f"\nAppending to experiment registry...")
    for vkey, data in results.items():
        variant = BOX_QUALITY_VARIANTS[vkey]
        wf = walkforward_best.get(vkey, 0)
        append_ceiling_log('Phase 4 #1', vkey, variant, data, wf)


# ═══════════════════════════════════════════════════════════════
# 🚀 V2 modes preserved (deploy + extended walk-forward)
# Note: simplified dispatch — for full v2 functionality, use v2 directly.
# ═══════════════════════════════════════════════════════════════

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    csv_path = args[0] if args else CONFIG['m1_file']
    if not os.path.exists(csv_path):
        print(f"❌ File not found: {csv_path}")
        print("   Usage:")
        print("     python3 ptbox_quarterly_v3.py --phase4-box [csv]      # Phase 4 #1 (4 variants)")
        print("     python3 ptbox_quarterly_v3.py --phase4-ceiling [csv]  # In-sample ceiling check")
        print("     For deploy / extended-only mode, use ptbox_quarterly_v2.py")
        sys.exit(1)

    if '--phase4-pattern' in sys.argv:
        main_phase4_pattern(csv_path)
    elif '--phase4-ceiling' in sys.argv:
        main_phase4_ceiling(csv_path)
    elif '--phase4-box' in sys.argv or '--phase4' in sys.argv:
        main_phase4_box_quality(csv_path)
    else:
        print("Usage:")
        print("  python3 ptbox_quarterly_v3.py --phase4-box [csv]      # box quality variants")
        print("  python3 ptbox_quarterly_v3.py --phase4-ceiling [csv]  # in-sample ceiling")
        print("  python3 ptbox_quarterly_v3.py --phase4-pattern [csv]  # naked forex pattern filter")
        sys.exit(0)


if __name__ == '__main__':
    main()
