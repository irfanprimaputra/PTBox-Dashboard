import pandas as pd

# ============================================================
# SETTING — EDIT DI SINI AJA
# ============================================================
DATA_FILE    = "/path/to/XAUUSD_M1.csv"  # ganti path file CSV lu
BOX_DURATION = 6       # durasi box dalam menit (ganti 5 → 6 di sini)
MAX_ATT      = 3       # max attempt per hari
LOT_SIZE     = 0.02    # lot size (untuk kalkulasi dollar)
PPT          = 2.0     # dollar per point (0.02 lot = $2/pt)

# Box times yang mau di-test (NY time)
BOX_TIMES = [
    # London
    (1, 0), (1, 15), (1, 20), (1, 30), (1, 35), (1, 45),
    (2, 0), (2, 15), (2, 30),
    # NY
    (8, 0), (8, 15), (8, 30), (9, 0),
    # Asia
    (19, 0), (19, 30), (20, 0), (20, 30), (21, 0), (21, 30),
]

# SL, TP1, TP2 yang mau di-test
SL_LIST  = [3.0, 5.0, 7.0]
TP1_LIST = [15.0]
TP2_LIST = [15.0, 20.0, 25.0, 30.0]
# ============================================================

# Load data
df = pd.read_csv(DATA_FILE, sep='\t')
df.columns = [c.strip('<>') for c in df.columns]
df['datetime'] = pd.to_datetime(df['DATE'] + ' ' + df['TIME'])
df = df.sort_values('datetime').reset_index(drop=True)

# Konversi ke NY time (server UTC+0, NY UTC-4)
df['ny_hour']    = (df['datetime'] - pd.Timedelta(hours=4)).dt.hour
df['ny_minute']  = (df['datetime'] - pd.Timedelta(hours=4)).dt.minute
df['ny_dow']     = (df['datetime'] - pd.Timedelta(hours=4)).dt.dayofweek
df['ny_date']    = (df['datetime'] - pd.Timedelta(hours=4)).dt.date
df['is_weekday'] = df['ny_dow'] < 5

# Pre-group by date untuk speed
date_groups = {
    date: group.reset_index(drop=True)
    for date, group in df[df['is_weekday']].groupby('ny_date')
}

def run_backtest(box_hour, box_minute, sl_buf, tp1_pts, tp2_pts):
    total_win=0; total_loss=0; total_tp1=0; total_tp2=0; total_pnl=0.0
    box_end = box_minute + BOX_DURATION

    for date, day_df in date_groups.items():
        vals = day_df[['ny_hour','ny_minute','HIGH','LOW','CLOSE']].values

        # Box formation
        box_rows = [r for r in vals if r[0]==box_hour and box_minute<=r[1]<box_end]
        if not box_rows: continue
        bx_hi = max(r[2] for r in box_rows)
        bx_lo = min(r[3] for r in box_rows)

        # After box candles
        after = [r for r in vals if r[0]>box_hour or (r[0]==box_hour and r[1]>=box_end)]
        if not after: continue

        attempt=0; bk_dir=0; in_trade=False
        entry_px=0; sl_px=0; tp1_px=0; tp2_px=0
        day_done=False; bk_i=None; sl_i=None

        for idx, (ch_, cm_, ch, cl, cc) in enumerate(after):
            if day_done or attempt >= MAX_ATT: break

            # Trade management
            if in_trade:
                hit_tp2 = (bk_dir==1 and ch>=tp2_px) or (bk_dir==-1 and cl<=tp2_px)
                hit_tp1 = (bk_dir==1 and ch>=tp1_px) or (bk_dir==-1 and cl<=tp1_px)
                hit_sl  = (bk_dir==1 and cl<=sl_px)  or (bk_dir==-1 and ch>=sl_px)

                if hit_tp2:
                    total_win+=1; total_tp2+=1
                    total_pnl+=tp2_pts
                    in_trade=False; day_done=True
                elif hit_tp1:
                    total_win+=1; total_tp1+=1
                    total_pnl+=tp1_pts
                    in_trade=False; day_done=True
                elif hit_sl:
                    total_loss+=1
                    total_pnl -= abs(entry_px - sl_px)
                    in_trade=False; bk_dir=0; bk_i=None; sl_i=idx
                    if attempt >= MAX_ATT: day_done=True
                continue

            if day_done or attempt >= MAX_ATT: break

            # Breakout detection
            past_sl = (sl_i is None) or (idx > sl_i)
            if past_sl:
                if bk_dir != 1 and cc > bx_hi: bk_dir=1; bk_i=idx
                elif bk_dir != -1 and cc < bx_lo: bk_dir=-1; bk_i=idx

            if bk_dir==0 or bk_i is None or idx<=bk_i: continue

            # Pullback detection
            pu  = (bk_dir==1)  and (cc > bx_hi) and (cl <= bx_hi)
            pd_ = (bk_dir==-1) and (cc < bx_lo) and (ch >= bx_lo)
            if not pu and not pd_: continue

            # Entry
            attempt+=1; in_trade=True; entry_px=cc
            if bk_dir==1:
                sl_px  = cl - sl_buf
                tp1_px = entry_px + tp1_pts
                tp2_px = entry_px + tp2_pts
            else:
                sl_px  = ch + sl_buf
                tp1_px = entry_px - tp1_pts
                tp2_px = entry_px - tp2_pts

    tt  = total_win + total_loss
    wr  = round(total_win/tt*100, 1) if tt > 0 else 0
    tp1p= round(total_tp1/total_win*100, 1) if total_win > 0 else 0
    tp2p= round(total_tp2/total_win*100, 1) if total_win > 0 else 0

    return {
        'win': total_win, 'loss': total_loss,
        'tp1_hit': total_tp1, 'tp2_hit': total_tp2,
        'wr': wr, 'tp1_pct': tp1p, 'tp2_pct': tp2p,
        'net_pnl': round(total_pnl, 1),
        'dollar': round(total_pnl * PPT, 2),
    }

# Run semua kombinasi
from itertools import product

print(f"\nPT Box Backtest | Duration: {BOX_DURATION} min | Lot: {LOT_SIZE}")
print(f"{'='*80}")
print(f"{'Box':10s} {'SL':>5} {'TP1':>5} {'TP2':>5} {'Win':>5} {'Loss':>5} {'WR':>7} {'TP2%':>6} {'Dollar':>10} {'Session':10s}")
print(f"{'-'*80}")

results = []
for (bh, bm), sl, tp1, tp2 in product(BOX_TIMES, SL_LIST, TP1_LIST, TP2_LIST):
    r = run_backtest(bh, bm, sl, tp1, tp2)
    if r['win'] + r['loss'] < 5: continue  # skip kalau data terlalu sedikit

    if bh < 7:    session = 'London'
    elif bh < 17: session = 'New York'
    else:         session = 'Asia'

    results.append({**r, 'box': f"{bh:02d}:{bm:02d} NY", 'sl': sl, 'tp1': tp1, 'tp2': tp2, 'session': session})

rdf = pd.DataFrame(results)

# Print per session
for sess in ['London', 'New York', 'Asia']:
    print(f"\n{'='*80}")
    print(f"SESSION: {sess.upper()} — Top 5 by Dollar")
    print(f"{'='*80}")
    top = rdf[rdf['session']==sess].sort_values('dollar', ascending=False).head(5)
    for _, row in top.iterrows():
        print(f"{row['box']:10s} {row['sl']:>5.0f} {row['tp1']:>5.0f} {row['tp2']:>5.0f} {row['win']:>5} {row['loss']:>5} {row['wr']:>6.1f}% {row['tp2_pct']:>5.1f}% {row['dollar']:>10.2f}")

print(f"\n{'='*80}")
print("TOP 10 OVERALL — by Dollar")
print(f"{'='*80}")
top_all = rdf.sort_values('dollar', ascending=False).head(10)
for _, row in top_all.iterrows():
    print(f"{row['box']:10s} {row['session']:10s} SL:{row['sl']:>2.0f} TP:{row['tp1']:>2.0f}/{row['tp2']:>2.0f} WR:{row['wr']:>5.1f}% TP2%:{row['tp2_pct']:>5.1f}% ${row['dollar']:>10.2f}")

print("\nDone!")
