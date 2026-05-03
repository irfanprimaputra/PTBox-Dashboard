"""Custom theme — AlignUI Apex Finance design tokens ported to Streamlit.

Source: ~/Downloads/template-finance-master (Next.js + Tailwind)
Adapted to CSS variables for Streamlit injection.
"""
import streamlit as st


# ═══════════════════════════════════════════════════════════════
# 🎨 COLOR PALETTE (AlignUI HSL tokens)
# ═══════════════════════════════════════════════════════════════
# Direct hex values (computed from HSL) for use in Plotly + inline CSS.

# Neutral scale
NEUTRAL = {
    "0":   "#FFFFFF",
    "50":  "#F5F7FA",
    "100": "#F2F5F8",
    "200": "#E1E4EA",
    "300": "#CACFD8",
    "400": "#99A0AE",
    "500": "#717784",
    "600": "#525866",
    "700": "#2B303B",
    "800": "#222530",
    "900": "#181B25",
    "950": "#0E121B",
}

# Blue (primary)
BLUE = {
    "50":  "#EBF1FF",
    "100": "#D5E2FF",
    "200": "#C0D5FF",
    "300": "#97B6FF",
    "400": "#6895FF",
    "500": "#335CFF",
    "600": "#3559E9",
    "700": "#2547D0",
    "800": "#1F3BAD",
    "900": "#182F8B",
    "950": "#162456",
}

GREEN = {
    "50":  "#E0FAEC",
    "100": "#D0FBE9",
    "200": "#C2F5DA",
    "300": "#84EBB4",
    "400": "#3EE089",
    "500": "#1FC16B",
    "600": "#1DAF61",
    "700": "#178C4E",
    "800": "#1A7544",
    "900": "#16643B",
    "950": "#0B4627",
}

ORANGE = {
    "50":  "#FFEFEB",
    "100": "#FFDED5",
    "200": "#FFCAB8",
    "300": "#FFA37B",
    "400": "#FF7847",
    "500": "#FB4710",
    "600": "#E04210",
    "700": "#C13310",
    "800": "#A32E0E",
    "900": "#85240C",
    "950": "#5A1D0B",
}

RED = {
    "50":  "#FFEBEE",
    "100": "#FFD5DC",
    "200": "#FFC0CA",
    "300": "#FF97A7",
    "400": "#FF6875",
    "500": "#FB3748",
    "600": "#E0354A",
    "700": "#C13045",
    "800": "#A32A3A",
    "900": "#85222F",
    "950": "#5A1D29",
}

YELLOW = {
    "50":  "#FFEFD6",
    "100": "#FFE5BA",
    "200": "#FFD58E",
    "300": "#FFC061",
    "400": "#F2AE40",
    "500": "#F1AE13",
    "600": "#E6A015",
    "700": "#B97D17",
    "800": "#94661A",
    "900": "#76521A",
    "950": "#4F3A0E",
}

PURPLE = {
    "50":  "#EFEBFF",
    "100": "#E0D5FF",
    "200": "#D2C0FF",
    "300": "#B6A3FF",
    "400": "#9785FF",
    "500": "#7D52F4",
    "600": "#693EE0",
    "700": "#5734BD",
    "800": "#46289C",
    "900": "#3B237D",
    "950": "#291A55",
}

SKY = {
    "50":  "#EBF8FF",
    "100": "#D5F0FF",
    "200": "#C0E8FF",
    "300": "#97D8FF",
    "400": "#68C8FF",
    "500": "#47C2FF",
    "600": "#359AE9",
    "700": "#2580D0",
    "800": "#1F66AD",
    "900": "#18548B",
    "950": "#10355C",
}

PINK = {
    "50":  "#FFEBF6",
    "100": "#FFD5EC",
    "200": "#FFC0E2",
    "300": "#FF97D0",
    "400": "#FF68B8",
    "500": "#FB47A0",
    "600": "#E03D8C",
    "700": "#C03377",
    "800": "#A32A65",
    "900": "#822152",
    "950": "#581637",
}

TEAL = {
    "50":  "#E4FBF8",
    "100": "#D0FAF4",
    "200": "#C2F5EE",
    "300": "#84E5DA",
    "400": "#42D7C5",
    "500": "#22D3BB",
    "600": "#14AB97",
    "700": "#0E8472",
    "800": "#1A6657",
    "900": "#155547",
    "950": "#093B33",
}


# ═══════════════════════════════════════════════════════════════
# 🎯 SEMANTIC TOKENS (dark mode mapping per AlignUI)
# ═══════════════════════════════════════════════════════════════

COLORS = {
    # Backgrounds (dark mode mapping)
    "bg_strong_950":  NEUTRAL["0"],
    "bg_surface_800": NEUTRAL["800"],
    "bg_sub_300":     NEUTRAL["600"],
    "bg_soft_200":    NEUTRAL["700"],
    "bg_weak_50":     NEUTRAL["900"],
    "bg_white_0":     NEUTRAL["950"],

    # Text (dark mode mapping)
    "text_strong_950": NEUTRAL["0"],
    "text_sub_600":    NEUTRAL["400"],
    "text_soft_400":   NEUTRAL["500"],
    "text_disabled":   NEUTRAL["600"],

    # Stroke
    "stroke_strong_950": NEUTRAL["0"],
    "stroke_sub_300":    NEUTRAL["600"],
    "stroke_soft_200":   NEUTRAL["700"],

    # Primary (blue)
    "primary_dark":   BLUE["800"],
    "primary_darker": BLUE["700"],
    "primary_base":   BLUE["500"],
    "primary_alpha_24": "rgba(51, 92, 255, 0.24)",
    "primary_alpha_16": "rgba(51, 92, 255, 0.16)",
    "primary_alpha_10": "rgba(51, 92, 255, 0.10)",

    # Status (semantic, dark mode)
    "success_dark":    GREEN["400"],
    "success_base":    GREEN["600"],
    "success_light":   "rgba(31, 193, 107, 0.24)",
    "success_lighter": "rgba(31, 193, 107, 0.16)",

    "warning_dark":    ORANGE["400"],
    "warning_base":    ORANGE["600"],
    "warning_light":   "rgba(251, 71, 16, 0.24)",
    "warning_lighter": "rgba(251, 71, 16, 0.16)",

    "error_dark":    RED["400"],
    "error_base":    RED["600"],
    "error_light":   "rgba(251, 55, 72, 0.24)",
    "error_lighter": "rgba(251, 55, 72, 0.16)",

    "information_dark":    BLUE["400"],
    "information_base":    BLUE["500"],
    "information_light":   "rgba(51, 92, 255, 0.24)",
    "information_lighter": "rgba(51, 92, 255, 0.16)",

    "feature_dark":    PURPLE["400"],
    "feature_base":    PURPLE["500"],
    "feature_light":   "rgba(125, 82, 244, 0.24)",
    "feature_lighter": "rgba(125, 82, 244, 0.16)",

    "verified_dark":    SKY["400"],
    "verified_base":    SKY["600"],
    "verified_light":   "rgba(71, 194, 255, 0.24)",
    "verified_lighter": "rgba(71, 194, 255, 0.16)",

    "away_dark":    YELLOW["400"],
    "away_base":    YELLOW["600"],
    "away_light":   "rgba(241, 174, 19, 0.24)",
    "away_lighter": "rgba(241, 174, 19, 0.16)",

    "stable_dark":    TEAL["400"],
    "stable_base":    TEAL["600"],

    # Backwards-compat aliases (existing code references)
    "bg":             NEUTRAL["950"],
    "surface":        NEUTRAL["900"],
    "surface_elevated": NEUTRAL["800"],
    "border":         "rgba(202, 207, 216, 0.08)",
    "border_hover":   "rgba(202, 207, 216, 0.2)",
    "text":           NEUTRAL["0"],
    "text_secondary": NEUTRAL["400"],
    "text_muted":     NEUTRAL["500"],
    "accent_blue":    BLUE["500"],
    "accent_blue_glow": "rgba(51, 92, 255, 0.16)",
    "success":        GREEN["500"],
    "success_glow":   "rgba(31, 193, 107, 0.16)",
    "warning":        YELLOW["500"],
    "warning_glow":   "rgba(241, 174, 19, 0.16)",
    "danger":         RED["500"],
    "danger_glow":    "rgba(251, 55, 72, 0.16)",
    "session_asia":   GREEN["500"],
    "session_london": BLUE["500"],
    "session_ny":     YELLOW["500"],
}


# ═══════════════════════════════════════════════════════════════
# 📐 TYPOGRAPHY SCALE (AlignUI text tokens)
# ═══════════════════════════════════════════════════════════════
# Each tuple: (size, line-height, letter-spacing, weight)

TYPOGRAPHY = {
    "title_h1":   ("3.5rem",   "4rem",     "-0.01em",  "500"),
    "title_h2":   ("3rem",     "3.5rem",   "-0.01em",  "500"),
    "title_h3":   ("2.5rem",   "3rem",     "-0.01em",  "500"),
    "title_h4":   ("2rem",     "2.5rem",   "-0.005em", "500"),
    "title_h5":   ("1.5rem",   "2rem",     "0",        "500"),
    "title_h6":   ("1.25rem",  "1.75rem",  "0",        "500"),
    "label_xl":   ("1.5rem",   "2rem",     "-0.015em", "500"),
    "label_lg":   ("1.125rem", "1.5rem",   "-0.015em", "500"),
    "label_md":   ("1rem",     "1.5rem",   "-0.011em", "500"),
    "label_sm":   ("0.875rem", "1.25rem",  "-0.006em", "500"),
    "label_xs":   ("0.75rem",  "1rem",     "0",        "500"),
    "para_xl":    ("1.5rem",   "2rem",     "-0.015em", "400"),
    "para_lg":    ("1.125rem", "1.5rem",   "-0.015em", "400"),
    "para_md":    ("1rem",     "1.5rem",   "-0.011em", "400"),
    "para_sm":    ("0.875rem", "1.25rem",  "-0.006em", "400"),
    "para_xs":    ("0.75rem",  "1rem",     "0",        "400"),
    "subhead_md": ("1rem",     "1.5rem",   "0.06em",   "500"),
    "subhead_sm": ("0.875rem", "1.25rem",  "0.06em",   "500"),
    "subhead_xs": ("0.75rem",  "1rem",     "0.04em",   "500"),
    "subhead_2xs":("0.6875rem","0.75rem",  "0.02em",   "500"),
}


# ═══════════════════════════════════════════════════════════════
# 🌑 SHADOWS (AlignUI shadow tokens)
# ═══════════════════════════════════════════════════════════════

SHADOWS = {
    "regular_xs": "0 1px 2px 0 rgba(10, 13, 20, 0.03)",
    "regular_sm": "0 2px 4px rgba(27, 28, 29, 0.04)",
    "regular_md": "0 16px 32px -12px rgba(14, 18, 27, 0.10)",
    "fancy_neutral": "0 1px 2px 0 rgba(27, 28, 29, 0.48), 0 0 0 1px #242628",
    "fancy_primary": f"0 1px 2px 0 rgba(14, 18, 27, 0.24), 0 0 0 1px {COLORS['primary_base']}",
    "tooltip": "0 12px 24px 0 rgba(14, 18, 27, 0.06), 0 1px 2px 0 rgba(14, 18, 27, 0.03)",
}


# ═══════════════════════════════════════════════════════════════
# 🎬 CSS INJECTION
# ═══════════════════════════════════════════════════════════════

def apply_theme():
    """Apply AlignUI-inspired theme via CSS injection."""

    # Generate CSS variable block
    css_vars = ":root {\n"
    for k, v in COLORS.items():
        css_vars += f"  --{k.replace('_', '-')}: {v};\n"
    css_vars += "}\n"

    st.markdown(f"""
    <style>
    /* Import fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    {css_vars}

    /* Hide Streamlit chrome */
    #MainMenu, footer, header[data-testid="stHeader"] {{visibility: hidden;}}
    .stDeployButton, [data-testid="stToolbar"] {{display: none !important;}}

    /* Base typography */
    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        font-feature-settings: 'cv11', 'ss01', 'ss03';
        -webkit-font-smoothing: antialiased;
    }}
    code, pre, [data-testid="stCode"] {{
        font-family: 'JetBrains Mono', 'SF Mono', Menlo, monospace !important;
    }}

    /* App background — AlignUI bg-white-0 dark = neutral-950 */
    .stApp {{
        background: {COLORS['bg_white_0']} !important;
    }}

    /* Main content padding */
    .block-container {{
        padding-top: 2.5rem !important;
        padding-bottom: 4rem !important;
        max-width: 1320px !important;
    }}

    /* Headings — AlignUI title-h tokens */
    h1 {{
        font-size: 2rem !important;          /* title-h4 ish */
        line-height: 2.5rem !important;
        letter-spacing: -0.005em !important;
        font-weight: 500 !important;
        color: {COLORS['text_strong_950']} !important;
        margin-bottom: 0.25rem !important;
    }}
    h2 {{
        font-size: 1.5rem !important;        /* title-h5 */
        line-height: 2rem !important;
        letter-spacing: 0 !important;
        font-weight: 500 !important;
        color: {COLORS['text_strong_950']} !important;
        margin-top: 2rem !important;
        margin-bottom: 0.75rem !important;
    }}
    h3 {{
        font-size: 1.125rem !important;      /* label-lg */
        line-height: 1.5rem !important;
        letter-spacing: -0.015em !important;
        font-weight: 500 !important;
        color: {COLORS['text_strong_950']} !important;
    }}

    /* Captions = paragraph-sm subdued */
    [data-testid="stCaptionContainer"] {{
        color: {COLORS['text_soft_400']} !important;
        font-size: 0.875rem !important;
        line-height: 1.25rem !important;
        letter-spacing: -0.006em !important;
    }}

    /* AlignUI Card pattern — bg-white-0 with stroke-soft-200 + regular-xs shadow */
    [data-testid="stMetric"] {{
        background: {COLORS['bg_weak_50']};
        border: 1px solid {COLORS['stroke_soft_200']};
        border-radius: 16px;
        padding: 1rem 1.25rem;
        box-shadow: {SHADOWS['regular_xs']};
        transition: border-color 0.15s ease;
    }}
    [data-testid="stMetric"]:hover {{
        border-color: {COLORS['stroke_sub_300']};
    }}
    [data-testid="stMetricLabel"] {{
        color: {COLORS['text_sub_600']} !important;
        font-size: 0.6875rem !important;     /* subhead-2xs */
        font-weight: 500 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.04em !important;
    }}
    [data-testid="stMetricValue"] {{
        font-size: 2rem !important;          /* title-h4 */
        line-height: 2.5rem !important;
        font-weight: 500 !important;
        letter-spacing: -0.005em !important;
        color: {COLORS['text_strong_950']} !important;
    }}
    [data-testid="stMetricDelta"] {{
        font-size: 0.875rem !important;
        font-weight: 500 !important;
    }}

    /* Container border (st.container border=True) — match Card */
    [data-testid="stVerticalBlockBorderWrapper"] {{
        background: {COLORS['bg_weak_50']} !important;
        border: 1px solid {COLORS['stroke_soft_200']} !important;
        border-radius: 16px !important;
        padding: 1.25rem !important;
        box-shadow: {SHADOWS['regular_xs']};
        transition: border-color 0.15s ease;
    }}
    [data-testid="stVerticalBlockBorderWrapper"]:hover {{
        border-color: {COLORS['stroke_sub_300']} !important;
    }}

    /* Sidebar — AlignUI nav style + STICKY (always visible) */
    [data-testid="stSidebar"] {{
        background: {COLORS['bg_white_0']} !important;
        border-right: 1px solid {COLORS['stroke_soft_200']} !important;
        /* Force always visible — prevent accidental hide */
        min-width: 244px !important;
        max-width: 244px !important;
        transform: translateX(0) !important;
        visibility: visible !important;
    }}
    /* Hide the collapse-sidebar button so it can't be accidentally clicked */
    [data-testid="stSidebarCollapseButton"],
    button[kind="headerNoPadding"][data-testid="baseButton-headerNoPadding"] {{
        display: none !important;
    }}
    /* Adjust main content area to account for sticky sidebar */
    [data-testid="stMain"] {{
        margin-left: 0 !important;
    }}
    [data-testid="stSidebarNav"] li a {{
        font-size: 0.875rem !important;      /* label-sm */
        font-weight: 500 !important;
        letter-spacing: -0.006em !important;
        border-radius: 8px !important;
        margin: 2px 6px !important;
        padding: 8px 12px !important;
        color: {COLORS['text_sub_600']} !important;
        transition: all 0.15s ease;
    }}
    [data-testid="stSidebarNav"] li a:hover {{
        background: {COLORS['bg_weak_50']} !important;
        color: {COLORS['text_strong_950']} !important;
    }}
    [data-testid="stSidebarNav"] li a[aria-current="page"] {{
        background: {COLORS['primary_alpha_10']} !important;
        color: {COLORS['primary_base']} !important;
    }}

    /* Divider — stroke-soft-200 */
    [data-testid="stDivider"] hr {{
        border-top: 1px solid {COLORS['stroke_soft_200']} !important;
        margin: 1.5rem 0 !important;
    }}

    /* Input/Select — AlignUI input style */
    [data-baseweb="select"] > div,
    [data-baseweb="input"] {{
        background: {COLORS['bg_weak_50']} !important;
        border: 1px solid {COLORS['stroke_soft_200']} !important;
        border-radius: 10px !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        color: {COLORS['text_strong_950']} !important;
        transition: all 0.15s ease;
    }}
    [data-baseweb="select"]:hover > div {{
        border-color: {COLORS['stroke_sub_300']} !important;
    }}
    [data-baseweb="select"]:focus-within > div {{
        border-color: {COLORS['primary_base']} !important;
        box-shadow: 0 0 0 4px {COLORS['primary_alpha_10']};
    }}

    /* Tags inside multiselect — pill style */
    [data-baseweb="tag"] {{
        background: {COLORS['primary_alpha_10']} !important;
        border: 1px solid {COLORS['primary_alpha_24']} !important;
        color: {COLORS['primary_base']} !important;
        border-radius: 999px !important;
        font-size: 0.75rem !important;
        font-weight: 500 !important;
        padding: 2px 10px !important;
    }}

    /* Tabs — AlignUI segmented control */
    [data-baseweb="tab-list"] {{
        gap: 4px !important;
        background: {COLORS['bg_weak_50']};
        padding: 4px;
        border-radius: 12px;
        border: 1px solid {COLORS['stroke_soft_200']};
        display: inline-flex !important;
    }}
    [data-baseweb="tab"] {{
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        letter-spacing: -0.006em !important;
        padding: 8px 16px !important;
        border-radius: 8px !important;
        background: transparent !important;
        color: {COLORS['text_sub_600']} !important;
        border: none !important;
        transition: all 0.15s ease;
    }}
    [data-baseweb="tab"]:hover {{
        color: {COLORS['text_strong_950']} !important;
    }}
    [data-baseweb="tab"][aria-selected="true"] {{
        background: {COLORS['bg_white_0']} !important;
        color: {COLORS['text_strong_950']} !important;
        box-shadow: {SHADOWS['regular_xs']};
    }}

    /* DataFrame — clean table */
    [data-testid="stDataFrame"] {{
        border: 1px solid {COLORS['stroke_soft_200']};
        border-radius: 12px;
        overflow: hidden;
    }}

    /* Alert boxes — AlignUI alert style */
    [data-testid="stAlert"] {{
        background: {COLORS['bg_weak_50']} !important;
        border: 1px solid {COLORS['stroke_soft_200']} !important;
        border-left-width: 3px !important;
        border-left-color: {COLORS['information_base']} !important;
        border-radius: 12px !important;
        font-size: 0.875rem !important;
        line-height: 1.5;
        padding: 0.875rem 1rem !important;
    }}

    /* JSON viewer */
    [data-testid="stJson"] {{
        background: {COLORS['bg_weak_50']} !important;
        border: 1px solid {COLORS['stroke_soft_200']} !important;
        border-radius: 10px;
        padding: 0.75rem !important;
        font-size: 0.8125rem !important;
    }}

    /* Code blocks */
    [data-testid="stCode"] {{
        background: {COLORS['bg_weak_50']} !important;
        border-radius: 10px !important;
        border: 1px solid {COLORS['stroke_soft_200']};
        font-size: 0.8125rem !important;
    }}

    /* Buttons */
    .stButton > button {{
        border-radius: 10px !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        letter-spacing: -0.006em !important;
        padding: 8px 16px !important;
        transition: all 0.15s ease;
        border: 1px solid {COLORS['stroke_soft_200']} !important;
        background: {COLORS['bg_weak_50']} !important;
        color: {COLORS['text_strong_950']} !important;
    }}
    .stButton > button:hover {{
        border-color: {COLORS['primary_base']} !important;
        background: {COLORS['primary_alpha_10']} !important;
        color: {COLORS['primary_base']} !important;
    }}

    /* Scrollbar — minimalist */
    ::-webkit-scrollbar {{
        width: 8px;
        height: 8px;
    }}
    ::-webkit-scrollbar-track {{
        background: transparent;
    }}
    ::-webkit-scrollbar-thumb {{
        background: {COLORS['stroke_soft_200']};
        border-radius: 4px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
        background: {COLORS['stroke_sub_300']};
    }}
    </style>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# 🧩 COMPONENT HELPERS (AlignUI-style component patterns)
# ═══════════════════════════════════════════════════════════════

def plotly_layout(**overrides):
    """Default Plotly layout matching AlignUI theme."""
    base = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=COLORS["text_strong_950"], size=12),
        margin=dict(t=30, b=40, l=50, r=20),
        xaxis=dict(
            gridcolor=COLORS["stroke_soft_200"],
            zerolinecolor=COLORS["stroke_sub_300"],
            tickfont=dict(color=COLORS["text_sub_600"], size=11),
        ),
        yaxis=dict(
            gridcolor=COLORS["stroke_soft_200"],
            zerolinecolor=COLORS["stroke_sub_300"],
            tickfont=dict(color=COLORS["text_sub_600"], size=11),
        ),
        legend=dict(
            bgcolor=COLORS["bg_weak_50"],
            bordercolor=COLORS["stroke_soft_200"],
            borderwidth=1,
            font=dict(color=COLORS["text_sub_600"], size=11),
        ),
        hoverlabel=dict(
            bgcolor=COLORS["bg_surface_800"],
            bordercolor=COLORS["stroke_sub_300"],
            font=dict(family="Inter, sans-serif", color=COLORS["text_strong_950"]),
        ),
    )
    base.update(overrides)
    return base


def metric_card(label: str, value: str, sub: str = None, color: str = None):
    """Render an AlignUI-style metric card."""
    color = color or COLORS["text_strong_950"]
    muted = COLORS["text_sub_600"]
    sub_html = f"<div style='color: {muted}; font-size: 0.75rem; font-weight: 500; margin-top: 6px; letter-spacing: -0.006em;'>{sub}</div>" if sub else ""
    st.markdown(f"""
    <div style="
        background: {COLORS['bg_weak_50']};
        border: 1px solid {COLORS['stroke_soft_200']};
        border-radius: 16px;
        padding: 1.125rem 1.25rem;
        box-shadow: {SHADOWS['regular_xs']};
        transition: border-color 0.15s ease;
    ">
        <div style="
            color: {COLORS['text_sub_600']};
            font-size: 0.6875rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 0.5rem;
        ">{label}</div>
        <div style="
            font-size: 1.875rem;
            font-weight: 500;
            letter-spacing: -0.01em;
            color: {color};
            line-height: 1.1;
        ">{value}</div>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)


def status_badge(text: str, variant: str = "neutral") -> str:
    """Generate AlignUI-style status badge HTML.

    variant: success / warning / error / information / feature / verified / away / neutral
    """
    colors = {
        "success":     (COLORS["success_base"], COLORS["success_lighter"]),
        "warning":     (COLORS["warning_base"], COLORS["warning_lighter"]),
        "error":       (COLORS["error_base"], COLORS["error_lighter"]),
        "information": (COLORS["information_base"], COLORS["information_lighter"]),
        "feature":     (COLORS["feature_base"], COLORS["feature_lighter"]),
        "verified":    (COLORS["verified_base"], COLORS["verified_lighter"]),
        "away":        (COLORS["away_base"], COLORS["away_lighter"]),
        "neutral":     (COLORS["text_sub_600"], COLORS["bg_weak_50"]),
    }
    fg, bg = colors.get(variant, colors["neutral"])
    return f"""<span style="
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 999px;
        background: {bg};
        color: {fg};
        font-size: 0.75rem;
        font-weight: 500;
        letter-spacing: 0;
        line-height: 1;
        border: 1px solid {fg}33;
    ">{text}</span>"""


def hero_card_html(label: str, value: str, value_color: str, sub_html: str, right_html: str = "", accent: str = "primary"):
    """Premium hero card (e.g., current best metric)."""
    accent_glow = {
        "primary": COLORS["primary_alpha_10"],
        "success": COLORS["success_lighter"],
        "warning": COLORS["warning_lighter"],
        "error":   COLORS["error_lighter"],
    }.get(accent, COLORS["primary_alpha_10"])

    return f"""
    <div style="
        background: linear-gradient(135deg, {accent_glow} 0%, {COLORS['bg_weak_50']} 60%);
        border: 1px solid {COLORS['stroke_soft_200']};
        border-radius: 20px;
        padding: 1.75rem 2rem;
        margin-bottom: 1.5rem;
        box-shadow: {SHADOWS['regular_md']};
    ">
        <div style="display: flex; align-items: baseline; justify-content: space-between; flex-wrap: wrap; gap: 1rem;">
            <div>
                <div style="
                    color: {COLORS['text_sub_600']};
                    font-size: 0.6875rem;
                    font-weight: 500;
                    text-transform: uppercase;
                    letter-spacing: 0.04em;
                    margin-bottom: 0.5rem;
                ">{label}</div>
                <div style="
                    font-size: 3rem;
                    font-weight: 500;
                    color: {value_color};
                    letter-spacing: -0.02em;
                    line-height: 1;
                ">{value}</div>
                <div style="margin-top: 0.5rem;">{sub_html}</div>
            </div>
            <div style="text-align: right; max-width: 50%;">{right_html}</div>
        </div>
    </div>
    """
