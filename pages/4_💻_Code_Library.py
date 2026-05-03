"""Code Library — browse all active code (Pinescript / MQL5 / Python)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import streamlit as st
from lib.code_loader import CODE_FILES, read_code, get_lang_for_file
from lib.theme import apply_theme, COLORS

st.set_page_config(page_title="Code Library · PT Box", page_icon="💻", layout="wide")
apply_theme()

st.markdown(f"""
<div style="margin-bottom: 1.5rem;">
    <h1 style="font-size: 2rem; margin: 0;">💻 Code Library</h1>
    <p style="color: {COLORS['text_secondary']}; margin: 0.25rem 0 0 0;">
        Browse all active source — Pinescript / MQL5 / Python
    </p>
</div>
""", unsafe_allow_html=True)

tab_ps, tab_mq, tab_py = st.tabs(["📜 Pinescript", "📈 MQL5", "🐍 Python"])

# --- Pinescript ---
with tab_ps:
    st.markdown(f"<div style='color: {COLORS['text_secondary']}; margin-bottom: 0.5rem;'><b style='color: {COLORS['text']};'>TradingView Pine Script</b> — visual indicator untuk live monitoring.</div>", unsafe_allow_html=True)
    ps_files = CODE_FILES["Pinescript"]
    selected = st.selectbox("Pick file", list(ps_files.keys()), key="ps_sel")
    path = ps_files[selected]
    if path.exists():
        size_kb = path.stat().st_size / 1024
        st.caption(f"📂 `{path}` · {size_kb:.1f} KB")
        content = read_code(path)
        # Pinescript files are .md notes with embedded code — render markdown
        st.markdown(content)
    else:
        st.error(f"File not found: {path}")

# --- MQL5 ---
with tab_mq:
    st.markdown(f"<div style='color: {COLORS['text_secondary']}; margin-bottom: 0.5rem;'><b style='color: {COLORS['text']};'>MQL5</b> — MT5 indicator untuk visual feedback.</div>", unsafe_allow_html=True)
    mq_files = CODE_FILES["MQL5"]
    selected = st.selectbox("Pick file", list(mq_files.keys()), key="mq_sel")
    path = mq_files[selected]
    if path.exists():
        st.caption(f"📂 `{path.name}` · {path.stat().st_size / 1024:.1f} KB")
        content = read_code(path)
        st.code(content, language=get_lang_for_file(path), line_numbers=True)
    else:
        st.error(f"File not found: {path}")

# --- Python ---
with tab_py:
    st.markdown(f"<div style='color: {COLORS['text_secondary']}; margin-bottom: 0.5rem;'><b style='color: {COLORS['text']};'>Python engines</b> — backtest + walk-forward + variant routing.</div>", unsafe_allow_html=True)
    py_files = CODE_FILES["Python"]
    selected = st.selectbox("Pick file", list(py_files.keys()), key="py_sel")
    path = py_files[selected]
    if path.exists():
        st.caption(f"📂 `{path.name}` · {path.stat().st_size / 1024:.1f} KB")
        content = read_code(path)
        st.code(content, language="python", line_numbers=True)
    else:
        st.error(f"File not found: {path}")

st.divider()

# --- Quick reference ---
st.markdown("<h2>📋 Quick Reference</h2>", unsafe_allow_html=True)
ref_data = []
for category, files in CODE_FILES.items():
    for name, path in files.items():
        if path.exists():
            ref_data.append({
                "Category": category,
                "Name": name,
                "Path": str(path).replace(str(Path.home()), "~"),
                "Size (KB)": f"{path.stat().st_size / 1024:.1f}",
            })

ref_df = pd.DataFrame(ref_data)
st.dataframe(ref_df, hide_index=True, use_container_width=True)
