"""Macro Sentiment — daily XAUUSD bias from 6 sources.

DXY, GLD, US 2Y/10Y yields, VIX, Reverse Repo (RRP).
Source: data/macro/*.csv (pulled via scripts/pull_macro_sentiment.py)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from lib.theme import apply_theme, COLORS, plotly_layout, metric_card

st.set_page_config(page_title="Macro Sentiment · PT Box", page_icon="📈", layout="wide")
apply_theme()

DATA_DIR = Path(__file__).parent.parent / "data" / "macro"


@st.cache_data(ttl=3600)
def load_bias_scores():
    df = pd.read_csv(DATA_DIR / "daily_bias_score.csv")
    df["date"] = pd.to_datetime(df["date"])
    return df


@st.cache_data(ttl=3600)
def load_xau_returns():
    """Compute next-day + 5d forward returns from GLD as XAU proxy."""
    gld = pd.read_csv(DATA_DIR / "gld_daily.csv")
    gld["date"] = pd.to_datetime(gld["date"])
    gld = gld.sort_values("date").reset_index(drop=True)
    gld["return_1d"] = gld["Close"].pct_change().shift(-1) * 100
    gld["return_5d"] = gld["Close"].pct_change(5).shift(-5) * 100
    return gld[["date", "Close", "return_1d", "return_5d"]]


# --- Header ---
st.markdown(f"""
<div style="margin-bottom: 1.5rem;">
    <h1 style="font-size: 2rem; margin: 0;">📈 Macro Sentiment — XAUUSD Daily Bias</h1>
    <p style="color: {COLORS['text_secondary']}; margin: 0.25rem 0 0 0;">
        6-source mechanical bias score · 2015 → 2026 · DXY · 10Y · 2Y · VIX · GLD · RRP
    </p>
</div>
""", unsafe_allow_html=True)

bias = load_bias_scores()
xau = load_xau_returns()
latest = bias.iloc[-1]

# --- Hero current bias card ---
score = int(latest["bias_score"])
label = latest["bias_label"]
date = latest["date"].strftime("%Y-%m-%d")

if score >= 4:
    color = COLORS["success"]
    desc = "Strong gold bullish · all systems green · LONG bias 1.5x sizing"
elif score >= 1:
    color = COLORS["success"]
    desc = "Bullish lean · LONG preferred · normal sizing"
elif score == 0:
    color = COLORS["text_secondary"]
    desc = "Neutral · both directions OK"
elif score >= -3:
    color = COLORS["danger"]
    desc = "Bearish lean · SHORT preferred · normal sizing"
else:
    color = COLORS["danger"]
    desc = "Strong gold bearish · SHORT bias 1.5x sizing · skip LONG signals"

st.markdown(f"""
<div style="
    background: linear-gradient(135deg, rgba(51, 92, 255, 0.06) 0%, rgba(15, 23, 42, 0.5) 60%);
    border: 1px solid {COLORS['border']};
    border-radius: 16px;
    padding: 1.75rem 2rem;
    margin-bottom: 1.5rem;
">
    <div style="display: flex; align-items: baseline; justify-content: space-between; flex-wrap: wrap; gap: 1rem;">
        <div>
            <div style="color: {COLORS['text_secondary']}; font-size: 0.75rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.5rem;">
                Today's Bias · {date}
            </div>
            <div style="font-size: 3.5rem; font-weight: 800; color: {color}; letter-spacing: -0.03em; line-height: 1;">
                {score:+d} <span style="font-size: 1rem; color: {COLORS['text_secondary']}; font-weight: 500;">/ ±6</span>
            </div>
            <div style="margin-top: 0.5rem; color: {color}; font-size: 1rem; font-weight: 600;">
                {label.replace("_", " ")}
            </div>
            <div style="margin-top: 0.4rem; color: {COLORS['text_secondary']}; font-size: 0.85rem;">
                {desc}
            </div>
        </div>
        <div style="text-align: right;">
            <div style="font-family: 'JetBrains Mono', monospace; color: {COLORS['text_secondary']}; font-size: 0.75rem;">XAUUSD daily filter</div>
            <div style="color: {COLORS['text']}; font-size: 0.95rem; margin-top: 0.25rem;">PT Box Variable X-9</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- 6 component values ---
st.markdown("<h2>6-Source Component Snapshot</h2>", unsafe_allow_html=True)

components = [
    ("DXY", latest["dxy"], int(latest["score_dxy"]), "USD Index — inverse driver"),
    ("10Y", f"{latest['yield_10y_pct']:.2f}%", int(latest["score_10y"]), "Long yield (real rate)"),
    ("2Y", f"{latest['yield_2y_pct']:.2f}%", int(latest["score_2y"]), "Fed expectations"),
    ("VIX", f"{latest['vix']:.1f}", int(latest["score_vix"]), "Risk-off detector"),
    ("GLD", f"${latest['gld']:.1f}", int(latest["score_gld"]), "ETF flow"),
    ("RRP", f"${latest['rrp_billion_usd']:.0f}B", int(latest["score_rrp"]), "Liquidity indicator"),
]

cols = st.columns(6)
for col, (name, val, comp_score, desc) in zip(cols, components):
    sign_color = COLORS["success"] if comp_score > 0 else (COLORS["danger"] if comp_score < 0 else COLORS["text_secondary"])
    score_str = f"{comp_score:+d}" if comp_score != 0 else "0"
    with col:
        st.markdown(f"""
        <div style="
            background: rgba(15, 23, 42, 0.4);
            border: 1px solid {COLORS['border']};
            border-radius: 10px;
            padding: 0.85rem 1rem;
            text-align: center;
        ">
            <div style="color: {COLORS['text_secondary']}; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.06em;">{name}</div>
            <div style="color: {COLORS['text']}; font-size: 1.05rem; font-weight: 700; margin: 0.25rem 0;">{val}</div>
            <div style="color: {sign_color}; font-size: 1.3rem; font-weight: 800; line-height: 1;">{score_str}</div>
            <div style="color: {COLORS['text_secondary']}; font-size: 0.7rem; margin-top: 0.3rem;">{desc}</div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# --- Sidebar filter ---
with st.sidebar:
    st.markdown("### 🔎 Filter")
    years = sorted(bias["date"].dt.year.unique())
    year_range = st.select_slider(
        "Year range",
        options=years,
        value=(years[0], years[-1]),
    )
    bias_f = bias[(bias["date"].dt.year >= year_range[0]) & (bias["date"].dt.year <= year_range[1])].copy()

    st.markdown("### 📊 Quick Stats")
    st.markdown(f"""
    Days: **{len(bias_f):,}**
    Mean score: **{bias_f['bias_score'].mean():+.2f}**
    Median: **{int(bias_f['bias_score'].median()):+d}**
    """)

# --- Bias score timeline ---
st.markdown("<h2>📊 Bias Score Timeline</h2>", unsafe_allow_html=True)

fig_score = go.Figure()
fig_score.add_trace(go.Scatter(
    x=bias_f["date"],
    y=bias_f["bias_score"],
    mode="lines",
    line=dict(color=COLORS["accent_blue"], width=1),
    fill="tozeroy",
    fillcolor="rgba(51, 92, 255, 0.08)",
    hovertemplate="<b>%{x|%Y-%m-%d}</b><br>Score: %{y:+d}<extra></extra>",
))
fig_score.add_hline(y=4, line_color=COLORS["success"], line_dash="dot", annotation_text="Strong Bullish (+4)", annotation_font_color=COLORS["success"])
fig_score.add_hline(y=-4, line_color=COLORS["danger"], line_dash="dot", annotation_text="Strong Bearish (-4)", annotation_font_color=COLORS["danger"])
fig_score.add_hline(y=0, line_color=COLORS["text_secondary"], line_dash="dash")
fig_score.update_layout(**plotly_layout(
    height=380,
    yaxis_title="Bias Score (-6 to +6)",
    yaxis=dict(range=[-7, 7]),
    title=dict(text="Daily Macro Bias Score", font=dict(color=COLORS["text"], size=14)),
))
st.plotly_chart(fig_score, use_container_width=True)

# --- Score distribution ---
c1, c2 = st.columns(2)

with c1:
    st.markdown("<h3>Score Distribution</h3>", unsafe_allow_html=True)
    hist_data = bias_f["bias_score"].value_counts().sort_index()

    fig_hist = go.Figure()
    colors_bar = [COLORS["danger"] if s < 0 else (COLORS["success"] if s > 0 else COLORS["text_secondary"]) for s in hist_data.index]
    fig_hist.add_trace(go.Bar(
        x=hist_data.index,
        y=hist_data.values,
        marker_color=colors_bar,
        text=hist_data.values,
        textposition="auto",
        textfont=dict(color=COLORS["text"], size=10),
    ))
    fig_hist.update_layout(**plotly_layout(
        height=320,
        xaxis_title="Bias Score",
        yaxis_title="Days",
        title=dict(text=f"{len(bias_f):,} days · {year_range[0]}-{year_range[1]}", font=dict(color=COLORS["text"], size=12)),
    ))
    st.plotly_chart(fig_hist, use_container_width=True)

# --- Validation: 5-day forward return per bucket ---
with c2:
    st.markdown("<h3>5-Day Forward Return per Bucket</h3>", unsafe_allow_html=True)
    df_val = bias_f.merge(xau, on="date", how="inner").dropna(subset=["bias_score", "return_5d"])

    buckets = [
        ("Strong Bear", df_val["bias_score"] <= -4, COLORS["danger"]),
        ("Bear", (df_val["bias_score"] >= -3) & (df_val["bias_score"] <= -1), COLORS["warning"]),
        ("Neutral", df_val["bias_score"] == 0, COLORS["text_secondary"]),
        ("Bull", (df_val["bias_score"] >= 1) & (df_val["bias_score"] <= 3), "#84EBB4"),
        ("Strong Bull", df_val["bias_score"] >= 4, COLORS["success"]),
    ]

    bucket_data = []
    for name, mask, c in buckets:
        grp = df_val[mask]["return_5d"]
        if len(grp) > 0:
            bucket_data.append({
                "bucket": name,
                "avg_return": grp.mean(),
                "win_rate": (grp > 0).sum() / len(grp) * 100,
                "days": len(grp),
                "color": c,
            })

    fig_val = go.Figure()
    fig_val.add_trace(go.Bar(
        x=[b["bucket"] for b in bucket_data],
        y=[b["avg_return"] for b in bucket_data],
        marker_color=[b["color"] for b in bucket_data],
        text=[f"{b['avg_return']:+.3f}%<br>WR {b['win_rate']:.1f}%<br>n={b['days']}" for b in bucket_data],
        textposition="auto",
        textfont=dict(color=COLORS["text"], size=10),
    ))
    fig_val.add_hline(y=0, line_color=COLORS["text_secondary"], line_dash="dash")
    fig_val.update_layout(**plotly_layout(
        height=320,
        yaxis_title="Avg 5-day Return %",
        title=dict(text=f"Validation · GLD as XAU proxy", font=dict(color=COLORS["text"], size=12)),
    ))
    st.plotly_chart(fig_val, use_container_width=True)

st.divider()

# --- 6-source price overlay ---
st.markdown("<h2>📉 6 Sources Historical Overlay</h2>", unsafe_allow_html=True)

normalize = st.toggle("Normalize (rebase to 100 at start)", value=True)

fig_overlay = go.Figure()
series_specs = [
    ("dxy", "DXY", BLUE_C := "#6895FF"),
    ("yield_10y_pct", "10Y Yield", "#FB4710"),
    ("yield_2y_pct", "2Y Yield", "#F77F00"),
    ("vix", "VIX", "#a855f7"),
    ("gld", "GLD", COLORS["success"]),
    ("rrp_billion_usd", "RRP ($B)", "#717784"),
]

for col_name, label_, c in series_specs:
    s = bias_f[["date", col_name]].dropna().copy()
    if len(s) == 0:
        continue
    if normalize:
        base = s[col_name].iloc[0] if s[col_name].iloc[0] != 0 else 1
        s["val"] = s[col_name] / base * 100
    else:
        s["val"] = s[col_name]
    fig_overlay.add_trace(go.Scatter(
        x=s["date"], y=s["val"], mode="lines",
        line=dict(color=c, width=1.3),
        name=label_,
        hovertemplate=f"<b>{label_}</b><br>%{{x|%Y-%m-%d}}: %{{y:.2f}}<extra></extra>",
    ))

fig_overlay.update_layout(**plotly_layout(
    height=420,
    yaxis_title=("Indexed (start=100)" if normalize else "Raw value"),
    title=dict(text=f"6 Macro Sources · {year_range[0]}-{year_range[1]}", font=dict(color=COLORS["text"], size=14)),
    hovermode="x unified",
    showlegend=True,
))
st.plotly_chart(fig_overlay, use_container_width=True)

st.divider()

# --- Recent 30 days table ---
st.markdown("<h2>📋 Recent 30 Days</h2>", unsafe_allow_html=True)

recent = bias.tail(30).iloc[::-1].copy()
display = recent[[
    "date", "bias_score", "bias_label",
    "dxy", "yield_10y_pct", "yield_2y_pct", "vix", "gld", "rrp_billion_usd",
]].copy()
display["date"] = display["date"].dt.strftime("%Y-%m-%d")
display.columns = ["Date", "Score", "Label", "DXY", "10Y%", "2Y%", "VIX", "GLD", "RRP $B"]

st.dataframe(
    display.style.format({
        "DXY": "{:.2f}",
        "10Y%": "{:.2f}",
        "2Y%": "{:.2f}",
        "VIX": "{:.1f}",
        "GLD": "${:.1f}",
        "RRP $B": "${:.0f}",
    }).background_gradient(subset=["Score"], cmap="RdYlGn", vmin=-6, vmax=6),
    hide_index=True, use_container_width=True, height=400,
)

st.caption(f"Bias score computed from 6 macro sources (2015-2026, {len(bias):,} days). Refresh: `python3 scripts/pull_macro_sentiment.py && python3 scripts/compute_macro_bias_score.py`")
