"""
╔══════════════════════════════════════════════════════════════════════╗
║           PT BOX QUARTERLY ENGINE — by Irfan                        ║
║           Pure Signal System — No Narasi Required                   ║
╚══════════════════════════════════════════════════════════════════════╝

CARA PAKAI (setiap 3 bulan):
1. Export CSV M1 XAUUSD dari MT5 (1 tahun ke belakang)
2. Rename file jadi: xauusd_m1.csv
3. Taruh di folder yang sama dengan script ini
4. Jalankan: python ptbox_quarterly.py
5. Lihat hasil di terminal + buka ptbox_results.html
6. Update timing di indicator MT5 / TradingView

TIDAK PERLU:
- Baca Bloomberg / Reuters
- Analisis narasi atau bias
- Generate ulang logic apapun
- Tanya ke Claude (kecuali ada masalah)

THRESHOLD MONITOR (cek manual harian):
- 2 chop berturut-turut per session → skip session itu
- 3 chop berturut-turut per session → stop + jalankan script ini
- 2 session kena threshold bersamaan → stop semua session
"""

import os, sys, json, datetime, time
import pandas as pd
import numpy as np

# ═══════════════════════════════════════════════════════════════
# ⚙️  CONFIG — TIDAK PERLU DIUBAH
# ═══════════════════════════════════════════════════════════════

CONFIG = {
    # File
    "m1_file": "xauusd_m1.csv",

    # Lookback untuk optimization (bulan)
    "lookback_months": 3,

    # Risk — fixed, tidak berubah
    "sl_pts": 3.0,
    "max_attempts": 3,

    # TP per session — hasil optimization final
    "tp_per_session": {
        "Asia":   {"tp1": 15, "tp2": 30},   # RR 1:5 / 1:10
        "London": {"tp1": 18, "tp2": 36},   # RR 1:6 / 1:12
        "NY":     {"tp1": 9,  "tp2": 18},   # RR 1:3 / 1:6
    },

    # Session ranges (UTC-4)
    "sessions": {
        "Asia":   {"start_min": 1140, "end_min": 1380},  # 19:00-23:00
        "London": {"start_min": 60,   "end_min": 300},   # 01:00-05:00
        "NY":     {"start_min": 480,  "end_min": 720},   # 08:00-12:00
    },

    # Durasi box yang ditest
    "durations": [3, 5, 7, 10],

    # Scan params
    "coarse_step": 5,
    "fine_window": 10,
    "min_trades": 5,

    # Timezone offset (broker UTC+0 → UTC-4)
    "tz_offset_hours": 4,
}

# ═══════════════════════════════════════════════════════════════
# 📥 DATA LOADING
# ═══════════════════════════════════════════════════════════════

def load_data(filepath):
    print(f"Loading: {filepath}")
    df = pd.read_csv(filepath, sep='\t')
    df.columns = ['date','time','open','high','low','close','tickvol','vol','spread']
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
    
    Contoh:
    - Run 1 Apr / 10 Apr / 30 Apr → Jan + Feb + Mar 2026
    - Run 1 Jul / 15 Jul          → Apr + May + Jun 2026
    """
    today = datetime.date.today()

    # End = akhir bulan lalu
    end_month = today.month - 1
    end_year  = today.year
    if end_month == 0:
        end_month = 12
        end_year -= 1

    if end_month == 12:
        end_date = datetime.date(end_year, 12, 31)
    else:
        end_date = datetime.date(end_year, end_month+1, 1) - datetime.timedelta(days=1)

    # Start = 3 bulan sebelum end_month
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
# 🔄 BACKTESTER CORE
# Realistic entry: signal di close pullback candle →
#                  entry di OPEN candle berikutnya
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

        # Build box
        bk = (tm >= BS) & (tm < BE)
        if bk.sum() == 0:
            pnl_list.append(0.); continue
        bx_hi = H[bk].max()
        bx_lo = L[bk].min()

        # Trading window
        tr = tm >= BE
        if tr.sum() < 3:
            pnl_list.append(0.); continue

        Hi = H[tr]; Lo = L[tr]; Cl = C[tr]; Op = O[tr]

        att = bkd = 0; bi = -1; itr = False
        ep = sp = t1p = t2p = 0.
        done = False; st = None; dp = 0.
        dw = dl = d1 = d2 = 0
        pending = None  # (direction, pb_low, pb_high)

        for i in range(len(Cl)):
            ch = Hi[i]; cl = Lo[i]; cc = Cl[i]; co = Op[i]

            # Execute pending entry at open of THIS candle
            if pending is not None and not itr:
                ed, pl_, ph_ = pending
                pending = None
                ep  = co  # entry at open
                att += 1; itr = True; bkd = ed; bi = -1
                if ed == 1:
                    sp  = pl_ - SL
                    t1p = ep + tp1
                    t2p = ep + tp2
                else:
                    sp  = ph_ + SL
                    t1p = ep - tp1
                    t2p = ep - tp2

            # Trade management
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

            # Breakout detection
            if bkd != 1  and cc > bx_hi: bkd=1;  bi=i
            elif bkd != -1 and cc < bx_lo: bkd=-1; bi=i

            # Pullback → set pending entry
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
# 🔍 OPTIMIZATION ENGINE
# Phase A: Coarse scan (step=5min)
# Phase B: Fine scan (±10min around top zones)
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

    # Phase A: Coarse
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

    # Phase B: Fine
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
# 📊 ROLLING WALK-FORWARD VALIDATION
# ═══════════════════════════════════════════════════════════════

def walk_forward_validation(df):
    print("\nRunning walk-forward validation...")

    quarters = [
        (datetime.date(2025,1,1),  datetime.date(2025,3,31),
         datetime.date(2025,4,1),  datetime.date(2025,6,30),  "Q2 2025"),
        (datetime.date(2025,4,1),  datetime.date(2025,6,30),
         datetime.date(2025,7,1),  datetime.date(2025,9,30),  "Q3 2025"),
        (datetime.date(2025,7,1),  datetime.date(2025,9,30),
         datetime.date(2025,10,1), datetime.date(2025,12,31), "Q4 2025"),
        (datetime.date(2025,10,1), datetime.date(2025,12,31),
         datetime.date(2026,1,1),  datetime.date(2026,3,31),  "Q1 2026"),
    ]

    results = []
    for train_s, train_e, val_s, val_e, label in quarters:
        df_train = df[(df['date_et']>=train_s)&(df['date_et']<=train_e)]
        df_val   = df[(df['date_et']>=val_s)  &(df['date_et']<=val_e)]

        tg, td = build_date_groups(df_train)
        vg, vd = build_date_groups(df_val)

        if len(td) < 15 or len(vd) < 10:
            continue

        q_val = 0
        for sess in ['Asia','London','NY']:
            tps = CONFIG['tp_per_season'][sess] if 'tp_per_season' in CONFIG else CONFIG['tp_per_session'][sess]
            tp1 = tps['tp1']; tp2 = tps['tp2']

            fine = optimize_session(tg, td, sess)
            if not fine: continue
            best = pd.DataFrame(fine).nlargest(1,'pnl').iloc[0]
            bh,bm,dur = int(best.bh),int(best.bm),int(best.dur)

            vr = backtest(vg, vd, bh, bm, dur, tp1, tp2)
            if vr:
                q_val += vr['pnl']
                results.append({
                    'quarter': label, 'sess': sess,
                    'val_pnl': vr['pnl'],
                    'val_wr':  vr['winrate'],
                    'pass':    vr['pnl'] > 0
                })

    return results


# ═══════════════════════════════════════════════════════════════
# 🖨️  TERMINAL OUTPUT
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
# 🌐 HTML DASHBOARD
# ═══════════════════════════════════════════════════════════════

def build_html(top5_per_sess, rec_timing, period_label, all_dates):
    emoji = {'Asia':'🟢','London':'🔵','NY':'🔴'}
    now   = datetime.datetime.now().strftime('%d %b %Y %H:%M')
    wib   = {'Asia':'06:23','London':'12:43','NY':'20:03'}
    tps   = CONFIG['tp_per_session']

    # Build top5 tables
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

    # Rec cards
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
# 🚀 MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    print("╔══════════════════════════════════════════════════════╗")
    print("║        PT BOX QUARTERLY ENGINE — Irfan              ║")
    print("╚══════════════════════════════════════════════════════╝\n")

    # 1. Load data
    if not os.path.exists(CONFIG['m1_file']):
        print(f"❌ File tidak ditemukan: {CONFIG['m1_file']}")
        print(f"   Export CSV M1 dari MT5, rename jadi: {CONFIG['m1_file']}")
        sys.exit(1)

    df_full = load_data(CONFIG['m1_file'])

    # 2. Filter ke 3 bulan kalender penuh
    print(f"\nFiltering quarter period...")
    df = filter_lookback(df_full)
    date_groups, all_dates = build_date_groups(df)
    period_label = f"{all_dates[0]} → {all_dates[-1]}"

    # 3. Optimize per session
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

    # 4. Get recommendations
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

    # 5. Print results
    print_results(top5_per_sess, rec_timing, period_label, all_dates)

    # 6. Build HTML
    html = build_html(top5_per_sess, rec_timing, period_label, all_dates)
    with open('ptbox_results.html','w') as f:
        f.write(html)
    print(f"\n✅ Dashboard: ptbox_results.html")

    # 7. Save config JSON (for reference)
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


if __name__ == '__main__':
    main()
