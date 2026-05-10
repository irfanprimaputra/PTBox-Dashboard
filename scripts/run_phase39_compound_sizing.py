"""
Phase 39 — Aggressive Compound Sizing (Opsi B) engine sim.

Validate sebelum touch Pine: 3 consecutive wins per session → naik tier lot
(0.02 → 0.03). Loss → instant balik base 0.02. Daily reset midnight ET.

Mental zero impact: per-trade $ risk constant DI DALAM streak, hanya bonus
kalau lagi hot streak. Loss tetap di base lot (worst trade SAMA).

Phase A gate (must pass):
- WR before/after assertion (sizing tidak ubah trade outcome)
- Closed PnL compound > closed PnL flat (delta ≥ +30% conservative threshold)
- Worst single trade compound ≤ -$140 USD (loss cap = base $116 × 1.2 buffer)
- Per-session breakdown: NO session goes net-negative

If Phase A pass → queue Pine v15 implementation.
If Phase A fail → reject, document why.
"""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
TRADES_PATH = ROOT / 'data' / 'phase14_e44_pullback_trades.json'

# ─── Config sweep ─────────────────────────────────────────────────────────────
SCENARIOS = [
    # (name, base_lot, tier_step, max_tier, threshold, scope, reset_on_loss)
    ('FLAT_baseline',          0.02, 0.00, 0.02, 99,  'session', True),
    ('Opsi_B_default',         0.02, 0.01, 0.03, 3,   'session', True),
    ('Opsi_B_aggressive_2',    0.02, 0.01, 0.03, 2,   'session', True),
    ('Opsi_B_conservative_4',  0.02, 0.01, 0.03, 4,   'session', True),
    ('Opsi_B_step2_max4',      0.02, 0.02, 0.04, 3,   'session', True),
    ('Opsi_B_max5',            0.02, 0.01, 0.05, 3,   'session', True),
    ('Opsi_B_global_streak',   0.02, 0.01, 0.03, 3,   'global',  True),
    ('Opsi_B_no_loss_reset',   0.02, 0.01, 0.03, 3,   'session', False),
]

USD_PER_PT_PER_LOT = 100  # XAUUSD: 1 lot × 1pt = $100


def simulate_compound(trades: pd.DataFrame, base_lot: float, tier_step: float,
                       max_tier: float, threshold: int, scope: str, reset_on_loss: bool):
    """Replay trades with compound sizing. Returns per-trade lot + USD PnL."""
    out = []
    streaks = {'Asia': 0, 'London': 0, 'NY': 0, 'global': 0}
    cur_date = None

    # Sort by date + tm_in to ensure chronological order
    trades = trades.sort_values(['date', 'tm_in']).reset_index(drop=True)

    for _, t in trades.iterrows():
        td = t['date']
        sess = t['sess']

        # Daily reset (midnight ET — date change)
        if cur_date is not None and td != cur_date:
            for k in streaks: streaks[k] = 0
        cur_date = td

        # Determine current streak based on scope
        streak_key = sess if scope == 'session' else 'global'
        cur_streak = streaks[streak_key]

        # Lot sizing
        if cur_streak >= threshold:
            tier_extra = min(tier_step * (cur_streak // threshold),
                             max_tier - base_lot)
            lot = min(base_lot + tier_extra, max_tier)
        else:
            lot = base_lot

        # Apply trade
        pnl_usd = t['pnl'] * lot * USD_PER_PT_PER_LOT
        win = t['reason'] == 'TP' or (t['reason'] == 'EOD' and t['pnl'] > 0)

        out.append({
            'date': td, 'sess': sess, 'reason': t['reason'],
            'pnl_pt': t['pnl'], 'lot': lot, 'pnl_usd': pnl_usd,
            'streak_before': cur_streak, 'win': win,
        })

        # Update streak
        if win:
            streaks[streak_key] += 1
        else:
            if reset_on_loss:
                streaks[streak_key] = 0

    return pd.DataFrame(out)


def summarize(name: str, df: pd.DataFrame) -> dict:
    total_usd = df['pnl_usd'].sum()
    n = len(df)
    wins = int(df['win'].sum())
    wr = 100 * wins / n
    worst = df['pnl_usd'].min()
    avg_loss = df[df['pnl_usd'] < 0]['pnl_usd'].mean()
    avg_win  = df[df['pnl_usd'] > 0]['pnl_usd'].mean()
    eq = df['pnl_usd'].cumsum()
    peak = eq.cummax()
    dd = (eq - peak).min()
    per_sess = df.groupby('sess')['pnl_usd'].sum().to_dict()
    tier_dist = df['lot'].value_counts(normalize=True).sort_index().to_dict()
    return {
        'scenario': name,
        'n_trades': n,
        'wr_pct': round(wr, 2),
        'total_usd': round(total_usd, 2),
        'usd_per_yr': round(total_usd / 5, 2),  # 5-year backtest
        'worst_trade_usd': round(worst, 2),
        'avg_loss_usd': round(avg_loss, 2) if pd.notna(avg_loss) else 0,
        'avg_win_usd': round(avg_win, 2) if pd.notna(avg_win) else 0,
        'max_drawdown_usd': round(dd, 2),
        'per_session_usd': {k: round(v, 2) for k, v in per_sess.items()},
        'tier_distribution': {f'{lot:.2f}': round(p * 100, 1) for lot, p in tier_dist.items()},
    }


def main():
    print(f"Loading {TRADES_PATH.name} ...")
    raw = json.load(open(TRADES_PATH))
    trades = pd.DataFrame(raw['trades'])
    trades['date'] = pd.to_datetime(trades['date'])
    print(f"  {len(trades)} trades loaded\n")

    summaries = []
    baseline = None
    for cfg in SCENARIOS:
        name, base, step, mx, thr, scope, reset = cfg
        df = simulate_compound(trades, base, step, mx, thr, scope, reset)
        s = summarize(name, df)
        summaries.append(s)
        if 'FLAT' in name:
            baseline = s

    # Print table
    print('=' * 130)
    print(f'PHASE 39 — COMPOUND SIZING SWEEP (5y, Opsi B variants)')
    print('=' * 130)
    print(f'{"Scenario":<28} | {"Trades":>7} | {"WR%":>6} | {"Total $":>9} | {"$/yr":>8} | {"Worst":>7} | {"AvgL":>6} | {"AvgW":>6} | {"MaxDD":>7}')
    print('-' * 130)
    for s in summaries:
        print(f'{s["scenario"]:<28} | {s["n_trades"]:>7} | {s["wr_pct"]:>6.2f} | {s["total_usd"]:>9.0f} | {s["usd_per_yr"]:>8.0f} | {s["worst_trade_usd"]:>7.0f} | {s["avg_loss_usd"]:>6.1f} | {s["avg_win_usd"]:>6.1f} | {s["max_drawdown_usd"]:>7.0f}')

    # Phase A gate validation
    print()
    print('=' * 130)
    print('PHASE A GATE VALIDATION (Opsi_B_default vs FLAT_baseline)')
    print('=' * 130)
    flat = baseline
    opsi = next(s for s in summaries if s['scenario'] == 'Opsi_B_default')
    delta_pct = (opsi['total_usd'] - flat['total_usd']) / abs(flat['total_usd']) * 100 if flat['total_usd'] != 0 else 0

    gates = []
    # Gate 1: WR unchanged (sizing doesn't modify trade outcome)
    gates.append(('WR identical', abs(opsi['wr_pct'] - flat['wr_pct']) < 0.01,
                  f"flat={flat['wr_pct']}% opsi={opsi['wr_pct']}%"))
    # Gate 2: Total PnL ≥ +30% vs flat
    gates.append(('PnL Δ ≥ +30%', delta_pct >= 30,
                  f'Δ={delta_pct:+.1f}% (flat=${flat["total_usd"]:.0f} → opsi=${opsi["total_usd"]:.0f})'))
    # Gate 3: Worst single trade ≤ -$140 (1.2× buffer over base $116)
    gates.append(('Worst trade ≤ -$140', opsi['worst_trade_usd'] >= -140,
                  f'worst=${opsi["worst_trade_usd"]:.0f}'))
    # Gate 4: Max drawdown within 1.5× flat
    flat_dd = abs(flat['max_drawdown_usd']) if flat['max_drawdown_usd'] else 1
    opsi_dd = abs(opsi['max_drawdown_usd'])
    gates.append(('DD within 1.5× flat', opsi_dd <= flat_dd * 1.5,
                  f'flat_dd={flat_dd:.0f} opsi_dd={opsi_dd:.0f} ratio={opsi_dd/flat_dd:.2f}×'))
    # Gate 5: NO session net-negative
    sess_neg = [s for s, v in opsi['per_session_usd'].items() if v < 0]
    gates.append(('No session net-negative', len(sess_neg) == 0,
                  f'negative={sess_neg if sess_neg else "none"}'))

    print()
    all_pass = True
    for label, ok, detail in gates:
        flag = '✅ PASS' if ok else '❌ FAIL'
        print(f'  {flag}  {label:<28} | {detail}')
        if not ok: all_pass = False

    verdict = 'PASS — queue Pine v15 implementation' if all_pass else 'FAIL — reject, do NOT touch Pine'
    print()
    print('=' * 130)
    print(f'  PHASE A VERDICT: {verdict}')
    print('=' * 130)

    # Trump-2 specific projection (2025-2026 trades only)
    trades_t2 = trades[trades['date'].dt.year.isin([2025, 2026])].copy()
    if len(trades_t2) > 0:
        df_t2_flat = simulate_compound(trades_t2, 0.02, 0.00, 0.02, 99, 'session', True)
        df_t2_opsi = simulate_compound(trades_t2, 0.02, 0.01, 0.03, 3, 'session', True)
        s_t2_flat = summarize('Trump2_FLAT', df_t2_flat)
        s_t2_opsi = summarize('Trump2_OpsiB', df_t2_opsi)
        # Annualize (Trump-2 era = 16 months ~ 1.33y)
        years_t2 = 1.33
        print()
        print('TRUMP-2 ERA (2025-2026) PROJECTION:')
        print(f'  FLAT      : ${s_t2_flat["total_usd"]:.0f} total → ${s_t2_flat["total_usd"]/years_t2:.0f}/yr')
        print(f'  Opsi B    : ${s_t2_opsi["total_usd"]:.0f} total → ${s_t2_opsi["total_usd"]/years_t2:.0f}/yr')
        boost_t2 = (s_t2_opsi['total_usd'] - s_t2_flat['total_usd']) / abs(s_t2_flat['total_usd']) * 100
        print(f'  Δ         : {boost_t2:+.1f}% boost (Opsi B vs FLAT, Trump-2 regime)')

    # Save
    out_path = ROOT / 'data' / 'phase39_compound_sizing.json'
    output = {
        'phase': 39,
        'description': 'Aggressive Compound Sizing (Opsi B) engine sim',
        'config_swept': [list(c) for c in SCENARIOS],
        'summaries': summaries,
        'phase_a_verdict': 'PASS' if all_pass else 'FAIL',
        'gate_results': [
            {'gate': lbl, 'pass': bool(ok), 'detail': det}
            for lbl, ok, det in gates
        ],
    }
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    print(f'\n[saved] {out_path}')


if __name__ == '__main__':
    main()
