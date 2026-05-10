"""
Phase 40 — Backtest stop-loss discipline rules.

Question: Kalau lu apply daily/weekly stop rules ke historical 5y data,
apakah lu masih hit target $/yr atau worse than just continue?

Stop rules tested:
- Daily stop: skip rest of day after cumulative loss reaches threshold
- Weekly stop: skip rest of week after cumulative loss reaches threshold
- Combined: both rules active

Compare vs baseline (no stops, trade every signal).
"""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
TRADES = json.load(open(ROOT / 'data' / 'phase14_e44_pullback_trades.json'))
df = pd.DataFrame(TRADES['trades'])
df['date'] = pd.to_datetime(df['date'])
df['week'] = df['date'].dt.to_period('W').astype(str)
df = df.sort_values(['date', 'tm_in']).reset_index(drop=True)

LOT = 0.02   # match user current sim with 0.02 → user uses 0.01 but doubles
USD_PER_PT = LOT * 100  # 0.02 lot = $2/pt

# Compute USD pnl per trade
df['pnl_usd'] = df['pnl'] * USD_PER_PT


def simulate(daily_stop_usd: float | None, weekly_stop_usd: float | None,
              max_consecutive_loss: int | None = None,
              flip_skip: bool = False):
    """Replay trades with stop rules. Skip trades that would fire after stop hit."""
    out = []
    daily_pnl = 0
    weekly_pnl = 0
    consec_loss = 0
    cur_day = None
    cur_week = None
    last_dir = {'Asia': None, 'London': None, 'NY': None}
    skipped = 0

    for _, t in df.iterrows():
        td = t['date']
        wk = t['week']

        # Reset daily on date change
        if cur_day is not None and td != cur_day:
            daily_pnl = 0
            consec_loss = 0
            last_dir = {'Asia': None, 'London': None, 'NY': None}
        cur_day = td

        # Reset weekly on week change
        if cur_week is not None and wk != cur_week:
            weekly_pnl = 0
        cur_week = wk

        # Stop checks BEFORE trade
        if daily_stop_usd is not None and daily_pnl <= daily_stop_usd:
            skipped += 1
            continue
        if weekly_stop_usd is not None and weekly_pnl <= weekly_stop_usd:
            skipped += 1
            continue
        if max_consecutive_loss is not None and consec_loss >= max_consecutive_loss:
            skipped += 1
            continue
        # Flip skip rule (skip if direction opposite of prev trade in same session)
        if flip_skip:
            sess = t['sess']
            if last_dir[sess] is not None and last_dir[sess] != t['dir']:
                skipped += 1
                last_dir[sess] = t['dir']
                continue

        # Execute trade
        out.append({
            'date': td, 'sess': t['sess'], 'dir': t['dir'],
            'pnl': t['pnl'], 'pnl_usd': t['pnl_usd'],
        })
        daily_pnl += t['pnl_usd']
        weekly_pnl += t['pnl_usd']
        last_dir[t['sess']] = t['dir']
        if t['pnl_usd'] < 0:
            consec_loss += 1
        else:
            consec_loss = 0

    return pd.DataFrame(out), skipped


def summarize(name, df_out, skipped):
    if len(df_out) == 0:
        return {'scenario': name, 'n': 0, 'skipped': skipped, 'pnl_usd': 0,
                'usd_per_yr': 0, 'wr': 0, 'worst_day': 0, 'worst_week': 0,
                'max_dd': 0}
    total = df_out['pnl_usd'].sum()
    wr = 100 * (df_out['pnl_usd'] > 0).sum() / len(df_out)
    daily = df_out.groupby('date')['pnl_usd'].sum()
    weekly = df_out.groupby(df_out['date'].dt.to_period('W'))['pnl_usd'].sum()
    eq = df_out['pnl_usd'].cumsum()
    peak = eq.cummax()
    dd = (eq - peak).min()
    return {
        'scenario': name,
        'n': len(df_out),
        'skipped': skipped,
        'pnl_usd': round(total, 2),
        'usd_per_yr': round(total / 5, 2),
        'wr': round(wr, 2),
        'worst_day': round(daily.min(), 2),
        'worst_week': round(weekly.min(), 2),
        'max_dd': round(dd, 2),
    }


print("=" * 130)
print(f"PHASE 40 — Stop Rules Backtest (5y, lot {LOT}, ${USD_PER_PT}/pt)")
print("=" * 130)
print()

scenarios = [
    ('Baseline (no stops)',                   None, None, None, False),
    ('Daily stop -$30',                       -30,  None, None, False),
    ('Daily stop -$50',                       -50,  None, None, False),
    ('Weekly stop -$50',                      None, -50,  None, False),
    ('Weekly stop -$100',                     None, -100, None, False),
    ('Daily -$30 + Weekly -$50',              -30,  -50,  None, False),
    ('Daily -$50 + Weekly -$100',             -50,  -100, None, False),
    ('Max 3 consecutive loss',                None, None, 3,    False),
    ('Max 5 consecutive loss',                None, None, 5,    False),
    ('Flip skip (skip opposite dir)',          None, None, None, True),
    ('FULL: Daily -$50 + Weekly -$100 + Flip', -50,  -100, None, True),
]

results = []
for name, ds, ws, mcl, fs in scenarios:
    df_out, skipped = simulate(ds, ws, mcl, fs)
    s = summarize(name, df_out, skipped)
    results.append(s)

# Print table
header = f'{"Scenario":<42} | {"trades":>6} | {"skipped":>7} | {"$ total":>9} | {"$/yr":>7} | {"WR%":>5} | {"worst day":>9} | {"worst wk":>9} | {"MaxDD":>7}'
print(header)
print('-' * len(header))
for r in results:
    print(f'{r["scenario"]:<42} | {r["n"]:>6} | {r["skipped"]:>7} | {r["pnl_usd"]:>9.0f} | {r["usd_per_yr"]:>7.0f} | {r["wr"]:>5.1f} | {r["worst_day"]:>9.0f} | {r["worst_week"]:>9.0f} | {r["max_dd"]:>7.0f}')

# Save
out_path = ROOT / 'data' / 'phase40_stop_rules_sim.json'
with open(out_path, 'w') as f:
    json.dump({'lot': LOT, 'usd_per_pt': USD_PER_PT, 'results': results}, f, indent=2)
print(f'\n[saved] {out_path}')

# Verdict
baseline = next(r for r in results if 'Baseline' in r['scenario'])
print()
print('=' * 130)
print('VERDICT — does discipline help?')
print('=' * 130)
for r in results[1:]:
    delta = r['pnl_usd'] - baseline['pnl_usd']
    delta_pct = 100 * delta / abs(baseline['pnl_usd']) if baseline['pnl_usd'] != 0 else 0
    worst_diff = r['worst_day'] - baseline['worst_day']
    print(f'  {r["scenario"]:<42} → ${r["pnl_usd"]:>7.0f} (Δ ${delta:+.0f} = {delta_pct:+.1f}%) | worst day Δ ${worst_diff:+.0f}')
