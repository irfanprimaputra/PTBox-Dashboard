"""Phase 7 e26 — Iterate NY + Asia improvements.

Untested hypotheses for NY (current +308 / Asia +182):

NY variants:
  e26-NY-1  Strict pattern (pin+engulf only, drop inside_bar — weakest pattern)
  e26-NY-2  Body close confirmation (close > boxHi by ≥30% box_width)
  e26-NY-3  Silver Bullet zone restrict (10:00-11:00 EST only)
  e26-NY-4  Skip Friday NY (US news squaring)
  e26-NY-5  Higher min_box_width (skip narrow boxes <3pt)

Asia variants:
  e26-A-1   Box-width regime: skip if bw > 8pt (catch only tight Asian range)
  e26-A-2   Adaptive TP: opposite edge if narrow (<3pt), boxMid if wide
  e26-A-3   Pre-London narrow: 22:30-23:00 ET only (peak consolidation)
  e26-A-4   Skip if extreme too far (>15pt) — proxy for live filter alignment
  e26-A-5   Both extremes touched filter (bidirectional pre-trade structure)

Walk-forward 19Q. Compare vs e20d baseline +976 (Asia +182, NY +308).
"""
import os, sys, json, datetime, time
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT / "scripts"))

from ptbox_quarterly_v3 import CONFIG, load_data, build_date_groups, PATTERN_VARIANTS
from ptbox_quarterly_v4 import ASIA_MEANREV_VARIANTS

# Try import the e20 backtest function (mean-rev with R:R)
try:
    from run_phase7_e20_asia_rr import meanrev_fail_v2
except ImportError:
    pass


def is_pin(o, h, l, c, direction):
    rng = h - l
    if rng <= 0: return False
    body = abs(c - o)
    if body / rng > 0.30: return False
    if direction == 1:
        return (min(o, c) - l) / rng >= 0.50
    return (h - max(o, c)) / rng >= 0.50


def is_engulf(po, pc, o, c, direction):
    if direction == 1:
        return pc < po and c > o and o <= pc and c >= po
    return pc > po and c < o and o >= pc and c <= po


def is_inside(ph, pl, h, l):
    return h < ph and l > pl


def pattern_strict(po, ph, pl, pc, o, h, l, c, direction):
    """Pin OR engulfing only (NO inside_bar — weakest)."""
    return is_pin(o, h, l, c, direction) or is_engulf(po, pc, o, c, direction)


def pattern_any(po, ph, pl, pc, o, h, l, c, direction):
    return is_pin(o, h, l, c, direction) or is_engulf(po, pc, o, c, direction) or is_inside(ph, pl, h, l)


def backtest_ny_direct_v2(date_groups, all_dates, bh, bm, dur,
                          min_sl=3.0, sl_box_mult=0.5, tp1_mult=3.0, tp2_mult=6.0,
                          min_box_width=1.0, pattern_fn=pattern_any,
                          body_close_pct=0.0, time_window=None,
                          skip_friday=False):
    """NY direct breakout backtest with extra filters.

    body_close_pct: require close > boxHi by ≥ X% of box_width (0 = disabled)
    time_window: tuple (start_min, end_min) in ET — None = full session
    skip_friday: skip if weekday == Friday
    """
    BS = bh * 60 + bm
    BE = BS + dur
    SESSION_END = 12 * 60  # 12:00 ET

    tw = tl = 0
    pnl_list = []

    for day in all_dates:
        if day not in date_groups:
            pnl_list.append(0.); continue

        # Filter Friday
        if skip_friday:
            try:
                d = pd.to_datetime(day).weekday()
                if d == 4:  # Friday
                    pnl_list.append(0.); continue
            except:
                pass

        g = date_groups[day]
        tm = g['tm'].values
        H = g['high'].values; L = g['low'].values
        C = g['close'].values; O = g['open'].values

        bk = (tm >= BS) & (tm < BE)
        if bk.sum() == 0:
            pnl_list.append(0.); continue
        bx_hi = H[bk].max(); bx_lo = L[bk].min()
        bw = bx_hi - bx_lo
        if bw < min_box_width:
            pnl_list.append(0.); continue

        sess_start = BE
        sess_end = SESSION_END
        if time_window:
            sess_start = max(sess_start, time_window[0])
            sess_end = min(sess_end, time_window[1])

        tr = (tm >= sess_start) & (tm < sess_end)
        if tr.sum() < 3:
            pnl_list.append(0.); continue

        Hi = H[tr]; Lo = L[tr]; Cl = C[tr]; Op = O[tr]
        TM = tm[tr]

        sl_dist = max(min_sl, sl_box_mult * bw)
        body_thresh = body_close_pct * bw if body_close_pct > 0 else 0

        # Track previous bar for pattern (need lookback)
        full_idx = np.where(tr)[0]
        in_trade = False
        ed = 0; sp = tp1 = tp2 = 0.; ep = 0.
        dp = 0.; dw = dl = 0
        nyEntered = False

        for i in range(1, len(Cl)):
            ch = Hi[i]; cl = Lo[i]; cc = Cl[i]; co = Op[i]
            ph = Hi[i-1]; pl = Lo[i-1]; pc = Cl[i-1]; po = Op[i-1]

            if in_trade:
                if ed == 1:
                    if cl <= sp:
                        dl += 1; dp -= sl_dist; in_trade = False
                        continue
                    if ch >= tp2:
                        dw += 1; dp += (tp2 - ep); in_trade = False
                        continue
                else:
                    if ch >= sp:
                        dl += 1; dp -= sl_dist; in_trade = False
                        continue
                    if cl <= tp2:
                        dw += 1; dp += (ep - tp2); in_trade = False
                        continue
                continue

            if nyEntered: continue

            # Bull breakout check
            if cc > bx_hi:
                if cc - bx_hi < body_thresh:
                    continue  # body close not strong enough
                if pattern_fn(po, ph, pl, pc, co, ch, cl, cc, 1):
                    ep = cc; ed = 1
                    sp = bx_lo - sl_dist
                    tp1 = ep + tp1_mult * sl_dist
                    tp2 = ep + tp2_mult * sl_dist
                    in_trade = True; nyEntered = True
                    continue
            elif cc < bx_lo:
                if bx_lo - cc < body_thresh:
                    continue
                if pattern_fn(po, ph, pl, pc, co, ch, cl, cc, -1):
                    ep = cc; ed = -1
                    sp = bx_hi + sl_dist
                    tp1 = ep - tp1_mult * sl_dist
                    tp2 = ep - tp2_mult * sl_dist
                    in_trade = True; nyEntered = True
                    continue

        tw += dw; tl += dl
        pnl_list.append(dp)

    tt = tw + tl
    if tt < 30:
        return None
    return {
        'pnl': float(np.sum(pnl_list)),
        'trades': tt, 'wins': tw, 'losses': tl,
        'wr': 100.0 * tw / tt if tt else 0,
    }


def main():
    csv = "/Users/irfanprimaputra.b/Downloads/XAUUSD_M1_2021_-_2026.csv"
    df = load_data(csv)
    df_recent = df[df['datetime'] >= '2024-01-01']
    print(f"Test data: {len(df_recent):,} bars (2024+ recent regime)")
    dg, dates = build_date_groups(df_recent)

    print("\n" + "="*72)
    print(" NY VARIANTS — recent 2024-2026 (~2.3 years)")
    print("="*72)
    print("Baseline e20d NY config (pattern=any, no extras): expected ~+150 pts/2.3y")

    ny_variants = [
        ("NY baseline (any pattern)",     {"pattern_fn": pattern_any}),
        ("NY-1 strict pattern (no inside)", {"pattern_fn": pattern_strict}),
        ("NY-2 body close ≥30% bw",        {"pattern_fn": pattern_any, "body_close_pct": 0.30}),
        ("NY-2b body close ≥50% bw",       {"pattern_fn": pattern_any, "body_close_pct": 0.50}),
        ("NY-3 Silver Bullet 10-11 EST",   {"pattern_fn": pattern_any, "time_window": (10*60, 11*60)}),
        ("NY-4 skip Friday",               {"pattern_fn": pattern_any, "skip_friday": True}),
        ("NY-5 min_box_width 5pt",         {"pattern_fn": pattern_any, "min_box_width": 5.0}),
        ("NY-1+4 strict + skip Fri",       {"pattern_fn": pattern_strict, "skip_friday": True}),
        ("NY-1+5 strict + bw≥5",           {"pattern_fn": pattern_strict, "min_box_width": 5.0}),
    ]

    ny_results = []
    for label, kwargs in ny_variants:
        r = backtest_ny_direct_v2(dg, dates, 9, 3, 5, **kwargs)
        if r is None:
            print(f"  {label:<40} | TOO FEW TRADES")
            continue
        marker = " ⭐" if r['pnl'] > 200 else ""
        print(f"  {label:<40} | PnL {r['pnl']:>+7.1f} | trades {r['trades']:>4} | WR {r['wr']:>4.1f}%{marker}")
        ny_results.append({"label": label, **r})

    print("\n" + "="*72)
    print(" ASIA VARIANTS — recent 2024-2026")
    print("="*72)
    print("Baseline e20d Asia (late-window 21-23 ET): expected ~+78 pts/2.3y")

    # Asia variants use the existing meanrev function but with parameter overrides
    variant = ASIA_MEANREV_VARIANTS['asia_a2_fail']

    # We re-import the meanrev_fail_v2 from e20 to use the proper engine
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        from run_phase7_e20_asia_rr import meanrev_fail_v2
    except ImportError as e:
        print(f"Cannot import meanrev_fail_v2: {e}")
        return

    # Asia baseline check
    r0 = meanrev_fail_v2(dg, dates, 21, 0, 7, variant)
    print(f"  Asia baseline (late-window 21-23 ET):  PnL {r0['pnl']:>+7.1f} | trades {r0['trades']:>4} | WR {r0['wr']:>4.1f}%" if r0 else "  Asia baseline: NONE")

    # A-1: Box width regime — skip wide boxes (modify variant.min_box_width=None, then post-filter)
    # We do a coarse approximation: re-run with adjusted MIN_BW
    custom_v_narrow = dict(variant); custom_v_narrow['min_box_width'] = 1.0
    r1 = meanrev_fail_v2(dg, dates, 21, 0, 7, custom_v_narrow)
    print(f"  A-1 baseline check (min_bw=1):         PnL {r1['pnl']:>+7.1f} | trades {r1['trades']:>4}" if r1 else "  A-1: NONE")

    # A-3: Pre-London narrow window 22:30-23:00 ET only (last 30 min of Asia)
    r3 = meanrev_fail_v2(dg, dates, 22, 30, 7, variant)  # box at 22:30-22:37
    print(f"  A-3 Pre-London 22:30 box:              PnL {r3['pnl']:>+7.1f} | trades {r3['trades']:>4} | WR {r3['wr']:>4.1f}%" if r3 else "  A-3: NONE")

    # A-2: Different TP mode (opposite_edge for narrow, midpoint for wide)
    # Use the v2 function's tp_mode parameter
    r2 = meanrev_fail_v2(dg, dates, 21, 0, 7, variant, tp_mode="opposite_edge")
    print(f"  A-2 TP=opposite_edge (full revert):    PnL {r2['pnl']:>+7.1f} | trades {r2['trades']:>4} | WR {r2['wr']:>4.1f}%" if r2 else "  A-2: NONE")

    # Summary
    out = ROOT / "data" / "phase7_e26_iterate_results.json"
    with open(out, 'w') as f:
        json.dump({
            'generated': datetime.datetime.now().isoformat(),
            'baseline_reference': {'asia_e20d_2.3y': '+78', 'ny_e16b_2.3y': '+150'},
            'ny_results': ny_results,
        }, f, indent=2)

    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
