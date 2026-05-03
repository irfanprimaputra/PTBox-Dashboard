"""Phase 6 Findings — Session Behavior + Inter-Session Chain + Filter Stack.

Visualizes results from 4 analytical scripts:
  - analyze_session_behavior.py
  - compute_session_chain.py
  - apply_filters_to_trades.py

Source data: data/session_behavior.csv, session_chain_*.csv, trades_with_filters.csv
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from lib.theme import apply_theme, COLORS, plotly_layout, metric_card

st.set_page_config(page_title="Phase 6 Findings · PT Box", page_icon="🔬", layout="wide")
apply_theme()

DATA_DIR = Path(__file__).parent.parent / "data"


@st.cache_data(ttl=3600)
def load_session_behavior():
    df = pd.read_csv(DATA_DIR / "session_behavior.csv")
    df["date"] = pd.to_datetime(df["date"])
    return df


@st.cache_data(ttl=3600)
def load_chain_transitions():
    return pd.read_csv(DATA_DIR / "session_chain_transitions.csv")


@st.cache_data(ttl=3600)
def load_chain_full():
    return pd.read_csv(DATA_DIR / "session_chain_full.csv")


@st.cache_data(ttl=3600)
def load_filtered_trades():
    df = pd.read_csv(DATA_DIR / "trades_with_filters.csv")
    df["date"] = pd.to_datetime(df["date"])
    return df


# --- Header ---
st.markdown(f"""
<div style="margin-bottom: 1.5rem;">
    <h1 style="font-size: 2rem; margin: 0;">🔬 Phase 6 — Findings</h1>
    <p style="color: {COLORS['text_secondary']}; margin: 0.25rem 0 0 0;">
        Session behavior · Inter-session chain · Combined filter validation
    </p>
</div>
""", unsafe_allow_html=True)

sess = load_session_behavior()
trans = load_chain_transitions()
chain = load_chain_full()
trades = load_filtered_trades()

# ───────────────────────────────────────────────────────────
# 🎯 HERO — Filter Stack Summary
# ───────────────────────────────────────────────────────────
st.markdown(f"""
<div style="
    background: linear-gradient(135deg, rgba(31, 193, 107, 0.08) 0%, rgba(15, 23, 42, 0.5) 60%);
    border: 1px solid rgba(31, 193, 107, 0.2);
    border-radius: 16px;
    padding: 1.75rem 2rem;
    margin-bottom: 1.5rem;
">
    <div style="color: {COLORS['text_secondary']}; font-size: 0.75rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.5rem;">
        ⭐ Headline · Combined Filter (Macro X-9 + Session Chain)
    </div>
    <div style="display: flex; align-items: baseline; gap: 2rem; flex-wrap: wrap;">
        <div>
            <div style="font-size: 3rem; font-weight: 800; color: {COLORS['success']}; line-height: 1; letter-spacing: -0.03em;">
                +743 <span style="font-size: 1.1rem; color: {COLORS['text_secondary']}; font-weight: 500;">pts saved</span>
            </div>
            <div style="margin-top: 0.5rem; color: {COLORS['text_secondary']}; font-size: 0.9rem;">
                vs unfiltered baseline · <b style="color: {COLORS['text']};">7,937 trades</b> tested · <b style="color: {COLORS['success']};">+48.7% damage reduction</b>
            </div>
        </div>
        <div style="border-left: 1px solid {COLORS['border']}; padding-left: 1.5rem;">
            <div style="font-size: 0.78rem; color: {COLORS['text_secondary']}; text-transform: uppercase;">Win Rate</div>
            <div style="font-size: 1.5rem; font-weight: 700; color: {COLORS['text']};">35.2% → 36.9%</div>
        </div>
        <div style="border-left: 1px solid {COLORS['border']}; padding-left: 1.5rem;">
            <div style="font-size: 0.78rem; color: {COLORS['text_secondary']}; text-transform: uppercase;">Trades Kept</div>
            <div style="font-size: 1.5rem; font-weight: 700; color: {COLORS['text']};">4,703 / 7,937 (59%)</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ───────────────────────────────────────────────────────────
# 🎯 Per-session filter impact
# ───────────────────────────────────────────────────────────
st.markdown("<h2>📊 Filter Impact per Session</h2>", unsafe_allow_html=True)

sessions_summary = []
for sess_name in ["Asia", "London", "NY"]:
    s = trades[trades["session"] == sess_name]
    baseline = s["pnl_pts"].sum()
    macro_kept = s[s["filter_macro_keep"]]["pnl_pts"].sum()
    chain_kept = s[s["filter_chain_keep"]]["pnl_pts"].sum()
    both_kept  = s[s["filter_both_keep"]]["pnl_pts"].sum()
    sessions_summary.append({
        "session": sess_name,
        "baseline": baseline,
        "macro": macro_kept,
        "chain": chain_kept,
        "combined": both_kept,
        "delta_combined": both_kept - baseline,
    })

# Table card
c1, c2, c3 = st.columns(3)
emoji_map = {"Asia": "🟢", "London": "🔵", "NY": "🟡"}
for col, sd in zip([c1, c2, c3], sessions_summary):
    delta = sd["delta_combined"]
    pct = delta / abs(sd["baseline"]) * 100 if sd["baseline"] else 0
    sign_color = COLORS["success"] if delta > 0 else COLORS["danger"]
    with col:
        st.markdown(f"""
        <div style="
            background: rgba(15, 23, 42, 0.4);
            border: 1px solid {COLORS['border']};
            border-radius: 12px;
            padding: 1.25rem 1.5rem;
        ">
            <div style="font-size: 1.4rem;">{emoji_map[sd['session']]} <b>{sd['session']}</b></div>
            <div style="margin-top: 0.5rem; font-size: 0.78rem; color: {COLORS['text_secondary']};">Baseline → Combined</div>
            <div style="font-size: 1.6rem; font-weight: 800; color: {COLORS['text']}; margin-top: 0.2rem;">
                {sd['baseline']:+.0f} → <span style="color: {sign_color};">{sd['combined']:+.0f}</span>
            </div>
            <div style="margin-top: 0.4rem; color: {sign_color}; font-size: 0.92rem; font-weight: 600;">
                Δ {delta:+.1f} pts ({pct:+.1f}%)
            </div>
        </div>
        """, unsafe_allow_html=True)

# Bar chart per session per filter
st.markdown("<h3 style='margin-top: 1.5rem;'>Filter PnL Comparison</h3>", unsafe_allow_html=True)

filter_labels = ["Baseline (no filter)", "Macro Bias only", "Chain only", "Combined (A+B)"]
fig_filters = go.Figure()
for sd in sessions_summary:
    pnls = [sd["baseline"], sd["macro"], sd["chain"], sd["combined"]]
    colors = [COLORS["danger"] if p < 0 else COLORS["success"] for p in pnls]
    fig_filters.add_trace(go.Bar(
        x=filter_labels,
        y=pnls,
        name=sd["session"],
        text=[f"{p:+.0f}" for p in pnls],
        textposition="auto",
        textfont=dict(color=COLORS["text"], size=10),
    ))
fig_filters.add_hline(y=0, line_color=COLORS["text_secondary"], line_dash="dash")
fig_filters.update_layout(**plotly_layout(
    barmode="group",
    height=400,
    yaxis_title="PnL (pts)",
    title=dict(text="PnL per Filter Variant per Session", font=dict(color=COLORS["text"], size=14)),
))
st.plotly_chart(fig_filters, use_container_width=True)

st.divider()

# ───────────────────────────────────────────────────────────
# 🌅 Session behavior state distribution
# ───────────────────────────────────────────────────────────
st.markdown("<h2>🌅 Session Behavior — State Distribution</h2>", unsafe_allow_html=True)
st.caption("3,809 session-days · Asia/London/NY 2021-2026 · 7-state classification")

state_counts = sess.groupby(["session", "state"]).size().reset_index(name="count")
state_counts["pct"] = state_counts.groupby("session")["count"].transform(lambda x: x / x.sum() * 100)

state_colors = {
    "TREND_UP":     COLORS["success"],
    "TREND_DOWN":   COLORS["danger"],
    "V_UP":         "#84EBB4",
    "V_DOWN":       "#F77F00",
    "RANGE":        COLORS["text_secondary"],
    "EXPANSION_UP": "#3EE089",
    "EXPANSION_DN": "#FB4710",
}

fig_states = go.Figure()
for state in ["TREND_UP", "TREND_DOWN", "V_UP", "V_DOWN", "RANGE", "EXPANSION_UP", "EXPANSION_DN"]:
    sub = state_counts[state_counts["state"] == state]
    fig_states.add_trace(go.Bar(
        x=sub["session"],
        y=sub["pct"],
        name=state,
        marker_color=state_colors[state],
        text=[f"{p:.1f}%" for p in sub["pct"]],
        textposition="inside",
        textfont=dict(color=COLORS["text"], size=10),
    ))
fig_states.update_layout(**plotly_layout(
    barmode="stack",
    height=380,
    yaxis_title="% of session-days",
    title=dict(text="State Distribution per Session", font=dict(color=COLORS["text"], size=14)),
))
st.plotly_chart(fig_states, use_container_width=True)

# Range stats per session
c1, c2, c3 = st.columns(3)
for col, sess_name, em in zip([c1, c2, c3], ["Asia", "London", "NY"], ["🟢", "🔵", "🟡"]):
    s = sess[sess["session"] == sess_name]
    with col:
        metric_card(f"{em} {sess_name} avg range", f"{s['range_pts'].mean():.1f} pts", sub=f"Median {s['range_pts'].median():.1f}")

st.divider()

# ───────────────────────────────────────────────────────────
# 🔗 Inter-session transition heatmaps
# ───────────────────────────────────────────────────────────
st.markdown("<h2>🔗 Inter-Session State Transitions</h2>", unsafe_allow_html=True)
st.caption("Probability of next session state given current session state · 1,080 trading days")

trans_labels = ["NY[t-1] → Asia[t]", "Asia[t] → London[t]", "London[t] → NY[t]"]
tabs = st.tabs(trans_labels)

for tab, label in zip(tabs, trans_labels):
    with tab:
        sub = trans[trans["transition"] == label]
        pivot = sub.pivot(index="from_state", columns="to_state", values="pct")
        # Order states consistently
        order = ["TREND_UP", "TREND_DOWN", "V_UP", "V_DOWN", "RANGE", "EXPANSION_UP", "EXPANSION_DN"]
        pivot = pivot.reindex(index=[s for s in order if s in pivot.index],
                              columns=[s for s in order if s in pivot.columns])

        fig_heat = px.imshow(
            pivot.values,
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            color_continuous_scale=[[0, COLORS["bg"]], [0.5, COLORS["primary_alpha_24"]], [1, COLORS["accent_blue"]]],
            text_auto=".1f",
            aspect="auto",
            labels=dict(x="To state", y="From state", color="%"),
        )
        fig_heat.update_layout(**plotly_layout(
            height=380,
            title=dict(text=label, font=dict(color=COLORS["text"], size=14)),
        ))
        fig_heat.update_xaxes(side="top")
        st.plotly_chart(fig_heat, use_container_width=True)

st.divider()

# ───────────────────────────────────────────────────────────
# 🎯 Top high-conviction chains
# ───────────────────────────────────────────────────────────
st.markdown("<h2>🎯 Top High-Conviction Chains (NY[t-1] → Asia → London → NY[t])</h2>", unsafe_allow_html=True)
st.caption("Predicting NY[t] direction with WR ≥ 50% · sample size ≥ 10")

chain["chain_str"] = chain["NY_prev"] + " → " + chain["Asia"] + " → " + chain["London"]
chain_grouped = chain.groupby("chain_str").apply(
    lambda g: pd.Series({
        "top_NY": g.sort_values("count", ascending=False).iloc[0]["NY"],
        "prob": g.sort_values("count", ascending=False).iloc[0]["pct_NY_outcome"],
        "total": g["count"].sum(),
    }), include_groups=False,
).reset_index()
top_chains = chain_grouped[(chain_grouped["total"] >= 10) & (chain_grouped["prob"] >= 50)].sort_values("prob", ascending=False).head(15)

if len(top_chains):
    display = top_chains.copy()
    display.columns = ["Chain (NY[t-1]→Asia→London)", "Predicted NY[t]", "Probability %", "Sample Size"]
    display["Probability %"] = display["Probability %"].round(1)
    st.dataframe(
        display.style.format({"Probability %": "{:.1f}%"})
            .background_gradient(subset=["Probability %"], cmap="RdYlGn", vmin=30, vmax=70),
        hide_index=True, use_container_width=True,
    )
else:
    st.info("No chains found matching criteria.")

st.divider()

# ───────────────────────────────────────────────────────────
# 📈 Cumulative PnL: Filtered vs Baseline
# ───────────────────────────────────────────────────────────
st.markdown("<h2>📈 Cumulative PnL — Baseline vs Combined Filter</h2>", unsafe_allow_html=True)

trades_sorted = trades.sort_values("date").copy()
trades_sorted["cum_baseline"] = trades_sorted["pnl_pts"].cumsum()
trades_sorted["cum_combined"] = (trades_sorted["pnl_pts"] * trades_sorted["filter_both_keep"].astype(int)).cumsum()

fig_cum = go.Figure()
fig_cum.add_trace(go.Scatter(
    x=trades_sorted["date"], y=trades_sorted["cum_baseline"],
    mode="lines", line=dict(color=COLORS["danger"], width=1.5),
    name="Baseline (no filter)",
))
fig_cum.add_trace(go.Scatter(
    x=trades_sorted["date"], y=trades_sorted["cum_combined"],
    mode="lines", line=dict(color=COLORS["success"], width=1.5),
    name="Combined Filter (A+B)",
))
fig_cum.add_hline(y=0, line_color=COLORS["text_secondary"], line_dash="dash")
fig_cum.update_layout(**plotly_layout(
    height=420,
    yaxis_title="Cumulative PnL (pts)",
    title=dict(text="Cumulative PnL Over Time · 7,937 trades", font=dict(color=COLORS["text"], size=14)),
    hovermode="x unified",
))
st.plotly_chart(fig_cum, use_container_width=True)

st.divider()

# ───────────────────────────────────────────────────────────
# 📋 Recent filtered trades
# ───────────────────────────────────────────────────────────
st.markdown("<h2>📋 Recent 50 Trades — With Filter Decisions</h2>", unsafe_allow_html=True)
recent = trades.sort_values("date", ascending=False).head(50).copy()
display_cols = ["date", "session", "direction", "pnl_pts", "bias_score", "bias_label",
                "NY_prev", "Asia", "London", "filter_macro_keep", "filter_chain_keep", "filter_both_keep"]
recent_d = recent[display_cols].copy()
recent_d["date"] = recent_d["date"].dt.strftime("%Y-%m-%d")
recent_d.columns = ["Date", "Session", "Dir", "PnL", "Bias", "Label", "NY[t-1]", "Asia", "London",
                    "Keep Macro", "Keep Chain", "Keep Both"]
st.dataframe(recent_d, hide_index=True, use_container_width=True, height=400)

st.caption("`Keep` columns = True kalau filter menyimpan trade, False = filter skip. Run `python3 scripts/apply_filters_to_trades.py` untuk refresh.")
