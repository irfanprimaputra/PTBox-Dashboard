"""Phase 7 Results — Final consolidated dashboard.

Visualizes complete Phase 7 journey:
- Variant evolution (e001 → e16b)
- OOS robustness validation
- Per-session breakdown current best
- Regime stability monitor
- All variants comparison table
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from lib.theme import apply_theme, COLORS, plotly_layout, metric_card

st.set_page_config(page_title="Phase 7 Results · PT Box", page_icon="🚀", layout="wide")
apply_theme()

DATA_DIR = Path(__file__).parent.parent / "data"


@st.cache_data(ttl=3600)
def load_phase7_data():
    data = {}
    if (DATA_DIR / "phase7_summary.json").exists():
        with open(DATA_DIR / "phase7_summary.json") as f: data["e14_full"] = json.load(f)
    if (DATA_DIR / "phase7_variant_results.json").exists():
        with open(DATA_DIR / "phase7_variant_results.json") as f: data["e14_variants"] = json.load(f)
    if (DATA_DIR / "phase7_ny_variants_results.json").exists():
        with open(DATA_DIR / "phase7_ny_variants_results.json") as f: data["e15"] = json.load(f)
    if (DATA_DIR / "phase7_e16_results.json").exists():
        with open(DATA_DIR / "phase7_e16_results.json") as f: data["e16"] = json.load(f)
    if (DATA_DIR / "phase7_e17_e18_results.json").exists():
        with open(DATA_DIR / "phase7_e17_e18_results.json") as f: data["e17_e18"] = json.load(f)
    # Prefer e37 OOS validation (2026-05-04, retention 316%) over old e16b OOS
    if (DATA_DIR / "phase7_e37_oos_validation.json").exists():
        with open(DATA_DIR / "phase7_e37_oos_validation.json") as f:
            e37_oos = json.load(f)
        data["oos"] = {
            "total_oos": e37_oos["oos_pnl"],
            "retention_pct": e37_oos["retention_pct"],
            "verdict": e37_oos["verdict"],
            "yearly": e37_oos.get("oos_per_yr", 2795),
        }
    elif (DATA_DIR / "phase7_oos_robustness.json").exists():
        with open(DATA_DIR / "phase7_oos_robustness.json") as f: data["oos"] = json.load(f)
    return data


@st.cache_data(ttl=3600)
def load_regime_data():
    if (DATA_DIR / "regime_stability_report.csv").exists():
        return pd.read_csv(DATA_DIR / "regime_stability_report.csv")
    return None


# ───────────────────────────────────────────────────────────
# 🎯 HEADER
# ───────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-bottom: 1.5rem;">
    <h1 style="font-size: 2rem; margin: 0;">🚀 Phase 7 — Final Results</h1>
    <p style="color: {COLORS['text_secondary']}; margin: 0.25rem 0 0 0;">
        Engine v11+ · 4-layer stack (e38 ATR + e39 TP + e40 NY delay + e41 session params) · <b>42 phases · 300+ iterations</b> · Modes: <b style="color: {COLORS['success']};">e41 BREAKOUT +3983</b> + <b style="color: rgb(20, 184, 166);">e44 PULLBACK +4301</b> · <span style="color: rgb(34, 197, 94); font-weight: 600;">🛡️ Pine v15 LIVE: BE Trail + V2 Asia Tight SL</span> WR 35→51% · Asia worst -$74→-$10 · <span style="color: {COLORS['text_secondary']}; font-size: 0.85em;">Phase 40 stop rules + Phase 42 wider TP REJECTED. TP 1:2 confirmed optimal. 8 dead variants.</span>
    </p>
</div>
""", unsafe_allow_html=True)

data = load_phase7_data()
regime = load_regime_data()

# ───────────────────────────────────────────────────────────
# 🏆 HERO — Current Best Baseline
# ───────────────────────────────────────────────────────────
oos_total = data.get("oos", {}).get("total_oos", 6428) if "oos" in data else 6428

st.markdown(f"""
<div style="
    background: linear-gradient(135deg, rgba(31, 193, 107, 0.10) 0%, rgba(15, 23, 42, 0.5) 60%);
    border: 1px solid rgba(31, 193, 107, 0.3);
    border-radius: 16px;
    padding: 2rem 2.25rem;
    margin-bottom: 1.5rem;
">
    <div style="color: {COLORS['text_secondary']}; font-size: 0.78rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.5rem;">
        ⭐ LIVE Pine v15: e41 BREAKOUT + e44 PULLBACK + 🛡️ BE Trail + V2 Asia Tight SL (Asia worst -$10, 86% safer than -$74 baseline) · WR 51% · TP 1:2 RR optimal (Phase 42 confirmed)
    </div>
    <div style="display: flex; align-items: baseline; gap: 2.5rem; flex-wrap: wrap;">
        <div>
            <div style="font-size: 3.5rem; font-weight: 800; color: {COLORS['success']}; line-height: 1; letter-spacing: -0.03em;">
                +3983 <span style="font-size: 1.1rem; color: {COLORS['text_secondary']}; font-weight: 500;">pts</span>
            </div>
            <div style="margin-top: 0.4rem; color: {COLORS['text_secondary']}; font-size: 0.85rem;">
                e41 5y total (closed +4145 / EOD -162) · 1589 trades · WR 60.9%
            </div>
        </div>
        <div style="border-left: 1px solid {COLORS['border']}; padding-left: 1.75rem;">
            <div style="font-size: 3rem; font-weight: 800; color: {COLORS['success']}; line-height: 1;">
                +3228 <span style="font-size: 1rem; color: {COLORS['text_secondary']}; font-weight: 500;">pts OOS</span>
            </div>
            <div style="margin-top: 0.4rem; color: {COLORS['text_secondary']}; font-size: 0.85rem;">
                Test 2024-2026 (+1374/yr) — e41 4-layer stack
            </div>
        </div>
        <div style="border-left: 1px solid {COLORS['border']}; padding-left: 1.75rem;">
            <div style="font-size: 1.5rem; font-weight: 700; color: {COLORS['success']};">
                560%
            </div>
            <div style="margin-top: 0.2rem; color: {COLORS['text_secondary']}; font-size: 0.8rem;">
                OOS retention (test &gt; train · 9/10 Q+)<br>
                ⚠ regime-dependent (2024-26 gold bull)
            </div>
        </div>
        <div style="border-left: 1px solid {COLORS['border']}; padding-left: 1.75rem;">
            <div style="font-size: 1.5rem; font-weight: 700; color: {COLORS['text']};">
                ~$1467/yr
            </div>
            <div style="margin-top: 0.2rem; color: {COLORS['text_secondary']}; font-size: 0.8rem;">
                $200 cap, lot 0.02 ($2/pt) · realistic incl EOD<br>
                +127% over e37 base (was $647/yr)
            </div>
        </div>
    </div>
    <div style="margin-top: 1rem; padding-top: 0.85rem; border-top: 1px solid {COLORS['border']}; color: {COLORS['text_secondary']}; font-size: 0.82rem;">
        ⭐ <b style="color: {COLORS['success']};">2026-05-05 e41 ITERATION CHAIN (Pine v12.3):</b> 4 stacked layers on engine v11+ baseline.<br>
        ① <b>e38 ATR filter</b>: skip days where today's range &lt; 30th pctile of last 30d (Δ +856)<br>
        ② <b>e39 TP boost</b>: TP×1.30 when ATR rank ≥72nd pctile (Δ +510)<br>
        ③ <b>e40 NY delay</b>: 25min entry delay after box close (skip 8:30-8:55 macro noise) (Δ +196)<br>
        ④ <b>e41 session params</b>: Asia start 19:00 + London SL 0.9×bw + NY end 13 ET (Δ +666)<br>
        Per-session 5y: 🟢 Asia +1024 (263 tr, 68% WR) | 🔵 London +1238 (628, 58%) | 🟡 NY +1883 (698, 61%)
    </div>
</div>
""", unsafe_allow_html=True)

# ───────────────────────────────────────────────────────────
# 📊 Per-session breakdown (current best e16b)
# ───────────────────────────────────────────────────────────
st.markdown("<h2>📍 Per-Session Breakdown (e20d)</h2>", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
sessions_e20d = [
    ("🟢 Asia", "18:00/90m DIRECT + 1 attempt/day (corrected v12)", 855, 24, 61),
    ("🔵 London", "00:00/60m DIRECT + body20% + 1 attempt/day (corrected v12)", 1186, 468, 62),
    ("🟡 NY", "07:00/60m + ANY + body30% + TP=2.5R (corrected v12)", 1182, -117, 58),
]
for col, (label, desc, pnl, e013_ref, wr) in zip([c1, c2, c3], sessions_e20d):
    delta = pnl - e013_ref
    delta_color = COLORS["success"] if delta > 0 else COLORS["danger"]
    with col:
        st.markdown(f"""
        <div style="
            background: rgba(15, 23, 42, 0.4);
            border: 1px solid {COLORS['border']};
            border-radius: 12px;
            padding: 1.25rem 1.5rem;
            min-height: 200px;
        ">
            <div style="font-size: 1.4rem; font-weight: 600; color: {COLORS['text']};">{label}</div>
            <div style="margin-top: 0.4rem; color: {COLORS['text_secondary']}; font-size: 0.8rem; line-height: 1.4;">{desc}</div>
            <div style="font-size: 2.2rem; font-weight: 800; color: {COLORS['success'] if pnl > 0 else COLORS['danger']}; letter-spacing: -0.02em; margin-top: 0.6rem;">
                {pnl:+.0f} <span style="font-size: 0.85rem; color: {COLORS['text_secondary']}; font-weight: 500;">pts</span>
            </div>
            <div style="margin-top: 0.4rem; color: {delta_color}; font-size: 0.92rem; font-weight: 600;">
                Δ {delta:+.0f} vs e013 ({e013_ref:+d})
            </div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# ───────────────────────────────────────────────────────────
# 📈 Variant Evolution (all 16+ tested)
# ───────────────────────────────────────────────────────────
st.markdown("<h2>📈 Variant Evolution — Phase 7 Journey</h2>", unsafe_allow_html=True)

evolution = pd.DataFrame([
    {"variant": "e001 baseline", "label": "Phase 1 unfiltered", "pnl": -2498, "stage": "early"},
    {"variant": "e010", "label": "Phase 4 any_pattern", "pnl": -562, "stage": "early"},
    {"variant": "e012", "label": "Phase 5 #A2 Asia mean-rev", "pnl": 202, "stage": "early"},
    {"variant": "e013", "label": "Phase 5 #B0 NY no pattern", "pnl": 375, "stage": "early"},
    {"variant": "e14_full", "label": "P7: V4 filter all sess (overfit)", "pnl": -93, "stage": "phase7"},
    {"variant": "e14a", "label": "P7: Macro only", "pnl": 232, "stage": "phase7"},
    {"variant": "e14b", "label": "P7: Adaptive only", "pnl": 232, "stage": "phase7"},
    {"variant": "e14c", "label": "P7: Filter NY+Asia", "pnl": 504, "stage": "phase7"},
    {"variant": "e14d", "label": "P7: Adaptive Asia ONLY", "pnl": 549, "stage": "phase7"},
    {"variant": "e15a", "label": "P7: NY Silver Bullet timing", "pnl": 29, "stage": "phase7"},
    {"variant": "e15b", "label": "P7: NY skip Friday", "pnl": 252, "stage": "phase7"},
    {"variant": "e15c", "label": "P7: NY First Candle Range", "pnl": 554, "stage": "phase7"},
    {"variant": "e15d", "label": "P7: NY Silver Bullet + Friday", "pnl": 492, "stage": "phase7"},
    {"variant": "e16a", "label": "P7: NY direct breakout", "pnl": 692, "stage": "phase7"},
    {"variant": "e16b", "label": "P7: NY direct + pattern ⭐", "pnl": 945, "stage": "phase7"},
    {"variant": "e16c", "label": "P7: London direct (worse)", "pnl": 522, "stage": "phase7"},
    {"variant": "e16d", "label": "P7: e16b + Silver Bullet", "pnl": 804, "stage": "phase7"},
    {"variant": "e17a", "label": "P7: London pin_bar only", "pnl": 504, "stage": "phase7"},
    {"variant": "e17b", "label": "P7: London engulfing only", "pnl": 524, "stage": "phase7"},
    {"variant": "e17c", "label": "P7: London killzone restrict", "pnl": 569, "stage": "phase7"},
    {"variant": "e17d", "label": "P7: London direct + pattern", "pnl": 603, "stage": "phase7"},
    {"variant": "e18a", "label": "P7: Asia Tokyo restrict", "pnl": 735, "stage": "phase7"},
    {"variant": "e18b", "label": "P7: Asia min_box_width=3", "pnl": 895, "stage": "phase7"},
    {"variant": "e18c", "label": "P7: Asia min_box_width=5", "pnl": 850, "stage": "phase7"},
    {"variant": "e20d", "label": "P7: Asia LATE-window 21-23 ET ⭐ NEW BASELINE", "pnl": 976, "stage": "phase7"},
    {"variant": "e23a", "label": "P7: Asia DoW skip Thu (DISCONFIRMED)", "pnl": 856, "stage": "phase7"},
    {"variant": "e23b", "label": "P7: Asia RANGE NY_prev (DISCONFIRMED)", "pnl": 807, "stage": "phase7"},
    {"variant": "e27e", "label": "P7: NY strict + body50% (proj WF)", "pnl": 1133, "stage": "phase7"},
    {"variant": "e30",  "label": "P7: e27e + timing sweep (proj WF)", "pnl": 1376, "stage": "phase7"},
    {"variant": "e31",  "label": "P7: e30 + TP=2.5R grid optimum (5y fixed)", "pnl": 1836, "stage": "phase7"},
    {"variant": "e32",  "label": "P7: e31 + Wyckoff pre-session (5y fixed)", "pnl": 3100, "stage": "phase7"},
    {"variant": "e33",  "label": "P7: e32 + regrid (any+body30+TP2.5) (5y fixed)", "pnl": 3370, "stage": "phase7"},
    {"variant": "e35",  "label": "P7: e33 + London DIRECT 00:00/60m (5y fixed)", "pnl": 3600, "stage": "phase7"},
    {"variant": "e36",  "label": "P7: ALL DIRECT (Asia/London/NY) (5y fixed)", "pnl": 5734, "stage": "phase7"},
    {"variant": "e37",  "label": "P7: e36 + extended session windows ⭐ NEW (proj WF)", "pnl": 6360, "stage": "phase7"},
])

# Line chart progression
fig_evo = go.Figure()
colors_evo = [COLORS["danger"] if p < 0 else (COLORS["warning"] if p < 400 else COLORS["success"]) for p in evolution["pnl"]]
fig_evo.add_trace(go.Bar(
    x=evolution["variant"],
    y=evolution["pnl"],
    text=[f"{p:+.0f}" for p in evolution["pnl"]],
    textposition="auto",
    textfont=dict(size=9, color=COLORS["text"]),
    marker_color=colors_evo,
    customdata=evolution["label"],
    hovertemplate="<b>%{x}</b><br>%{customdata}<br>PnL: %{y:+.0f} pts<extra></extra>",
))
fig_evo.add_hline(y=0, line_color=COLORS["text_secondary"], line_dash="dash")
fig_evo.add_hline(y=6360, line_color=COLORS["success"], line_dash="solid", line_width=2,
                   annotation_text="e37 PROJECTED +6360 (extended sessions)",
                   annotation_font_color=COLORS["success"])
fig_evo.add_hline(y=5734, line_color=COLORS["text_secondary"], line_dash="dot",
                   annotation_text="e36 prior +5734",
                   annotation_font_color=COLORS["text_secondary"])
fig_evo.add_hline(y=976, line_color=COLORS["text_secondary"], line_dash="dot",
                   annotation_text="e20d prior +976",
                   annotation_font_color=COLORS["text_secondary"])
fig_evo.add_hline(y=375, line_color=COLORS["warning"], line_dash="dot",
                   annotation_text="e013 baseline +375",
                   annotation_font_color=COLORS["warning"])
fig_evo.update_layout(**plotly_layout(
    height=480,
    yaxis_title="PnL (pts)",
    title=dict(text="All 24 Variants Tested · Walk-forward 19Q", font=dict(color=COLORS["text"], size=14)),
    xaxis=dict(tickangle=-45, tickfont=dict(size=9)),
))
st.plotly_chart(fig_evo, use_container_width=True)

st.divider()

# ───────────────────────────────────────────────────────────
# 🎯 OOS vs Walk-forward
# ───────────────────────────────────────────────────────────
st.markdown("<h2>🎯 OOS Robustness Validation</h2>", unsafe_allow_html=True)
st.caption("Train e16b config on 2021-2023 ONLY → lock parameters → apply to 2024-2026 unseen. Tests if strategy works without per-quarter re-tuning.")

oos = data.get("oos", {})
locked = oos.get("locked_params", {})
oos_results = oos.get("oos_results", {})
wf_recent = oos.get("walkforward_recent_reference", {"Asia": 142, "London": 468, "NY": 187})

c1, c2 = st.columns(2)

with c1:
    st.markdown("<h3>Locked OOS Params (from 2021-2023 train)</h3>", unsafe_allow_html=True)
    if locked:
        rows = []
        for sess in ["Asia", "London", "NY"]:
            p = locked.get(sess, {})
            r = oos_results.get(sess, {})
            rows.append({
                "Session": sess,
                "Best timing": f"{int(p.get('bh', 0)):02d}:{int(p.get('bm', 0)):02d}",
                "Duration": f"{int(p.get('dur', 0))}min",
                "Train PnL": f"{p.get('train_pnl', 0):+.1f}",
                "Test PnL (OOS)": f"{r.get('test_pnl', 0):+.1f}",
                "Test WR": f"{r.get('test_wr', 0):.1f}%",
            })
        df_oos = pd.DataFrame(rows)
        st.dataframe(df_oos, hide_index=True, use_container_width=True)

with c2:
    st.markdown("<h3>OOS vs Walk-forward Comparison</h3>", unsafe_allow_html=True)
    cmp_data = []
    for sess in ["Asia", "London", "NY"]:
        oos_pnl = oos_results.get(sess, {}).get("test_pnl", 0)
        wf_pnl = wf_recent.get(sess, 0)
        cmp_data.append({"session": sess, "OOS Locked": oos_pnl, "Walk-forward": wf_pnl})

    cmp_df = pd.DataFrame(cmp_data)
    fig_cmp = go.Figure()
    fig_cmp.add_trace(go.Bar(x=cmp_df["session"], y=cmp_df["OOS Locked"],
                              name="OOS Locked (2024-2026)", marker_color=COLORS["accent_blue"],
                              text=[f"{v:+.0f}" for v in cmp_df["OOS Locked"]], textposition="auto"))
    fig_cmp.add_trace(go.Bar(x=cmp_df["session"], y=cmp_df["Walk-forward"],
                              name="Walk-forward Recent", marker_color=COLORS["success"],
                              text=[f"{v:+.0f}" for v in cmp_df["Walk-forward"]], textposition="auto"))
    fig_cmp.update_layout(**plotly_layout(barmode="group", height=320,
                                           yaxis_title="PnL (pts)",
                                           title=dict(text="Per-session: OOS vs WF Recent", font=dict(color=COLORS["text"], size=12))))
    st.plotly_chart(fig_cmp, use_container_width=True)

st.divider()

# ───────────────────────────────────────────────────────────
# 🛡️ Regime Stability Monitor
# ───────────────────────────────────────────────────────────
st.markdown("<h2>🛡️ Regime Stability Monitor</h2>", unsafe_allow_html=True)

if regime is not None:
    drift = []
    for sess in ["Asia", "London", "NY"]:
        s = regime[regime["session"] == sess].sort_values("quarter")
        if len(s) < 8: continue
        historical = s.iloc[:-4]
        recent = s.iloc[-4:]
        hist_mean = historical["val_pnl"].mean()
        hist_std = historical["val_pnl"].std()
        recent_mean = recent["val_pnl"].mean()
        z = (recent_mean - hist_mean) / (hist_std / (4 ** 0.5)) if hist_std else 0

        if z < -2: verdict = "🚨 STOP"; vcolor = COLORS["danger"]
        elif z < -1: verdict = "⚠️ REDUCE 50%"; vcolor = COLORS["warning"]
        elif z > 2: verdict = "✅ STRONG"; vcolor = COLORS["success"]
        else: verdict = "✓ NORMAL"; vcolor = COLORS["success"]

        drift.append({
            "Session": sess,
            "Hist Mean": f"{hist_mean:+.2f}",
            "Recent Mean (4Q)": f"{recent_mean:+.2f}",
            "Drift z-score": f"{z:+.2f}",
            "Verdict": verdict,
        })
    if drift:
        st.dataframe(pd.DataFrame(drift), hide_index=True, use_container_width=True)

    # Per-quarter PnL chart
    fig_q = go.Figure()
    for sess in ["Asia", "London", "NY"]:
        s = regime[regime["session"] == sess].sort_values("quarter")
        color = {"Asia": COLORS["success"], "London": COLORS["accent_blue"], "NY": "#F77F00"}[sess]
        fig_q.add_trace(go.Bar(x=s["quarter"], y=s["val_pnl"], name=sess, marker_color=color))
    fig_q.add_hline(y=0, line_color=COLORS["text_secondary"], line_dash="dash")
    fig_q.update_layout(**plotly_layout(
        barmode="group",
        height=380,
        yaxis_title="PnL per Quarter",
        title=dict(text="Per-Quarter PnL · Regime Stability View", font=dict(color=COLORS["text"], size=14)),
        xaxis=dict(tickangle=-45),
    ))
    st.plotly_chart(fig_q, use_container_width=True)

st.divider()

# ───────────────────────────────────────────────────────────
# 📋 Action Framework
# ───────────────────────────────────────────────────────────
st.markdown(f"""
<h2>🎯 Live Deploy Action Framework</h2>
<div style="
    font-size: 0.92rem;
    line-height: 1.8;
    color: {COLORS['text_secondary']};
    background: rgba(15, 23, 42, 0.3);
    border: 1px solid {COLORS['border']};
    border-left: 3px solid {COLORS['success']};
    border-radius: 10px;
    padding: 1rem 1.25rem;
">
<b style="color: {COLORS['text']};">Drift z-score response:</b><br>
✓ <b>Normal</b> (-1 ≤ z ≤ +1): Continue current parameters<br>
⚠️ <b>Mild Decay</b> (-2 ≤ z &lt; -1): REDUCE size 50%, monitor next 2Q<br>
🚨 <b>Strong Decay</b> (z &lt; -2): STOP session, re-optimize parameters<br>
✅ <b>Strong Regime</b> (z &gt; +2): Consider increase size 1.5x<br><br>

<b style="color: {COLORS['text']};">Run monthly:</b> <code style="color: {COLORS['accent_blue']};">python3 scripts/regime_stability_monitor.py</code><br>
<b style="color: {COLORS['text']};">Refresh data weekly:</b> <code style="color: {COLORS['accent_blue']};">scripts/refresh-data.sh</code> + <code style="color: {COLORS['accent_blue']};">scripts/pull_macro_sentiment.py</code>
</div>
""", unsafe_allow_html=True)

st.caption("All 24 variants tested in Phase 7. e16b confirmed local optimum — further variant testing = diminishing returns. Recommended: deploy live, journal, monitor regime.")
