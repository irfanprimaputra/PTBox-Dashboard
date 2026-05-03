#!/bin/bash
# Refresh dashboard data from latest backtest outputs in ~/Downloads/
# Run after every new backtest iteration.
set -e
cd "$(dirname "$0")/.."

echo "→ Copying CSV results from ~/Downloads/..."
cp ~/Downloads/ptbox_phase4_experiments.csv data/ 2>/dev/null && echo "  ✓ master registry"
cp ~/Downloads/ptbox_phase4_box_quality_results.csv data/ 2>/dev/null && echo "  ✓ phase4 box quality"
cp ~/Downloads/ptbox_phase4_pattern_results.csv data/ 2>/dev/null && echo "  ✓ phase4 pattern"
cp ~/Downloads/ptbox_phase5_asia_meanrev_results.csv data/ 2>/dev/null && echo "  ✓ phase5 asia meanrev"
cp ~/Downloads/ptbox_phase5b_results.csv data/ 2>/dev/null && echo "  ✓ phase5b"
cp ~/Downloads/ptbox_walkforward_extended.csv data/ 2>/dev/null && echo "  ✓ walkforward baseline"

echo "→ Copying JSON summaries..."
cp ~/Downloads/ptbox_*_summary.json data/ 2>/dev/null && echo "  ✓ summaries"
cp ~/Downloads/ptbox_phase4_ceiling_results.json data/ 2>/dev/null && echo "  ✓ ceiling"

echo "→ Copying code (Python engines + MQL5)..."
cp ~/Downloads/ptbox_quarterly*.py code/ 2>/dev/null && echo "  ✓ python engines"
cp ~/Downloads/ptbox_backtest.py code/ 2>/dev/null && echo "  ✓ ptbox_backtest"
cp ~/Downloads/ptbox_run.py code/ 2>/dev/null && echo "  ✓ ptbox_run"
cp ~/Downloads/PTBox_*.mq5 code/ 2>/dev/null && echo "  ✓ mql5"

echo "→ Copying Pinescripts from vault..."
VAULT_IMPL=~/Documents/Obsidian/Irfan-Vault/03-Trading/01-Forex/Strategies/PT-Box/Implementation
cp "$VAULT_IMPL/PT-Box-Asian-Pinescript.md" code/pinescripts/Asia.md 2>/dev/null && echo "  ✓ Asia"
cp "$VAULT_IMPL/PT-Box-London-Pinescript.md" code/pinescripts/London.md 2>/dev/null && echo "  ✓ London"
cp "$VAULT_IMPL/PT-Box-NY-Pinescript.md" code/pinescripts/NY.md 2>/dev/null && echo "  ✓ NY"
cp "$VAULT_IMPL/PT-Box-Pinescripts-Index.md" code/pinescripts/Index.md 2>/dev/null && echo "  ✓ Index"

echo ""
echo "✅ Done. Restart Streamlit to clear cache:"
echo "    Ctrl-C in Streamlit terminal → run again"
