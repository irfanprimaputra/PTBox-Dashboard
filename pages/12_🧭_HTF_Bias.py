"""HTF Daily Bias — Mental filter for PT Box live trade.

Display today's HTF bias score + factors. Used as mental layer ON TOP of
Pine v15 systematic signals. No code change to Pine, pure info aid.

User explicitly skipped multi-strategy systematic (Phase 45, 47 rejected).
This page = SMC-inspired manual filter for PT Box.
"""
import streamlit as st
import json
from pathlib import Path
from datetime import datetime

# Theme
from lib.theme import COLORS, inject_css

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

st.set_page_config(page_title="HTF Bias", page_icon="🧭", layout="wide")
inject_css()


@st.cache_data(ttl=300)
def load_bias():
    p = DATA_DIR / "daily_bias.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


data = load_bias()

# ─── Header ──────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-bottom: 1.5rem;">
    <h1 style="font-size: 2rem; margin: 0;">🧭 HTF Bias — Daily Mental Filter</h1>
    <p style="color: {COLORS['text_secondary']}; margin: 0.25rem 0 0 0;">
        SMC-inspired bias for PT Box signals · Manual filter, no Pine code change · Update daily via <code>compute_daily_bias.py</code>
    </p>
</div>
""", unsafe_allow_html=True)

if not data or not data.get('today'):
    st.error("⚠️ Bias data not found. Run `python scripts/compute_daily_bias.py` first.")
    st.stop()

today = data['today']
history = data.get('history_30d', [])

# ─── TODAY HERO CARD ─────────────────────────────────────────────────────────
score = today['score']
verdict = today['verdict']

if score >= 70:
    bg_color = "rgba(34, 197, 94, 0.15)"
    border_color = "rgb(34, 197, 94)"
    score_color = "rgb(34, 197, 94)"
elif score >= 60:
    bg_color = "rgba(74, 222, 128, 0.10)"
    border_color = "rgb(74, 222, 128)"
    score_color = "rgb(74, 222, 128)"
elif score >= 40:
    bg_color = "rgba(156, 163, 175, 0.10)"
    border_color = "rgb(156, 163, 175)"
    score_color = "rgb(156, 163, 175)"
elif score >= 30:
    bg_color = "rgba(248, 113, 113, 0.10)"
    border_color = "rgb(248, 113, 113)"
    score_color = "rgb(248, 113, 113)"
else:
    bg_color = "rgba(239, 68, 68, 0.15)"
    border_color = "rgb(239, 68, 68)"
    score_color = "rgb(239, 68, 68)"

st.markdown(f"""
<div style="
    background: {bg_color};
    border: 2px solid {border_color};
    border-radius: 16px;
    padding: 2.5rem;
    margin-bottom: 1.5rem;
    text-align: center;
">
    <div style="font-size: 0.85rem; color: {COLORS['text_secondary']}; letter-spacing: 0.1em; font-weight: 600;">
        TODAY · {today['date']}
    </div>
    <div style="font-size: 5rem; font-weight: 800; color: {score_color}; line-height: 1; margin: 0.5rem 0;">
        {score}
        <span style="font-size: 1.5rem; color: {COLORS['text_secondary']}; font-weight: 500;">/100</span>
    </div>
    <div style="font-size: 1.8rem; font-weight: 700; color: {score_color}; margin: 0.5rem 0;">
        {verdict}
    </div>
    <div style="font-size: 1rem; color: {COLORS['text_secondary']}; max-width: 600px; margin: 0.75rem auto 0;">
        {today['action']}
    </div>
</div>
""", unsafe_allow_html=True)

# ─── Score Breakdown ─────────────────────────────────────────────────────────
st.markdown("### 📊 Score Factor Breakdown")

factors = today['factors']
levels = today['levels']

c1, c2 = st.columns(2)

with c1:
    st.markdown(f"""
    <div style="background: rgba(31, 41, 55, 0.5); padding: 1.25rem; border-radius: 10px; border: 1px solid {COLORS['border']};">
        <h4 style="margin: 0 0 0.75rem 0; color: {COLORS['text']};">🎯 Bias Factors</h4>

    """, unsafe_allow_html=True)
    trend_color = 'rgb(34, 197, 94)' if factors['trend_3d'] == 1 else ('rgb(239, 68, 68)' if factors['trend_3d'] == -1 else 'rgb(156, 163, 175)')
    trend_label = 'BULLISH' if factors['trend_3d'] == 1 else ('BEARISH' if factors['trend_3d'] == -1 else 'NEUTRAL')
    pdc_color = 'rgb(34, 197, 94)' if factors['today_open_vs_pdc'] > 0 else 'rgb(239, 68, 68)'
    zone_color = 'rgb(239, 68, 68)' if factors['zone_in_5d_range'] == 'PREMIUM' else ('rgb(34, 197, 94)' if factors['zone_in_5d_range'] == 'DISCOUNT' else 'rgb(156, 163, 175)')

    st.markdown(f"""
    <table style="width: 100%; border-collapse: collapse; font-size: 0.9rem;">
        <tr><td style="padding: 0.4rem 0;">3-Day Close Trend</td><td style="text-align:right; color: {trend_color}; font-weight: 600;">{trend_label}</td></tr>
        <tr><td style="padding: 0.4rem 0;">Today Open vs PDC</td><td style="text-align:right; color: {pdc_color}; font-weight: 600;">{factors['today_open_vs_pdc']:+.2f}</td></tr>
        <tr><td style="padding: 0.4rem 0;">Today Open vs PDM</td><td style="text-align:right; font-weight: 600;">{factors['today_open_vs_pdm'].upper()}</td></tr>
        <tr><td style="padding: 0.4rem 0;">5-Day Range Zone</td><td style="text-align:right; color: {zone_color}; font-weight: 600;">{factors['zone_in_5d_range']}</td></tr>
        <tr><td style="padding: 0.4rem 0;">Position in Range</td><td style="text-align:right; font-weight: 600;">{factors['position_pct']:.1f}%</td></tr>
        <tr><td style="padding: 0.4rem 0;">Prior Day Close Type</td><td style="text-align:right; font-weight: 600;">{factors['pd_close_type']}</td></tr>
        <tr><td style="padding: 0.4rem 0;">Nearest Round $50</td><td style="text-align:right; font-weight: 600;">${factors['nearest_round_50']}</td></tr>
        <tr><td style="padding: 0.4rem 0;">Dist to Round</td><td style="text-align:right; font-weight: 600;">{factors['dist_to_round']:.2f}pt</td></tr>
    </table>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div style="background: rgba(31, 41, 55, 0.5); padding: 1.25rem; border-radius: 10px; border: 1px solid {COLORS['border']};">
        <h4 style="margin: 0 0 0.75rem 0; color: {COLORS['text']};">📐 Today Price Levels</h4>
    <table style="width: 100%; border-collapse: collapse; font-size: 0.9rem;">
        <tr><td style="padding: 0.4rem 0;">Today Open</td><td style="text-align:right; font-weight: 600; color: {COLORS['text']};">${levels['today_open']:.2f}</td></tr>
        <tr><td style="padding: 0.4rem 0;">Today High</td><td style="text-align:right; font-weight: 600;">${levels['today_high']:.2f}</td></tr>
        <tr><td style="padding: 0.4rem 0;">Today Low</td><td style="text-align:right; font-weight: 600;">${levels['today_low']:.2f}</td></tr>
        <tr><td style="padding: 0.4rem 0;">PDH (Prior Day High)</td><td style="text-align:right; font-weight: 600; color: rgb(239, 68, 68);">${levels['pdh']:.2f}</td></tr>
        <tr><td style="padding: 0.4rem 0;">PDM (Prior Day Mid)</td><td style="text-align:right; font-weight: 600; color: rgb(156, 163, 175);">${levels['pdm']:.2f}</td></tr>
        <tr><td style="padding: 0.4rem 0;">PDL (Prior Day Low)</td><td style="text-align:right; font-weight: 600; color: rgb(34, 197, 94);">${levels['pdl']:.2f}</td></tr>
        <tr><td style="padding: 0.4rem 0;">5-Day Range High</td><td style="text-align:right; font-weight: 600;">${levels['range_5d_high']:.2f}</td></tr>
        <tr><td style="padding: 0.4rem 0;">5-Day Range Low</td><td style="text-align:right; font-weight: 600;">${levels['range_5d_low']:.2f}</td></tr>
    </table>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ─── 30-day Bias History ─────────────────────────────────────────────────────
st.markdown("### 📈 30-Day Bias History")

import pandas as pd
hist_df = pd.DataFrame([{
    'date': h['date'],
    'score': h['score'],
    'verdict': h['verdict'],
    'zone': h['factors']['zone_in_5d_range'],
    'trend_3d': h['factors']['trend_3d'],
} for h in history])

if not hist_df.empty:
    import plotly.express as px
    fig = px.bar(
        hist_df, x='date', y='score',
        color='score',
        color_continuous_scale=['rgb(239, 68, 68)', 'rgb(156, 163, 175)', 'rgb(34, 197, 94)'],
        range_color=[0, 100],
        title="Daily Bias Score (0=Strong Sell, 50=Neutral, 100=Strong Buy)",
    )
    fig.add_hline(y=50, line_dash="dash", line_color="white", opacity=0.3)
    fig.add_hline(y=70, line_dash="dot", line_color="rgb(34, 197, 94)", opacity=0.5, annotation_text="Strong Buy")
    fig.add_hline(y=30, line_dash="dot", line_color="rgb(239, 68, 68)", opacity=0.5, annotation_text="Strong Sell")
    fig.update_layout(
        height=350, margin=dict(t=40, b=20),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color=COLORS['text'],
    )
    st.plotly_chart(fig, use_container_width=True)

# ─── How to Use ──────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 💡 How to Use This Bias")

st.markdown(f"""
<div style="background: rgba(99, 102, 241, 0.08); border-left: 3px solid rgb(99, 102, 241); border-radius: 8px; padding: 1.25rem;">

**Pure mental filter** — Pine v15 Pine code UNCHANGED. Lu yang decide eksekusi.

**Workflow harian (5 menit pagi):**

1. **Pre-market 06:00 WIB:** open this page → cek today's score
2. **Sesi Asia/London/NY:** PT Box auto signal fire alert HP
3. **Lu evaluate:**
   - Bias **≥70 BUY**: ✅ take ALL BUY signals full lot, ❌ skip/half SELL
   - Bias **40-60 NEUTRAL**: ✅ trade both equal lot
   - Bias **≤30 SELL**: ✅ take ALL SELL signals, ❌ skip/half BUY
4. **End of day:** review trade journal vs bias accuracy

**SMC mapping (mentor framework reference):**
- 3-Day Trend = Market Structure (HH HL / LH LL)
- Today vs PDH/PDL = Premium/Discount
- 5-Day Range Zone = Equilibrium positioning
- Round Numbers = Liquidity magnets (institutional levels)

**Important caveat:** Bias = probabilistic, BUKAN deterministic. 30% time bias salah. Lu masih harus pakai daily stop -$50 / weekly -$100 regardless of bias.

**Phase 47 confirmed:** systematic bias filter on PT Box = no edge (cuts winners equal). Use as MENTAL aid only, BUKAN auto-filter.

</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div style="margin-top: 1rem; padding: 1rem; background: rgba(31, 41, 55, 0.3); border-radius: 8px; color: {COLORS['text_secondary']}; font-size: 0.85rem;">
<strong>⚙️ Update:</strong> Run <code>python scripts/compute_daily_bias.py</code> daily before market open untuk refresh data ini. Auto-cache 5 menit Streamlit.
</div>
""", unsafe_allow_html=True)
