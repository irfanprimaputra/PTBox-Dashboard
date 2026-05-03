"""Compare two iterations side-by-side."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from lib.data_loader import (
    load_master_registry,
    load_per_quarter,
    QUARTER_ORDER,
    get_session_color,
    get_verdict_badge,
)
from lib.theme import apply_theme, COLORS, plotly_layout

st.set_page_config(page_title="Compare · PT Box", page_icon="🆚", layout="wide")
apply_theme()

st.markdown(f"""
<div style="margin-bottom: 1.5rem;">
    <h1 style="font-size: 2rem; margin: 0;">🆚 Compare Iterations</h1>
    <p style="color: {COLORS['text_secondary']}; margin: 0.25rem 0 0 0;">
        Side-by-side delta · pick 2 experiments
    </p>
</div>
""", unsafe_allow_html=True)

df = load_master_registry()
exp_options = df["experiment_id"].tolist()

# Default: latest 2 promising
promising = df[df["verdict"] == "promising"].sort_values("experiment_id")
default_a = st.query_params.get("a", promising["experiment_id"].iloc[-2] if len(promising) >= 2 else exp_options[0])
default_b = st.query_params.get("b", promising["experiment_id"].iloc[-1] if len(promising) >= 1 else exp_options[-1])

c1, c2 = st.columns(2)
with c1:
    id_a = st.selectbox(
        "Iteration A (baseline)",
        exp_options,
        index=exp_options.index(default_a) if default_a in exp_options else 0,
        format_func=lambda x: f"{x} — {df[df['experiment_id']==x]['variant_label'].iloc[0]}",
        key="sel_a",
    )
with c2:
    id_b = st.selectbox(
        "Iteration B (compare to)",
        exp_options,
        index=exp_options.index(default_b) if default_b in exp_options else len(exp_options) - 1,
        format_func=lambda x: f"{x} — {df[df['experiment_id']==x]['variant_label'].iloc[0]}",
        key="sel_b",
    )

row_a = df[df["experiment_id"] == id_a].iloc[0]
row_b = df[df["experiment_id"] == id_b].iloc[0]

st.divider()

# --- Headline diff ---
st.markdown("<h2>Delta Summary</h2>", unsafe_allow_html=True)
diff_total = row_b["total_pnl"] - row_a["total_pnl"]
diff_asia = row_b["asia_pnl"] - row_a["asia_pnl"]
diff_london = row_b["london_pnl"] - row_a["london_pnl"]
diff_ny = row_b["ny_pnl"] - row_a["ny_pnl"]

def delta_card(label, value, sub=None):
    color = COLORS["success"] if value > 0 else (COLORS["danger"] if value < 0 else COLORS["text_muted"])
    muted = COLORS["text_muted"]
    sub_html = f"<div style='color: {muted}; font-size: 0.78rem; margin-top: 4px;'>{sub}</div>" if sub else ""
    arrow = "↑" if value > 0 else ("↓" if value < 0 else "·")
    return f"""
    <div style="
        background: linear-gradient(180deg, rgba(30, 41, 59, 0.4) 0%, rgba(15, 23, 42, 0.4) 100%);
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
        padding: 1rem 1.25rem;
    ">
        <div style="color: {COLORS['text_secondary']}; font-size: 0.72rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em;">{label}</div>
        <div style="font-size: 1.875rem; font-weight: 700; color: {color}; letter-spacing: -0.02em; margin-top: 4px; line-height: 1;">
            {arrow} {value:+.0f}
        </div>
        {sub_html}
    </div>
    """

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(delta_card("Total PnL Δ", diff_total, f"vs {row_a['total_pnl']:+.0f} → {row_b['total_pnl']:+.0f}"), unsafe_allow_html=True)
with col2:
    st.markdown(delta_card("🟢 Asia Δ", diff_asia), unsafe_allow_html=True)
with col3:
    st.markdown(delta_card("🔵 London Δ", diff_london), unsafe_allow_html=True)
with col4:
    st.markdown(delta_card("🟡 NY Δ", diff_ny), unsafe_allow_html=True)

# --- Side-by-side cards ---
st.markdown("<br>", unsafe_allow_html=True)
col_a, col_b = st.columns(2)
for col, row, label, accent in [(col_a, row_a, "A", COLORS["text_muted"]), (col_b, row_b, "B", COLORS["accent_blue"])]:
    with col:
        emoji, color = get_verdict_badge(row["verdict"])
        sign = COLORS["success"] if row["total_pnl"] > 0 else COLORS["danger"]
        st.markdown(f"""
        <div style="
            background: rgba(15, 23, 42, 0.4);
            border: 1px solid {accent}33;
            border-left: 3px solid {accent};
            border-radius: 12px;
            padding: 1.25rem 1.5rem;
            min-height: 200px;
        ">
            <div style="display: flex; align-items: baseline; gap: 0.5rem; margin-bottom: 0.5rem;">
                <span style="font-size: 1.05rem; font-weight: 700; color: {accent};">{label}</span>
                <span style="font-size: 1rem;">{emoji}</span>
                <span style="font-family: 'JetBrains Mono', monospace; color: {COLORS['accent_blue']}; font-weight: 600;">{row['experiment_id']}</span>
            </div>
            <div style="color: {COLORS['text']}; font-size: 0.95rem; font-weight: 500; line-height: 1.4; margin-bottom: 0.75rem;">
                {row['variant_label']}
            </div>
            <div style="color: {COLORS['text_muted']}; font-size: 0.78rem; margin-bottom: 1rem;">
                {row['angle']}
            </div>
            <div style="font-size: 2rem; font-weight: 800; color: {sign}; letter-spacing: -0.02em; line-height: 1;">
                {row['total_pnl']:+.0f}<span style="font-size: 0.85rem; color: {COLORS['text_secondary']}; font-weight: 500;"> pts</span>
            </div>
            <div style="display: flex; gap: 1rem; margin-top: 0.75rem; font-size: 0.82rem; color: {COLORS['text_secondary']};">
                <div>🟢 <b style="color: {COLORS['text']};">{row['asia_pnl']:+.0f}</b></div>
                <div>🔵 <b style="color: {COLORS['text']};">{row['london_pnl']:+.0f}</b></div>
                <div>🟡 <b style="color: {COLORS['text']};">{row['ny_pnl']:+.0f}</b></div>
            </div>
            {f'<div style="color: {COLORS["text_muted"]}; font-size: 0.8rem; font-style: italic; margin-top: 0.75rem; border-top: 1px solid {COLORS["border"]}; padding-top: 0.5rem;">💭 {row["notes"]}</div>' if row.get("notes") else ""}
        </div>
        """, unsafe_allow_html=True)

st.divider()

# --- Equity curve overlay ---
st.markdown("<h2>Equity Curve Overlay</h2>", unsafe_allow_html=True)

perq_a = load_per_quarter(id_a)
perq_b = load_per_quarter(id_b)

if perq_a is not None and perq_b is not None:
    def to_cumulative(perq):
        pivot = perq.pivot_table(
            index="quarter", columns="session", values="val_pnl", aggfunc="sum"
        ).reindex(QUARTER_ORDER)
        return pivot.sum(axis=1).fillna(0).cumsum()

    cum_a = to_cumulative(perq_a)
    cum_b = to_cumulative(perq_b)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=cum_a.index, y=cum_a.values,
        mode="lines+markers", name=f"A · {id_a}",
        line=dict(color=COLORS["text_muted"], width=2, dash="dash"),
        marker=dict(size=7),
    ))
    fig.add_trace(go.Scatter(
        x=cum_b.index, y=cum_b.values,
        mode="lines+markers", name=f"B · {id_b}",
        line=dict(color=COLORS["accent_blue"], width=2.5),
        marker=dict(size=8, line=dict(width=2, color=COLORS["bg"])),
        fill="tonexty",
        fillcolor="rgba(59, 130, 246, 0.06)",
    ))
    fig.add_hline(y=0, line_color=COLORS["text_muted"], line_dash="dot")
    fig.update_layout(**plotly_layout(
        height=420,
        yaxis_title="Cumulative PnL (pts)",
        hovermode="x unified",
    ))
    st.plotly_chart(fig, use_container_width=True)

    # Per-Q delta table
    st.markdown("<h3>Per-Quarter Delta</h3>", unsafe_allow_html=True)
    quarterly_a = perq_a.pivot_table(
        index="quarter", columns="session", values="val_pnl", aggfunc="sum"
    ).reindex(QUARTER_ORDER).sum(axis=1)
    quarterly_b = perq_b.pivot_table(
        index="quarter", columns="session", values="val_pnl", aggfunc="sum"
    ).reindex(QUARTER_ORDER).sum(axis=1)
    delta_df = pd.DataFrame({
        "Quarter": QUARTER_ORDER,
        f"A: {id_a}": quarterly_a.values,
        f"B: {id_b}": quarterly_b.values,
        "Δ (B-A)": (quarterly_b - quarterly_a).values,
    })
    st.dataframe(
        delta_df.style.format({
            f"A: {id_a}": "{:+.1f}",
            f"B: {id_b}": "{:+.1f}",
            "Δ (B-A)": "{:+.1f}",
        }).background_gradient(subset=["Δ (B-A)"], cmap="RdYlGn", vmin=-100, vmax=100),
        hide_index=True, use_container_width=True,
    )
else:
    st.warning("Per-Q detail not available for one or both iterations.")

st.divider()

# --- Config diff ---
st.markdown("<h2>⚙️ Config Diff</h2>", unsafe_allow_html=True)
col_a, col_b = st.columns(2)
with col_a:
    st.markdown(f"**A · `{id_a}`**")
    st.json(row_a.get("config", {}))
with col_b:
    st.markdown(f"**B · `{id_b}`**")
    st.json(row_b.get("config", {}))
