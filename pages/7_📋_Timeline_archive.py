"""Timeline view — all iterations chronologically."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import plotly.graph_objects as go
from lib.data_loader import load_master_registry, get_verdict_badge
from lib.theme import apply_theme, COLORS, plotly_layout

st.set_page_config(page_title="Timeline · PT Box", page_icon="📋", layout="wide")
apply_theme()

st.markdown(f"""
<div style="margin-bottom: 1.5rem;">
    <h1 style="font-size: 2rem; margin: 0;">📋 Iteration Timeline</h1>
    <p style="color: {COLORS['text_secondary']}; margin: 0.25rem 0 0 0;">
        Chronological journey e001 → e013 across Phase 4 + Phase 5
    </p>
</div>
""", unsafe_allow_html=True)

df = load_master_registry()

# --- Filter sidebar ---
with st.sidebar:
    st.subheader("🔎 Filter")
    angles = sorted(df["angle"].unique())
    selected_angles = st.multiselect("Angle/Phase", angles, default=angles)
    verdicts = sorted(df["verdict"].unique())
    selected_verdicts = st.multiselect("Verdict", verdicts, default=verdicts)
    show_sanity = st.checkbox("Show sanity_check rows", value=False)

filtered = df[
    df["angle"].isin(selected_angles) &
    df["verdict"].isin(selected_verdicts)
].copy()
if not show_sanity:
    filtered = filtered[filtered["verdict"] != "sanity_check"]

# --- Cumulative progression chart ---
st.markdown("<h2>PnL Progression</h2>", unsafe_allow_html=True)
non_ref = filtered[~filtered["verdict"].isin(["ceiling_reference", "sanity_check"])].copy()
non_ref = non_ref.sort_values("experiment_id")

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=non_ref["experiment_id"],
    y=non_ref["total_pnl"],
    mode="lines+markers+text",
    text=non_ref["total_pnl"].round(0).astype(int).astype(str),
    textposition="top center",
    textfont=dict(size=11, color=COLORS["text_secondary"]),
    line=dict(color=COLORS["accent_blue"], width=2.5),
    marker=dict(
        size=14,
        color=non_ref["total_pnl"],
        colorscale=[[0, COLORS["danger"]], [0.5, COLORS["warning"]], [1, COLORS["success"]]],
        showscale=False,
        line=dict(width=2, color=COLORS["bg"]),
    ),
    hovertemplate="<b>%{x}</b><br>PnL: %{y:+.0f} pts<br>%{customdata}<extra></extra>",
    customdata=non_ref["variant_label"],
))
fig.add_hline(y=0, line_dash="dash", line_color=COLORS["text_muted"], annotation_text="Break-even", annotation_font_color=COLORS["text_muted"])
ceiling_row = df[df["variant_name"] == "dyn_sl_tp_ceiling"]
if len(ceiling_row):
    fig.add_hline(
        y=ceiling_row["total_pnl"].iloc[0],
        line_dash="dot",
        line_color="#a855f7",
        annotation_text="🎯 In-sample ceiling",
        annotation_font_color="#a855f7",
    )
fig.update_layout(**plotly_layout(
    height=420,
    xaxis_title="Experiment ID",
    yaxis_title="Total PnL (pts)",
    hovermode="x unified",
))
st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- Iteration cards ---
st.markdown("<h2>Iterations</h2>", unsafe_allow_html=True)
for _, row in filtered.iterrows():
    emoji, color = get_verdict_badge(row["verdict"])
    delta_pct = row["vs_baseline_pct"]
    delta_pts = row["vs_baseline_delta"]
    sign_color = COLORS["success"] if row["total_pnl"] > 0 else COLORS["danger"]
    delta_color = COLORS["success"] if delta_pts > 0 else (COLORS["danger"] if delta_pts < 0 else COLORS["text_muted"])

    notes_html = f'<div style="color: {COLORS["text_muted"]}; font-size: 0.82rem; font-style: italic; margin-top: 0.5rem;">💭 {row["notes"]}</div>' if row["notes"] else ""
    delta_html = f'<div style="color: {delta_color}; font-size: 0.82rem; font-weight: 500;">Δ {delta_pts:+.0f} ({delta_pct:+.1f}%) vs baseline</div>' if delta_pts != 0 else ""

    card_html = (
        f'<div style="background: rgba(15, 23, 42, 0.4); border: 1px solid {COLORS["border"]}; '
        f'border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 0.75rem; backdrop-filter: blur(8px);">'
        f'<div style="display: grid; grid-template-columns: 100px 1fr auto auto; gap: 1.25rem; align-items: center;">'
        f'<div>'
        f'<div style="font-size: 1.5rem; line-height: 1;">{emoji}</div>'
        f'<div style="font-family: \'JetBrains Mono\', monospace; color: {COLORS["accent_blue"]}; '
        f'font-size: 0.9rem; font-weight: 600; margin-top: 4px;">{row["experiment_id"]}</div>'
        f'<div style="color: {COLORS["text_muted"]}; font-size: 0.72rem; margin-top: 2px;">{row["date_run"]}</div>'
        f'</div>'
        f'<div>'
        f'<div style="color: {COLORS["text"]}; font-size: 0.95rem; font-weight: 500;">{row["variant_label"]}</div>'
        f'<div style="color: {COLORS["text_muted"]}; font-size: 0.78rem; margin-top: 4px;">'
        f'{row["angle"]} · <code style="color: {COLORS["text_secondary"]};">{row["variant_name"]}</code>'
        f'</div>'
        f'</div>'
        f'<div style="text-align: right;">'
        f'<div style="font-size: 1.6rem; font-weight: 700; color: {sign_color}; letter-spacing: -0.02em;">'
        f'{row["total_pnl"]:+.0f}<span style="font-size: 0.85rem; color: {COLORS["text_secondary"]}; font-weight: 500;"> pts</span>'
        f'</div>'
        f'{delta_html}'
        f'</div>'
        f'<div style="padding: 5px 12px; border-radius: 999px; background: {color}1f; color: {color}; '
        f'display: inline-block; font-weight: 600; font-size: 0.75rem; white-space: nowrap;">{row["verdict"]}</div>'
        f'</div>'
        f'<div style="display: flex; gap: 1.5rem; margin-top: 0.75rem; padding-top: 0.75rem; '
        f'border-top: 1px solid {COLORS["border"]}; font-size: 0.82rem; color: {COLORS["text_secondary"]};">'
        f'<div>🟢 Asia: <b style="color: {COLORS["text"]};">{row["asia_pnl"]:+.0f}</b> · {row["asia_pass_rate"]:.0f}%</div>'
        f'<div>🔵 London: <b style="color: {COLORS["text"]};">{row["london_pnl"]:+.0f}</b> · {row["london_pass_rate"]:.0f}%</div>'
        f'<div>🟡 NY: <b style="color: {COLORS["text"]};">{row["ny_pnl"]:+.0f}</b> · {row["ny_pass_rate"]:.0f}%</div>'
        f'<div style="margin-left: auto;">'
        f'<a href="Detail?id={row["experiment_id"]}" target="_self" style="color: {COLORS["accent_blue"]}; text-decoration: none;">Detail →</a>'
        f'<span style="margin: 0 0.5rem; color: {COLORS["border"]};">|</span>'
        f'<a href="Compare?a={row["experiment_id"]}" target="_self" style="color: {COLORS["accent_blue"]}; text-decoration: none;">Compare</a>'
        f'</div>'
        f'</div>'
        f'{notes_html}'
        f'</div>'
    )
    st.html(card_html)

st.caption(f"Showing {len(filtered)} iterations.")
