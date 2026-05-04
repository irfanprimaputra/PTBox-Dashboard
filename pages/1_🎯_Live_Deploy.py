"""Live Deploy — PT Box e33 deploy guide + today's session schedule.

Real-time clock showing current WIB/ET, next session countdown, deploy
checklist, manual execution flow.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta, timezone
import streamlit as st

from lib.theme import apply_theme, COLORS

st.set_page_config(page_title="Live Deploy · PT Box", page_icon="🎯", layout="wide")
apply_theme()

ROOT = Path(__file__).parent.parent

# Time helpers
def now_utc():
    return datetime.now(timezone.utc)

def now_et(utc):
    return utc - timedelta(hours=4)  # EDT

def now_wib(utc):
    return utc + timedelta(hours=7)

# Sessions in ET (e37 Wyckoff pre-session config)
SESSIONS = [
    {"name": "Asia", "emoji": "🟢", "et_start": (18, 0), "et_end": (24, 0),
     "box_window": "18:00-19:30 ET (90m)", "model": "DIRECT breakout + body0% + TP=1.5R (e37)",
     "wib_start": (5, 0), "wib_end": (11, 0),
     "color": COLORS["success"]},
    {"name": "London", "emoji": "🔵", "et_start": (0, 0), "et_end": (8, 0),
     "box_window": "00:00-01:00 ET (60m)", "model": "DIRECT breakout + body20% + TP=2.0R (e37)",
     "wib_start": (11, 0), "wib_end": (19, 0),
     "color": COLORS["accent_blue"]},
    {"name": "NY", "emoji": "🟡", "et_start": (7, 0), "et_end": (12, 0),
     "box_window": "07:00-08:00 ET (60m)", "model": "DIRECT breakout + body30% + TP=2.5R (e37)",
     "wib_start": (18, 0), "wib_end": (23, 0),
     "color": COLORS["warning"]},
]

# ───────────────────────────────────────────────────────────
# 🎯 HEADER
# ───────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-bottom: 1.5rem;">
    <h1 style="font-size: 2rem; margin: 0;">🎯 Live Deploy — PT Box e37 (OOS PASSED ✅)</h1>
    <p style="color: {COLORS['text_secondary']}; margin: 0.25rem 0 0 0;">
        Pinescript on TradingView · Manual MT5 execution · Trade journal
    </p>
</div>
""", unsafe_allow_html=True)

# ───────────────────────────────────────────────────────────
# 🕐 LIVE CLOCK + Next Session Countdown
# ───────────────────────────────────────────────────────────
utc_now = now_utc()
et = now_et(utc_now)
wib = now_wib(utc_now)

# Find next session
def next_session(et_now):
    et_min = et_now.hour * 60 + et_now.minute
    for sess in SESSIONS:
        sess_start = sess["et_start"][0] * 60 + sess["et_start"][1]
        if sess_start > et_min:
            mins_until = sess_start - et_min
            return sess, mins_until
    # Wrap to next day
    sess = SESSIONS[0]  # Asia is first session
    sess_start = sess["et_start"][0] * 60 + sess["et_start"][1]
    mins_until = (24 * 60 - et_min) + sess_start
    return sess, mins_until


def is_session_active(sess, et_now):
    et_min = et_now.hour * 60 + et_now.minute
    s_start = sess["et_start"][0] * 60 + sess["et_start"][1]
    s_end = sess["et_end"][0] * 60 + sess["et_end"][1]
    return s_start <= et_min < s_end


next_sess, mins_until = next_session(et)
hours_until = mins_until // 60
min_remainder = mins_until % 60

# Active session
active = None
for sess in SESSIONS:
    if is_session_active(sess, et):
        active = sess
        break

# Live clock card
status_color = COLORS["success"] if active else COLORS["accent_blue"]
status_text = f"{active['emoji']} {active['name']} ACTIVE" if active else f"⏳ Next: {next_sess['emoji']} {next_sess['name']}"

st.markdown(f"""
<div style="
    background: linear-gradient(135deg, rgba(31, 193, 107, 0.10) 0%, rgba(15, 23, 42, 0.5) 60%);
    border: 1px solid {status_color};
    border-radius: 16px;
    padding: 1.5rem 2rem;
    margin-bottom: 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 1rem;
">
    <div>
        <div style="font-size: 0.75rem; color: {COLORS['text_secondary']}; text-transform: uppercase; letter-spacing: 0.06em;">Status</div>
        <div style="font-size: 1.6rem; font-weight: 800; color: {status_color}; margin-top: 0.2rem;">{status_text}</div>
        {f'<div style="margin-top: 0.4rem; color: {COLORS["text_secondary"]}; font-size: 0.85rem;">Countdown: <b style="color: {COLORS["text"]};">{hours_until}h {min_remainder}m</b> · Box opens {next_sess["box_window"]}</div>' if not active else f'<div style="margin-top: 0.4rem; color: {COLORS["text_secondary"]}; font-size: 0.85rem;">Box: {active["box_window"]} · Watch entry signals</div>'}
    </div>
    <div style="text-align: right;">
        <div style="font-size: 0.75rem; color: {COLORS['text_secondary']}; text-transform: uppercase;">WIB</div>
        <div style="font-size: 1.4rem; font-weight: 700; color: {COLORS['text']};">{wib.strftime('%H:%M')}</div>
        <div style="font-size: 0.75rem; color: {COLORS['text_secondary']}; margin-top: 0.3rem;">ET (UTC-4): <b>{et.strftime('%H:%M')}</b></div>
    </div>
</div>
""", unsafe_allow_html=True)

# Auto-refresh hint
st.caption("⟳ Refresh page (R) atau klik Rerun atas-kanan untuk update jam.")

# ───────────────────────────────────────────────────────────
# 📅 Today's Session Cards
# ───────────────────────────────────────────────────────────
st.markdown("<h2>📅 Today's Sessions</h2>", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
for col, sess in zip([c1, c2, c3], SESSIONS):
    et_start_min = sess["et_start"][0] * 60 + sess["et_start"][1]
    et_end_min = sess["et_end"][0] * 60 + sess["et_end"][1]
    et_now_min = et.hour * 60 + et.minute

    if et_now_min >= et_end_min:
        status = "✅ DONE"
        scolor = COLORS["text_secondary"]
    elif et_start_min <= et_now_min < et_end_min:
        status = "🔴 LIVE"
        scolor = COLORS["danger"]
    else:
        mins_until_start = et_start_min - et_now_min
        if mins_until_start < 0:
            mins_until_start += 24 * 60
        h = mins_until_start // 60
        m = mins_until_start % 60
        status = f"⏳ in {h}h {m}m"
        scolor = COLORS["accent_blue"]

    pnl_ref = {"Asia": "+182", "London": "+486", "NY": "+308"}[sess["name"]]
    with col:
        st.markdown(f"""
        <div style="
            background: rgba(15, 23, 42, 0.4);
            border: 1px solid {sess['color']};
            border-radius: 12px;
            padding: 1.25rem 1.5rem;
            min-height: 200px;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="font-size: 1.4rem; font-weight: 700; color: {COLORS['text']};">{sess['emoji']} {sess['name']}</div>
                <div style="font-size: 0.85rem; font-weight: 600; color: {scolor};">{status}</div>
            </div>
            <div style="margin-top: 0.5rem; color: {COLORS['text_secondary']}; font-size: 0.78rem; line-height: 1.4;">{sess['model']}</div>
            <div style="margin-top: 0.75rem; padding-top: 0.5rem; border-top: 1px solid {COLORS['border']};">
                <div style="font-size: 0.72rem; color: {COLORS['text_secondary']};">WIB</div>
                <div style="font-size: 0.95rem; font-weight: 600; color: {COLORS['text']};">
                    {sess['wib_start'][0]:02d}:{sess['wib_start'][1]:02d} - {sess['wib_end'][0]:02d}:{sess['wib_end'][1]:02d}
                </div>
                <div style="margin-top: 0.4rem; font-size: 0.72rem; color: {COLORS['text_secondary']};">ET</div>
                <div style="font-size: 0.85rem; color: {COLORS['text']};">
                    {sess['et_start'][0]:02d}:{sess['et_start'][1]:02d} - {sess['et_end'][0]:02d}:{sess['et_end'][1]:02d}
                </div>
                <div style="margin-top: 0.4rem; font-size: 0.72rem; color: {COLORS['text_secondary']};">Backtest PnL</div>
                <div style="font-size: 1.2rem; font-weight: 700; color: {sess['color']};">{pnl_ref} pts</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# ───────────────────────────────────────────────────────────
# 🚀 Deploy Checklist
# ───────────────────────────────────────────────────────────
st.markdown("<h2>🚀 Deploy Checklist</h2>", unsafe_allow_html=True)

c1, c2 = st.columns(2)

with c1:
    st.markdown(f"""
    <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid {COLORS['border']};
                border-radius: 12px; padding: 1.25rem 1.5rem;">
        <h3 style="margin: 0 0 1rem 0; color: {COLORS['text']};">📜 Pinescript Setup (5 min)</h3>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    1. Buka [PTBox_e20d.pine](https://github.com/irfanprimaputra/PTBox-Dashboard/blob/main/code/pinescripts/PTBox_e20d.pine) → click **Raw** → Cmd+A, Cmd+C
    2. TradingView → chart **XAUUSD** M1
    3. Bottom-right tab **Pine Editor** → paste
    4. Click **Save** → "PT Box e33"
    5. Click **Add to chart**
    6. Right-click chart → Settings → Timezone → **New York (UTC-4)**

    **🆕 2026-05-04 v10 update:** added **risk management filter**:
    - `maxSlPts` filter (default 10pt) — auto-skip wide-SL trades for $200 cap protection
    - **Suggested lot** in entry label based on risk budget
    - Today vs Cumulative stats mode toggle
    - W/L exit markers + auto label cleanup on exit
    - Cross-day box state leak fix (replay mode)

    Always pull latest from GitHub raw to get all v10 features:
    [PTBox_e20d.pine raw](https://raw.githubusercontent.com/irfanprimaputra/PTBox-Dashboard/main/code/pinescripts/PTBox_e20d.pine)
    """)

with c2:
    st.markdown(f"""
    <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid {COLORS['border']};
                border-radius: 12px; padding: 1.25rem 1.5rem;">
        <h3 style="margin: 0 0 1rem 0; color: {COLORS['text']};">🔔 Alert Setup (2 min)</h3>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    1. Right-click chart → **Add Alert**
    2. Condition: **PT Box e33** → **Any alert() function call**
    3. Frequency: **Once Per Bar Close**
    4. Notifications: ✅ **Push to Phone** (TradingView mobile required)
    5. ✅ **Email** (backup)
    6. Click **Create**

    Sample alert akan masuk HP:
    ```
    NY DIRECT SHORT @ 2360.10 | SL 2363.40 | TP1 2350.20
    ```

    **⏱️ Entry timing:** Signal fires SAAT close confirmation candle.
    Live entry = OPEN candle berikutnya (1 bar after alert). Slippage 0-2 pts vs backtest is normal.
    """)

st.divider()

# ───────────────────────────────────────────────────────────
# 💰 Manual Execution Flow (Exness MT5)
# ───────────────────────────────────────────────────────────
st.markdown("<h2>💰 Manual Execution — Exness MT5</h2>", unsafe_allow_html=True)

st.markdown(f"""
<div style="background: rgba(15, 23, 42, 0.4); border: 1px solid {COLORS['border']};
            border-radius: 12px; padding: 1.25rem 1.5rem;">
<b style="color: {COLORS['warning']};">⚠️ Belum ada EA. Manual entry per signal.</b>
<ol style="margin-top: 0.75rem; padding-left: 1.5rem;">
    <li><b>Alert HP masuk</b> → cek chart TradingView, validate signal valid (no extreme news event)</li>
    <li><b>Buka MT5 Exness</b> (atau MT4)</li>
    <li><b>New Order:</b>
        <ul>
            <li>Symbol: <b>XAUUSD</b></li>
            <li>Volume: <b>0.02 lot</b> ($200 cap, ~1% risk)</li>
            <li>Type: BUY/SELL per alert direction</li>
            <li>Stop Loss: input level dari alert</li>
            <li>Take Profit: input <b>TP1</b> (atau TP2 kalau confidence tinggi)</li>
        </ul>
    </li>
    <li><b>Confirm execution</b></li>
    <li><b>Journal entry</b> di template (next section)</li>
    <li><b>STOP looking at chart</b> — biarkan setup main, jangan revenge-trade</li>
</ol>
</div>
""", unsafe_allow_html=True)

st.divider()

# ───────────────────────────────────────────────────────────
# 🛡️ Risk Management Hard Rules
# ───────────────────────────────────────────────────────────
st.markdown(f"""
<h2>🛡️ Risk Management — HARD RULES</h2>
<div style="
    background: rgba(15, 23, 42, 0.3);
    border: 1px solid {COLORS['border']};
    border-left: 4px solid {COLORS['danger']};
    border-radius: 10px;
    padding: 1rem 1.25rem;
    font-size: 0.95rem;
    line-height: 1.9;
">
1. <b style="color: {COLORS['text']};">Position size: 0.02 lot ALWAYS</b> — no exception, no oversize<br>
2. <b style="color: {COLORS['text']};">Daily stop: 2L OR 1W</b> → close MT5 immediately<br>
3. <b style="color: {COLORS['text']};">Max DD: -30% peak</b> → halt trading 1 week, investigate<br>
4. <b style="color: {COLORS['text']};">Friday after 12:00 ET</b> → NO new trades (position squaring)<br>
5. <b style="color: {COLORS['text']};">Body kill switch:</b> sleep &lt;4h × 3 nights → halt 1 week<br>
6. <b style="color: {COLORS['text']};">NEVER trade outside alert signal</b> — no FOMO, no gambling<br>
7. <b style="color: {COLORS['text']};">NEVER trade without journal</b> — every entry documented<br>
8. <b style="color: {COLORS['text']};">Drift z &lt; -1</b> → reduce size 50% next session<br>
9. <b style="color: {COLORS['warning']};">🆕 maxSlPts filter ON (default 10pt)</b> → skip wide-SL trades automatically (Pinescript v10)<br>
10. <b style="color: {COLORS['text']};">Wonky-box trade defense:</b> see "🚫 SKIP" label = DON'T enter (cap protection)<br>
</div>
""", unsafe_allow_html=True)

st.divider()

# ───────────────────────────────────────────────────────────
# 📋 Today's Action Plan
# ───────────────────────────────────────────────────────────
st.markdown("<h2>📋 Today's Action Plan</h2>", unsafe_allow_html=True)

passed_asia = (et.hour > 23) or (et.hour < 21 and et.hour > 0 and et.hour < 1)  # if past Asia end
# More accurate: Asia ends at 23:00 ET, so passed if ET >= 23 or ET < 21 (next day)

et_now_min = et.hour * 60 + et.minute

asia_passed = et_now_min >= 23 * 60 or et_now_min < 21 * 60
london_passed = et_now_min >= 5 * 60 and et_now_min < 9 * 60 + 3
ny_passed = et_now_min >= 12 * 60 or et_now_min < 9 * 60 + 3

asia_status = "✅ Done" if (et_now_min >= 23 * 60) else ("🔴 Live" if 21*60 <= et_now_min < 23*60 else "⏳ Pending today")
london_status = "✅ Done" if (et_now_min >= 5 * 60 and et_now_min < 9 * 60 + 3) else ("🔴 Live" if 1*60+43 <= et_now_min < 5*60 else "⏳ Pending today")
ny_status = "✅ Done" if (et_now_min >= 12 * 60 and et_now_min < 21*60) else ("🔴 Live" if 9*60+3 <= et_now_min < 12*60 else "⏳ Pending today")

st.markdown(f"""
<div style="background: rgba(15, 23, 42, 0.4); border: 1px solid {COLORS['border']};
            border-radius: 12px; padding: 1.25rem 1.5rem;">
<table style="width: 100%; border-collapse: collapse;">
    <thead>
        <tr style="border-bottom: 1px solid {COLORS['border']};">
            <th style="text-align: left; padding: 0.5rem; color: {COLORS['text_secondary']};">Session</th>
            <th style="text-align: left; padding: 0.5rem; color: {COLORS['text_secondary']};">Time WIB</th>
            <th style="text-align: left; padding: 0.5rem; color: {COLORS['text_secondary']};">Status</th>
            <th style="text-align: left; padding: 0.5rem; color: {COLORS['text_secondary']};">Pre-position checklist</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td style="padding: 0.5rem; color: {COLORS['success']};">🟢 Asia</td>
            <td style="padding: 0.5rem; color: {COLORS['text']};">08:00-10:00</td>
            <td style="padding: 0.5rem;">{asia_status}</td>
            <td style="padding: 0.5rem; color: {COLORS['text_secondary']}; font-size: 0.85rem;">Pre-position 07:50, alert listen 08:00-08:07</td>
        </tr>
        <tr>
            <td style="padding: 0.5rem; color: {COLORS['accent_blue']};">🔵 London</td>
            <td style="padding: 0.5rem; color: {COLORS['text']};">12:43-16:00</td>
            <td style="padding: 0.5rem;">{london_status}</td>
            <td style="padding: 0.5rem; color: {COLORS['text_secondary']}; font-size: 0.85rem;">Pre-position 12:30, box forms 12:43-12:46, signal possible 13:00+</td>
        </tr>
        <tr>
            <td style="padding: 0.5rem; color: {COLORS['warning']};">🟡 NY</td>
            <td style="padding: 0.5rem; color: {COLORS['text']};">20:03-24:00</td>
            <td style="padding: 0.5rem;">{ny_status}</td>
            <td style="padding: 0.5rem; color: {COLORS['text_secondary']}; font-size: 0.85rem;">Pre-position 19:50, box forms 20:03-20:08, primetime ⭐</td>
        </tr>
    </tbody>
</table>
</div>
""", unsafe_allow_html=True)

st.divider()

# ───────────────────────────────────────────────────────────
# 📚 Resources
# ───────────────────────────────────────────────────────────
st.markdown("<h2>📚 Resources</h2>", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"""
    <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid {COLORS['border']};
                border-radius: 12px; padding: 1.25rem 1.5rem; min-height: 140px;">
        <h4 style="margin: 0 0 0.5rem 0; color: {COLORS['text']};">📜 Pinescript Source</h4>
        <p style="color: {COLORS['text_secondary']}; font-size: 0.85rem;">
            Pine v5 indicator full source di GitHub.
        </p>
        <a href="https://github.com/irfanprimaputra/PTBox-Dashboard/blob/main/code/pinescripts/PTBox_e20d.pine"
           target="_blank" style="color: {COLORS['accent_blue']};">→ Open PTBox_e20d.pine</a>
    </div>
    """, unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid {COLORS['border']};
                border-radius: 12px; padding: 1.25rem 1.5rem; min-height: 140px;">
        <h4 style="margin: 0 0 0.5rem 0; color: {COLORS['text']};">📖 Deploy Guide</h4>
        <p style="color: {COLORS['text_secondary']}; font-size: 0.85rem;">
            8-step setup full instructions.
        </p>
        <a href="https://github.com/irfanprimaputra/PTBox-Dashboard/blob/main/code/pinescripts/DEPLOY_GUIDE.md"
           target="_blank" style="color: {COLORS['accent_blue']};">→ Open DEPLOY_GUIDE.md</a>
    </div>
    """, unsafe_allow_html=True)
with c3:
    st.markdown(f"""
    <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid {COLORS['border']};
                border-radius: 12px; padding: 1.25rem 1.5rem; min-height: 140px;">
        <h4 style="margin: 0 0 0.5rem 0; color: {COLORS['text']};">📋 Trade Journal</h4>
        <p style="color: {COLORS['text_secondary']}; font-size: 0.85rem;">
            Per-trade schema + daily/weekly/monthly templates.
        </p>
        <a href="https://github.com/irfanprimaputra/PTBox-Dashboard/blob/main/code/pinescripts/TRADE_JOURNAL_TEMPLATE.md"
           target="_blank" style="color: {COLORS['accent_blue']};">→ Open Journal template</a>
    </div>
    """, unsafe_allow_html=True)

st.caption(f"Page reflects current time. Refresh untuk update countdown. Backtest reference: e33 +4772 fixed-config (Wyckoff pre-session), e20d +976 walk-forward, +1,206 OOS validated.")
