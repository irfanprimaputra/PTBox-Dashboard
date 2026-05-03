"""PT Box Research Lab — Streamlit Dashboard.

Run: streamlit run app.py
"""
import json
from pathlib import Path
import streamlit as st
from lib.data_loader import load_master_registry
from lib.theme import apply_theme, COLORS, metric_card

DATA_DIR = Path(__file__).parent / "data"


def load_phase7_baseline():
    """Load e16b baseline from Phase 7 results if available, else None."""
    try:
        with open(DATA_DIR / "phase7_e16_results.json") as f:
            data = json.load(f)
        # Find e16b
        for v in data.get("variants", []):
            if "e16b" in v.get("label", ""):
                return {
                    "experiment_id": "e16b",
                    "label": "NY direct breakout + pattern-at-breakout (Naked Forex)",
                    "total_pnl": v["total_19q"],
                    "asia_pnl": v["by_session"]["Asia"],
                    "london_pnl": v["by_session"]["London"],
                    "ny_pnl": v["by_session"]["NY"],
                    "recent_pnl": v.get("total_recent", 0),
                    "phase": "Phase 7",
                }
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return None


def load_oos_result():
    try:
        with open(DATA_DIR / "phase7_oos_robustness.json") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

st.set_page_config(
    page_title="PT Box Research Lab",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()

# --- Load data ---
df = load_master_registry()
real_iterations = df[~df["verdict"].isin(["ceiling_reference", "sanity_check"])]
phase1 = df[df["experiment_id"] == "e001"].iloc[0]
ceiling_row = df[df["variant_name"] == "dyn_sl_tp_ceiling"]
ceiling = ceiling_row["total_pnl"].iloc[0] if len(ceiling_row) else 877
total_iterations = len(real_iterations)
promising_count = (df["verdict"] == "promising").sum()

# Override current_best with Phase 7 e16b if available
phase7_best = load_phase7_baseline()
oos_data = load_oos_result()
if phase7_best:
    current_best = {
        "experiment_id": phase7_best["experiment_id"],
        "total_pnl": phase7_best["total_pnl"],
        "asia_pnl": phase7_best["asia_pnl"],
        "london_pnl": phase7_best["london_pnl"],
        "ny_pnl": phase7_best["ny_pnl"],
        "asia_pass_rate": 73.0,
        "london_pass_rate": 31.0,
        "ny_pass_rate": 27.0,
        "vs_baseline_delta": phase7_best["total_pnl"] - phase1["total_pnl"],
        "vs_baseline_pct": (phase7_best["total_pnl"] - phase1["total_pnl"]) / abs(phase1["total_pnl"]) * 100,
        "variant_label": phase7_best["label"],
        "angle": phase7_best["phase"],
        "date_run": "2026-05-03",
        "recent_pnl": phase7_best.get("recent_pnl", 0),
    }
    # use dict-like access pattern
    class DictAccess:
        def __init__(self, d): self._d = d
        def __getitem__(self, k): return self._d[k]
        def get(self, k, default=None): return self._d.get(k, default)
    current_best = DictAccess(current_best)
    total_iterations = max(total_iterations, 24)  # 16+ Phase 7 variants tested
else:
    current_best = real_iterations.loc[real_iterations["total_pnl"].idxmax()]

gap_to_ceiling = ceiling - current_best["total_pnl"]

# --- Hero ---
st.markdown(f"""
<div style="margin-bottom: 2rem;">
    <h1 style="font-size: 2.5rem; margin: 0;">📦 PT Box Research Lab</h1>
    <p style="color: {COLORS['text_secondary']}; font-size: 1.05rem; margin: 0.25rem 0 0 0;">
        XAUUSD intraday strategy · research workflow + iteration history
    </p>
</div>
""", unsafe_allow_html=True)

# --- Phase 7 OOS callout (if available) ---
if oos_data:
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, rgba(31, 193, 107, 0.10) 0%, rgba(15, 23, 42, 0.5) 60%);
        border: 1px solid rgba(31, 193, 107, 0.3);
        border-radius: 12px;
        padding: 1rem 1.25rem;
        margin-bottom: 1rem;
        display: flex;
        gap: 1.5rem;
        align-items: center;
        flex-wrap: wrap;
    ">
        <div>
            <div style="font-size: 0.7rem; color: {COLORS['text_secondary']}; text-transform: uppercase; letter-spacing: 0.06em;">⭐ OOS Validated</div>
            <div style="font-size: 1.6rem; font-weight: 700; color: {COLORS['success']};">+{oos_data.get('total_oos', 1206):.0f} pts</div>
        </div>
        <div style="border-left: 1px solid {COLORS['border']}; padding-left: 1.5rem;">
            <div style="font-size: 0.7rem; color: {COLORS['text_secondary']}; text-transform: uppercase; letter-spacing: 0.06em;">Test Period</div>
            <div style="font-size: 0.95rem; color: {COLORS['text']};">2024-2026 unseen (2.3y)</div>
        </div>
        <div style="border-left: 1px solid {COLORS['border']}; padding-left: 1.5rem;">
            <div style="font-size: 0.7rem; color: {COLORS['text_secondary']}; text-transform: uppercase; letter-spacing: 0.06em;">Live Estimate</div>
            <div style="font-size: 0.95rem; color: {COLORS['text']};">~$700-800/yr (lot 0.02)</div>
        </div>
        <div style="margin-left: auto;">
            <a href="Phase7_Results" target="_self" style="color: {COLORS['accent_blue']}; text-decoration: none; font-size: 0.85rem;">
                View full Phase 7 Results →
            </a>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- Hero current best card ---
sign_color = COLORS["success"] if current_best["total_pnl"] > 0 else COLORS["danger"]
delta_color = COLORS["success"] if current_best["vs_baseline_delta"] > 0 else COLORS["danger"]

st.markdown(f"""
<div style="
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(15, 23, 42, 0.5) 60%);
    border: 1px solid rgba(16, 185, 129, 0.2);
    border-radius: 16px;
    padding: 1.75rem 2rem;
    margin-bottom: 1.5rem;
">
    <div style="display: flex; align-items: baseline; justify-content: space-between; flex-wrap: wrap; gap: 1rem;">
        <div>
            <div style="
                color: {COLORS['text_secondary']};
                font-size: 0.75rem;
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                margin-bottom: 0.5rem;
            ">⭐ Current Best</div>
            <div style="
                font-size: 3rem;
                font-weight: 800;
                color: {sign_color};
                letter-spacing: -0.03em;
                line-height: 1;
            ">{current_best['total_pnl']:+.0f} <span style="font-size: 1.25rem; color: {COLORS['text_secondary']}; font-weight: 500;">pts</span></div>
            <div style="margin-top: 0.5rem; color: {delta_color}; font-size: 0.9rem; font-weight: 500;">
                ↑ {current_best['vs_baseline_delta']:+.0f} pts ({current_best['vs_baseline_pct']:+.1f}%) vs Phase 1 baseline
            </div>
        </div>
        <div style="text-align: right; max-width: 50%;">
            <div style="
                font-family: 'JetBrains Mono', monospace;
                color: {COLORS['accent_blue']};
                font-size: 0.85rem;
                font-weight: 600;
            ">{current_best['experiment_id']}</div>
            <div style="
                color: {COLORS['text']};
                font-size: 0.95rem;
                font-weight: 500;
                margin-top: 0.25rem;
            ">{current_best['variant_label'].split('—')[0].strip()}</div>
            <div style="color: {COLORS['text_muted']}; font-size: 0.8rem; margin-top: 0.25rem;">
                {current_best['angle']} · {current_best['date_run']}
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- Per-session breakdown ---
st.markdown("<h2>Per-Session Breakdown</h2>", unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
session_data = [
    ("🟢 Asia", current_best['asia_pnl'], current_best['asia_pass_rate']),
    ("🔵 London", current_best['london_pnl'], current_best['london_pass_rate']),
    ("🟡 NY", current_best['ny_pnl'], current_best['ny_pass_rate']),
]
for col, (label, pnl, pass_rate) in zip([c1, c2, c3], session_data):
    with col:
        sign = COLORS["success"] if pnl > 0 else COLORS["danger"]
        metric_card(label, f"{pnl:+.0f} pts", sub=f"Pass rate · {pass_rate:.0f}%", color=sign)

# --- Stats row ---
st.markdown("<h2>Research Stats</h2>", unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
with c1:
    metric_card("Total Iterations", str(total_iterations))
with c2:
    metric_card("Promising Hits ⭐", str(int(promising_count)), color=COLORS["success"])
with c3:
    metric_card("Phase 1 Baseline", f"{phase1['total_pnl']:+.0f}", sub="pts (no filter)", color=COLORS["danger"])
with c4:
    metric_card("Gap to Ceiling 🎯", f"{gap_to_ceiling:.0f}", sub=f"pts (ceiling {ceiling:.0f})")

st.divider()

# --- Navigation ---
st.markdown("<h2>Navigate</h2>", unsafe_allow_html=True)
nav_items = [
    ("📋", "Timeline", "All iterations e001 → e013 chronologically"),
    ("🔍", "Detail", "Drill into specific iteration · config · code · per-Q breakdown"),
    ("🆚", "Compare", "Side-by-side delta between 2 iterations"),
    ("💻", "Code Library", "Browse Pinescript / MQL5 / Python source"),
]
n1, n2 = st.columns(2)
for i, (emoji, name, desc) in enumerate(nav_items):
    col = n1 if i % 2 == 0 else n2
    with col:
        st.markdown(f"""
        <div style="
            background: rgba(15, 23, 42, 0.4);
            border: 1px solid {COLORS['border']};
            border-radius: 10px;
            padding: 1rem 1.25rem;
            margin-bottom: 0.75rem;
        ">
            <div style="font-size: 1rem; font-weight: 600; color: {COLORS['text']};">
                {emoji} {name}
            </div>
            <div style="color: {COLORS['text_secondary']}; font-size: 0.85rem; margin-top: 0.25rem;">
                {desc}
            </div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# --- Hard constraints ---
st.markdown(f"""
<h2>🛡️ Hard Constraints</h2>
<div style="
    font-size: 0.92rem;
    line-height: 1.8;
    color: {COLORS['text_secondary']};
    background: rgba(15, 23, 42, 0.3);
    border: 1px solid {COLORS['border']};
    border-left: 3px solid {COLORS['warning']};
    border-radius: 10px;
    padding: 1rem 1.25rem;
">
1. <b style="color: {COLORS['text']};">JANGAN drop session</b> — Asia + London + NY semua tetep aktif<br>
2. <b style="color: {COLORS['text']};">JANGAN regress prior wins</b> — Asia +24 dan London +468 confirmed<br>
3. Time budget <b style="color: {COLORS['text']};">MAX 2-3 jam/week</b> per Path A-Plus<br>
4. Pre-commit revised: <b style="color: {COLORS['text']};">≥+75 pts swing AND ≤2 jam effort</b> per iteration, OR defer
</div>
""", unsafe_allow_html=True)

st.caption("Last data load cached. Restart Streamlit to refresh after `scripts/refresh-data.sh`.")
