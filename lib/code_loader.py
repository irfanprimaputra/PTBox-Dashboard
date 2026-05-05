"""Code file loading (Pinescript / MQL5 / Python)."""
from pathlib import Path

DASHBOARD_ROOT = Path(__file__).parent.parent
CODE_DIR = DASHBOARD_ROOT / "code"
PINESCRIPTS_DIR = CODE_DIR / "pinescripts"


CODE_FILES = {
    "Pinescript": {
        "PTBox_e37 ⭐ LIVE": PINESCRIPTS_DIR / "PTBox_e37.pine",
    },
    "MQL5": {
        "PTBox_e37 ⭐ LIVE": CODE_DIR / "mql5" / "PTBox_e37.mq5",
    },
    "Python": {
        "ptbox_engine_e37 ⭐ LIVE": CODE_DIR / "ptbox_engine_e37.py",
        "ptbox_quarterly_v3 (core)": CODE_DIR / "ptbox_quarterly_v3.py",
    },
}


def read_code(path: Path) -> str:
    """Safe read code file content."""
    try:
        return path.read_text()
    except Exception as e:
        return f"# Error reading file: {e}"


def get_lang_for_file(path: Path) -> str:
    """Streamlit language hint for syntax highlighting."""
    suffix = path.suffix.lower()
    return {
        ".py": "python",
        ".mq5": "cpp",   # MQL5 syntax close enough to C++ for highlighting
        ".md": "markdown",
        ".pine": "javascript",  # Pine resembles JS visually
    }.get(suffix, "text")
