"""Trade Analytics — day/week/month/day-of-week breakdown across 11 years."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from lib.data_loader import load_trades, get_session_color, DOW_ORDER
from lib.theme import apply_theme, COLORS, plotly_layout, metric_card

st.set_page_config(page_title="Trade Analytics · PT Box", page_icon="📊", layout="wide")
apply_theme()

st.markdown(f"""
<div style="margin-bottom: 1.5rem;">
    <h1 style="font-size: 2rem; margin: 0;">📊 Trade Analytics</h1>
    <p style="color: {COLORS['text_secondary']}; margin: 0.25rem 0 0 0;">
        Per-trade history · 2015 → 2026 · day-of-week, weekly, monthly patterns
    </p>
</div>
""", unsafe_allow_html=True)

trades = load_trades()
if trades is None or len(trades) == 0:
    st.error("⚠️ Trade data not found. Run `python3 code/ptbox_v6_trade_export.py` first.")
    st.stop()

st.success(f"""
**✅ e37 TRADE DATA (live config)** — Asia 18:00/90m DIRECT, London 00:00/60m DIRECT, NY 07:00/60m DIRECT.
Period: 2021 → 2026 (5 years). **Total PnL +9084 pts · WR 60.2% · OOS validated 316% retention.**

Per-session: Asia +1839 (594 trades, 61% WR) · London +3220 (958, 62% WR) · NY +4025 (881, 58% WR).
Use filters below to slice by session, year, direction, day-of-week patterns.
""")

# --- Sidebar filters ---
with st.sidebar:
    st.markdown("### 🔎 Filter")
    sessions_pick = st.multiselect(
        "Sessions",
        ["Asia", "London", "NY"],
        default=["Asia", "London", "NY"],
    )

    years = sorted(trades["year"].unique())
    year_range = st.select_slider(
        "Year range",
        options=years,
        value=(years[0], years[-1]),
    )

    direction_pick = st.multiselect(
        "Direction",
        ["long", "short"],
        default=["long", "short"],
    )

# Apply filters
df = trades[
    trades["session"].isin(sessions_pick) &
    trades["year"].between(year_range[0], year_range[1]) &
    trades["direction"].isin(direction_pick)
].copy()

# --- Summary metrics ---
total_trades = len(df)
wins = (df["pnl_pts"] > 0).sum()
losses = (df["pnl_pts"] < 0).sum()
total_pnl = df["pnl_pts"].sum()
avg_pnl = df["pnl_pts"].mean() if len(df) else 0
wr = wins / total_trades * 100 if total_trades else 0

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    metric_card("Total Trades", f"{total_trades:,}")
with c2:
    metric_card("Wins / Losses", f"{wins:,} / {losses:,}", color=COLORS["text"])
with c3:
    metric_card("Win Rate", f"{wr:.1f}%", color=(COLORS["success"] if wr > 50 else COLORS["warning"]))
with c4:
    metric_card("Total PnL", f"{total_pnl:+.0f} pts", color=(COLORS["success"] if total_pnl > 0 else COLORS["danger"]))
with c5:
    metric_card("Avg/Trade", f"{avg_pnl:+.2f} pts", color=(COLORS["success"] if avg_pnl > 0 else COLORS["danger"]))

st.divider()

# --- Day-of-Week pattern ---
st.markdown("<h2>📅 Day-of-Week Pattern</h2>", unsafe_allow_html=True)

dow_agg = df.groupby(["day_of_week", "session"]).agg(
    trades=("pnl_pts", "count"),
    pnl=("pnl_pts", "sum"),
    wins=("pnl_pts", lambda x: (x > 0).sum()),
).reset_index()
dow_agg["wr"] = dow_agg["wins"] / dow_agg["trades"] * 100
dow_agg["day_of_week"] = pd.Categorical(dow_agg["day_of_week"], categories=DOW_ORDER, ordered=True)
dow_agg = dow_agg.sort_values(["day_of_week", "session"])

# Stacked bar: PnL per day-of-week per session
fig_dow_pnl = go.Figure()
for sess in ["Asia", "London", "NY"]:
    if sess in sessions_pick:
        sd = dow_agg[dow_agg["session"] == sess]
        fig_dow_pnl.add_trace(go.Bar(
            x=sd["day_of_week"].astype(str),
            y=sd["pnl"],
            name=sess,
            marker_color=get_session_color(sess),
            text=[f"{v:+.0f}" for v in sd["pnl"]],
            textposition="auto",
            textfont=dict(size=10, color=COLORS["text"]),
        ))
fig_dow_pnl.update_layout(**plotly_layout(
    barmode="relative",
    height=380,
    title=dict(text="PnL per Day-of-Week × Session", font=dict(color=COLORS["text"], size=14)),
    yaxis_title="PnL (pts)",
))
st.plotly_chart(fig_dow_pnl, use_container_width=True)

# Day-of-week heatmap (WR × session)
heatmap_wr = dow_agg.pivot_table(index="day_of_week", columns="session", values="wr", observed=True)
heatmap_wr = heatmap_wr.reindex(DOW_ORDER)

fig_heat = px.imshow(
    heatmap_wr.values,
    x=heatmap_wr.columns.tolist(),
    y=heatmap_wr.index.tolist(),
    color_continuous_scale=[[0, COLORS["danger"]], [0.5, COLORS["warning"]], [1, COLORS["success"]]],
    text_auto=".1f",
    aspect="auto",
    range_color=[20, 80],
    labels=dict(color="WR %"),
)
fig_heat.update_layout(**plotly_layout(
    height=320,
    title=dict(text="Win Rate Heatmap · Day-of-Week × Session", font=dict(color=COLORS["text"], size=14)),
))
fig_heat.update_xaxes(side="top")
st.plotly_chart(fig_heat, use_container_width=True)

# Day-of-week table
st.markdown("<h3>Day-of-Week Detail</h3>", unsafe_allow_html=True)
dow_total = df.groupby("day_of_week").agg(
    trades=("pnl_pts", "count"),
    wr=("pnl_pts", lambda x: (x > 0).sum() / len(x) * 100),
    total_pnl=("pnl_pts", "sum"),
    avg_pnl=("pnl_pts", "mean"),
    best_trade=("pnl_pts", "max"),
    worst_trade=("pnl_pts", "min"),
).reset_index()
dow_total["day_of_week"] = pd.Categorical(dow_total["day_of_week"], categories=DOW_ORDER, ordered=True)
dow_total = dow_total.sort_values("day_of_week")

st.dataframe(
    dow_total.style.format({
        "wr": "{:.1f}%",
        "total_pnl": "{:+.1f}",
        "avg_pnl": "{:+.2f}",
        "best_trade": "{:+.1f}",
        "worst_trade": "{:+.1f}",
    }).background_gradient(subset=["total_pnl"], cmap="RdYlGn", vmin=-500, vmax=500)
      .background_gradient(subset=["wr"], cmap="RdYlGn", vmin=20, vmax=80),
    hide_index=True, use_container_width=True,
)

st.divider()

# --- Monthly aggregation ---
st.markdown("<h2>📆 Monthly Pattern</h2>", unsafe_allow_html=True)

monthly = df.groupby(["month", "session"]).agg(
    trades=("pnl_pts", "count"),
    pnl=("pnl_pts", "sum"),
    wins=("pnl_pts", lambda x: (x > 0).sum()),
).reset_index()
monthly["wr"] = monthly["wins"] / monthly["trades"] * 100

# Monthly PnL stacked bar
monthly_pivot = monthly.pivot(index="month", columns="session", values="pnl").fillna(0)

fig_monthly = go.Figure()
for sess in ["Asia", "London", "NY"]:
    if sess in sessions_pick and sess in monthly_pivot.columns:
        fig_monthly.add_trace(go.Bar(
            x=monthly_pivot.index,
            y=monthly_pivot[sess],
            name=sess,
            marker_color=get_session_color(sess),
        ))
fig_monthly.update_layout(**plotly_layout(
    barmode="relative",
    height=400,
    title=dict(text="Monthly PnL · stacked by session", font=dict(color=COLORS["text"], size=14)),
    yaxis_title="PnL (pts)",
))
st.plotly_chart(fig_monthly, use_container_width=True)

# Calendar heatmap (Year × Month)
df["month_num"] = df["date"].dt.month
yearly_monthly = df.groupby(["year", "month_num"])["pnl_pts"].sum().reset_index()
ym_pivot = yearly_monthly.pivot(index="year", columns="month_num", values="pnl_pts").fillna(0)

fig_cal = px.imshow(
    ym_pivot.values,
    x=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    y=ym_pivot.index.tolist(),
    color_continuous_scale=[[0, COLORS["danger"]], [0.5, "#1e293b"], [1, COLORS["success"]]],
    text_auto=".0f",
    aspect="auto",
    range_color=[-100, 100],
    labels=dict(color="PnL"),
)
fig_cal.update_layout(**plotly_layout(
    height=380,
    title=dict(text="Calendar Heatmap · Year × Month PnL", font=dict(color=COLORS["text"], size=14)),
))
fig_cal.update_xaxes(side="top")
st.plotly_chart(fig_cal, use_container_width=True)

st.divider()

# --- Cumulative equity curve ---
st.markdown("<h2>📈 Equity Curve</h2>", unsafe_allow_html=True)

df_sorted = df.sort_values("date").copy()
df_sorted["cumulative"] = df_sorted["pnl_pts"].cumsum()

fig_eq = go.Figure()
fig_eq.add_trace(go.Scatter(
    x=df_sorted["date"],
    y=df_sorted["cumulative"],
    mode="lines",
    line=dict(color=COLORS["accent_blue"], width=1.5),
    fill="tozeroy",
    fillcolor="rgba(59, 130, 246, 0.06)",
    hovertemplate="<b>%{x}</b><br>Cumulative: %{y:+.0f} pts<extra></extra>",
))
fig_eq.add_hline(y=0, line_color=COLORS["text_muted"], line_dash="dash")
fig_eq.update_layout(**plotly_layout(
    height=380,
    title=dict(text="Cumulative PnL Over Time", font=dict(color=COLORS["text"], size=14)),
    yaxis_title="Cumulative (pts)",
))
st.plotly_chart(fig_eq, use_container_width=True)

# Per-session equity curves
fig_eq_sess = go.Figure()
for sess in ["Asia", "London", "NY"]:
    if sess in sessions_pick:
        sd = df[df["session"] == sess].sort_values("date").copy()
        sd["cumulative"] = sd["pnl_pts"].cumsum()
        fig_eq_sess.add_trace(go.Scatter(
            x=sd["date"],
            y=sd["cumulative"],
            mode="lines",
            line=dict(color=get_session_color(sess), width=1.5),
            name=sess,
        ))
fig_eq_sess.add_hline(y=0, line_color=COLORS["text_muted"], line_dash="dash")
fig_eq_sess.update_layout(**plotly_layout(
    height=380,
    title=dict(text="Per-Session Equity Curves", font=dict(color=COLORS["text"], size=14)),
    yaxis_title="Cumulative (pts)",
    hovermode="x unified",
))
st.plotly_chart(fig_eq_sess, use_container_width=True)

st.divider()

# --- Win/Loss distribution ---
st.markdown("<h2>📐 Trade Distribution</h2>", unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    fig_hist = go.Figure()
    fig_hist.add_trace(go.Histogram(
        x=df["pnl_pts"],
        nbinsx=50,
        marker_color=COLORS["accent_blue"],
        marker_line_color=COLORS["bg"],
        marker_line_width=1,
    ))
    fig_hist.add_vline(x=0, line_color=COLORS["text_muted"], line_dash="dash")
    fig_hist.update_layout(**plotly_layout(
        height=320,
        title=dict(text="PnL Distribution per Trade", font=dict(color=COLORS["text"], size=14)),
        xaxis_title="PnL (pts)",
        yaxis_title="Count",
    ))
    st.plotly_chart(fig_hist, use_container_width=True)

with c2:
    # Hit type donut
    hit_summary = df.groupby("hit_type").size().reset_index(name="count")
    fig_donut = go.Figure()
    fig_donut.add_trace(go.Pie(
        labels=hit_summary["hit_type"],
        values=hit_summary["count"],
        hole=0.55,
        marker=dict(colors=[COLORS["success"], COLORS["warning"], COLORS["danger"], "#a855f7"]),
        textinfo="label+percent",
    ))
    fig_donut.update_layout(**plotly_layout(
        height=320,
        title=dict(text="Hit Type Breakdown", font=dict(color=COLORS["text"], size=14)),
    ))
    st.plotly_chart(fig_donut, use_container_width=True)

st.divider()

# --- Raw trade table (paginated) ---
st.markdown("<h2>📋 Raw Trade Log</h2>", unsafe_allow_html=True)
st.caption(f"Showing {len(df):,} trades. Latest first.")

display_cols = ["date", "day_of_week", "session", "direction", "entry_time", "exit_time",
                "entry_price", "exit_price", "hit_type", "pnl_pts", "box_width"]
df_display = df[display_cols].sort_values("date", ascending=False).head(500)
st.dataframe(df_display, hide_index=True, use_container_width=True, height=400)

st.caption("Showing latest 500 trades. Use sidebar filters to narrow down.")
