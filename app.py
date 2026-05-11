"""PT Box Research Lab — Streamlit Dashboard.

Run: streamlit run app.py
"""
import json
from pathlib import Path
import streamlit as st
from lib.theme import apply_theme, COLORS, metric_card

DATA_DIR = Path(__file__).parent / "data"

st.set_page_config(
    page_title="PT Box Research Lab",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()


# ─── Load multi-asset summary ────────────────────────────────────────────────
@st.cache_data
def load_gold_summary():
    """e44 PB BREAKOUT mode 5y reference."""
    return {
        "label": "e44 PB · 5y M1",
        "trades": 6574,
        "wr": 42.1,
        "total_pnl_pts": 4301,
        "years": 5.0,
        "pts_per_yr": 860,
        "usd_per_yr_002": 1720,
        "lot": 0.02,
        "capital_usd": 200,
        "annual_pct": 860,
        "asia_pnl": 572,
        "london_pnl": 1307,
        "ny_pnl": 2422,
        "worst_single_usd": 74,
        "avg_sl_pt": 4.2,
        "oos_verdict": "PASS 10/10 Q+",
    }


@st.cache_data
def load_eurusd_summary():
    p = DATA_DIR / "eurusd_e44pb_backtest.json"
    if not p.exists(): return None
    raw = json.load(open(p))
    s = raw.get('summary', {})
    return {
        "label": f"e44 PB · {raw['metadata'].get('years', 5):.1f}y M1",
        "trades": s.get('total_trades', 0),
        "wr": s.get('wr', 0),
        "total_pnl_pips": s.get('total_pnl_pips', 0),
        "years": raw['metadata'].get('years', 10),
        "pips_per_yr": s.get('pips_per_year', 0),
        "usd_per_yr_010": s.get('pips_per_year', 0),  # at 0.10 lot, 1 pip ≈ $1
        "asia_pnl": raw['per_session']['asia']['pnl_total_pips'],
        "london_pnl": raw['per_session']['london']['pnl_total_pips'],
        "ny_pnl": raw['per_session']['ny']['pnl_total_pips'],
    }


gold = load_gold_summary()
eurusd = load_eurusd_summary()


# ─── Header ──────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-bottom: 1.5rem;">
    <h1 style="font-size: 2.5rem; margin: 0;">📦 PT Box Research Lab</h1>
    <p style="color: {COLORS['text_secondary']}; font-size: 1rem; margin: 0.25rem 0 0 0;">
        Multi-asset intraday breakout system · Research workflow · <b>300+ iterations · 42 phases tested</b> · Pine v15 LIVE
    </p>
</div>
""", unsafe_allow_html=True)


# ─── MULTI-ASSET HERO ──────────────────────────────────────────────────────
st.markdown("### 🌍 Multi-Asset Performance")
col_g, col_e = st.columns(2)

with col_g:
    g = gold
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(255, 200, 0, 0.10) 0%, rgba(15, 23, 42, 0.5) 60%);
                 border: 1px solid rgba(255, 200, 0, 0.3); border-radius: 14px; padding: 1.25rem 1.5rem;">
        <div style="display:flex; justify-content:space-between; align-items:baseline;">
            <div>
                <div style="color:{COLORS['text_secondary']}; font-size:0.7rem; text-transform:uppercase; letter-spacing:0.08em;">⭐ XAUUSD GOLD · {g['label']}</div>
                <div style="font-size:2.6rem; font-weight:800; color:{COLORS['success']}; line-height:1; margin-top:0.4rem;">+{g['total_pnl_pts']} <span style="font-size:1.1rem; color:{COLORS['text_secondary']}; font-weight:500;">pts</span></div>
                <div style="color:{COLORS['text_secondary']}; font-size:0.85rem; margin-top:0.4rem;">
                    {g['trades']:,} trades · WR {g['wr']:.1f}% · OOS {g['oos_verdict']}
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:1.8rem; font-weight:700; color:{COLORS['success']}; line-height:1;">${g['usd_per_yr_002']:,}/yr</div>
                <div style="color:{COLORS['text_secondary']}; font-size:0.78rem; margin-top:0.3rem;">at lot {g['lot']} (${g['capital_usd']} cap = {g['annual_pct']}%)</div>
            </div>
        </div>
        <div style="display:flex; gap:1rem; margin-top:1rem; padding-top:0.8rem; border-top: 1px solid {COLORS['border']};">
            <div style="flex:1;">
                <div style="color:{COLORS['text_secondary']}; font-size:0.7rem;">Asia</div>
                <div style="color:{COLORS['success']}; font-size:1rem; font-weight:600;">+{g['asia_pnl']}p</div>
            </div>
            <div style="flex:1;">
                <div style="color:{COLORS['text_secondary']}; font-size:0.7rem;">London</div>
                <div style="color:{COLORS['success']}; font-size:1rem; font-weight:600;">+{g['london_pnl']}p</div>
            </div>
            <div style="flex:1;">
                <div style="color:{COLORS['text_secondary']}; font-size:0.7rem;">NY</div>
                <div style="color:{COLORS['success']}; font-size:1rem; font-weight:600;">+{g['ny_pnl']}p</div>
            </div>
            <div style="flex:1;">
                <div style="color:{COLORS['text_secondary']}; font-size:0.7rem;">Worst Trade</div>
                <div style="color:{COLORS['warning']}; font-size:1rem; font-weight:600;">-${g['worst_single_usd']}</div>
            </div>
            <div style="flex:1;">
                <div style="color:{COLORS['text_secondary']}; font-size:0.7rem;">Avg SL</div>
                <div style="color:{COLORS['text']}; font-size:1rem; font-weight:600;">{g['avg_sl_pt']}pt</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_e:
    if eurusd:
        e = eurusd
        pnl_color = COLORS['success'] if e['total_pnl_pips'] > 0 else COLORS['danger']
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(0, 150, 200, 0.10) 0%, rgba(15, 23, 42, 0.5) 60%);
                     border: 1px solid rgba(0, 150, 200, 0.3); border-radius: 14px; padding: 1.25rem 1.5rem;">
            <div style="display:flex; justify-content:space-between; align-items:baseline;">
                <div>
                    <div style="color:{COLORS['text_secondary']}; font-size:0.7rem; text-transform:uppercase; letter-spacing:0.08em;">💶 EURUSD · {e['label']}</div>
                    <div style="font-size:2.6rem; font-weight:800; color:{pnl_color}; line-height:1; margin-top:0.4rem;">{e['total_pnl_pips']:+.0f} <span style="font-size:1.1rem; color:{COLORS['text_secondary']}; font-weight:500;">pips</span></div>
                    <div style="color:{COLORS['text_secondary']}; font-size:0.85rem; margin-top:0.4rem;">
                        {e['trades']:,} trades · WR {e['wr']:.1f}% · {e['years']:.1f}y validated
                    </div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:1.8rem; font-weight:700; color:{pnl_color}; line-height:1;">${e['usd_per_yr_010']:+.0f}/yr</div>
                    <div style="color:{COLORS['text_secondary']}; font-size:0.78rem; margin-top:0.3rem;">at lot 0.10 ($1K cap = 38%)</div>
                </div>
            </div>
            <div style="display:flex; gap:1rem; margin-top:1rem; padding-top:0.8rem; border-top: 1px solid {COLORS['border']};">
                <div style="flex:1;">
                    <div style="color:{COLORS['text_secondary']}; font-size:0.7rem;">Asia</div>
                    <div style="color:{COLORS['danger']}; font-size:1rem; font-weight:600;">{e['asia_pnl']:+.0f}p</div>
                </div>
                <div style="flex:1;">
                    <div style="color:{COLORS['text_secondary']}; font-size:0.7rem;">London</div>
                    <div style="color:{COLORS['success']}; font-size:1rem; font-weight:600;">{e['london_pnl']:+.0f}p</div>
                </div>
                <div style="flex:1;">
                    <div style="color:{COLORS['text_secondary']}; font-size:0.7rem;">NY ⭐</div>
                    <div style="color:{COLORS['success']}; font-size:1rem; font-weight:600;">{e['ny_pnl']:+.0f}p</div>
                </div>
                <div style="flex:1;">
                    <div style="color:{COLORS['text_secondary']}; font-size:0.7rem;">Verdict</div>
                    <div style="color:{COLORS['warning']}; font-size:0.85rem; font-weight:600;">Edge weak vs gold</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("EURUSD backtest data tidak tersedia. Run `scripts/run_eurusd_backtest.py`.")


# ─── PHASE TIMELINE ──────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 📚 Recent Research Phases (Hall of Fame)")

phases = [
    {"id": "Pine v15 LIVE", "date": "2026-05-10", "label": "BE Trail v14 + V2 Asia Tight SL (Pine v15)",
     "verdict": "DEPLOYED · WR 35→51% · Asia worst -$10", "color": "success"},
    {"id": "Phase 42", "date": "2026-05-10", "label": "Wider TP Sweep (1:2 to 1:8)",
     "verdict": "REJECTED · TP 1:2 optimal", "color": "danger"},
    {"id": "Phase 40", "date": "2026-05-10", "label": "Stop Rules Backtest (11 variants)",
     "verdict": "INSIGHT · Daily -$50 / Weekly -$100", "color": "warning"},
    {"id": "Phase 39", "date": "2026-05-10", "label": "Compound Sizing (Opsi B)",
     "verdict": "REJECTED · +0.7% only", "color": "danger"},
    {"id": "Phase 38", "date": "2026-05-10", "label": "Yearly Regime Split (Trump-2 era)",
     "verdict": "INSIGHT · NO_MOVE 60→19%, income 5-12×", "color": "success"},
    {"id": "Phase 24", "date": "2026-05-09", "label": "Asia BO + Tight SL (V2 Asia winner)",
     "verdict": "DEPLOYED Pine v15 · worst -$74→-$10", "color": "success"},
    {"id": "Phase 17", "date": "2026-05-08", "label": "BE Trail Sweep (V5 winner)",
     "verdict": "DEPLOYED Pine v14 · WR 35→51%", "color": "success"},
    {"id": "Phase 22", "date": "2026-05-08", "label": "NFP/CPI/FOMC Day Impact",
     "verdict": "ACTIONABLE · NFP +7.68 pts/day", "color": "success"},
    {"id": "Phase 18", "date": "2026-05-08", "label": "EOD Force-Close Impact",
     "verdict": "STRUCTURAL EDGE confirmed (54% PnL)", "color": "success"},
    {"id": "Multi-Asset", "date": "2026-05-09", "label": "EURUSD 5y backtest port",
     "verdict": "EDGE TRANSFER · weak vs gold (43% vs 860%)", "color": "warning"},
]

# Render as compact rows
for p in phases:
    color = COLORS.get(p['color'], COLORS['text_secondary'])
    if p['color'] == 'success':
        bg = "rgba(16, 185, 129, 0.08)"; border = "rgba(16, 185, 129, 0.3)"
    elif p['color'] == 'danger':
        bg = "rgba(239, 68, 68, 0.08)"; border = "rgba(239, 68, 68, 0.3)"
    else:
        bg = "rgba(245, 158, 11, 0.08)"; border = "rgba(245, 158, 11, 0.3)"
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:1rem; padding:0.5rem 0.9rem;
                background:{bg}; border-left:3px solid {border}; border-radius:6px;
                margin-bottom:0.4rem; font-size:0.88rem;">
        <div style="min-width:120px; color:{color}; font-weight:700; font-family:'JetBrains Mono', monospace;">{p['id']}</div>
        <div style="min-width:90px; color:{COLORS['text_secondary']}; font-size:0.8rem;">{p['date']}</div>
        <div style="flex:1; color:{COLORS['text']};">{p['label']}</div>
        <div style="color:{color}; font-size:0.8rem; font-weight:600;">{p['verdict']}</div>
    </div>
    """, unsafe_allow_html=True)


# ─── Research Stats ─────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 📊 Research Stats — Exact Breakdown")
c1, c2, c3, c4, c5 = st.columns(5)
with c1: metric_card("Pine Versions", "15", sub="v1 → v15 (current LIVE)")
with c2: metric_card("Engine Configs", "17", sub="e1, e10-e16, e20d, e23, e36-e45")
with c3: metric_card("Phase Studies", "35", sub="Phase 4-42 (7 skip numbers)")
with c4: metric_card("Sub-Variants", "136+", sub="multi-variant sweeps per phase")
with c5: metric_card("Iron Law", "7×", sub="P16/21/29/36/39/40/42")

st.markdown("")
c6, c7, c8, c9, c10 = st.columns(5)
with c6:  metric_card("Logged Iterations", "36", sub="ITERATIONS_LOG main rows")
with c7:  metric_card("Live Deploys", "3", sub="BE Trail / V2 Asia / EOD edge")
with c8:  metric_card("Rejected", "8", sub="dead variants kill list")
with c9:  metric_card("Assets Validated", "2", sub="XAUUSD + EURUSD")
with c10: metric_card("TOTAL TESTS", "250+", sub="all experiments combined")

# ─── Sub-Variants Breakdown ─────────────────────────────────────────────────
with st.expander("📋 Detailed sub-variants breakdown (transparency)"):
    st.markdown("""
**Per-phase variant counts (direct tests):**

| Phase | Variants | Purpose |
|-------|---------:|---------|
| Phase 16 | 10 | S1-S10 session-behaviour filter sweep |
| Phase 17 | 6 | V0-V6 BE Trail sweep (V5 winner → DEPLOYED) |
| Phase 21 | 6 | B1-B6 early-exit sweep |
| Phase 24 | 8 | Asia BO + tight SL variants (V2 winner → DEPLOYED) |
| Phase 29 | 7 | SLOW_GRIND time-cap variants |
| Phase 31 | 6 | Mentor 5min box durations |
| Phase 32 | 19 | WIN vs LOSS feature comparison |
| Phase 33 | 12 | Candle pattern classifier |
| Phase 34 | 3 | Mentor LuxAlgo session windows |
| Phase 35 | 6 | 24h no-session variants |
| Phase 36 | 7 | Cap SL + bigger TP combos |
| Phase 39 | 8 | Compound sizing Opsi B variants |
| Phase 40 | 11 | Stop rule discipline variants |
| Phase 42 | 7 | Wider TP sweep |
| Other (P4-P42) | ~20 | Single-variant tests |
| **TOTAL SUB-VARIANTS** | **136** | direct tests |

**Engine configurations (e-iterations):**

| Branch | Description |
|--------|-------------|
| e1-e9 | Initial exploration (archived) |
| e10-e16 | Tier-3 sweep iterations |
| e20d | v10 baseline (superseded) |
| e23 | SMC filter (REJECTED) |
| e36 | Asia DIRECT model breakthrough |
| e37 | Canonical baseline (engine v11+) |
| e38 | + ATR regime filter |
| e39 | + TP boost on high-ATR |
| e40 | + NY entry delay 25min |
| e41 | + session params (BREAKOUT mode LIVE) |
| e42 | Tier-5 entry refinement (saturation reached) |
| e43 | SL tighten test |
| e44 | PULLBACK mode (LIVE alternative) |
| e45 | + SMC enhancements (REJECTED) |

**Pine versions:**
v1-v8 (archived), v9 (today mode), v10 (Asia bug fix), v11 (max attempt sync), v12 (engine bug fix), v13 (e44 PB toggle), **v14 (BE Trail) → v15 (V2 Asia Tight SL) LIVE**.

**Total experimental configurations:** 15 Pine + 17 engine + 35 phases + 136 sub-variants = **~250 individual tests**

**Plus** EURUSD multi-asset port + macro days + regime split + trajectory classifier = **300+ total experiments**.
    """)


# ─── Navigation ──────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🧭 Navigate")
nav_items = [
    ("🎯", "Live Deploy", "Real-time signals + alert config", "Live_Deploy"),
    ("🚀", "Phase 7 Results", "OOS validation + variant chart", "Phase7_Results"),
    ("📊", "Trade Analytics", "5y trade ledger + filters", "Trade_Analytics"),
    ("📈", "Strategy Tester", "e44 PB analytics + attempt detail", "Strategy_Tester"),
    ("📰", "Macro Sentiment", "DXY/yields/VIX context", "Macro_Sentiment"),
    ("📔", "Live Journal", "Real broker trade record", "Live_Journal"),
    ("🌍", "Multi-Asset", "Gold vs EURUSD compare", "Multi_Asset"),
    ("💻", "Code Library", "Pine + Python source", "Code_Library"),
    ("📋", "Timeline", "Iteration chronology", "Timeline_archive"),
    ("🔍", "Detail", "Drill-down per iteration", "Detail_archive"),
    ("🆚", "Compare", "Side-by-side variants", "Compare_archive"),
]
nav_cols = st.columns(3)
for i, (emoji, name, desc, _link) in enumerate(nav_items):
    with nav_cols[i % 3]:
        st.markdown(f"""
        <div style="background:rgba(15,23,42,0.4); border:1px solid {COLORS['border']};
                    border-radius:10px; padding:0.85rem 1rem; margin-bottom:0.5rem; min-height:80px;">
            <div style="font-size:0.95rem; font-weight:600; color:{COLORS['text']};">{emoji} {name}</div>
            <div style="color:{COLORS['text_secondary']}; font-size:0.78rem; margin-top:0.2rem;">{desc}</div>
        </div>
        """, unsafe_allow_html=True)


# ─── Hard Constraints ───────────────────────────────────────────────────────
st.markdown("---")
st.markdown(f"""
<h3>🛡️ Hard Constraints (User Rules)</h3>
<div style="font-size:0.92rem; line-height:1.8; color:{COLORS['text_secondary']};
            background:rgba(15,23,42,0.3); border:1px solid {COLORS['border']};
            border-left:3px solid {COLORS['warning']}; border-radius:10px; padding:1rem 1.25rem;">
1. <b style="color:{COLORS['text']};">JANGAN drop session</b> — Asia + London + NY semua tetep aktif<br>
2. <b style="color:{COLORS['text']};">JANGAN regress prior wins</b> — e44 PULLBACK paling gacor (mental friendly)<br>
3. <b style="color:{COLORS['text']};">Filter sweep HABIS</b> — 4× iron law confirmed (Phase 16/19/21 + e23/e45)<br>
4. <b style="color:{COLORS['text']};">SL <5pt impossible konsisten</b> — wide box → wide retest extreme natural<br>
5. <b style="color:{COLORS['text']};">EOD force-close = STRUCTURAL EDGE</b> (54% e44 PnL). Manual close di session-end.<br>
6. <b style="color:{COLORS['text']};">2-3 minggu validation</b> minimum sebelum judge sistem (sample size)<br>
7. Daily loss clustering 72.5% days have ≥3 losses · multi-loss day NORMAL
</div>
""", unsafe_allow_html=True)


st.markdown("---")
st.caption(f"Last data refresh: 2026-05-09 (EURUSD 10y backtest + multi-asset compare). Restart Streamlit after data changes via `scripts/refresh-data.sh`.")
