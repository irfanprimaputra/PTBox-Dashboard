"""
╔══════════════════════════════════════════════════════════════════════╗
║         PT BOX QUARTERLY ENGINE v2 — Superset of v1                 ║
║         Original by Irfan, refactored with extended walk-forward    ║
╚══════════════════════════════════════════════════════════════════════╝

CHANGES vs v1:
1. ✅ Fix typo: 'tp_per_season' → 'tp_per_session' (was line 338 di v1)
2. ✅ Add walk_forward_validation_extended: auto-generate quarters dari
      first/last date di data (vs hardcode 4 quarter)
3. ✅ Save extended walk-forward result ke CSV + summary JSON
4. ✅ CLI flag --extended toggle, original 3-month deploy preserved
5. ✅ Fix label bug di print_walkforward_summary (best_quarter pake worst label)

CARA PAKAI:

   # Mode 1: 3-month deploy (default — same as v1, untuk update timing per kuartal)
   python3 ptbox_quarterly_v2.py [path-to-csv]

   # Mode 2: Extended walk-forward diagnostic (Phase 1 — backtest semua quarter)
   python3 ptbox_quarterly_v2.py --extended [path-to-csv]

   Default csv: cari xauusd_m1.csv di folder yg sama

OUTPUT (Mode 1 — deploy):
   - ptbox_results.html (current quarter optimization view)
   - ptbox_config.json (deploy config 3 bulan ke depan)

OUTPUT (Mode 2 — extended):
   - ptbox_walkforward_extended.csv (semua quarter result)
   - ptbox_walkforward_summary.json (per-session summary)
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

# ═══════════════════════════════════════════════════════════════
# 📥 DATA LOADING
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


def get_quarter_period():
    """
    Ambil 3 bulan kalender penuh sebelum bulan ini.
    Run kapanpun di bulan yang sama → hasil SELALU sama.
    """
    today = datetime.date.today()
    end_month = today.month - 1
    end_year  = today.year
    if end_month == 0:
        end_month = 12
        end_year -= 1

    if end_month == 12:
        end_date = datetime.date(end_year, 12, 31)
    else:
        end_date = datetime.date(end_year, end_month+1, 1) - datetime.timedelta(days=1)

    start_month = end_month - 2
    start_year  = end_year
    if start_month <= 0:
        start_month += 12
        start_year  -= 1

    start_date = datetime.date(start_year, start_month, 1)
    return start_date, end_date


def filter_lookback(df, months=3):
    start_date, end_date = get_quarter_period()
    df_out = df[(df['date_et'] >= start_date) & (df['date_et'] <= end_date)].copy()
    print(f"  Quarter: {start_date} → {end_date} ({df_out['date_et'].nunique()} trading days)")
    print(f"  (Logic: 3 bulan kalender penuh sebelum bulan ini — hasil sama kapanpun lo run di bulan ini)")
    return df_out


def build_date_groups(df):
    dg = {}
    for d, grp in df.groupby('date_et'):
        g = grp.copy()
        g['tm'] = g['hour_et'] * 60 + g['min_et']
        dg[d] = g
    return dg, sorted(dg.keys())


# ═══════════════════════════════════════════════════════════════
# 🔄 BACKTESTER CORE — IDENTICAL TO V1
# ═══════════════════════════════════════════════════════════════

def backtest(date_groups, all_dates, bh, bm, dur, tp1, tp2):
    SL      = CONFIG['sl_pts']
    MAX_ATT = CONFIG['max_attempts']
    BS = bh * 60 + bm
    BE = BS + dur
    tw = tl = t1c = t2c = 0
    pnl_list = []

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
                    t1p = ep + tp1
                    t2p = ep + tp2
                else:
                    sp  = ph_ + SL
                    t1p = ep - tp1
                    t2p = ep - tp2

            if itr:
                if (bkd==1 and ch>=t2p) or (bkd==-1 and cl<=t2p):
                    dw+=1; d2+=1; dp+=tp2; itr=False; done=True; continue
                if (bkd==1 and ch>=t1p) or (bkd==-1 and cl<=t1p):
                    dw+=1; d1+=1; dp+=tp1; itr=False; done=True; continue
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
                if bkd==1  and cc > bx_hi and cl <= bx_hi:
                    pending = (1,  cl, ch); bi=-1
                elif bkd==-1 and cc < bx_lo and ch >= bx_lo:
                    pending = (-1, cl, ch); bi=-1

        tw += dw; tl += dl; t1c += d1; t2c += d2
        pnl_list.append(dp)

    tt = tw + tl
    if tt < CONFIG['min_trades']:
        return None

    arr = np.cumsum(pnl_list)
    mdd = float((arr - np.maximum.accumulate(arr)).min())
    tp1_rate = round(t1c/tw*100, 1) if tw else 0
    tp2_rate = round(t2c/tw*100, 1) if tw else 0

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
    }


# ═══════════════════════════════════════════════════════════════
# 🔍 OPTIMIZATION ENGINE — IDENTICAL TO V1
# ═══════════════════════════════════════════════════════════════

def optimize_session(date_groups, all_dates, sess_name):
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
            r = backtest(date_groups, all_dates, bh, bm, dur, tp1, tp2)
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
                r = backtest(date_groups, all_dates, fh, fm, dur, tp1, tp2)
                if r: fine.append(r)

    return fine


# ═══════════════════════════════════════════════════════════════
# 📊 EXTENDED WALK-FORWARD
# ═══════════════════════════════════════════════════════════════

def generate_quarters(start_date, end_date):
    """
    Auto-generate (train_start, train_end, val_start, val_end, label) tuples
    untuk semua quarter dari start_date sampai end_date.

    Train = 3 bulan kalender penuh sebelum validation quarter.
    Val   = quarter Q (Q1: Jan-Mar, Q2: Apr-Jun, dll)
    Skip kalo train_start < start_date (insufficient training data).
    """
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
            if q > 4:
                q = 1; y += 1
            if y > end_date.year + 1:
                break
            continue

        if val_end > end_date:
            break

        label = f"Q{q} {y}"
        quarters.append((train_start, train_end, val_start, val_end, label))

        q += 1
        if q > 4:
            q = 1; y += 1

    return quarters


def walk_forward_validation_extended(df):
    """
    Auto-generate quarters dari range data, run walk-forward across all.
    """
    print("\n" + "="*65)
    print("EXTENDED WALK-FORWARD VALIDATION")
    print("="*65)

    data_start = df['date_et'].min()
    data_end   = df['date_et'].max()
    quarters   = generate_quarters(data_start, data_end)

    print(f"Data range: {data_start} → {data_end}")
    print(f"Quarters to test: {len(quarters)}")
    print(f"  First: {quarters[0][4]} | Last: {quarters[-1][4]}\n")

    results = []
    for idx, (train_s, train_e, val_s, val_e, label) in enumerate(quarters, 1):
        df_train = df[(df['date_et']>=train_s)&(df['date_et']<=train_e)]
        df_val   = df[(df['date_et']>=val_s)  &(df['date_et']<=val_e)]

        tg, td = build_date_groups(df_train)
        vg, vd = build_date_groups(df_val)

        if len(td) < 15 or len(vd) < 10:
            print(f"  [{idx:2d}/{len(quarters)}] {label}: SKIP (insufficient data: train={len(td)}d, val={len(vd)}d)")
            continue

        print(f"  [{idx:2d}/{len(quarters)}] {label}: ", end='', flush=True)

        q_total_pnl = 0
        q_results = {}

        for sess in ['Asia','London','NY']:
            tps = CONFIG['tp_per_session'][sess]
            tp1 = tps['tp1']; tp2 = tps['tp2']

            fine = optimize_session(tg, td, sess)
            if not fine:
                q_results[sess] = None
                continue
            best = pd.DataFrame(fine).nlargest(1,'pnl').iloc[0]
            bh,bm,dur = int(best.bh),int(best.bm),int(best.dur)

            vr = backtest(vg, vd, bh, bm, dur, tp1, tp2)
            if vr:
                q_total_pnl += vr['pnl']
                q_results[sess] = {
                    'train_time': f"{bh:02d}:{bm:02d}",
                    'train_dur': dur,
                    'val_pnl': vr['pnl'],
                    'val_wr':  vr['winrate'],
                    'val_trades': vr['trades'],
                    'val_max_dd': vr['max_dd'],
                    'pass': vr['pnl'] > 0,
                }
                results.append({
                    'quarter': label,
                    'session': sess,
                    'train_time': f"{bh:02d}:{bm:02d}",
                    'train_dur': dur,
                    'val_pnl': vr['pnl'],
                    'val_wr':  vr['winrate'],
                    'val_trades': vr['trades'],
                    'val_max_dd': vr['max_dd'],
                    'pass': vr['pnl'] > 0,
                })

        sess_summary = []
        for s in ['Asia','London','NY']:
            r = q_results.get(s)
            if r:
                ind = "✓" if r['pass'] else "✗"
                sess_summary.append(f"{s}{ind}{r['val_pnl']:+.0f}")
            else:
                sess_summary.append(f"{s}-")
        print(f"Total {q_total_pnl:+.0f} | " + " ".join(sess_summary))

    return results


def print_walkforward_summary(results):
    """Aggregate stats per session across all quarters."""
    if not results:
        print("\nNo walk-forward results.")
        return {}

    print("\n" + "="*65)
    print("PER-SESSION SUMMARY (across all quarters)")
    print("="*65)

    df_r = pd.DataFrame(results)
    summary = {}

    for sess in ['Asia','London','NY']:
        s_data = df_r[df_r['session']==sess]
        if len(s_data) == 0: continue

        total_pnl   = s_data['val_pnl'].sum()
        n_quarters  = len(s_data)
        n_pass      = s_data['pass'].sum()
        pass_rate   = n_pass / n_quarters * 100
        avg_pnl     = s_data['val_pnl'].mean()
        median_pnl  = s_data['val_pnl'].median()
        std_pnl     = s_data['val_pnl'].std()
        worst_q     = s_data.loc[s_data['val_pnl'].idxmin()]
        best_q      = s_data.loc[s_data['val_pnl'].idxmax()]
        avg_wr      = s_data['val_wr'].mean()

        sharpe_q = avg_pnl / std_pnl if std_pnl > 0 else 0

        summary[sess] = {
            'total_pnl': round(float(total_pnl), 1),
            'n_quarters': int(n_quarters),
            'n_pass': int(n_pass),
            'pass_rate_pct': round(float(pass_rate), 1),
            'avg_pnl_per_q': round(float(avg_pnl), 1),
            'median_pnl_per_q': round(float(median_pnl), 1),
            'std_pnl': round(float(std_pnl), 1),
            'sharpe_quarterly': round(float(sharpe_q), 2),
            'avg_winrate': round(float(avg_wr), 1),
            'best_quarter':  {'label': best_q['quarter'],  'pnl': float(best_q['val_pnl'])},
            'worst_quarter': {'label': worst_q['quarter'], 'pnl': float(worst_q['val_pnl'])},
        }

        emoji = {'Asia':'🟢','London':'🔵','NY':'🔴'}
        print(f"\n{emoji[sess]} {sess}")
        print(f"   Total PnL (all quarters):  {total_pnl:>+8.1f} pts")
        print(f"   Quarters tested:           {n_quarters}")
        print(f"   Profitable quarters:       {n_pass}/{n_quarters} ({pass_rate:.1f}%)")
        print(f"   Avg PnL per quarter:       {avg_pnl:>+7.1f} pts")
        print(f"   Median PnL per quarter:    {median_pnl:>+7.1f} pts")
        print(f"   Std deviation:             {std_pnl:>7.1f} pts")
        print(f"   Sharpe-like (quarterly):   {sharpe_q:>7.2f}")
        print(f"   Avg win rate:              {avg_wr:>6.1f}%")
        print(f"   Best quarter:              {best_q['quarter']} ({best_q['val_pnl']:+.1f})")
        print(f"   Worst quarter:             {worst_q['quarter']} ({worst_q['val_pnl']:+.1f})")

    total_all = df_r['val_pnl'].sum()
    print(f"\n{'='*65}")
    print(f"COMBINED ALL SESSIONS: {total_all:+.1f} pts across {len(results)} session-quarters")
    print(f"{'='*65}")

    return summary


# ═══════════════════════════════════════════════════════════════
# 🖨️  TERMINAL OUTPUT — DEPLOY MODE
# ═══════════════════════════════════════════════════════════════

def print_results(top5_per_sess, rec_timing, period_label, all_dates):
    emoji = {'Asia':'🟢','London':'🔵','NY':'🔴'}
    now   = datetime.datetime.now().strftime('%d %b %Y %H:%M')

    print(f"\n{'='*65}")
    print(f"PT BOX QUARTERLY RESULTS")
    print(f"Period: {period_label} | {len(all_dates)} days")
    print(f"SL=3pts | Asia TP=15/30 | London TP=18/36 | NY TP=9/18")
    print(f"{'='*65}")

    for sess in ['Asia','London','NY']:
        data = top5_per_sess.get(sess, [])
        if not data: continue
        df_r = pd.DataFrame(data).nlargest(5,'pnl').reset_index(drop=True)
        tps  = CONFIG['tp_per_session'][sess]
        print(f"\n{emoji[sess]} {sess} — TP1={tps['tp1']} TP2={tps['tp2']}")
        print(f"  {'#':<3} {'TIME':<8} {'DUR':<5} {'WR':>6} {'PnL':>8} {'DD':>8} {'T':>5}")
        print(f"  {'-'*45}")
        for i, row in df_r.iterrows():
            t  = f"{int(row.bh):02d}:{int(row.bm):02d}"
            mk = " ← DEPLOY" if i==0 else ""
            print(f"  #{i+1:<2} {t:<8} {int(row.dur)}m    {row.winrate:>5.1f}% {row.pnl:>+8.1f} {row.max_dd:>8.1f} {row.trades:>5}{mk}")

    print(f"\n{'='*65}")
    print(f"📌 DEPLOY CONFIG — next 3 months from {now[:11]}")
    print(f"{'='*65}")
    wib = {'Asia':6,'London':12,'NY':20}
    wib_m = {'Asia':23,'London':43,'NY':3}
    for sess, rec in rec_timing.items():
        tps = CONFIG['tp_per_session'][sess]
        print(f"  {emoji[sess]} {sess:<8}: {rec['time']} dur={rec['dur']}m "
              f"| WIB={wib[sess]:02d}:{wib_m[sess]:02d} "
              f"| WR={rec['wr']}% PnL={rec['pnl']:+.1f}pts")
    print(f"\n  SL=3pts fixed")
    print(f"  Asia   TP1=15 TP2=30 (RR 1:5/1:10)")
    print(f"  London TP1=18 TP2=36 (RR 1:6/1:12)")
    print(f"  NY     TP1=9  TP2=18 (RR 1:3/1:6)")

    print(f"\n{'='*65}")
    print(f"⚠️  THRESHOLD MONITOR (cek manual harian):")
    print(f"  2 chop berturut-turut/session → skip session itu")
    print(f"  3 chop berturut-turut/session → stop + run script ini lagi")
    print(f"  2 session kena threshold       → stop semua")
    print(f"{'='*65}")


# ═══════════════════════════════════════════════════════════════
# 🌐 HTML DASHBOARD — DEPLOY MODE
# ═══════════════════════════════════════════════════════════════

def build_html(top5_per_sess, rec_timing, period_label, all_dates):
    emoji = {'Asia':'🟢','London':'🔵','NY':'🔴'}
    now   = datetime.datetime.now().strftime('%d %b %Y %H:%M')
    wib   = {'Asia':'06:23','London':'12:43','NY':'20:03'}
    tps   = CONFIG['tp_per_session']

    tables_html = ''
    for sess in ['Asia','London','NY']:
        data = top5_per_sess.get(sess,[])
        if not data: continue
        df_r = pd.DataFrame(data).nlargest(5,'pnl').reset_index(drop=True)
        rows = ''
        for i, row in df_r.iterrows():
            t   = f"{int(row.bh):02d}:{int(row.bm):02d}"
            rec = ' ⭐' if i==0 else ''
            pc  = '#00e5a0' if row.pnl>=0 else '#ff4466'
            rows += f"""<tr class="{'top-row' if i==0 else ''}">
                <td>#{i+1}</td><td class="tv">{t}{rec}</td>
                <td>{int(row.dur)}m</td>
                <td style="color:#00e5a0">{row.winrate}%</td>
                <td style="color:{pc}">{row.pnl:+.1f}</td>
                <td style="color:#ff4466">{row.max_dd:.1f}</td>
                <td>{row.trades}</td></tr>"""
        tables_html += f"""<div class="sblock">
            <div class="st">{emoji[sess]} {sess} · TP1={tps[sess]['tp1']} TP2={tps[sess]['tp2']}</div>
            <table class="rt"><thead><tr>
                <th>#</th><th>TIME</th><th>DUR</th><th>WR</th><th>PnL</th><th>DD</th><th>T</th>
            </tr></thead><tbody>{rows}</tbody></table></div>"""

    rec_cards = ''
    for sess, rec in rec_timing.items():
        pc = '#00e5a0' if rec['pnl']>=0 else '#ff4466'
        rec_cards += f"""<div class="rc">
            <div class="rs">{emoji[sess]} {sess}</div>
            <div class="rt2">{rec['time']}</div>
            <div class="rm">dur={rec['dur']}m · WIB {wib[sess]}</div>
            <div class="rp" style="color:{pc}">{rec['pnl']:+.1f} pts</div>
            <div class="rw">WR {rec['wr']}%</div></div>"""

    return f"""<!DOCTYPE html><html><head>
<meta charset="UTF-8"><title>PT Box · {period_label}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@700;800&display=swap');
:root{{--bg:#060810;--bg2:#0c1020;--border:#1e2a40;--gold:#f5c842;
      --green:#00e5a0;--red:#ff4466;--text:#e2e8f0;--muted:#64748b;
      --mono:'Space Mono',monospace;--sans:'Syne',sans-serif;}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:var(--mono);padding:32px}}
body::after{{content:'';position:fixed;inset:0;
  background-image:linear-gradient(rgba(245,200,66,.03) 1px,transparent 1px),
  linear-gradient(90deg,rgba(245,200,66,.03) 1px,transparent 1px);
  background-size:40px 40px;pointer-events:none;z-index:0}}
.wrap{{position:relative;z-index:1;max-width:1100px;margin:0 auto}}
h1{{font-family:var(--sans);font-size:40px;font-weight:800;color:#fff;margin-bottom:4px}}
h1 span{{color:var(--gold)}}
.meta{{font-size:11px;color:var(--muted);margin-bottom:32px;line-height:2}}
.badge{{font-size:9px;letter-spacing:.2em;color:var(--gold);
  background:rgba(245,200,66,.08);border:1px solid rgba(245,200,66,.2);
  padding:3px 10px;border-radius:2px;display:inline-block;margin-bottom:12px}}
.stitle{{font-size:10px;letter-spacing:.15em;color:var(--gold);
  border-bottom:1px solid var(--border);padding-bottom:8px;margin:32px 0 16px}}
.g2{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}}
.g3{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}}
.sblock{{background:var(--bg2);border:1px solid var(--border);border-radius:4px;padding:20px}}
.st{{font-size:13px;font-weight:700;margin-bottom:14px}}
.rt{{width:100%;border-collapse:collapse;font-size:11px}}
.rt th{{padding:6px 8px;text-align:left;font-size:9px;color:var(--muted);
  border-bottom:1px solid var(--border)}}
.rt td{{padding:8px}}
.rt tr.top-row td{{background:rgba(245,200,66,.04)}}
.tv{{color:var(--gold);font-weight:700}}
.rc{{background:rgba(245,200,66,.04);border:1px solid rgba(245,200,66,.2);
  border-radius:4px;padding:20px;text-align:center}}
.rs{{font-size:10px;letter-spacing:.15em;color:var(--muted);margin-bottom:8px}}
.rt2{{font-size:36px;font-weight:700;color:var(--gold)}}
.rm{{font-size:10px;color:var(--muted);margin:6px 0 12px}}
.rp{{font-size:20px;font-weight:700}}
.rw{{font-size:11px;color:var(--muted);margin-top:4px}}
.warn{{background:rgba(255,68,102,.06);border:1px solid rgba(255,68,102,.2);
  border-radius:3px;padding:14px;font-size:11px;color:#ff6680;
  line-height:1.8;margin-top:16px}}
footer{{margin-top:48px;border-top:1px solid var(--border);padding-top:16px;
  font-size:10px;color:var(--muted);display:flex;justify-content:space-between}}
</style></head><body><div class="wrap">
<div class="badge">PT BOX QUARTERLY ENGINE</div>
<h1>PT BOX <span>RESULTS</span></h1>
<div class="meta">Period: {period_label} · {len(all_dates)} trading days · {now}<br>
SL=3pts · Asia TP=15/30 · London TP=18/36 · NY TP=9/18 · Max 3 attempts</div>

<div class="stitle">📌 DEPLOY CONFIG — next 3 months</div>
<div class="g3">{rec_cards}</div>
<div class="warn">⚠️ THRESHOLD: 2 chop/session → skip · 3 chop/session → stop + re-run · 2 session kena → stop all</div>

<div class="stitle">🏆 TOP 5 PER SESSION</div>
<div class="g2">{tables_html}</div>

<footer><span>PT Box Engine · Irfan XAUUSD</span>
<span>Run setiap 3 bulan · {now}</span></footer>
</div></body></html>"""


# ═══════════════════════════════════════════════════════════════
# 🚀 MAIN — DEPLOY MODE (3-month optimization for next quarter)
# ═══════════════════════════════════════════════════════════════

def main_deploy(csv_path):
    print("╔══════════════════════════════════════════════════════╗")
    print("║   PT BOX QUARTERLY ENGINE v2 — DEPLOY MODE          ║")
    print("║   (3-month optimization for next quarter timing)    ║")
    print("╚══════════════════════════════════════════════════════╝\n")

    df_full = load_data(csv_path)

    print(f"\nFiltering quarter period...")
    df = filter_lookback(df_full)
    date_groups, all_dates = build_date_groups(df)
    if not all_dates:
        print("❌ No trading days in lookback window. Check data freshness.")
        sys.exit(1)
    period_label = f"{all_dates[0]} → {all_dates[-1]}"

    print(f"\n{'='*55}")
    print(f"OPTIMIZATION — {period_label}")
    print(f"{'='*55}")

    top5_per_sess = {}
    for sess in ['Asia','London','NY']:
        print(f"\n[{sess}] scanning...")
        t0 = time.time()
        results = optimize_session(date_groups, all_dates, sess)
        elapsed = time.time() - t0
        top5_per_sess[sess] = results
        if results:
            best = pd.DataFrame(results).nlargest(1,'pnl').iloc[0]
            print(f"  Done {elapsed:.1f}s | Best: {int(best.bh):02d}:{int(best.bm):02d} "
                  f"dur={int(best.dur)}m WR={best.winrate}% PnL={best.pnl:+.1f}")

    rec_timing = {}
    for sess in ['Asia','London','NY']:
        data = top5_per_sess.get(sess,[])
        if not data: continue
        best = pd.DataFrame(data).nlargest(1,'pnl').iloc[0]
        rec_timing[sess] = {
            'time': f"{int(best.bh):02d}:{int(best.bm):02d}",
            'dur':  int(best.dur),
            'wr':   best.winrate,
            'pnl':  best.pnl,
        }

    print_results(top5_per_sess, rec_timing, period_label, all_dates)

    html = build_html(top5_per_sess, rec_timing, period_label, all_dates)
    with open('ptbox_results.html','w') as f:
        f.write(html)
    print(f"\n✅ Dashboard: ptbox_results.html")

    config_out = {
        'generated': datetime.datetime.now().isoformat(),
        'period': period_label,
        'deploy_until': (all_dates[-1] + datetime.timedelta(days=90)).isoformat(),
        'configs': {}
    }
    for sess, rec in rec_timing.items():
        tps = CONFIG['tp_per_session'][sess]
        config_out['configs'][sess] = {
            'time_utc4': rec['time'],
            'duration_min': rec['dur'],
            'sl_pts': CONFIG['sl_pts'],
            'tp1_pts': tps['tp1'],
            'tp2_pts': tps['tp2'],
            'winrate': rec['wr'],
            'backtest_pnl': rec['pnl'],
        }
    with open('ptbox_config.json','w') as f:
        json.dump(config_out, f, indent=2)
    print(f"✅ Config saved: ptbox_config.json\n")


# ═══════════════════════════════════════════════════════════════
# 🚀 MAIN — EXTENDED MODE (walk-forward all quarters diagnostic)
# ═══════════════════════════════════════════════════════════════

def main_extended(csv_path):
    print("╔══════════════════════════════════════════════════════╗")
    print("║   PT BOX QUARTERLY ENGINE v2 — EXTENDED MODE        ║")
    print("║   (walk-forward diagnostic across all quarters)     ║")
    print("╚══════════════════════════════════════════════════════╝\n")

    df = load_data(csv_path)

    t0 = time.time()
    results = walk_forward_validation_extended(df)
    elapsed = time.time() - t0
    print(f"\nWalk-forward complete in {elapsed:.1f}s")

    summary = print_walkforward_summary(results)

    df_results = pd.DataFrame(results)
    csv_out = 'ptbox_walkforward_extended.csv'
    df_results.to_csv(csv_out, index=False)
    print(f"\n✅ Detailed results: {csv_out}")

    summary_out = 'ptbox_walkforward_summary.json'
    summary_full = {
        'generated': datetime.datetime.now().isoformat(),
        'data_range': {
            'start': str(df['date_et'].min()),
            'end': str(df['date_et'].max()),
            'trading_days': int(df['date_et'].nunique()),
        },
        'quarters_tested': df_results['quarter'].nunique(),
        'session_quarters': len(df_results),
        'per_session': summary,
        'config': {
            'sl_pts': CONFIG['sl_pts'],
            'max_attempts': CONFIG['max_attempts'],
            'tp_per_session': CONFIG['tp_per_session'],
            'durations_tested': CONFIG['durations'],
        },
    }
    with open(summary_out, 'w') as f:
        json.dump(summary_full, f, indent=2)
    print(f"✅ Summary: {summary_out}\n")


# ═══════════════════════════════════════════════════════════════
# 🚀 ENTRY POINT — CLI dispatcher
# ═══════════════════════════════════════════════════════════════

def main():
    args = [a for a in sys.argv[1:] if a != '--extended']
    extended = '--extended' in sys.argv

    csv_path = args[0] if args else CONFIG['m1_file']
    if not os.path.exists(csv_path):
        print(f"❌ File not found: {csv_path}")
        print(f"   Usage:")
        print(f"     python3 ptbox_quarterly_v2.py [csv_path]              # deploy mode")
        print(f"     python3 ptbox_quarterly_v2.py --extended [csv_path]   # walk-forward")
        sys.exit(1)

    if extended:
        main_extended(csv_path)
    else:
        main_deploy(csv_path)


if __name__ == '__main__':
    main()
