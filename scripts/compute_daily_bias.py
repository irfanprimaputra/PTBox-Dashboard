"""
Daily HTF Bias Computer.

Compute today's HTF bias score (0-100) based on:
1. 3-day close trend (25%)
2. Open vs PDM/PDC position (20%)
3. Position in last 5-day range (premium/discount) (20%)
4. DXY inverse correlation hint (15%)
5. Round number proximity (10%)
6. Last D1 candle close type (10%)

Output JSON consumed by dashboard widget.
"""
import sys
import json
from pathlib import Path
from datetime import date, datetime
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
from ptbox_engine_e37 import load_data, build_date_groups

CSV = "/Users/irfanprimaputra.b/Downloads/XAUUSD_M1_2021_-_2026.csv"


def compute_today_bias(date_groups, all_dates, target_date=None):
    """Compute bias for target_date (default = last available)."""
    sorted_dates = sorted(all_dates)
    if target_date is None:
        target_date = sorted_dates[-1]

    if target_date not in date_groups:
        return None

    today_g = date_groups[target_date]
    if len(today_g) < 50: return None

    today_open = float(today_g['close'].iloc[0])
    today_high = float(today_g['high'].max())
    today_low = float(today_g['low'].min())
    today_close = float(today_g['close'].iloc[-1])

    # Find prior days
    idx = sorted_dates.index(target_date)
    if idx < 5: return None

    prior_days = sorted_dates[idx-5:idx]  # last 5 trading days
    prior_closes = []
    prior_highs = []
    prior_lows = []
    for pd_date in prior_days:
        if pd_date not in date_groups: continue
        pg = date_groups[pd_date]
        if len(pg) < 50: continue
        prior_closes.append(float(pg['close'].iloc[-1]))
        prior_highs.append(float(pg['high'].max()))
        prior_lows.append(float(pg['low'].min()))

    if len(prior_closes) < 5: return None

    pdc = prior_closes[-1]  # prior day close
    pdh = prior_highs[-1]
    pdl = prior_lows[-1]
    pdm = (pdh + pdl) / 2

    score = 50  # neutral baseline

    # Factor 1: 3-day close trend (weight 25)
    trend_3d = 0
    if prior_closes[-1] > prior_closes[-3] * 1.005:
        score += 12; trend_3d = 1
    elif prior_closes[-1] < prior_closes[-3] * 0.995:
        score -= 12; trend_3d = -1

    # Factor 2: Today open vs PDM/PDC (weight 20)
    if today_open > pdc * 1.002:
        score += 10
    elif today_open < pdc * 0.998:
        score -= 10
    open_vs_pdm = 'above' if today_open > pdm else 'below'

    # Factor 3: Today position in 5-day range (weight 20)
    range_5d_high = max(prior_highs)
    range_5d_low = min(prior_lows)
    range_5d_size = range_5d_high - range_5d_low
    if range_5d_size > 0:
        position_pct = (today_open - range_5d_low) / range_5d_size
        if position_pct > 0.7:
            score -= 10  # PREMIUM = bearish bias
            zone = 'PREMIUM'
        elif position_pct < 0.3:
            score += 10  # DISCOUNT = bullish bias
            zone = 'DISCOUNT'
        else:
            zone = 'EQUILIBRIUM'
    else:
        position_pct = 0.5; zone = 'EQUILIBRIUM'

    # Factor 4: DXY hint (placeholder — strong USD = bearish gold)
    # Without DXY data, skip this factor
    # TODO: integrate macro feed

    # Factor 5: Round number proximity (weight 10)
    nearest_round_50 = round(today_open / 50) * 50
    dist_to_round = abs(today_open - nearest_round_50)
    if dist_to_round < 5:
        # Near round = potential resistance/support
        # Don't shift bias, just flag
        round_flag = True
    else:
        round_flag = False

    # Factor 6: Prior day close type (weight 10)
    prior_open = float(date_groups[prior_days[-1]]['close'].iloc[0])
    prior_close = pdc
    if prior_close > prior_open:
        score += 5  # bullish close yesterday
        pd_close_type = 'BULLISH'
    elif prior_close < prior_open:
        score -= 5
        pd_close_type = 'BEARISH'
    else:
        pd_close_type = 'NEUTRAL'

    score = max(0, min(100, score))

    # Verdict
    if score >= 70:
        verdict = 'STRONG BUY BIAS'
        action = 'Take ALL PT Box BUY signals full lot. Skip/half-lot SELL signals.'
    elif score >= 60:
        verdict = 'BUY BIAS'
        action = 'Prefer BUY signals. SELL signals at reduced lot.'
    elif score >= 40:
        verdict = 'NEUTRAL'
        action = 'Trade both directions equal lot.'
    elif score >= 30:
        verdict = 'SELL BIAS'
        action = 'Prefer SELL signals. BUY signals at reduced lot.'
    else:
        verdict = 'STRONG SELL BIAS'
        action = 'Take ALL PT Box SELL signals full lot. Skip/half-lot BUY signals.'

    return {
        'date': str(target_date),
        'score': score,
        'verdict': verdict,
        'action': action,
        'factors': {
            'trend_3d': trend_3d,
            'today_open_vs_pdc': round(today_open - pdc, 2),
            'today_open_vs_pdm': open_vs_pdm,
            'zone_in_5d_range': zone,
            'position_pct': round(position_pct * 100, 1),
            'pd_close_type': pd_close_type,
            'round_50_proximity': round_flag,
            'nearest_round_50': nearest_round_50,
            'dist_to_round': round(dist_to_round, 2),
        },
        'levels': {
            'today_open': today_open,
            'today_high': today_high,
            'today_low': today_low,
            'today_close': today_close,
            'pdh': pdh, 'pdl': pdl, 'pdm': pdm, 'pdc': pdc,
            'range_5d_high': range_5d_high,
            'range_5d_low': range_5d_low,
        },
    }


def main():
    print("Loading...")
    df = load_data(CSV)
    dg, all_dates = build_date_groups(df)
    print(f"  {len(dg)} days\n")

    # Compute bias for last 10 days for dashboard widget history
    sorted_dates = sorted(all_dates)
    history = []
    for d in sorted_dates[-30:]:
        result = compute_today_bias(dg, all_dates, d)
        if result: history.append(result)

    today = history[-1] if history else None
    if today:
        print("=" * 80)
        print(f"TODAY ({today['date']}) HTF BIAS")
        print("=" * 80)
        print(f"  Score: {today['score']}/100")
        print(f"  Verdict: {today['verdict']}")
        print(f"  Action: {today['action']}")
        print(f"\nFactors:")
        for k, v in today['factors'].items():
            print(f"  - {k}: {v}")
        print(f"\nLevels (today):")
        for k, v in today['levels'].items():
            print(f"  - {k}: {v}")

    # Save
    out = ROOT / 'data' / 'daily_bias.json'
    with open(out, 'w') as f:
        json.dump({'today': today, 'history_30d': history}, f, indent=2)
    print(f'\n[saved] {out}')


if __name__ == '__main__':
    main()
