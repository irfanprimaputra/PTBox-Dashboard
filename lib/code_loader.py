"""Code file loading (Pinescript / MQL5 / Python)."""
from pathlib import Path

DASHBOARD_ROOT = Path(__file__).parent.parent
CODE_DIR = DASHBOARD_ROOT / "code"
PINESCRIPTS_DIR = CODE_DIR / "pinescripts"


CODE_FILES = {
    "Pinescript": {
        "Asia": PINESCRIPTS_DIR / "Asia.md",
        "London": PINESCRIPTS_DIR / "London.md",
        "NY": PINESCRIPTS_DIR / "NY.md",
        "Index": PINESCRIPTS_DIR / "Index.md",
    },
    "MQL5": {
        "PTBox_NY": CODE_DIR / "PTBox_NY.mq5",
        "PTBox_v140": CODE_DIR / "PTBox_v140.mq5",
    },
    "Python": {
        "v1 (deploy)": CODE_DIR / "ptbox_quarterly.py",
        "v2 (walk-forward)": CODE_DIR / "ptbox_quarterly_v2.py",
        "v3 (Phase 4)": CODE_DIR / "ptbox_quarterly_v3.py",
        "v4 (Phase 5 #A)": CODE_DIR / "ptbox_quarterly_v4.py",
        "v5 (Phase 5 #B) ⭐": CODE_DIR / "ptbox_quarterly_v5.py",
        "ptbox_backtest": CODE_DIR / "ptbox_backtest.py",
        "ptbox_run": CODE_DIR / "ptbox_run.py",
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
