"""Iteration Detail — drill into specific experiment."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from lib.data_loader import (
    load_master_registry,
    load_per_quarter,
    QUARTER_ORDER,
    get_session_color,
    get_verdict_badge,
    EXPERIMENT_TO_PERQ_FILE,
)
from lib.code_loader import CODE_FILES, read_code, get_lang_for_file
from lib.theme import apply_theme, COLORS, plotly_layout, metric_card

st.set_page_config(page_title="Detail · PT Box", page_icon="🔍", layout="wide")
apply_theme()

df = load_master_registry()

# --- Selector ---
real_iterations = df[~df["verdict"].isin(["ceiling_reference", "sanity_check"])]
default_id = st.query_params.get("id", real_iterations.loc[real_iterations["total_pnl"].idxmax(), "experiment_id"])
exp_options = df["experiment_id"].tolist()
default_idx = exp_options.index(default_id) if default_id in exp_options else len(exp_options) - 1

exp_id = st.selectbox(
    "Pick iteration",
    exp_options,
    index=default_idx,
    format_func=lambda x: f"{x} — {df[df['experiment_id']==x]['variant_label'].iloc[0]}",
)
row = df[df["experiment_id"] == exp_id].iloc[0]
emoji, color = get_verdict_badge(row["verdict"])
sign_color = COLORS["success"] if row["total_pnl"] > 0 else COLORS["danger"]

# --- Hero card ---
st.markdown(f"""
<div style="
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.06) 0%, rgba(15, 23, 42, 0.5) 60%);
    border: 1px solid {COLORS['border']};
    border-radius: 16px;
    padding: 1.75rem 2rem;
    margin-bottom: 1.5rem;
">
    <div style="display: flex; align-items: baseline; gap: 0.75rem; margin-bottom: 0.5rem;">
        <span style="font-size: 1.5rem;">{emoji}</span>
        <span style="
            font-family: 'JetBrains Mono', monospace;
            color: {COLORS['accent_blue']};
            font-size: 1rem;
            font-weight: 700;
        ">{exp_id}</span>
        <span style="color: {COLORS['text_muted']}; font-size: 0.85rem;">·</span>
        <span style="color: {COLORS['text_muted']}; font-size: 0.85rem;">{row['angle']}</span>
        <span style="color: {COLORS['text_muted']}; font-size: 0.85rem;">·</span>
        <span style="color: {COLORS['text_muted']}; font-size: 0.85rem;">{row['date_run']}</span>
    </div>
    <h1 style="font-size: 1.5rem; font-weight: 600; color: {COLORS['text']}; margin: 0 0 1rem 0; line-height: 1.3;">
        {row['variant_label']}
    </h1>
    <div style="display: flex; gap: 2rem; flex-wrap: wrap; align-items: baseline;">
        <div>
            <div style="color: {COLORS['text_secondary']}; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.08em;">Total PnL</div>
            <div style="font-size: 2.5rem; font-weight: 800; color: {sign_color}; letter-spacing: -0.03em; line-height: 1;">
                {row['total_pnl']:+.0f}<span style="font-size: 0.9rem; color: {COLORS['text_secondary']}; font-weight: 500;"> pts</span>
            </div>
            <div style="color: {COLORS['success'] if row['vs_baseline_delta'] > 0 else COLORS['danger']}; font-size: 0.85rem; font-weight: 500; margin-top: 0.25rem;">
                Δ {row['vs_baseline_delta']:+.0f} ({row['vs_baseline_pct']:+.1f}%) vs baseline
            </div>
        </div>
        <div>
            <div style="color: {COLORS['text_secondary']}; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.08em;">Avg WR</div>
            <div style="font-size: 1.75rem; font-weight: 700; color: {COLORS['text']}; letter-spacing: -0.02em;">
                {row['avg_winrate']:.1f}<span style="font-size: 0.85rem; color: {COLORS['text_secondary']}; font-weight: 500;">%</span>
            </div>
        </div>
        <div style="margin-left: auto;">
            <div style="
                padding: 6px 14px;
                border-radius: 999px;
                background: {color}1f;
                color: {color};
                font-weight: 600;
                font-size: 0.8rem;
                display: inline-block;
            ">{row['verdict']}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Per-session metric cards
c1, c2, c3 = st.columns(3)
session_data = [
    ("🟢 Asia", row['asia_pnl'], row['asia_pass_rate']),
    ("🔵 London", row['london_pnl'], row['london_pass_rate']),
    ("🟡 NY", row['ny_pnl'], row['ny_pass_rate']),
]
for col, (label, pnl, pass_rate) in zip([c1, c2, c3], session_data):
    with col:
        sc = COLORS["success"] if pnl > 0 else COLORS["danger"]
        metric_card(label, f"{pnl:+.0f} pts", sub=f"Pass rate · {pass_rate:.0f}%", color=sc)

if row["notes"]:
    st.info(f"💭 {row['notes']}")

st.divider()

# --- Per-quarter detail ---
perq = load_per_quarter(exp_id)
if perq is not None and len(perq) > 0:
    st.markdown("<h2>Per-Quarter Breakdown</h2>", unsafe_allow_html=True)
    pivot = perq.pivot_table(
        index="quarter",
        columns="session",
        values="val_pnl",
        aggfunc="sum",
    ).reindex(QUARTER_ORDER)

    # Equity curve (cumulative across quarters, summed over sessions)
    quarterly_total = pivot.sum(axis=1)
    cumulative = quarterly_total.cumsum()

    fig_eq = go.Figure()
    fig_eq.add_trace(go.Scatter(
        x=cumulative.index,
        y=cumulative.values,
        mode="lines+markers",
        line=dict(color=COLORS["accent_blue"], width=2.5),
        marker=dict(size=8, color=COLORS["accent_blue"], line=dict(width=2, color=COLORS["bg"])),
        fill="tozeroy",
        fillcolor="rgba(59, 130, 246, 0.08)",
        name="Cumulative",
        hovertemplate="<b>%{x}</b><br>Cumulative: %{y:+.0f}<extra></extra>",
    ))
    fig_eq.add_hline(y=0, line_color=COLORS["text_muted"], line_dash="dash")
    fig_eq.update_layout(**plotly_layout(
        height=320,
        title=dict(text="Equity Curve · Cumulative PnL", font=dict(color=COLORS["text"], size=14)),
    ))
    st.plotly_chart(fig_eq, use_container_width=True)

    # Per-Q stacked bar by session
    fig_stk = go.Figure()
    for sess in ["Asia", "London", "NY"]:
        if sess in pivot.columns:
            fig_stk.add_trace(go.Bar(
                x=pivot.index,
                y=pivot[sess].fillna(0),
                name=sess,
                marker_color=get_session_color(sess),
            ))
    fig_stk.update_layout(**plotly_layout(
        barmode="relative",
        height=360,
        title=dict(text="Per-Q PnL · stacked by session", font=dict(color=COLORS["text"], size=14)),
    ))
    st.plotly_chart(fig_stk, use_container_width=True)

    # Detail table
    st.markdown("<h3>Per-Q × Session Detail</h3>", unsafe_allow_html=True)
    display_cols = ["quarter", "session", "session_model", "train_time", "train_dur",
                    "val_pnl", "val_wr", "val_trades", "val_max_dd", "pass"]
    available_cols = [c for c in display_cols if c in perq.columns]
    perq_display = perq[available_cols].copy()
    if "quarter" in perq_display.columns:
        perq_display["quarter"] = pd.Categorical(
            perq_display["quarter"], categories=QUARTER_ORDER, ordered=True
        )
        perq_display = perq_display.sort_values(["quarter", "session"])
    st.dataframe(perq_display, hide_index=True, use_container_width=True)
else:
    st.warning("⚠️ Per-quarter detail not available for this iteration (ceiling reference / sanity check).")

st.divider()

# --- Config + Code panels ---
col_cfg, col_code = st.columns([1, 2])

with col_cfg:
    st.markdown("<h2>⚙️ Config</h2>", unsafe_allow_html=True)
    config = row.get("config", {})
    if config:
        st.json(config)
    else:
        st.caption("No config available")
    st.caption(f"📂 Source: `{EXPERIMENT_TO_PERQ_FILE.get(exp_id, 'N/A')}`")

with col_code:
    st.markdown("<h2>💻 Code Reference</h2>", unsafe_allow_html=True)
    # Map angle → likely engine version
    engine_hint = {
        "Phase 4 #1": "v3 (Phase 4)",
        "Phase 4 #1 ceiling": "v3 (Phase 4)",
        "Phase 4 #2": "v3 (Phase 4)",
        "Phase 5 #A2": "v4 (Phase 5 #A)",
        "Phase 5 #B0": "v5 (Phase 5 #B) ⭐",
    }.get(row["angle"], "v5 (Phase 5 #B) ⭐")

    st.markdown(f"**Likely engine version:** `{engine_hint}`")
    py_path = CODE_FILES["Python"].get(engine_hint)
    if py_path and py_path.exists():
        with st.expander(f"View {py_path.name}", expanded=False):
            code = read_code(py_path)
            st.code(code, language="python", line_numbers=True)

# Pinescripts always available
st.divider()
st.markdown("<h2>📜 Pinescripts (TradingView)</h2>", unsafe_allow_html=True)
ps_tabs = st.tabs(["🟢 Asia", "🔵 London", "🟡 NY", "📋 Index"])
for tab, key in zip(ps_tabs, ["Asia", "London", "NY", "Index"]):
    with tab:
        path = CODE_FILES["Pinescript"][key]
        if path.exists():
            st.caption(f"📂 `{path.relative_to(Path.home())}`")
            st.markdown(read_code(path))
        else:
            st.warning(f"File not found: {path}")
