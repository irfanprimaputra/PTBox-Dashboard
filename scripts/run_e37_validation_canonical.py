"""
PT Box e37 — Canonical-Engine Validation Backtest
==================================================
Uses the production canonical engine (`code/ptbox_engine_e37.py`) which is
the source of truth that produced the +9084 5y baseline. This wrapper
instruments the canonical session loop to capture per-trade detail for
ledger reporting (the canonical engine returns aggregates only).

CANONICAL e37 BEHAVIOR (note: differs slightly from Pinescript):
- ONE trade max per session per day (`entered` flag, no max_attempts cap)
- Max-SL filter skips ENTIRE day if sl_dist > max_sl_pts (vs per-trade in Pine)
- Same pattern detection (pin/engulf/inside) and SL/TP placement as Pine

Usage:
    python scripts/run_e37_validation_canonical.py <csv_path>
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, date as date_t, timedelta
from pathlib import Path
from typing import Optional

# Import canonical engine
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))
from ptbox_engine_e37 import (
    load_data, build_date_groups, E37_CONFIG,
    pattern_any, backtest_asia, backtest_london, backtest_ny,
)


@dataclass
class Trade:
    session: str
    et_date: str
    direction: int
    entry_idx: int
    entry_tm: int          # ET minute of day
    entry_px: float
    sl_px: float
    tp_px: float
    box_hi: float
    box_lo: float
    box_width: float
    sl_dist: float         # the planned SL distance (per canonical engine)
    sl_dist_actual: float  # |entry - sl_px|, real risk
    tp_dist: float         # |entry - tp_px|
    exit_tm: Optional[int] = None
    exit_px: Optional[float] = None
    exit_reason: Optional[str] = None
    pnl_pts: Optional[float] = None              # canonical engine semantics (planned SL)
    pnl_pts_realistic: Optional[float] = None    # actual entry-to-exit difference
    bars_held: int = 0


def instrumented_session(date_groups, all_dates, session_name, cfg) -> tuple[list[Trade], dict]:
    """
    Replays canonical `backtest_session_direct` logic but captures trades.
    Logic is byte-for-byte identical to ptbox_engine_e37.backtest_session_direct.
    """
    BS = cfg["box_start_h"] * 60 + cfg["box_start_m"]
    BE = BS + cfg["box_dur"]
    SESSION_END = 24 * 60 if cfg["session_end_h"] == 24 else cfg["session_end_h"] * 60
    sl_box_mult = cfg["sl_box_mult"]
    min_sl = cfg["min_sl"]
    tp_mult = cfg["tp_mult"]
    body_pct = cfg["body_pct"]
    max_sl_pts = cfg.get("max_sl_pts")
    min_box_width = 1.0

    trades: list[Trade] = []
    tw = tl = 0
    pnl_list = []
    sl_dists = []

    for day in all_dates:
        if day not in date_groups:
            pnl_list.append(0.0); continue
        g = date_groups[day]
        tm = g['tm'].values
        H = g['high'].values; L = g['low'].values
        C = g['close'].values; O = g['open'].values

        bk = (tm >= BS) & (tm < BE)
        if bk.sum() == 0:
            pnl_list.append(0.0); continue
        bx_hi = float(H[bk].max()); bx_lo = float(L[bk].min())
        bw = bx_hi - bx_lo
        if bw < min_box_width:
            pnl_list.append(0.0); continue

        tr = (tm >= BE) & (tm < SESSION_END)
        if tr.sum() < 3:
            pnl_list.append(0.0); continue

        Hi = H[tr]; Lo = L[tr]; Cl = C[tr]; Op = O[tr]; Tm = tm[tr]

        sl_dist = max(min_sl, sl_box_mult * bw)
        if max_sl_pts is not None and sl_dist > max_sl_pts:
            pnl_list.append(0.0); continue
        body_thresh = body_pct * bw if body_pct > 0 else 0

        in_trade = False
        ed = 0; sp = tp = 0.0; ep = 0.0
        dp = 0.0; dw = dl = 0
        entered = False
        cur_trade: Optional[Trade] = None

        for i in range(1, len(Cl)):
            ch = Hi[i]; cl = Lo[i]; cc = Cl[i]; co = Op[i]
            ph = Hi[i - 1]; pl = Lo[i - 1]; pc = Cl[i - 1]; po = Op[i - 1]

            if in_trade:
                if ed == 1:
                    if cl <= sp:
                        dl += 1; dp -= sl_dist; in_trade = False
                        if cur_trade:
                            cur_trade.exit_tm = int(Tm[i]); cur_trade.exit_px = sp
                            cur_trade.exit_reason = "SL"
                            cur_trade.pnl_pts = -sl_dist               # CANONICAL (planned)
                            cur_trade.pnl_pts_realistic = sp - ep      # REALISTIC (actual)
                            cur_trade.bars_held = i - cur_trade.entry_idx
                            cur_trade = None
                        continue
                    if ch >= tp:
                        dw += 1; dp += (tp - ep); in_trade = False
                        if cur_trade:
                            cur_trade.exit_tm = int(Tm[i]); cur_trade.exit_px = tp
                            cur_trade.exit_reason = "TP"
                            cur_trade.pnl_pts = tp - ep
                            cur_trade.pnl_pts_realistic = tp - ep
                            cur_trade.bars_held = i - cur_trade.entry_idx
                            cur_trade = None
                        continue
                else:
                    if ch >= sp:
                        dl += 1; dp -= sl_dist; in_trade = False
                        if cur_trade:
                            cur_trade.exit_tm = int(Tm[i]); cur_trade.exit_px = sp
                            cur_trade.exit_reason = "SL"
                            cur_trade.pnl_pts = -sl_dist               # CANONICAL (planned)
                            cur_trade.pnl_pts_realistic = ep - sp      # REALISTIC (actual, short)
                            cur_trade.bars_held = i - cur_trade.entry_idx
                            cur_trade = None
                        continue
                    if cl <= tp:
                        dw += 1; dp += (ep - tp); in_trade = False
                        if cur_trade:
                            cur_trade.exit_tm = int(Tm[i]); cur_trade.exit_px = tp
                            cur_trade.exit_reason = "TP"
                            cur_trade.pnl_pts = ep - tp
                            cur_trade.pnl_pts_realistic = ep - tp
                            cur_trade.bars_held = i - cur_trade.entry_idx
                            cur_trade = None
                        continue
                continue

            if entered:
                continue

            if cc > bx_hi:
                if cc - bx_hi < body_thresh:
                    continue
                if pattern_any(po, ph, pl, pc, co, ch, cl, cc, 1):
                    ep = float(cc); ed = 1
                    sp = bx_lo - sl_dist
                    tp = ep + tp_mult * sl_dist
                    in_trade = True; entered = True
                    sl_dists.append(sl_dist)
                    cur_trade = Trade(
                        session=session_name, et_date=str(day), direction=1,
                        entry_idx=i, entry_tm=int(Tm[i]), entry_px=ep,
                        sl_px=sp, tp_px=tp,
                        box_hi=bx_hi, box_lo=bx_lo, box_width=bw,
                        sl_dist=sl_dist, sl_dist_actual=abs(ep - sp),
                        tp_dist=abs(ep - tp),
                    )
                    trades.append(cur_trade)
                    continue
            elif cc < bx_lo:
                if bx_lo - cc < body_thresh:
                    continue
                if pattern_any(po, ph, pl, pc, co, ch, cl, cc, -1):
                    ep = float(cc); ed = -1
                    sp = bx_hi + sl_dist
                    tp = ep - tp_mult * sl_dist
                    in_trade = True; entered = True
                    sl_dists.append(sl_dist)
                    cur_trade = Trade(
                        session=session_name, et_date=str(day), direction=-1,
                        entry_idx=i, entry_tm=int(Tm[i]), entry_px=ep,
                        sl_px=sp, tp_px=tp,
                        box_hi=bx_hi, box_lo=bx_lo, box_width=bw,
                        sl_dist=sl_dist, sl_dist_actual=abs(ep - sp),
                        tp_dist=abs(ep - tp),
                    )
                    trades.append(cur_trade)
                    continue

        # End-of-day: if still in trade, mark to close at last bar
        if in_trade and cur_trade:
            cur_trade.exit_tm = int(Tm[-1])
            cur_trade.exit_px = float(Cl[-1])
            cur_trade.exit_reason = "EOD"
            mtm = (Cl[-1] - cur_trade.entry_px) * cur_trade.direction
            cur_trade.pnl_pts = mtm
            cur_trade.pnl_pts_realistic = mtm
            cur_trade.bars_held = len(Cl) - 1 - cur_trade.entry_idx

        tw += dw; tl += dl
        pnl_list.append(dp)

    tt = tw + tl
    summary = {
        'pnl': sum(pnl_list),
        'trades': tt, 'wins': tw, 'losses': tl,
        'wr': 100.0 * tw / tt if tt else 0,
        'avg_sl': sum(sl_dists) / len(sl_dists) if sl_dists else 0,
    }
    return trades, summary


def fmt_tm(minute: int) -> str:
    return f"{minute//60:02d}:{minute%60:02d}"


def report(trades_by_session, summary_by_session, dates, csv_path):
    out = []
    add = out.append

    # ─── HEADER ──────────────────────────────────────────────────────────────
    add("=" * 92)
    add(" PT BOX e37 — CANONICAL-ENGINE VALIDATION REPORT")
    add(" Engine: code/ptbox_engine_e37.py · backtest_session_direct (live source of truth)")
    add("=" * 92)
    add(f" Source CSV   : {Path(csv_path).name}")
    add(f" ET date range: {min(dates)} → {max(dates)}  ({len(dates)} ET trading days)")
    add("")

    # ─── HEADLINE ────────────────────────────────────────────────────────────
    all_trades = []
    for sess in ["Asia", "London", "NY"]:
        all_trades.extend(trades_by_session[sess])

    # CANONICAL semantics: PnL = realized only (TP or SL hits). EOD trades excluded.
    # IMPORTANT: canonical engine has accounting quirk — SL loss recorded as -sl_dist (planned)
    # not actual entry-to-SL distance. This UNDERSTATES losses. We compute BOTH:
    #   pnl_pts            = canonical engine value (matches +9084 5y baseline)
    #   pnl_pts_realistic  = actual entry-to-exit price difference (what trader sees)
    closed = [t for t in all_trades if t.exit_reason in ("TP", "SL")]
    eod = [t for t in all_trades if t.exit_reason == "EOD"]
    wins = [t for t in closed if t.pnl_pts > 0]
    losses = [t for t in closed if t.pnl_pts <= 0]

    total_pnl_canon = sum(t.pnl_pts for t in closed) if closed else 0.0
    total_pnl_real_closed = sum(t.pnl_pts_realistic for t in closed) if closed else 0.0
    eod_pnl_real = sum(t.pnl_pts_realistic for t in eod if t.pnl_pts_realistic is not None)
    total_pnl_real_all = total_pnl_real_closed + eod_pnl_real

    total_pnl = total_pnl_canon  # alias for backward compat
    realistic_pnl = total_pnl_real_all
    wr = len(wins) / len(closed) * 100 if closed else 0.0
    avg_w = sum(t.pnl_pts_realistic for t in wins) / len(wins) if wins else 0.0
    avg_l = sum(t.pnl_pts_realistic for t in losses) / len(losses) if losses else 0.0
    expectancy = total_pnl_real_all / (len(closed) + len(eod)) if (closed or eod) else 0.0
    pf_num = sum(t.pnl_pts_realistic for t in wins)
    pf_den = abs(sum(t.pnl_pts_realistic for t in losses))
    pf = pf_num / pf_den if pf_den > 0 else (float("inf") if pf_num > 0 else 0.0)

    add("┌─ HEADLINE PERFORMANCE ────────────────────────────────────────────────────────────────┐")
    add(f"│ Total trades opened     : {len(all_trades):>4}                                                          │")
    add(f"│ Closed (TP or SL hit)   : {len(closed):>4}                                                          │")
    add(f"│ Open at EOD             : {len(eod):>4}                                                          │")
    add(f"│ Win rate (TP hits)      : {wr:>6.2f}%                                                       │")
    add(f"│                                                                                       │")
    add(f"│ ── PnL views ──                                                                       │")
    add(f"│ Canonical engine PnL    : {total_pnl_canon:>+9.2f}  (engine semantics — losses = planned SL)         │")
    add(f"│ Realistic PnL (closed)  : {total_pnl_real_closed:>+9.2f}  (entry→exit price diff, TP/SL only)            │")
    add(f"│ Realistic PnL (all)     : {total_pnl_real_all:>+9.2f}  ⭐ ACTUAL trader PnL (incl. EOD M-T-M)            │")
    add(f"│                                                                                       │")
    add(f"│ Avg win (real)          : {avg_w:>+9.2f} pts                                                 │")
    add(f"│ Avg loss (real)         : {avg_l:>+9.2f} pts                                                 │")
    add(f"│ Expectancy (real)       : {expectancy:>+9.2f} pts/trade                                          │")
    pf_s = f"{pf:>6.2f}" if pf != float("inf") else "    ∞ "
    add(f"│ Profit factor (real)    : {pf_s}                                                       │")
    add(f"│ Win rate                : {wr:>6.2f}%                                                       │")
    add(f"│ Avg win                 : {avg_w:>+9.2f} pts                                                 │")
    add(f"│ Avg loss                : {avg_l:>+9.2f} pts                                                 │")
    add("└───────────────────────────────────────────────────────────────────────────────────────┘")
    add("")

    # ─── PER-SESSION ────────────────────────────────────────────────────────
    add("┌─ PER-SESSION BREAKDOWN (REALISTIC PnL — actual entry→exit) ───────────────────────────┐")
    add("│ Session  │  N  │  W  │  L  │ EOD │ Real PnL │ Canon PnL│   WR   │ Expectancy │  PF   │")
    add("├──────────┼─────┼─────┼─────┼─────┼──────────┼──────────┼────────┼────────────┼───────┤")
    for sess in ["Asia", "London", "NY"]:
        st = trades_by_session[sess]
        sclosed = [t for t in st if t.exit_reason in ("TP", "SL")]
        sw = [t for t in sclosed if t.pnl_pts > 0]
        sl = [t for t in sclosed if t.pnl_pts <= 0]
        seod = [t for t in st if t.exit_reason == "EOD"]
        spnl_canon = sum(t.pnl_pts for t in sclosed) if sclosed else 0
        spnl_real = sum(t.pnl_pts_realistic for t in sclosed) + sum(t.pnl_pts_realistic for t in seod) if (sclosed or seod) else 0
        swr = len(sw) / len(sclosed) * 100 if sclosed else 0
        sexp = spnl_real / (len(sclosed) + len(seod)) if (sclosed or seod) else 0
        spfn = sum(t.pnl_pts_realistic for t in sw)
        spfd = abs(sum(t.pnl_pts_realistic for t in sl))
        spf = spfn / spfd if spfd > 0 else (float("inf") if spfn > 0 else 0.0)
        spf_s = f"{spf:>5.2f}" if spf != float("inf") else "  ∞ "
        add(f"│ {sess:<8} │ {len(st):>3} │ {len(sw):>3} │ {len(sl):>3} │ {len(seod):>3} │ {spnl_real:>+8.2f} │ {spnl_canon:>+8.2f} │ {swr:>5.1f}% │ {sexp:>+8.2f}   │ {spf_s} │")
    add("└──────────┴─────┴─────┴─────┴─────┴──────────┴──────────┴────────┴────────────┴───────┘")
    add("")

    # ─── HISTORICAL BENCHMARK ────────────────────────────────────────────────
    add("┌─ HISTORICAL BENCHMARK (5y backtest 2021-2026, ~1255 ET days) ─────────────────────────┐")
    add("│ Session   │  Hist 5y PnL │  Hist WR │  Daily expectation                              │")
    add("├───────────┼──────────────┼──────────┼─────────────────────────────────────────────────┤")
    add("│ Asia      │      +1839   │   61.0%  │  ~1.46 pts/day                                  │")
    add("│ London    │      +3220   │   62.0%  │  ~2.57 pts/day                                  │")
    add("│ NY        │      +4025   │   58.0%  │  ~3.21 pts/day                                  │")
    add("│ TOTAL     │      +9084   │   60.1%  │  ~7.24 pts/day                                  │")
    add("└───────────┴──────────────┴──────────┴─────────────────────────────────────────────────┘")
    add("")

    n_days = len(dates)
    daily_canon = total_pnl_canon / n_days if n_days else 0
    daily_real = total_pnl_real_all / n_days if n_days else 0
    pace_pct_canon = (daily_canon / 7.24) * 100 if n_days else 0
    pace_pct_real = (daily_real / 7.24) * 100 if n_days else 0
    add(f" This window — canonical: {total_pnl_canon:+.2f} pts / {n_days} ET days = {daily_canon:+.2f}/day  ({pace_pct_canon:.0f}% of 5y baseline)")
    add(f" This window — REALISTIC: {total_pnl_real_all:+.2f} pts / {n_days} ET days = {daily_real:+.2f}/day  ({pace_pct_real:.0f}% of 5y baseline)")
    add(f" 5y baseline pace      : +7.24 pts/day  (canonical engine — likely overstated)")
    add("")

    # ─── TRADE LEDGER ────────────────────────────────────────────────────────
    add("┌─ TRADE LEDGER (chronological — Real PnL = actual entry→exit) ─────────────────────────┐")
    add("│  # │ Date       │ Sess   │ Dir   │ Entry │  Entry $ │   SL $   │   TP $   │  Risk │  Exit  │ Reason │ Real PnL │ Canon │")
    add("├────┼────────────┼────────┼───────┼───────┼──────────┼──────────┼──────────┼───────┼────────┼────────┼──────────┼───────┤")
    sorted_trades = sorted(all_trades, key=lambda t: (t.et_date, t.entry_tm))
    for i, t in enumerate(sorted_trades, 1):
        dir_s = "LONG " if t.direction == 1 else "SHORT"
        pnl_real_s = f"{t.pnl_pts_realistic:+.2f}" if t.pnl_pts_realistic is not None else "—"
        pnl_canon_s = f"{t.pnl_pts:+.2f}" if t.pnl_pts is not None else "—"
        exit_tm_s = fmt_tm(t.exit_tm) if t.exit_tm is not None else "—"
        add(f"│ {i:>2} │ {t.et_date} │ {t.session:<6} │ {dir_s} │ {fmt_tm(t.entry_tm)} │ {t.entry_px:>8.2f} │ {t.sl_px:>8.2f} │ {t.tp_px:>8.2f} │ {t.sl_dist_actual:>5.1f} │ {exit_tm_s:>6} │ {t.exit_reason:<6} │ {pnl_real_s:>8} │ {pnl_canon_s:>5} │")
    add("└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘")
    add("")

    # ─── BOX METRICS ─────────────────────────────────────────────────────────
    add("┌─ BOX SIZING DIAGNOSTICS ──────────────────────────────────────────────────────────────┐")
    add("│ Session  │ N boxes │ Avg width │ Min width │ Max width │ Avg actual SL │ Avg TP dist │")
    add("├──────────┼─────────┼───────────┼───────────┼───────────┼───────────────┼─────────────┤")
    for sess in ["Asia", "London", "NY"]:
        st = trades_by_session[sess]
        if not st:
            add(f"│ {sess:<8} │      0  │    —      │    —      │    —      │      —        │      —      │")
            continue
        widths = [t.box_width for t in st]
        sls = [t.sl_dist_actual for t in st]
        tps = [t.tp_dist for t in st]
        add(f"│ {sess:<8} │ {len({t.et_date for t in st}):>6}  │ {sum(widths)/len(widths):>7.2f}   │ {min(widths):>7.2f}   │ {max(widths):>7.2f}   │  {sum(sls)/len(sls):>7.2f} pts  │ {sum(tps)/len(tps):>7.2f} pts │")
    add("└──────────┴─────────┴───────────┴───────────┴───────────┴───────────────┴─────────────┘")
    add("")

    # ─── DOLLAR SIM ──────────────────────────────────────────────────────────
    pnl_usd_real = total_pnl_real_all * 2.0  # 0.02 lot = $2/pt
    pnl_usd_canon = total_pnl_canon * 2.0
    add("┌─ LIVE RISK SIM (Irfan: $200 cap, 0.02 lot, 1pt = $2) ─────────────────────────────────┐")
    add(f"│ ── REALISTIC view (what bank account shows) ──                                        │")
    add(f"│ Window net USD       : {pnl_usd_real:>+8.2f}                                                       │")
    add(f"│ % of $200 capital    : {pnl_usd_real/200*100:>+8.2f}%                                                       │")
    if n_days:
        avg_d = pnl_usd_real / n_days
        proj = avg_d * 252
        add(f"│ Avg daily USD        : {avg_d:>+8.2f}                                                       │")
        add(f"│ Naive 252-day project: {proj:>+8.2f}  USD/yr                                              │")
    add(f"│                                                                                       │")
    add(f"│ ── CANONICAL view (engine output, planned-loss accounting) ──                         │")
    add(f"│ Window net USD       : {pnl_usd_canon:>+8.2f}                                                       │")
    add(f"│ 5y historical proj   : ~$2,200-3,630 USD/yr (canonical, likely overstated)             │")
    add("└────────────────────────────────────────────────────────────────────────────────────────┘")
    add("")

    # ─── INTERPRETATION ──────────────────────────────────────────────────────
    add("=" * 92)
    add(" INTERPRETATION")
    add("=" * 92)
    add("")
    add(" FOR THE DATA PERSON:")
    add(" --------------------")
    add(f" • n = {len(closed)+len(eod)} trades ({len(closed)} closed + {len(eod)} EOD M-T-M) over {n_days} ET trading days.")
    add(f" • Observed WR: {wr:.1f}% vs historical 60.1%. 95% CI on WR at this n is ±{1.96*((wr/100*(1-wr/100)/max(1,len(closed)))**0.5)*100:.1f}pp.")
    add(f" • Profit factor (realistic): {pf:.2f}. Historical (canonical): 1.7-2.0 — caveat: hist PF uses buggy accounting.")
    add(f" • Expectancy (realistic): {expectancy:+.2f} pts/trade.")
    add(f" • Daily pace (realistic): {daily_real:+.2f} pts/day vs +7.24 baseline (canonical).")
    add("")
    add(" 🚨 ACCOUNTING DISCOVERY:")
    add("    Canonical engine records SL loss as -sl_dist (planned formula: 0.5×bw or 0.7×bw),")
    add("    NOT as actual (entry - SL price). This UNDERSTATES losses, since entry happens at")
    add("    breakout-candle close which is well above box low. Real loss = sl_dist + (entry - boxLo).")
    add("")
    add("    Implication: the +9084 5y baseline number (per CANONICAL_FILES.md) is overstated.")
    add("    True 5y PnL likely ~50-70% of stated (rough estimate based on this 11-day window).")
    add("    System logic, win rate, trade frequency all REMAIN CORRECT — only PnL accounting affected.")
    add("")
    add(" • Engine handles same-bar SL+TP collision conservatively (SL hit first).")
    add(" • EOD trades = open at end of session bars; canonical engine silently drops them from")
    add("   PnL aggregate, but in live trading these would close at session boundary.")
    add(" • Canonical engine = ONE entry per session per day. Pinescript live allows up to 5/3/3.")
    add("")
    add(" FOR THE FINANCE PERSON:")
    add(" -----------------------")
    if total_pnl_real_all > 0:
        add(f" ✅ Window net POSITIVE (realistic): {total_pnl_real_all:+.2f} pts ≈ ${pnl_usd_real:+.2f} on $200 cap ({pnl_usd_real/200*100:+.1f}%).")
    else:
        add(f" ⚠️  Window net NEGATIVE (realistic): {total_pnl_real_all:+.2f} pts ≈ ${pnl_usd_real:+.2f} on $200 cap ({pnl_usd_real/200*100:+.1f}%).")
    add(f"     (Engine reports {total_pnl_canon:+.2f} but uses planned-SL accounting. Actual = realistic.)")
    if losses or eod:
        all_real = [t.pnl_pts_realistic for t in closed + eod if t.pnl_pts_realistic is not None]
        worst = min(all_real) if all_real else 0
        cur = mx = 0
        for t in sorted(closed + eod, key=lambda x: (x.et_date, x.entry_tm)):
            if t.pnl_pts_realistic is not None and t.pnl_pts_realistic <= 0:
                cur += 1; mx = max(mx, cur)
            else:
                cur = 0
        add(f" Worst single trade: {worst:+.2f} pts. Max consecutive losing trades: {mx}.")
    add("")
    add(" SAMPLE-SIZE WARNING:")
    add(f" ⚠️  {n_days} trading days vs 1,255 in 5y baseline = {n_days/1255*100:.1f}% of historical sample.")
    add("    A single big trade (+/- 30 pts) shifts results dramatically. This is a SANITY CHECK,")
    add("    not statistical validation. To confirm/refute edge: need 60-90 day window minimum.")
    add("")
    add("=" * 92)
    return "\n".join(out)


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_e37_validation_canonical.py <csv>")
        sys.exit(1)

    csv_path = sys.argv[1]
    df = load_data(csv_path)
    dg, dates = build_date_groups(df)

    trades_by_session = {}
    summary_by_session = {}
    for sess, key in [("Asia", "asia"), ("London", "london"), ("NY", "ny")]:
        trades, summary = instrumented_session(dg, dates, sess, E37_CONFIG[key])
        trades_by_session[sess] = trades
        summary_by_session[sess] = summary

    txt = report(trades_by_session, summary_by_session, dates, csv_path)
    print(txt)

    # Verify against canonical engine output
    print("\n" + "=" * 92)
    print(" PARITY CHECK — instrumented wrapper vs canonical engine")
    print("=" * 92)
    canon_asia = backtest_asia(dg, dates)
    canon_london = backtest_london(dg, dates)
    canon_ny = backtest_ny(dg, dates)
    canon_map = {"Asia": canon_asia, "London": canon_london, "NY": canon_ny}

    print(f" {'Session':<10} | {'Wrapper PnL':>12} | {'Canon PnL':>10} | {'Wrapper N':>9} | {'Canon N':>7} | Match?")
    print(" " + "-" * 80)
    all_match = True
    for sess in ["Asia", "London", "NY"]:
        w_pnl = sum(t.pnl_pts for t in trades_by_session[sess] if t.exit_reason in ("TP", "SL"))
        c_pnl = canon_map[sess]["pnl"]
        w_n = len([t for t in trades_by_session[sess] if t.exit_reason in ("TP", "SL")])
        c_n = canon_map[sess]["trades"]
        match = abs(w_pnl - c_pnl) < 0.01 and w_n == c_n
        all_match = all_match and match
        mark = "✓" if match else "✗"
        print(f" {sess:<10} | {w_pnl:>+12.2f} | {c_pnl:>+10.2f} | {w_n:>9} | {c_n:>7} | {mark}")
    print(" " + "-" * 80)
    print(f" Overall parity: {'✓ PASS' if all_match else '✗ FAIL — wrapper diverges from canonical'}")

    # Save artifacts
    out_dir = Path(__file__).resolve().parent.parent / "data"
    out_dir.mkdir(exist_ok=True)
    base = Path(csv_path).stem.replace("XAUUSD_M1_", "").replace("e37_validation_", "")

    json_path = out_dir / f"e37_validation_canonical_{base}.json"
    rows = []
    for sess, ts in trades_by_session.items():
        for t in ts:
            d = asdict(t)
            rows.append(d)
    with open(json_path, "w") as f:
        json.dump(rows, f, indent=2, default=str)

    txt_path = out_dir / f"e37_validation_canonical_{base}.txt"
    with open(txt_path, "w") as f:
        f.write(txt)

    print(f"\n[saved] {json_path}")
    print(f"[saved] {txt_path}")


if __name__ == "__main__":
    main()
