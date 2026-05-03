"""Data loading + caching layer untuk PT Box Dashboard."""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
import streamlit as st

DASHBOARD_ROOT = Path(__file__).parent.parent
DATA_DIR = DASHBOARD_ROOT / "data"
CODE_DIR = DASHBOARD_ROOT / "code"
VAULT_PT_BOX = Path.home() / "Documents/Obsidian/Irfan-Vault/03-Trading/01-Forex/Strategies/PT-Box"

# Mapping experiment_id → per-quarter result file
EXPERIMENT_TO_PERQ_FILE = {
    "e001": "ptbox_phase4_box_quality_results.csv",
    "e002": "ptbox_phase4_box_quality_results.csv",
    "e003": "ptbox_phase4_box_quality_results.csv",
    "e004": "ptbox_phase4_box_quality_results.csv",
    "e005": None,  # ceiling, JSON only
    "e006": None,  # ceiling, JSON only
    "e007": "ptbox_phase4_pattern_results.csv",
    "e008": "ptbox_phase4_pattern_results.csv",
    "e009": "ptbox_phase4_pattern_results.csv",
    "e010": "ptbox_phase4_pattern_results.csv",
    "e011": "ptbox_phase5_asia_meanrev_results.csv",
    "e012": "ptbox_phase5_asia_meanrev_results.csv",
    "e013": "ptbox_phase5b_results.csv",
}

# Mapping experiment_id → variant name (untuk filter per-Q file)
EXPERIMENT_TO_VARIANT = {
    "e001": "control",
    "e002": "dyn_sl_0.5",
    "e003": "dyn_sl_1.0",
    "e004": "dyn_sl_tp",
    "e007": "dyn_sl_tp_baseline",
    "e008": "pin_bar_only",
    "e009": "engulfing_only",
    "e010": "any_pattern",
    "e011": "phase5_sanity_any_pattern",
    "e012": "asia_a2_fail",
    "e013": "b0_ny_no_pattern",
}


@st.cache_data
def load_master_registry() -> pd.DataFrame:
    """Load master experiment registry (e001-e013)."""
    path = DATA_DIR / "ptbox_phase4_experiments.csv"
    df = pd.read_csv(path)
    # Parse config_json into dict column (handles malformed gracefully)
    def safe_parse(s):
        try:
            return json.loads(s) if isinstance(s, str) else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    df["config"] = df["config_json"].apply(safe_parse)
    return df


@st.cache_data
def load_per_quarter(experiment_id: str) -> pd.DataFrame | None:
    """Load per-quarter result data for a specific experiment."""
    file = EXPERIMENT_TO_PERQ_FILE.get(experiment_id)
    if file is None:
        return None
    path = DATA_DIR / file
    if not path.exists():
        return None
    df = pd.read_csv(path)
    variant = EXPERIMENT_TO_VARIANT.get(experiment_id)
    if variant and "phase5_variant" in df.columns:
        df = df[df["phase5_variant"] == variant]
    elif variant and "variant" in df.columns:
        df = df[df["variant"] == variant]
    return df.reset_index(drop=True)


@st.cache_data
def load_walkforward_baseline() -> pd.DataFrame:
    """Phase 1 baseline 19Q walk-forward."""
    path = DATA_DIR / "ptbox_walkforward_extended.csv"
    return pd.read_csv(path)


@st.cache_data
def load_trades() -> pd.DataFrame:
    """Per-trade log dari engine v6 (2015-2026 fixed deploy config).

    Columns: date, session, model, direction, entry_time, exit_time,
             entry_price, exit_price, sl_price, tp1_price, tp2_price,
             box_width, sl_distance, hit_type, pnl_pts, attempt,
             day_of_week, week, month, quarter, year
    """
    path = DATA_DIR / "ptbox_v6_trades.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    df['date'] = pd.to_datetime(df['date'])
    return df


# Day-of-week ordering
DOW_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Sunday"]


# Quarter ordering for charts
QUARTER_ORDER = [
    "Q3 2021", "Q4 2021",
    "Q1 2022", "Q2 2022", "Q3 2022", "Q4 2022",
    "Q1 2023", "Q2 2023", "Q3 2023", "Q4 2023",
    "Q1 2024", "Q2 2024", "Q3 2024", "Q4 2024",
    "Q1 2025", "Q2 2025", "Q3 2025", "Q4 2025",
    "Q1 2026",
]


def get_session_color(session: str) -> str:
    """Consistent color per session across charts."""
    return {
        "Asia": "#22c55e",      # green
        "London": "#3b82f6",    # blue
        "NY": "#f59e0b",        # amber
    }.get(session, "#888")


def get_verdict_badge(verdict: str) -> tuple[str, str]:
    """(emoji, color) tuple per verdict."""
    return {
        "baseline": ("⚪", "#888"),
        "no_change": ("⚪", "#888"),
        "marginal_improve": ("🟡", "#eab308"),
        "promising": ("⭐", "#22c55e"),
        "reject_worse": ("❌", "#ef4444"),
        "ceiling_reference": ("🎯", "#a855f7"),
        "sanity_check": ("✓", "#3b82f6"),
    }.get(verdict, ("•", "#888"))
