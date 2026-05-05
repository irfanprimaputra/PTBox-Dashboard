import pandas as pd
import numpy as np
from itertools import product

# ── Load data ──────────────────────────────────────────────────────────────
df = pd.read_csv('/mnt/user-data/uploads/1775575008883_XAUUSD_M1_202601012305_202604071456.csv', sep='\t')
df.columns = [c.strip('<>') for c in df.columns]
df['datetime'] = pd.to_datetime(df['DATE'] + ' ' + df['TIME'])
df = df.sort_values('datetime').reset_index(drop=True)

# Server time = UTC+0, NY = UTC-4 → server + 4 = NY... wait, server - 4 = NY
# Server UTC+0, NY UTC-4: NY = server - 4 jam? No.
# NY UTC-4 means NY = UTC - 4
# Server UTC+0 = UTC
# So NY = Server - 4 jam? No!
# UTC = NY + 4 → NY = UTC - 4
# Server = UTC+0 = UTC
# NY = Server - 4? That means server 12:00 = NY 08:00 ✓ YES

df['ny_hour']   = (df['datetime'] - pd.Timedelta(hours=4)).dt.hour
df['ny_minute'] = (df['datetime'] - pd.Timedelta(hours=4)).dt.minute
df['ny_dow']    = (df['datetime'] - pd.Timedelta(hours=4)).dt.dayofweek  # 0=Mon, 6=Sun
df['ny_date']   = (df['datetime'] - pd.Timedelta(hours=4)).dt.date
df['is_weekday'] = df['ny_dow'] < 5  # Mon-Fri

# ── Backtest function ───────────────────────────────────────────────────────
def run_backtest(box_hour, box_minute, box_duration=5, sl_buf=3.0, tp1_pts=15.0, tp2_pts=30.0, max_att=3):
    results = []
    
    # Group by NY date
    dates = df[df['is_weekday']]['ny_date'].unique()
    
    total_win = 0
    total_loss = 0
    total_chop = 0
    total_tp1 = 0
    total_tp2 = 0
    total_pnl = 0.0
    trading_days = 0

    for date in dates:
        day_df = df[df['ny_date'] == date].copy()
        if len(day_df) == 0:
            continue

        # Box candles
        box_mask = (
            day_df['is_weekday'] &
            (day_df['ny_hour'] == box_hour) &
            (day_df['ny_minute'] >= box_minute) &
            (day_df['ny_minute'] < box_minute + box_duration)
        )
        box_candles = day_df[box_mask]
        if len(box_candles) == 0:
            continue

        bx_hi = box_candles['HIGH'].max()
        bx_lo = box_candles['LOW'].min()
        day_hi = bx_hi
        day_lo = bx_lo
        trading_days += 1

        # After box candles
        box_end_minute = box_minute + box_duration
        after_mask = (
            day_df['is_weekday'] &
            ~(
                (day_df['ny_hour'] == box_hour) &
                (day_df['ny_minute'] < box_end_minute)
            ) &
            (
                (day_df['ny_hour'] > box_hour) |
                (
                    (day_df['ny_hour'] == box_hour) &
                    (day_df['ny_minute'] >= box_end_minute)
                )
            )
        )
        after_df = day_df[after_mask].copy()
        if len(after_df) == 0:
            continue

        attempt = 0
        bk_dir = 0
        in_trade = False
        entry_px = 0
        sl_px = 0
        tp1_px = 0
        tp2_px = 0
        day_done = False
        bk_bar_idx = None
        sl_bar_idx = None

        for i, row in after_df.iterrows():
            if day_done:
                break
            if attempt >= max_att:
                break

            c_high = row['HIGH']
            c_low  = row['LOW']
            c_close = row['CLOSE']

            # Trade management
            if in_trade:
                hit_sl  = (c_low <= sl_px)  if bk_dir == 1 else (c_high >= sl_px)
                hit_tp1 = (c_high >= tp1_px) if bk_dir == 1 else (c_low <= tp1_px)
                hit_tp2 = (c_high >= tp2_px) if bk_dir == 1 else (c_low <= tp2_px)

                if hit_tp2:
                    total_win += 1
                    total_tp2 += 1
                    total_pnl += tp2_pts
                    in_trade = False
                    day_done = True
                elif hit_tp1:
                    total_win += 1
                    total_tp1 += 1
                    total_pnl += tp1_pts
                    in_trade = False
                    day_done = True
                elif hit_sl:
                    actual_loss = abs(entry_px - sl_px)
                    total_loss += 1
                    total_pnl -= actual_loss
                    in_trade = False
                    bk_dir = 0
                    bk_bar_idx = None
                    sl_bar_idx = i
                    if attempt >= max_att:
                        total_chop += 1
                        day_done = True
                continue

            if day_done or attempt >= max_att:
                break

            # Breakout detection
            is_past_sl = (sl_bar_idx is None) or (i > sl_bar_idx)
            if is_past_sl:
                if bk_dir != 1 and c_close > day_hi:
                    bk_dir = 1
                    bk_bar_idx = i
                elif bk_dir != -1 and c_close < day_lo:
                    bk_dir = -1
                    bk_bar_idx = i

            # Pullback detection
            if bk_dir == 0 or bk_bar_idx is None:
                continue
            if i <= bk_bar_idx:
                continue

            pullback_up   = (bk_dir == 1)  and (c_close > day_hi) and (c_low  <= day_hi)
            pullback_down = (bk_dir == -1) and (c_close < day_lo)  and (c_high >= day_lo)

            if not pullback_up and not pullback_down:
                continue

            # Entry
            attempt += 1
            in_trade = True
            entry_px = c_close
            if bk_dir == 1:
                sl_px  = c_low  - sl_buf
                tp1_px = entry_px + tp1_pts
                tp2_px = entry_px + tp2_pts
            else:
                sl_px  = c_high + sl_buf
                tp1_px = entry_px - tp1_pts
                tp2_px = entry_px - tp2_pts

    total_trades = total_win + total_loss
    win_rate = (total_win / total_trades * 100) if total_trades > 0 else 0
    tp1_pct  = (total_tp1 / total_win * 100) if total_win > 0 else 0
    tp2_pct  = (total_tp2 / total_win * 100) if total_win > 0 else 0

    return {
        'box_time': f"{box_hour:02d}:{box_minute:02d} NY",
        'box_dur': box_duration,
        'sl': sl_buf,
        'tp1': tp1_pts,
        'tp2': tp2_pts,
        'win': total_win,
        'loss': total_loss,
        'chop': total_chop,
        'tp1_hit': total_tp1,
        'tp2_hit': total_tp2,
        'wr': round(win_rate, 1),
        'tp1_pct': round(tp1_pct, 1),
        'tp2_pct': round(tp2_pct, 1),
        'net_pnl': round(total_pnl, 1),
        'dollar': round(total_pnl * 2, 2),  # lot 0.02 = $2/pt
        'trading_days': trading_days,
    }

# ── Test semua kombinasi ────────────────────────────────────────────────────
print("Running PT Box backtest engine...")
print("="*80)

# Box times to test — London, NY, Asia
box_times = [
    # London area
    (1, 0), (1, 15), (1, 20), (1, 30), (1, 35), (1, 45),
    (2, 0), (2, 15), (2, 30), (2, 45),
    (3, 0), (3, 15), (3, 30),
    # NY area
    (7, 45), (8, 0), (8, 15), (8, 30),
    (9, 0), (9, 30),
    # Asia area
    (19, 0), (19, 15), (19, 30), (19, 45),
    (20, 0), (20, 15), (20, 30),
    (21, 0), (21, 30),
]

sl_buffers  = [3.0, 5.0, 7.0]
tp1_options = [15.0]
tp2_options = [20.0, 25.0, 30.0]
durations   = [5]

all_results = []

total_combinations = len(box_times) * len(sl_buffers) * len(tp1_options) * len(tp2_options) * len(durations)
print(f"Testing {total_combinations} combinations...\n")

for (bh, bm), sl, tp1, tp2, dur in product(box_times, sl_buffers, tp1_options, tp2_options, durations):
    r = run_backtest(bh, bm, dur, sl, tp1, tp2)
    all_results.append(r)

results_df = pd.DataFrame(all_results)

# ── Top results by WR ───────────────────────────────────────────────────────
print("\n" + "="*80)
print("TOP 20 — BY WIN RATE (min 10 trades)")
print("="*80)
top_wr = results_df[results_df['win'] + results_df['loss'] >= 10].sort_values('wr', ascending=False).head(20)
print(top_wr[['box_time','sl','tp1','tp2','win','loss','wr','tp2_pct','net_pnl','dollar']].to_string(index=False))

# ── Top results by Net PnL ──────────────────────────────────────────────────
print("\n" + "="*80)
print("TOP 20 — BY NET P&L DOLLAR")
print("="*80)
top_pnl = results_df[results_df['win'] + results_df['loss'] >= 10].sort_values('dollar', ascending=False).head(20)
print(top_pnl[['box_time','sl','tp1','tp2','win','loss','wr','tp2_pct','net_pnl','dollar']].to_string(index=False))

# ── Session summary ─────────────────────────────────────────────────────────
print("\n" + "="*80)
print("SESSION SUMMARY — SL 3pts, TP1 15, TP2 30 (apple-to-apple vs backtest lu)")
print("="*80)
baseline = results_df[
    (results_df['sl'] == 3.0) &
    (results_df['tp1'] == 15.0) &
    (results_df['tp2'] == 30.0)
].sort_values('wr', ascending=False)
print(baseline[['box_time','win','loss','chop','wr','tp2_pct','net_pnl','dollar']].to_string(index=False))

print("\nDone! Semua kombinasi udah di-test.")
