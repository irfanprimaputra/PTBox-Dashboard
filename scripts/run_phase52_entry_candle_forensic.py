"""
Phase 52 — Entry Candle Pattern Forensic.

User question: PT Box entry trigger candle = pattern apa?
Classify every entry candle, track outcome per pattern.

Output:
- Pattern type per entry (pin bar, engulf, hammer, inside bar, doji, strong body, etc)
- Frequency per pattern
- Outcome distribution (TP / SL / BE / TRAIL / EOD) per pattern
- WR per pattern
- Avg PnL per pattern
- Per-session breakdown
- Pre-bar setup (breakout direction, retest depth)

Data source: phase14_e44_pullback_trades.json + raw M1 OHLC.
"""
import sys
import json
from pathlib import Path
import numpy as np
import pandas as pd
from datetime import date

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
from ptbox_engine_e37 import load_data, build_date_groups

CSV = "/Users/irfanprimaputra.b/Downloads/XAUUSD_M1_2021_-_2026.csv"
TRADES_JSON = ROOT / 'data' / 'phase14_e44_pullback_trades.json'
TRUMP_START = date(2025, 1, 1)


def classify_candle(o, h, l, c, po, ph, pl, pc, dir_):
    """Classify entry candle into 1+ pattern categories.
    Returns list of pattern names (a single candle can match multiple).
    """
    patterns = []
    rng = h - l
    if rng <= 0: return ['no_range']
    body = abs(c - o)
    body_pct = body / rng
    upper_wick = h - max(c, o)
    lower_wick = min(c, o) - l

    # Bull/bear neutral
    is_bull = c > o
    is_bear = c < o
    direction_matches = (dir_ == 1 and is_bull) or (dir_ == -1 and is_bear)

    # 1. Pin Bar (long wick opposite direction)
    if dir_ == 1:  # bull pin = long lower wick
        if (c - l) / rng > 0.6 and is_bull and lower_wick > body * 1.5:
            patterns.append('bull_pin')
    else:  # bear pin = long upper wick
        if (h - c) / rng > 0.6 and is_bear and upper_wick > body * 1.5:
            patterns.append('bear_pin')

    # 2. Engulfing
    if dir_ == 1 and c > po and o < pc and is_bull:
        patterns.append('bull_engulf')
    if dir_ == -1 and c < po and o > pc and is_bear:
        patterns.append('bear_engulf')

    # 3. Hammer / Shooting Star
    if dir_ == 1:
        if (c - l) / rng > 0.5 and upper_wick / rng < 0.3 and is_bull:
            patterns.append('hammer')
    else:
        if (h - c) / rng > 0.5 and lower_wick / rng < 0.3 and is_bear:
            patterns.append('shooting_star')

    # 4. Inside Bar
    if h <= ph and l >= pl:
        if dir_ == 1 and is_bull: patterns.append('bull_inside')
        elif dir_ == -1 and is_bear: patterns.append('bear_inside')

    # 5. Strong Body (>70%)
    if body_pct > 0.7:
        if dir_ == 1 and is_bull: patterns.append('strong_body_bull')
        elif dir_ == -1 and is_bear: patterns.append('strong_body_bear')

    # 6. Doji (small body)
    if body_pct < 0.15:
        patterns.append('doji')

    # 7. Marubozu (no wicks)
    if body_pct > 0.85 and upper_wick / rng < 0.1 and lower_wick / rng < 0.1:
        if dir_ == 1 and is_bull: patterns.append('marubozu_bull')
        elif dir_ == -1 and is_bear: patterns.append('marubozu_bear')

    # 8. Long Wick Both Sides (uncertainty)
    if upper_wick / rng > 0.3 and lower_wick / rng > 0.3 and body_pct < 0.4:
        patterns.append('spinning_top')

    # 9. Counter-direction candle (entry vs candle direction mismatch)
    if not direction_matches:
        patterns.append('counter_direction')

    # 10. Other (fallback)
    if not patterns:
        if direction_matches:
            patterns.append('plain_body_direction')
        else:
            patterns.append('plain_body_neutral')

    return patterns


def main():
    print("Loading data...")
    raw = json.load(open(TRADES_JSON))
    trades_data = raw['trades']
    print(f"  {len(trades_data)} trades loaded")

    df = load_data(CSV)
    dg, all_dates = build_date_groups(df)
    print(f"  {len(dg)} days OHLC")

    # Enrich each trade with entry candle OHLC
    enriched = []
    no_match = 0
    for t in trades_data:
        td = pd.to_datetime(t['date']).date()
        if td not in dg:
            no_match += 1; continue
        g = dg[td]
        match = g[g['tm'] == t['tm_in']]
        if len(match) == 0:
            no_match += 1; continue
        idx = match.index[0]
        # Get prev bar
        prev_match = g[g['tm'] == t['tm_in'] - 1]
        if len(prev_match) == 0:
            # Try lookback within session
            prev_idx = idx - 1
            if prev_idx < g.index[0]:
                no_match += 1; continue
            try:
                prev = g.loc[prev_idx]
            except:
                no_match += 1; continue
        else:
            prev = prev_match.iloc[0]

        cur = g.loc[idx]
        patterns = classify_candle(
            cur['open'], cur['high'], cur['low'], cur['close'],
            prev['open'], prev['high'], prev['low'], prev['close'],
            t['dir']
        )

        # Outcome classification
        win = t['reason'] == 'TP' or (t['reason'] == 'EOD' and t['pnl'] > 0)

        enriched.append({
            'date': td, 'sess': t['sess'], 'dir': t['dir'],
            'pnl': t['pnl'], 'reason': t['reason'], 'win': win,
            'patterns': patterns,
        })

    print(f"  Matched: {len(enriched)} | Skipped: {no_match}\n")
    edf = pd.DataFrame(enriched)
    edf['date'] = pd.to_datetime(edf['date'])
    edf['year'] = edf['date'].dt.year
    edf['era'] = edf['year'].apply(lambda y: 'Trump-2' if y >= 2025 else 'Biden')

    # ===== PATTERN FREQUENCY (overall) =====
    print('=' * 110)
    print("PHASE 52 — Entry Candle Pattern Forensic (5y backtest data, 6,574 trades)")
    print('=' * 110)

    # Explode patterns (one row per pattern occurrence per trade)
    pattern_rows = []
    for _, r in edf.iterrows():
        for p in r['patterns']:
            pattern_rows.append({
                'pattern': p, 'sess': r['sess'], 'pnl': r['pnl'],
                'reason': r['reason'], 'win': r['win'], 'era': r['era'],
            })
    pdf = pd.DataFrame(pattern_rows)

    # Frequency table (overall)
    print("\n=== OVERALL PATTERN FREQUENCY + OUTCOME ===")
    print(f'{"Pattern":<22} | {"Count":>6} | {"%total":>6} | {"WR%":>5} | {"avg PnL":>8} | {"TP":>5} | {"SL":>5} | {"EOD":>5}')
    print('-' * 100)

    pattern_summary = pdf.groupby('pattern').agg(
        n=('pnl', 'count'),
        wins=('win', 'sum'),
        avg_pnl=('pnl', 'mean'),
        tp=('reason', lambda x: (x == 'TP').sum()),
        sl=('reason', lambda x: (x == 'SL').sum()),
        eod=('reason', lambda x: (x == 'EOD').sum()),
    ).reset_index()
    pattern_summary['wr_pct'] = (100 * pattern_summary['wins'] / pattern_summary['n']).round(1)
    pattern_summary['pct_total'] = (100 * pattern_summary['n'] / len(edf)).round(1)
    pattern_summary = pattern_summary.sort_values('n', ascending=False)

    for _, r in pattern_summary.iterrows():
        print(f'{r["pattern"]:<22} | {r["n"]:>6} | {r["pct_total"]:>5.1f}% | {r["wr_pct"]:>4.1f}% | {r["avg_pnl"]:>+8.2f} | {r["tp"]:>5} | {r["sl"]:>5} | {r["eod"]:>5}')

    # ===== PER SESSION =====
    print("\n=== PER-SESSION PATTERN BREAKDOWN ===")
    for sess in ['Asia', 'London', 'NY']:
        sub = pdf[pdf['sess'] == sess]
        print(f"\n## {sess} (n={len(sub)})")
        per_pat = sub.groupby('pattern').agg(
            n=('pnl', 'count'),
            wins=('win', 'sum'),
            avg_pnl=('pnl', 'mean'),
        ).reset_index()
        per_pat['wr_pct'] = (100 * per_pat['wins'] / per_pat['n']).round(1)
        per_pat['pct'] = (100 * per_pat['n'] / len(sub)).round(1)
        per_pat = per_pat.sort_values('n', ascending=False).head(8)
        for _, r in per_pat.iterrows():
            print(f'  {r["pattern"]:<22} | {r["n"]:>5} ({r["pct"]:>4.1f}%) | WR {r["wr_pct"]:>4.1f}% | avg {r["avg_pnl"]:>+6.2f}')

    # ===== TRUMP-2 ERA SPECIFIC =====
    print("\n=== TRUMP-2 ERA PATTERN BREAKDOWN (2025-2026) ===")
    trump_pdf = pdf[pdf['era'] == 'Trump-2']
    trump_summary = trump_pdf.groupby('pattern').agg(
        n=('pnl', 'count'),
        wins=('win', 'sum'),
        avg_pnl=('pnl', 'mean'),
        tp=('reason', lambda x: (x == 'TP').sum()),
        sl=('reason', lambda x: (x == 'SL').sum()),
    ).reset_index()
    trump_summary['wr_pct'] = (100 * trump_summary['wins'] / trump_summary['n']).round(1)
    trump_summary['pct'] = (100 * trump_summary['n'] / len(trump_pdf)).round(1)
    trump_summary = trump_summary.sort_values('n', ascending=False)

    print(f'{"Pattern":<22} | {"Count":>6} | {"%total":>6} | {"WR%":>5} | {"avg PnL":>8} | {"TP":>5} | {"SL":>5}')
    print('-' * 90)
    for _, r in trump_summary.iterrows():
        print(f'{r["pattern"]:<22} | {r["n"]:>6} | {r["pct"]:>5.1f}% | {r["wr_pct"]:>4.1f}% | {r["avg_pnl"]:>+8.2f} | {r["tp"]:>5} | {r["sl"]:>5}')

    # ===== TOP / BOTTOM patterns by WR =====
    print("\n=== TOP 5 PATTERNS BY WR ===")
    qualified = pattern_summary[pattern_summary['n'] >= 100].sort_values('wr_pct', ascending=False).head(5)
    print(qualified[['pattern', 'n', 'wr_pct', 'avg_pnl']].to_string(index=False))

    print("\n=== BOTTOM 5 PATTERNS BY WR (n>=100) ===")
    bottom = pattern_summary[pattern_summary['n'] >= 100].sort_values('wr_pct').head(5)
    print(bottom[['pattern', 'n', 'wr_pct', 'avg_pnl']].to_string(index=False))

    # Save
    out = ROOT / 'data' / 'phase52_entry_candle_forensic.json'
    output = {
        'pattern_summary_overall': pattern_summary.to_dict('records'),
        'pattern_summary_trump': trump_summary.to_dict('records'),
        'top_5_wr': qualified.to_dict('records'),
        'bottom_5_wr': bottom.to_dict('records'),
    }
    with open(out, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    print(f'\n[saved] {out}')


if __name__ == '__main__':
    main()
