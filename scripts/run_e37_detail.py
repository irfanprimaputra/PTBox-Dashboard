"""Run e37 backtest with per-trade detail (for TradingView verification).

Outputs each trade: ET datetime, session, direction, entry, SL, TP, exit, PnL.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "code"))

import numpy as np
from ptbox_engine_e37 import (
    load_data, build_date_groups, E37_CONFIG, pattern_any,
)


def session_detail(date_groups, all_dates, sess_name, cfg):
    BS = cfg['box_start_h'] * 60 + cfg['box_start_m']
    BE = BS + cfg['box_dur']
    SESSION_END = (24 * 60) if cfg['session_end_h'] == 24 else cfg['session_end_h'] * 60

    trades = []
    for day in all_dates:
        if day not in date_groups:
            continue
        g = date_groups[day]
        tm = g['tm'].values
        H = g['high'].values; L = g['low'].values
        C = g['close'].values; O = g['open'].values
        DT = g['datetime'].values

        bk = (tm >= BS) & (tm < BE)
        if bk.sum() == 0:
            continue
        bx_hi = H[bk].max(); bx_lo = L[bk].min()
        bw = bx_hi - bx_lo
        if bw < 1.0:
            continue

        tr = (tm >= BE) & (tm < SESSION_END)
        if tr.sum() < 3:
            continue

        Hi = H[tr]; Lo = L[tr]; Cl = C[tr]; Op = O[tr]; DTr = DT[tr]; TMr = tm[tr]

        sl_dist = max(cfg['min_sl'], cfg['sl_box_mult'] * bw)
        body_thresh = cfg['body_pct'] * bw if cfg['body_pct'] > 0 else 0

        in_trade = False
        ed = 0; sp = tp = 0.; ep = 0.
        entry_dt = None
        entered = False

        for i in range(1, len(Cl)):
            ch = Hi[i]; cl = Lo[i]; cc = Cl[i]; co = Op[i]
            ph = Hi[i - 1]; pl = Lo[i - 1]; pc = Cl[i - 1]; po = Op[i - 1]

            if in_trade:
                if ed == 1:
                    if cl <= sp:
                        trades.append({
                            'session': sess_name, 'day': str(day),
                            'entry_dt': entry_dt, 'exit_dt': str(DTr[i]),
                            'dir': 'BUY', 'entry': ep, 'sl': sp, 'tp': tp, 'exit': sp,
                            'box_hi': bx_hi, 'box_lo': bx_lo, 'bw': bw, 'sl_dist': sl_dist,
                            'pnl': -sl_dist, 'result': 'SL',
                        }); in_trade = False; continue
                    if ch >= tp:
                        trades.append({
                            'session': sess_name, 'day': str(day),
                            'entry_dt': entry_dt, 'exit_dt': str(DTr[i]),
                            'dir': 'BUY', 'entry': ep, 'sl': sp, 'tp': tp, 'exit': tp,
                            'box_hi': bx_hi, 'box_lo': bx_lo, 'bw': bw, 'sl_dist': sl_dist,
                            'pnl': tp - ep, 'result': 'TP',
                        }); in_trade = False; continue
                else:
                    if ch >= sp:
                        trades.append({
                            'session': sess_name, 'day': str(day),
                            'entry_dt': entry_dt, 'exit_dt': str(DTr[i]),
                            'dir': 'SELL', 'entry': ep, 'sl': sp, 'tp': tp, 'exit': sp,
                            'box_hi': bx_hi, 'box_lo': bx_lo, 'bw': bw, 'sl_dist': sl_dist,
                            'pnl': -sl_dist, 'result': 'SL',
                        }); in_trade = False; continue
                    if cl <= tp:
                        trades.append({
                            'session': sess_name, 'day': str(day),
                            'entry_dt': entry_dt, 'exit_dt': str(DTr[i]),
                            'dir': 'SELL', 'entry': ep, 'sl': sp, 'tp': tp, 'exit': tp,
                            'box_hi': bx_hi, 'box_lo': bx_lo, 'bw': bw, 'sl_dist': sl_dist,
                            'pnl': ep - tp, 'result': 'TP',
                        }); in_trade = False; continue
                continue

            if entered:
                continue

            if cc > bx_hi:
                if cc - bx_hi < body_thresh:
                    continue
                if pattern_any(po, ph, pl, pc, co, ch, cl, cc, 1):
                    ep = cc; ed = 1
                    sp = bx_lo - sl_dist
                    tp = ep + cfg['tp_mult'] * sl_dist
                    in_trade = True; entered = True
                    entry_dt = str(DTr[i])
                    continue
            elif cc < bx_lo:
                if bx_lo - cc < body_thresh:
                    continue
                if pattern_any(po, ph, pl, pc, co, ch, cl, cc, -1):
                    ep = cc; ed = -1
                    sp = bx_hi + sl_dist
                    tp = ep - cfg['tp_mult'] * sl_dist
                    in_trade = True; entered = True
                    entry_dt = str(DTr[i])
                    continue
    return trades


def main():
    csv = sys.argv[1] if len(sys.argv) > 1 else "/Users/irfanprimaputra.b/Downloads/XAUUSD_M1_e37_validation_20260422_20260427.csv"
    df = load_data(csv)
    dg, dates = build_date_groups(df)

    all_trades = []
    for sess_name, cfg in [('ASIA', E37_CONFIG['asia']), ('LONDON', E37_CONFIG['london']), ('NY', E37_CONFIG['ny'])]:
        all_trades.extend(session_detail(dg, dates, sess_name, cfg))

    # Sort by entry datetime
    all_trades.sort(key=lambda t: t['entry_dt'])

    print("\n" + "═" * 110)
    print(" PT BOX e37 — PER-TRADE DETAIL (ET timezone)")
    print("═" * 110)
    print(f"{'#':<3} {'Session':<7} {'Day':<11} {'Entry (ET)':<19} {'Dir':<5} {'Entry':<10} {'SL':<10} {'TP':<10} {'Exit':<10} {'Result':<6} {'PnL':>8}")
    print("─" * 110)
    total = 0
    for i, t in enumerate(all_trades, 1):
        # entry_dt format like '2026-04-21T19:35:00.000000000'
        et_str = t['entry_dt'].replace('T', ' ')[:19]
        print(f"{i:<3} {t['session']:<7} {t['day']:<11} {et_str:<19} {t['dir']:<5} "
              f"{t['entry']:<10.3f} {t['sl']:<10.3f} {t['tp']:<10.3f} {t['exit']:<10.3f} "
              f"{t['result']:<6} {t['pnl']:>+8.2f}")
        total += t['pnl']
    print("─" * 110)
    print(f"{'TOTAL':<87} {total:>+8.2f} pts ({len(all_trades)} trades)")

    # Per-session summary
    print("\n" + "═" * 60)
    print(" PER-SESSION SUMMARY")
    print("═" * 60)
    for sess in ['ASIA', 'LONDON', 'NY']:
        s_trades = [t for t in all_trades if t['session'] == sess]
        if not s_trades:
            print(f"  {sess:<8} | no trades")
            continue
        wins = sum(1 for t in s_trades if t['result'] == 'TP')
        losses = len(s_trades) - wins
        pnl = sum(t['pnl'] for t in s_trades)
        avg_sl = np.mean([t['sl_dist'] for t in s_trades])
        print(f"  {sess:<8} | trades {len(s_trades)} | W {wins} L {losses} | WR {100*wins/len(s_trades):.0f}% | PnL {pnl:+.2f} | avg SL {avg_sl:.1f}pt")

    # Box info per day per session (verify against Pine boxes)
    print("\n" + "═" * 60)
    print(" BOX INFO PER DAY (verify against TradingView)")
    print("═" * 60)
    for sess_name, cfg in [('ASIA', E37_CONFIG['asia']), ('LONDON', E37_CONFIG['london']), ('NY', E37_CONFIG['ny'])]:
        print(f"\n  {sess_name} (box {cfg['box_start_h']:02d}:{cfg['box_start_m']:02d}/{cfg['box_dur']}m ET):")
        BS = cfg['box_start_h'] * 60 + cfg['box_start_m']
        BE = BS + cfg['box_dur']
        for day in dates:
            if day not in dg: continue
            g = dg[day]
            tm = g['tm'].values
            bk = (tm >= BS) & (tm < BE)
            if bk.sum() == 0:
                print(f"    {day} — no box data"); continue
            bh = g['high'].values[bk].max()
            bl = g['low'].values[bk].min()
            bw = bh - bl
            print(f"    {day} — Hi {bh:.3f}  Lo {bl:.3f}  Width {bw:.2f}pt")


if __name__ == "__main__":
    main()
