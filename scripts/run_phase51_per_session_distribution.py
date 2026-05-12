"""
Phase 51 — Per-Session + Distribution Analysis (REAL pain capture).

User feedback: aggregate PnL nice but doesn't capture variance/pain.
Real trader needs:
- Per-session breakdown (Asia/London/NY independent)
- Daily PnL distribution (P10/P25/P50/P75/P90)
- Worst day frequency (days with -$50+, -$100+)
- Max drawdown per variant
- Loss cluster patterns
- Combinable per-session strategy hybrid

Tests:
A. Per-session breakdown each variant (single strategy all sessions)
B. Hybrid combos (different strategy per session)
C. Daily PnL distribution
D. Pain metrics (max DD, bad day freq)
"""
import sys
import json
from pathlib import Path
import numpy as np
import pandas as pd
from datetime import date

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT / "scripts"))
from ptbox_engine_e37 import load_data, build_date_groups, compute_atr_filter_dates, compute_atr_rank_map
from run_phase50_small_box_full_engine import run_session_full

CSV = "/Users/irfanprimaputra.b/Downloads/XAUUSD_M1_2021_-_2026.csv"
TRUMP_START = date(2025, 1, 1)


def run_session_with_trade_log(dg, dates, sess_name, atr_pass, atr_rank, *,
                                 box_dur, entry_mode, be_trigger_r=1.5):
    """Like run_session_full but also logs per-trade PnL with date for distribution analysis."""
    from run_phase50_small_box_full_engine import (
        is_pin, is_engulf, is_strong_body
    )

    cfg_map = {
        'Asia':   {'box_start_h': 19, 'session_end_h': 24, 'entry_delay_min': 0},
        'London': {'box_start_h': 0,  'session_end_h': 8,  'entry_delay_min': 0},
        'NY':     {'box_start_h': 7,  'session_end_h': 13, 'entry_delay_min': 25},
    }
    cfg = cfg_map[sess_name]
    tp_mult = 2.0; tp_boost_pctile = 72; tp_boost_mult = 1.30
    pb_retest_tol = 3.0; pb_sl_buffer = 2.0
    max_attempts = 5; max_wait_bars = 60

    trades_log = []  # list of (date, pnl_pts)

    for d in dates:
        if d not in dg: continue
        if d not in atr_pass: continue
        g = dg[d]
        if len(g) < 50: continue

        BS = cfg['box_start_h'] * 60
        BE_min = BS + box_dur
        SE = 1439 if cfg['session_end_h'] == 24 else cfg['session_end_h'] * 60 - 1

        tm = g['tm'].values
        H = g['high'].values; L_ = g['low'].values; C = g['close'].values; O = g['open'].values
        box_mask = (tm >= BS) & (tm < BE_min)
        if box_mask.sum() < max(2, box_dur // 5): continue
        bx_hi = H[box_mask].max(); bx_lo = L_[box_mask].min()
        bw = bx_hi - bx_lo
        if bw < 0.5: continue

        delay = cfg['entry_delay_min']
        tr = (tm >= BE_min + delay) & (tm < SE)
        if tr.sum() < 5: continue
        Hi = H[tr]; Lo = L_[tr]; Cl = C[tr]; Op = O[tr]

        atr_rank_today = atr_rank.get(d, 0.5)
        tp_eff = tp_mult * (tp_boost_mult if atr_rank_today >= tp_boost_pctile / 100 else 1.0)

        attempts = 0; in_trade = False
        ed = 0; sp = tp_ = ep = 0.0; sl_orig = 0.0
        be_triggered = False; run_extreme = 0.0
        state = 0; bk_dir = 0; bk_idx = -1

        for i in range(1, len(Cl)):
            ch = Hi[i]; cl_ = Lo[i]; cc = Cl[i]; co = Op[i]
            ph = Hi[i-1]; pl = Lo[i-1]; pc = Cl[i-1]; po = Op[i-1]

            if in_trade:
                sl_dist = abs(ep - sl_orig)
                if not be_triggered:
                    if ed == 1 and ch >= ep + be_trigger_r * sl_dist:
                        sp = max(sp, ep); be_triggered = True; run_extreme = ch
                    elif ed == -1 and cl_ <= ep - be_trigger_r * sl_dist:
                        sp = min(sp, ep); be_triggered = True; run_extreme = cl_
                else:
                    if ed == 1:
                        run_extreme = max(run_extreme, ch)
                        sp = max(sp, run_extreme - sl_dist)
                    else:
                        run_extreme = min(run_extreme, cl_)
                        sp = min(sp, run_extreme + sl_dist)

                if ed == 1:
                    if cl_ <= sp:
                        trades_log.append((d, sp - ep)); in_trade = False; be_triggered = False; continue
                    elif ch >= tp_:
                        trades_log.append((d, tp_ - ep)); in_trade = False; be_triggered = False; continue
                else:
                    if ch >= sp:
                        trades_log.append((d, ep - sp)); in_trade = False; be_triggered = False; continue
                    elif cl_ <= tp_:
                        trades_log.append((d, ep - tp_)); in_trade = False; be_triggered = False; continue
                continue

            if attempts >= max_attempts: continue

            if entry_mode == 'breakout':
                if cc > bx_hi:
                    sl_d = max(2.0, pb_sl_buffer + bw * 0.3); sl_px = cc - sl_d
                    tp_px = cc + tp_eff * sl_d
                    ep = cc; sp = sl_px; sl_orig = sl_px; tp_ = tp_px; ed = 1
                    in_trade = True; attempts += 1; be_triggered = False
                elif cc < bx_lo:
                    sl_d = max(2.0, pb_sl_buffer + bw * 0.3); sl_px = cc + sl_d
                    tp_px = cc - tp_eff * sl_d
                    ep = cc; sp = sl_px; sl_orig = sl_px; tp_ = tp_px; ed = -1
                    in_trade = True; attempts += 1; be_triggered = False

            elif entry_mode == 'breakout_strong':
                if cc > bx_hi and is_strong_body(co, ch, cl_, cc, 1):
                    sl_d = max(2.0, pb_sl_buffer + bw * 0.3); sl_px = cc - sl_d
                    tp_px = cc + tp_eff * sl_d
                    ep = cc; sp = sl_px; sl_orig = sl_px; tp_ = tp_px; ed = 1
                    in_trade = True; attempts += 1; be_triggered = False
                elif cc < bx_lo and is_strong_body(co, ch, cl_, cc, -1):
                    sl_d = max(2.0, pb_sl_buffer + bw * 0.3); sl_px = cc + sl_d
                    tp_px = cc - tp_eff * sl_d
                    ep = cc; sp = sl_px; sl_orig = sl_px; tp_ = tp_px; ed = -1
                    in_trade = True; attempts += 1; be_triggered = False

            elif entry_mode == 'pullback':
                if state == 0:
                    if cc > bx_hi: state = 1; bk_dir = 1; bk_idx = i
                    elif cc < bx_lo: state = 1; bk_dir = -1; bk_idx = i
                elif state == 1:
                    if i - bk_idx > max_wait_bars: state = 0; bk_dir = 0; continue
                    if bk_dir == 1 and cl_ <= bx_hi + pb_retest_tol: state = 2
                    elif bk_dir == -1 and ch >= bx_lo - pb_retest_tol: state = 2
                elif state == 2:
                    if bk_dir == 1 and cl_ >= bx_hi - pb_retest_tol and (is_pin(co, ch, cl_, cc, 1) or is_engulf(po, pc, co, cc, 1)):
                        sl_px = min(cl_, pl) - pb_sl_buffer; sl_d = cc - sl_px
                        if 0 < sl_d <= 30:
                            tp_px = cc + tp_eff * sl_d
                            ep = cc; sp = sl_px; sl_orig = sl_px; tp_ = tp_px; ed = 1
                            in_trade = True; attempts += 1; state = 0; be_triggered = False
                        else: attempts += 1; state = 0
                    elif bk_dir == -1 and ch <= bx_lo + pb_retest_tol and (is_pin(co, ch, cl_, cc, -1) or is_engulf(po, pc, co, cc, -1)):
                        sl_px = max(ch, ph) + pb_sl_buffer; sl_d = sl_px - cc
                        if 0 < sl_d <= 30:
                            tp_px = cc - tp_eff * sl_d
                            ep = cc; sp = sl_px; sl_orig = sl_px; tp_ = tp_px; ed = -1
                            in_trade = True; attempts += 1; state = 0; be_triggered = False
                        else: attempts += 1; state = 0

    return trades_log


def compute_pain_metrics(trades_log, lot=0.02):
    """Compute realistic pain metrics from trade log."""
    if not trades_log:
        return None
    df = pd.DataFrame(trades_log, columns=['date', 'pnl_pt'])
    df['pnl_usd'] = df['pnl_pt'] * lot * 100  # $2/pt at lot 0.02

    # Per-day aggregation
    daily = df.groupby('date')['pnl_usd'].sum()

    # Distribution
    p10 = daily.quantile(0.10)
    p25 = daily.quantile(0.25)
    p50 = daily.quantile(0.50)
    p75 = daily.quantile(0.75)
    p90 = daily.quantile(0.90)

    # Worst metrics
    worst_day = daily.min()
    worst_trade = df['pnl_usd'].min()
    days_neg50 = (daily <= -50).sum()
    days_neg100 = (daily <= -100).sum()
    days_pos50 = (daily >= 50).sum()
    days_pos100 = (daily >= 100).sum()

    # Equity curve
    eq = df['pnl_usd'].cumsum()
    peak = eq.cummax()
    drawdown = (eq - peak)
    max_dd = drawdown.min()

    # Consecutive loss streak
    df['loss'] = df['pnl_usd'] < 0
    max_consec = 0
    current = 0
    for is_loss in df['loss']:
        if is_loss:
            current += 1
            max_consec = max(max_consec, current)
        else:
            current = 0

    return {
        'total_usd': float(df['pnl_usd'].sum()),
        'total_pts': float(df['pnl_pt'].sum()),
        'n_trades': len(df),
        'n_days': len(daily),
        'wr_pct': float(100 * (df['pnl_pt'] > 0).sum() / len(df)),
        'avg_per_day': float(daily.mean()),
        'median_per_day': float(p50),
        'p10_day': float(p10),
        'p25_day': float(p25),
        'p75_day': float(p75),
        'p90_day': float(p90),
        'worst_day': float(worst_day),
        'worst_trade': float(worst_trade),
        'days_loss_50plus': int(days_neg50),
        'days_loss_100plus': int(days_neg100),
        'days_win_50plus': int(days_pos50),
        'days_win_100plus': int(days_pos100),
        'max_drawdown_usd': float(max_dd),
        'max_consec_loss': int(max_consec),
    }


def main():
    print("Loading 5y data...")
    df = load_data(CSV)
    dg, all_dates = build_date_groups(df)
    trump_dates = [d for d in all_dates if d >= TRUMP_START]
    print(f"  Trump-2 era: {len(trump_dates)} days")

    atr_full_set = compute_atr_filter_dates(dg, all_dates, lookback=30, percentile=30)
    atr_pass_trump = {d: True for d in atr_full_set if d >= TRUMP_START}
    atr_rank_map = compute_atr_rank_map(dg, all_dates, lookback=30)
    print(f"  ATR pass Trump: {len(atr_pass_trump)}/{len(trump_dates)}\n")

    print("=" * 130)
    print("PHASE 51 — Per-Session + Distribution + Pain Metrics")
    print("=" * 130)

    # Configs to test (focus on top candidates)
    configs = [
        ('Pine v15 current (BE 1.0R, 90min PB)',   {'box_dur': 90, 'entry_mode': 'pullback', 'be_trigger_r': 1.0}),
        ('Pine v15.1 candidate (BE 1.5R, 90min PB)', {'box_dur': 90, 'entry_mode': 'pullback', 'be_trigger_r': 1.5}),
        ('Pine v15.2 alt (BE 1.5R, 60min BO_strong)', {'box_dur': 60, 'entry_mode': 'breakout_strong', 'be_trigger_r': 1.5}),
        ('Pine v15.3 fast (BE 1.5R, 30min BO)',     {'box_dur': 30, 'entry_mode': 'breakout', 'be_trigger_r': 1.5}),
    ]

    all_results = {}
    for name, cfg in configs:
        print(f"\n### {name} ###")

        # Get per-session trade log
        session_metrics = {}
        all_trades_combined = []
        for sess in ['Asia', 'London', 'NY']:
            trades_log = run_session_with_trade_log(dg, trump_dates, sess, atr_pass_trump, atr_rank_map,
                                                       box_dur=cfg['box_dur'], entry_mode=cfg['entry_mode'],
                                                       be_trigger_r=cfg['be_trigger_r'])
            metrics = compute_pain_metrics(trades_log)
            if metrics:
                session_metrics[sess] = metrics
                all_trades_combined.extend(trades_log)

        # Combined daily (all sessions roll-up)
        combined_metrics = compute_pain_metrics(all_trades_combined)

        all_results[name] = {
            'per_session': session_metrics,
            'combined': combined_metrics,
        }

        # Print per session
        print(f'{"Session":<8} | {"trades":>6} | {"days":>4} | {"WR%":>5} | {"$/yr":>7} | {"avg/d":>6} | {"P10":>6} | {"P90":>6} | {"worst$":>7} | {"-$50":>5} | {"+$50":>5} | {"MaxDD":>7}')
        print('-' * 130)
        for sess in ['Asia', 'London', 'NY']:
            m = session_metrics.get(sess)
            if m:
                usd_yr = m['total_usd'] / 1.33
                print(f'{sess:<8} | {m["n_trades"]:>6} | {m["n_days"]:>4} | {m["wr_pct"]:>5.1f} | {usd_yr:>+7.0f} | {m["avg_per_day"]:>+6.1f} | {m["p10_day"]:>+6.1f} | {m["p90_day"]:>+6.1f} | {m["worst_day"]:>+7.1f} | {m["days_loss_50plus"]:>5} | {m["days_win_50plus"]:>5} | {m["max_drawdown_usd"]:>+7.0f}')
        # Combined
        if combined_metrics:
            usd_yr_c = combined_metrics['total_usd'] / 1.33
            print(f'{"TOTAL":<8} | {combined_metrics["n_trades"]:>6} | {combined_metrics["n_days"]:>4} | {combined_metrics["wr_pct"]:>5.1f} | {usd_yr_c:>+7.0f} | {combined_metrics["avg_per_day"]:>+6.1f} | {combined_metrics["p10_day"]:>+6.1f} | {combined_metrics["p90_day"]:>+6.1f} | {combined_metrics["worst_day"]:>+7.1f} | {combined_metrics["days_loss_50plus"]:>5} | {combined_metrics["days_win_50plus"]:>5} | {combined_metrics["max_drawdown_usd"]:>+7.0f}')

    # === HYBRID COMBO TEST ===
    print('\n' + '=' * 130)
    print("HYBRID COMBO: Different strategy per session (Best per-session pick)")
    print('=' * 130)

    # Per-session best from the configs tested
    # Determine best per session
    print("\nPer-session winner (by $/yr):")
    for sess in ['Asia', 'London', 'NY']:
        best_config = max(all_results.items(),
                          key=lambda x: x[1]['per_session'].get(sess, {}).get('total_usd', -999999))
        m = best_config[1]['per_session'].get(sess)
        if m:
            print(f"  {sess}: {best_config[0]} → ${m['total_usd']/1.33:+.0f}/yr | P10 ${m['p10_day']:+.1f} | worst day ${m['worst_day']:+.1f}")

    # Save
    out = ROOT / 'data' / 'phase51_per_session_distribution.json'
    with open(out, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f'\n[saved] {out}')

    # === PAIN REALITY CHECK ===
    print('\n' + '=' * 130)
    print("PAIN REALITY CHECK (Pine v15.1 candidate)")
    print('=' * 130)
    cand = all_results['Pine v15.1 candidate (BE 1.5R, 90min PB)']['combined']
    if cand:
        print(f"User trade today: -$29.25 ({-29.25 / 200 * 100:.1f}% balance)")
        print(f"\nFor Pine v15.1 deployment, what to expect:")
        print(f"  Avg per active day: ${cand['avg_per_day']:+.2f}")
        print(f"  P10 (worst 10% days): ${cand['p10_day']:+.2f}")
        print(f"  P25 (worst 25% days): ${cand['p25_day']:+.2f}")
        print(f"  P50 median day: ${cand['median_per_day']:+.2f}")
        print(f"  P75 day: ${cand['p75_day']:+.2f}")
        print(f"  P90 day: ${cand['p90_day']:+.2f}")
        print(f"  Worst day ever: ${cand['worst_day']:+.2f}")
        print(f"\nFrequency:")
        print(f"  Days >$50 loss: {cand['days_loss_50plus']} of {cand['n_days']} = {100*cand['days_loss_50plus']/cand['n_days']:.1f}%")
        print(f"  Days >$100 loss: {cand['days_loss_100plus']} of {cand['n_days']} = {100*cand['days_loss_100plus']/cand['n_days']:.1f}%")
        print(f"  Days >$50 win: {cand['days_win_50plus']} of {cand['n_days']} = {100*cand['days_win_50plus']/cand['n_days']:.1f}%")
        print(f"  Max consecutive loss trades: {cand['max_consec_loss']}")
        print(f"  Max drawdown ever: ${cand['max_drawdown_usd']:+.0f}")


if __name__ == '__main__':
    main()
