"""
PT Box e44 PULLBACK — Strategy Tester (TV-style).

Mimics https://id.tradingview.com/support/solutions/43000764138/ layout:
- Overview tab: equity curve, drawdown, key metrics
- Performance Summary: full statistics table
- Trades Analysis: per-trade breakdown
- List of Trades: chronological filterable
- Compound Projection: 3 variants (Pesi/Real/Opti)
"""
import json
from pathlib import Path

import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from lib.theme import apply_theme, COLORS

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

st.set_page_config(
    page_title="Strategy Tester — PT Box",
    page_icon="📈",
    layout="wide",
)
apply_theme()


# ─── Load e44 trades ─────────────────────────────────────────────────────────
@st.cache_data
def load_trades():
    p = DATA_DIR / "phase14_e44_pullback_trades.json"
    if not p.exists():
        return None
    raw = json.load(open(p))
    df = pd.DataFrame(raw['trades'])
    df['date'] = pd.to_datetime(df['date'])
    df['weekday'] = df['date'].dt.day_name()
    df['risk_pts'] = (df['entry'] - df['sp']).abs()
    df['win'] = (df['reason'] == 'TP') | ((df['reason'] == 'EOD') & (df['pnl'] > 0))
    df['cum_pnl_pts'] = df['pnl'].cumsum()
    df['cum_pnl_usd_002'] = df['cum_pnl_pts'] * 2  # 0.02 lot
    df['trade_num'] = range(1, len(df) + 1)
    # Attempt index per session-day (1..N within same date+session, ordered by tm_in)
    df = df.sort_values(['date', 'sess', 'tm_in']).reset_index(drop=True)
    df['attempt_idx'] = df.groupby(['date', 'sess']).cumcount() + 1
    df['entry_hour'] = df['tm_in'] // 60
    df['month'] = df['date'].dt.to_period('M').astype(str)
    df['week'] = df['date'].dt.to_period('W').astype(str)
    df['year_month'] = df['date'].dt.strftime('%Y-%m')
    return df

@st.cache_data
def load_compound():
    p = DATA_DIR / "compound_projection.json"
    if not p.exists():
        return None
    return json.load(open(p))


df = load_trades()
compound = load_compound()

if df is None or len(df) == 0:
    st.error("⚠️ e44 trade data not found. Run `python scripts/run_e44_pullback.py` first.")
    st.stop()


# ─── Header ──────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-bottom: 1.5rem;">
    <h1 style="font-size: 2rem; margin: 0;">📈 Strategy Tester — e44 PULLBACK (Pine v15 base)</h1>
    <p style="color: {COLORS['text_secondary']}; margin: 0.25rem 0 0 0;">
        TradingView-style backtest · 5y XAUUSD M1 · 1368 days · 6,574 trades · WR 35→51% with BE Trail v14
    </p>
</div>
""", unsafe_allow_html=True)


# ─── Filters sidebar ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔎 Filter")
    sessions_pick = st.multiselect(
        "Sessions", ["Asia", "London", "NY"],
        default=["Asia", "London", "NY"],
    )
    direction_pick = st.multiselect(
        "Direction", [1, -1],
        default=[1, -1],
        format_func=lambda x: "LONG" if x == 1 else "SHORT",
    )
    weekday_pick = st.multiselect(
        "Weekday",
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Sunday"],
        default=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Sunday"],
    )
    reason_pick = st.multiselect(
        "Exit Reason", ["TP", "SL", "EOD"],
        default=["TP", "SL", "EOD"],
    )
    years = sorted(df['date'].dt.year.unique())
    year_pick = st.multiselect("Year", years, default=years)
    lot_size = st.number_input("Lot size for $ calc", value=0.02, step=0.01, format="%.2f")

# Apply filters
fdf = df[
    df['sess'].isin(sessions_pick)
    & df['dir'].isin(direction_pick)
    & df['weekday'].isin(weekday_pick)
    & df['reason'].isin(reason_pick)
    & df['date'].dt.year.isin(year_pick)
].copy()
fdf['cum_pnl_pts'] = fdf['pnl'].cumsum()
fdf['cum_pnl_usd'] = fdf['cum_pnl_pts'] * (lot_size / 0.01) * 1.0  # $1/pt per 0.01 lot
fdf['trade_num'] = range(1, len(fdf) + 1)

if len(fdf) == 0:
    st.warning("No trades match current filter.")
    st.stop()


# ─── Tabs ────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Overview",
    "📋 Performance Summary",
    "🔍 Trades Analysis",
    "💸 Compound Projection",
    "🔬 Attempt & Time Detail",
])


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║ TAB 1: OVERVIEW                                                        ║
# ╚═══════════════════════════════════════════════════════════════════════╝
with tab1:
    # Key metrics row
    total_trades = len(fdf)
    wins = fdf['win'].sum()
    losses = total_trades - wins
    wr = 100 * wins / total_trades
    net_pnl_pts = fdf['pnl'].sum()
    net_pnl_usd = net_pnl_pts * (lot_size / 0.01) * 1.0
    gross_profit = fdf[fdf['pnl'] > 0]['pnl'].sum()
    gross_loss = fdf[fdf['pnl'] < 0]['pnl'].sum()
    profit_factor = abs(gross_profit / gross_loss) if gross_loss < 0 else float('inf')
    avg_win = fdf[fdf['pnl'] > 0]['pnl'].mean() if wins > 0 else 0
    avg_loss = fdf[fdf['pnl'] < 0]['pnl'].mean() if losses > 0 else 0
    largest_win = fdf['pnl'].max()
    largest_loss = fdf['pnl'].min()

    # Drawdown calc
    fdf_sorted = fdf.sort_values('trade_num').reset_index(drop=True)
    cum = fdf_sorted['cum_pnl_usd']
    running_max = cum.cummax()
    dd = cum - running_max
    max_dd = dd.min()
    max_dd_pct = (max_dd / max(1, running_max.max())) * 100 if running_max.max() > 0 else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        sign = COLORS['success'] if net_pnl_pts > 0 else COLORS['danger']
        st.markdown(f"""
        <div style="background:rgba(0,0,0,0.3); padding:1rem; border-radius:10px; border:1px solid {COLORS['border']};">
            <div style="color:{COLORS['text_secondary']}; font-size:0.7rem; text-transform:uppercase;">Net Profit</div>
            <div style="color:{sign}; font-size:1.6rem; font-weight:800;">{net_pnl_pts:+.0f} pts</div>
            <div style="color:{sign}; font-size:0.85rem;">${net_pnl_usd:+.0f} USD ({lot_size} lot)</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div style="background:rgba(0,0,0,0.3); padding:1rem; border-radius:10px; border:1px solid {COLORS['border']};">
            <div style="color:{COLORS['text_secondary']}; font-size:0.7rem; text-transform:uppercase;">Total Trades</div>
            <div style="color:{COLORS['text']}; font-size:1.6rem; font-weight:800;">{total_trades:,}</div>
            <div style="color:{COLORS['text_secondary']}; font-size:0.85rem;">{wins} W / {losses} L</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div style="background:rgba(0,0,0,0.3); padding:1rem; border-radius:10px; border:1px solid {COLORS['border']};">
            <div style="color:{COLORS['text_secondary']}; font-size:0.7rem; text-transform:uppercase;">Profit Factor</div>
            <div style="color:{COLORS['success'] if profit_factor>1 else COLORS['danger']}; font-size:1.6rem; font-weight:800;">{profit_factor:.2f}</div>
            <div style="color:{COLORS['text_secondary']}; font-size:0.85rem;">Gross W / Gross L</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div style="background:rgba(0,0,0,0.3); padding:1rem; border-radius:10px; border:1px solid {COLORS['border']};">
            <div style="color:{COLORS['text_secondary']}; font-size:0.7rem; text-transform:uppercase;">Win Rate</div>
            <div style="color:{COLORS['text']}; font-size:1.6rem; font-weight:800;">{wr:.1f}%</div>
            <div style="color:{COLORS['text_secondary']}; font-size:0.85rem;">winners / total</div>
        </div>
        """, unsafe_allow_html=True)
    with c5:
        st.markdown(f"""
        <div style="background:rgba(0,0,0,0.3); padding:1rem; border-radius:10px; border:1px solid {COLORS['border']};">
            <div style="color:{COLORS['text_secondary']}; font-size:0.7rem; text-transform:uppercase;">Max Drawdown</div>
            <div style="color:{COLORS['danger']}; font-size:1.6rem; font-weight:800;">${max_dd:+.0f}</div>
            <div style="color:{COLORS['text_secondary']}; font-size:0.85rem;">peak-to-trough</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")

    # Equity curve + drawdown
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.65, 0.35],
        vertical_spacing=0.05,
        subplot_titles=("Equity Curve (cumulative $ at " + str(lot_size) + " lot)", "Drawdown ($)"),
    )
    fig.add_trace(go.Scatter(
        x=fdf_sorted['trade_num'], y=fdf_sorted['cum_pnl_usd'],
        mode='lines', name='Equity', line=dict(color=COLORS['success'], width=2),
        fill='tozeroy', fillcolor=f"rgba(16, 185, 129, 0.1)",
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=fdf_sorted['trade_num'], y=dd,
        mode='lines', name='Drawdown', line=dict(color=COLORS['danger'], width=1.5),
        fill='tozeroy', fillcolor=f"rgba(239, 68, 68, 0.15)",
    ), row=2, col=1)
    fig.update_layout(
        height=600,
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['text']),
    )
    fig.update_xaxes(showgrid=True, gridcolor=COLORS['border'], row=1, col=1)
    fig.update_xaxes(showgrid=True, gridcolor=COLORS['border'], title_text="Trade #", row=2, col=1)
    fig.update_yaxes(showgrid=True, gridcolor=COLORS['border'], row=1, col=1)
    fig.update_yaxes(showgrid=True, gridcolor=COLORS['border'], row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║ TAB 2: PERFORMANCE SUMMARY                                             ║
# ╚═══════════════════════════════════════════════════════════════════════╝
with tab2:
    st.markdown("### Performance Summary")

    # Build TV-style table
    rows = [
        ("Total Net Profit", f"${net_pnl_usd:+.2f}", f"{net_pnl_pts:+.2f} pts"),
        ("Gross Profit", f"${gross_profit * (lot_size/0.01):.2f}", f"{gross_profit:.2f} pts"),
        ("Gross Loss", f"${gross_loss * (lot_size/0.01):.2f}", f"{gross_loss:.2f} pts"),
        ("Total Closed Trades", f"{total_trades:,}", "—"),
        ("Number of Winning Trades", f"{wins}", f"{wr:.2f}%"),
        ("Number of Losing Trades", f"{losses}", f"{100-wr:.2f}%"),
        ("Largest Winning Trade", f"${largest_win * (lot_size/0.01):.2f}", f"{largest_win:.2f} pts"),
        ("Largest Losing Trade", f"${largest_loss * (lot_size/0.01):.2f}", f"{largest_loss:.2f} pts"),
        ("Average Winning Trade", f"${avg_win * (lot_size/0.01):.2f}", f"{avg_win:.2f} pts"),
        ("Average Losing Trade", f"${avg_loss * (lot_size/0.01):.2f}", f"{avg_loss:.2f} pts"),
        ("Profit Factor", f"{profit_factor:.2f}", "—"),
        ("Max Drawdown", f"${max_dd:.2f}", f"{max_dd_pct:.2f}%"),
        ("Avg PnL per Trade", f"${(net_pnl_usd/total_trades):.2f}", f"{(net_pnl_pts/total_trades):.4f} pts"),
        ("Win/Loss Ratio", f"{abs(avg_win/avg_loss):.2f}" if avg_loss != 0 else "∞", "—"),
        ("Sharpe Ratio (approx)", f"{(fdf['pnl'].mean()/fdf['pnl'].std()*np.sqrt(252)):.2f}" if fdf['pnl'].std() > 0 else "—", "—"),
    ]
    perf_df = pd.DataFrame(rows, columns=["Metric", "Value (USD)", "Points / %"])
    st.dataframe(perf_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # By session breakdown
    st.markdown("### By Session")
    sess_rows = []
    for s in ['Asia', 'London', 'NY']:
        sd = fdf[fdf['sess'] == s]
        if len(sd) == 0: continue
        sw = sd['win'].sum(); sl = len(sd) - sw
        s_pnl = sd['pnl'].sum()
        s_pf = abs(sd[sd['pnl']>0]['pnl'].sum() / sd[sd['pnl']<0]['pnl'].sum()) if sd[sd['pnl']<0]['pnl'].sum() < 0 else float('inf')
        sess_rows.append({
            'Session': s, 'Trades': len(sd), 'W': sw, 'L': sl,
            'WR': f"{100*sw/len(sd):.1f}%",
            'Net pts': f"{s_pnl:+.1f}",
            'Net USD': f"${s_pnl * (lot_size/0.01):+.0f}",
            'Avg PnL': f"{sd['pnl'].mean():+.2f}",
            'Worst': f"{sd['pnl'].min():+.1f}",
            'PF': f"{s_pf:.2f}" if s_pf != float('inf') else "∞",
        })
    st.dataframe(pd.DataFrame(sess_rows), use_container_width=True, hide_index=True)

    # By weekday
    st.markdown("### By Weekday")
    wd_rows = []
    for wd in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Sunday']:
        wd_d = fdf[fdf['weekday'] == wd]
        if len(wd_d) == 0: continue
        ww = wd_d['win'].sum(); wl = len(wd_d) - ww
        w_pnl = wd_d['pnl'].sum()
        wd_rows.append({
            'Weekday': wd, 'Trades': len(wd_d), 'W': ww, 'L': wl,
            'WR': f"{100*ww/len(wd_d):.1f}%",
            'Net pts': f"{w_pnl:+.1f}",
            'Net USD': f"${w_pnl * (lot_size/0.01):+.0f}",
        })
    st.dataframe(pd.DataFrame(wd_rows), use_container_width=True, hide_index=True)


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║ TAB 3: TRADES ANALYSIS                                                 ║
# ╚═══════════════════════════════════════════════════════════════════════╝
with tab3:
    st.markdown("### Trade Distribution")

    # Histogram of PnL
    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=fdf['pnl'], nbinsx=50,
            marker=dict(color=COLORS['accent_blue']),
            name='PnL distribution'
        ))
        fig.update_layout(
            title="PnL Distribution (pts)",
            height=350,
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color=COLORS['text']),
            showlegend=False,
        )
        fig.update_xaxes(showgrid=True, gridcolor=COLORS['border'])
        fig.update_yaxes(showgrid=True, gridcolor=COLORS['border'])
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=fdf['risk_pts'], nbinsx=50,
            marker=dict(color=COLORS['warning']),
            name='SL distance'
        ))
        fig.update_layout(
            title="SL Distance Distribution (pts)",
            height=350,
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color=COLORS['text']),
            showlegend=False,
        )
        fig.update_xaxes(showgrid=True, gridcolor=COLORS['border'])
        fig.update_yaxes(showgrid=True, gridcolor=COLORS['border'])
        st.plotly_chart(fig, use_container_width=True)

    # Monthly PnL bars
    st.markdown("### Monthly PnL")
    fdf['month'] = fdf['date'].dt.to_period('M').astype(str)
    monthly = fdf.groupby('month')['pnl'].sum().reset_index()
    monthly['usd'] = monthly['pnl'] * (lot_size/0.01)
    monthly['color'] = monthly['pnl'].apply(lambda x: COLORS['success'] if x > 0 else COLORS['danger'])

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=monthly['month'], y=monthly['usd'],
        marker=dict(color=monthly['color']),
        text=monthly['usd'].round(0).apply(lambda x: f"${int(x):+}"),
        textposition='outside',
    ))
    fig.update_layout(
        title=f"Monthly P&L (USD at {lot_size} lot)",
        height=400,
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['text']),
        showlegend=False,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor=COLORS['border'])
    st.plotly_chart(fig, use_container_width=True)

    # Win/Loss streaks
    st.markdown("### Win / Loss Streaks")
    s_cur = 0; max_w = 0; max_l = 0; cur_l = 0
    streaks_w = []; streaks_l = []
    for w in fdf_sorted['win']:
        if w:
            if cur_l > 0: streaks_l.append(cur_l)
            s_cur += 1; cur_l = 0
            max_w = max(max_w, s_cur)
        else:
            if s_cur > 0: streaks_w.append(s_cur)
            cur_l += 1; s_cur = 0
            max_l = max(max_l, cur_l)

    streaks_df = pd.DataFrame({
        'Metric': ['Max Consecutive Wins', 'Max Consecutive Losses', 'Avg Win Streak', 'Avg Loss Streak'],
        'Value': [max_w, max_l,
                  f"{np.mean(streaks_w):.1f}" if streaks_w else "0",
                  f"{np.mean(streaks_l):.1f}" if streaks_l else "0"],
    })
    st.dataframe(streaks_df, use_container_width=True, hide_index=True)


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║ TAB 4: COMPOUND PROJECTION                                             ║
# ╚═══════════════════════════════════════════════════════════════════════╝
with tab4:
    st.markdown("### Compound Projection — 3 Variants")
    st.markdown(f"Base: e44 backtest +$1,584/yr at 0.02 lot · Lot scales +0.01 per +$100 cap")

    if compound is None:
        st.warning("Compound data not found. Run script first.")
    else:
        # Build chart
        fig = go.Figure()
        colors_v = {'Pesimistik (30%)': COLORS['danger'], 'Realistik (60%)': COLORS['warning'], 'Optimistik (90%)': COLORS['success']}

        for name, vdata in compound['variants'].items():
            months = [h['month'] for h in vdata['history']]
            caps = [h['cap_end'] for h in vdata['history']]
            fig.add_trace(go.Scatter(
                x=months, y=caps,
                mode='lines+markers', name=name,
                line=dict(color=colors_v.get(name, COLORS['accent_blue']), width=2),
                marker=dict(size=4),
            ))

        fig.update_layout(
            title="Capital Growth — 24 month projection (log scale)",
            height=500,
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color=COLORS['text']),
            yaxis_type="log",
            xaxis_title="Month",
            yaxis_title="Capital (USD, log scale)",
        )
        fig.update_xaxes(showgrid=True, gridcolor=COLORS['border'])
        fig.update_yaxes(showgrid=True, gridcolor=COLORS['border'])
        st.plotly_chart(fig, use_container_width=True)

        # Side-by-side table
        st.markdown("### Month-by-month comparison")
        table_data = []
        for i in range(24):
            row = {'Month': f"M{i+1}"}
            row['Lot'] = compound['variants']['Realistik (60%)']['history'][i]['lot']
            for name in ['Pesimistik (30%)', 'Realistik (60%)', 'Optimistik (90%)']:
                h = compound['variants'][name]['history'][i]
                row[f"{name.split(' ')[0]} cap"] = f"${h['cap_end']:,.0f}"
                row[f"{name.split(' ')[0]} earn"] = f"+${h['monthly_earn']:,.0f}"
            table_data.append(row)
        st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### ⚠️ Reality Caveats")
        st.markdown("""
        - **Pesimistik (30%)** = include slippage, spread, missed signals, emotion errors. Closest to real first-year for new trader.
        - **Realistik (60%)** = good execution, occasional missed setups. Year-1 target if disciplined.
        - **Optimistik (90%)** = near-perfect, no slippage. Mathematical projection only — **NOT achievable in reality** at high lot sizes due to broker liquidity + variance.
        - **17 consecutive losses** observed in 5y backtest. Year-2+ optimistic projection unrealistic — drawdowns scale with lot size.
        - Real expectation: **Pesimistik to Realistik range** ($1,500 - $8,000 year-1).
        """)


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║ TAB 5: ATTEMPT & TIME DETAIL                                           ║
# ╚═══════════════════════════════════════════════════════════════════════╝
with tab5:
    st.markdown("### 🔬 Attempt-Level & Time-Aggregated Breakdown")
    st.caption(f"Max attempt = 5 per session per day (Asia/London/NY). Filtered: {len(fdf):,} trades · Lot {lot_size}")

    # ─── A. Per-Attempt WR + PnL ────────────────────────────────────────────
    st.markdown("#### A. Per-Attempt Performance (1st → 5th attempt within session-day)")
    att_grp = fdf.groupby('attempt_idx').agg(
        n=('pnl', 'count'),
        wins=('win', 'sum'),
        pnl_total=('pnl', 'sum'),
        avg_pnl=('pnl', 'mean'),
        avg_risk=('risk_pts', 'mean'),
        avg_win_pnl=('pnl', lambda x: x[x > 0].mean() if (x > 0).any() else 0),
        avg_loss_pnl=('pnl', lambda x: x[x <= 0].mean() if (x <= 0).any() else 0),
    ).reset_index()
    att_grp['wr_pct'] = (att_grp['wins'] / att_grp['n'] * 100).round(1)
    att_grp['loss_pct'] = (100 - att_grp['wr_pct']).round(1)
    att_grp['pnl_usd'] = (att_grp['pnl_total'] * (lot_size / 0.01)).round(0)
    att_grp['pf'] = att_grp.apply(
        lambda r: round(abs(fdf[(fdf['attempt_idx'] == r['attempt_idx']) & (fdf['pnl'] > 0)]['pnl'].sum() /
                              fdf[(fdf['attempt_idx'] == r['attempt_idx']) & (fdf['pnl'] < 0)]['pnl'].sum()), 2)
        if fdf[(fdf['attempt_idx'] == r['attempt_idx']) & (fdf['pnl'] < 0)]['pnl'].sum() < 0 else float('nan'),
        axis=1,
    )
    att_disp = att_grp[['attempt_idx', 'n', 'wr_pct', 'loss_pct', 'pnl_total', 'pnl_usd', 'avg_pnl', 'avg_risk', 'avg_win_pnl', 'avg_loss_pnl', 'pf']].copy()
    att_disp.columns = ['Attempt #', 'Trades', 'Win %', 'Loss %', 'PnL pts', 'PnL $', 'Avg PnL', 'Avg Risk', 'Avg Win', 'Avg Loss', 'PF']
    st.dataframe(att_disp, use_container_width=True, hide_index=True)

    # Bar chart: WR vs Loss% per attempt
    fig_att = go.Figure()
    fig_att.add_trace(go.Bar(name='Win %', x=att_grp['attempt_idx'], y=att_grp['wr_pct'], marker_color=COLORS['success']))
    fig_att.add_trace(go.Bar(name='Loss %', x=att_grp['attempt_idx'], y=att_grp['loss_pct'], marker_color=COLORS['danger']))
    fig_att.update_layout(barmode='stack', height=280, margin=dict(t=20, b=20),
                          xaxis_title='Attempt # within session-day', yaxis_title='%',
                          plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                          font_color=COLORS['text'])
    st.plotly_chart(fig_att, use_container_width=True)

    # ─── B. Per-Attempt × Per-Session Matrix ────────────────────────────────
    st.markdown("#### B. Per-Attempt × Per-Session Matrix")
    matrix = fdf.groupby(['sess', 'attempt_idx']).agg(
        n=('pnl', 'count'),
        wins=('win', 'sum'),
        pnl=('pnl', 'sum'),
    ).reset_index()
    matrix['wr_pct'] = (matrix['wins'] / matrix['n'] * 100).round(1)
    pivot_wr = matrix.pivot(index='sess', columns='attempt_idx', values='wr_pct').fillna(0)
    pivot_pnl = matrix.pivot(index='sess', columns='attempt_idx', values='pnl').fillna(0)
    pivot_n = matrix.pivot(index='sess', columns='attempt_idx', values='n').fillna(0).astype(int)

    cA, cB = st.columns(2)
    with cA:
        st.markdown("**Win Rate % (per session × attempt)**")
        st.dataframe(pivot_wr.round(1).rename_axis(index='Session', columns='Attempt #'),
                     use_container_width=True)
    with cB:
        st.markdown("**Net PnL pts (per session × attempt)**")
        st.dataframe(pivot_pnl.round(0).astype(int).rename_axis(index='Session', columns='Attempt #'),
                     use_container_width=True)

    st.markdown("**Trade Count (per session × attempt)**")
    st.dataframe(pivot_n.rename_axis(index='Session', columns='Attempt #'), use_container_width=True)

    # ─── C. Attempt Cascade — % session-days firing N attempts ─────────────
    st.markdown("#### C. Attempt Cascade — % session-days firing N attempts")
    sess_day_max = fdf.groupby(['date', 'sess'])['attempt_idx'].max().reset_index(name='max_att')
    cascade = []
    for sess in ['Asia', 'London', 'NY']:
        sub = sess_day_max[sess_day_max['sess'] == sess]
        if len(sub) == 0: continue
        total_days = len(sub)
        for n in [1, 2, 3, 4, 5]:
            pct = (sub['max_att'] >= n).sum() / total_days * 100
            cascade.append({'Session': sess, 'Attempt ≥': n, '% session-days': round(pct, 1),
                            'Days': int((sub['max_att'] >= n).sum())})
    cdf = pd.DataFrame(cascade)
    cpiv = cdf.pivot(index='Session', columns='Attempt ≥', values='% session-days')
    st.dataframe(cpiv.rename_axis(columns='Fire ≥ N attempts'), use_container_width=True)

    avg_att = sess_day_max.groupby('sess')['max_att'].mean().round(2)
    st.markdown(f"**Avg attempts per session-day:** Asia={avg_att.get('Asia', 0)} · London={avg_att.get('London', 0)} · NY={avg_att.get('NY', 0)}")

    # ─── D. Monthly PnL ────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### D. Monthly PnL Aggregation")
    monthly = fdf.groupby('year_month').agg(
        trades=('pnl', 'count'),
        wins=('win', 'sum'),
        pnl_pts=('pnl', 'sum'),
    ).reset_index()
    monthly['wr_pct'] = (monthly['wins'] / monthly['trades'] * 100).round(1)
    monthly['pnl_usd'] = (monthly['pnl_pts'] * (lot_size / 0.01)).round(0)
    monthly = monthly.sort_values('year_month')

    fig_m = go.Figure()
    colors_m = [COLORS['success'] if v >= 0 else COLORS['danger'] for v in monthly['pnl_pts']]
    fig_m.add_trace(go.Bar(x=monthly['year_month'], y=monthly['pnl_pts'], marker_color=colors_m,
                            text=monthly['pnl_pts'].round(0), textposition='outside'))
    fig_m.update_layout(height=400, margin=dict(t=30, b=20),
                        xaxis_title='Month', yaxis_title='Net PnL (pts)',
                        title='Monthly Net PnL — green=profit, red=loss',
                        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                        font_color=COLORS['text'])
    st.plotly_chart(fig_m, use_container_width=True)

    cM1, cM2, cM3, cM4 = st.columns(4)
    pos_months = (monthly['pnl_pts'] > 0).sum()
    neg_months = (monthly['pnl_pts'] < 0).sum()
    avg_month_pnl = monthly['pnl_pts'].mean()
    avg_month_usd = monthly['pnl_usd'].mean()
    best_m = monthly.loc[monthly['pnl_pts'].idxmax()]
    worst_m = monthly.loc[monthly['pnl_pts'].idxmin()]
    cM1.metric("Months Profitable", f"{pos_months} / {len(monthly)}",
               f"{100*pos_months/len(monthly):.0f}%")
    cM2.metric("Avg Monthly PnL", f"{avg_month_pnl:+.0f} pts", f"${avg_month_usd:+,.0f}")
    cM3.metric("Best Month", f"{best_m['pnl_pts']:+.0f} pts", best_m['year_month'])
    cM4.metric("Worst Month", f"{worst_m['pnl_pts']:+.0f} pts", worst_m['year_month'])

    # ─── E. Weekly PnL ─────────────────────────────────────────────────────
    st.markdown("#### E. Weekly PnL Aggregation")
    weekly = fdf.groupby('week').agg(
        trades=('pnl', 'count'),
        wins=('win', 'sum'),
        pnl_pts=('pnl', 'sum'),
    ).reset_index()
    weekly['wr_pct'] = (weekly['wins'] / weekly['trades'] * 100).round(1)
    weekly['pnl_usd'] = (weekly['pnl_pts'] * (lot_size / 0.01)).round(0)
    weekly = weekly.sort_values('week')

    fig_w = go.Figure()
    colors_w = [COLORS['success'] if v >= 0 else COLORS['danger'] for v in weekly['pnl_pts']]
    fig_w.add_trace(go.Bar(x=weekly['week'], y=weekly['pnl_pts'], marker_color=colors_w))
    fig_w.update_layout(height=350, margin=dict(t=30, b=20),
                        xaxis_title='Week', yaxis_title='Net PnL (pts)',
                        title='Weekly Net PnL (5y)',
                        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                        font_color=COLORS['text'])
    fig_w.update_xaxes(tickmode='auto', nticks=20)
    st.plotly_chart(fig_w, use_container_width=True)

    cW1, cW2, cW3, cW4 = st.columns(4)
    pos_weeks = (weekly['pnl_pts'] > 0).sum()
    neg_weeks = (weekly['pnl_pts'] < 0).sum()
    avg_week_pnl = weekly['pnl_pts'].mean()
    avg_week_usd = weekly['pnl_usd'].mean()
    best_w = weekly.loc[weekly['pnl_pts'].idxmax()]
    worst_w = weekly.loc[weekly['pnl_pts'].idxmin()]
    cW1.metric("Weeks Profitable", f"{pos_weeks} / {len(weekly)}",
               f"{100*pos_weeks/len(weekly):.0f}%")
    cW2.metric("Avg Weekly PnL", f"{avg_week_pnl:+.1f} pts", f"${avg_week_usd:+,.0f}")
    cW3.metric("Best Week", f"{best_w['pnl_pts']:+.0f} pts", best_w['week'])
    cW4.metric("Worst Week", f"{worst_w['pnl_pts']:+.0f} pts", worst_w['week'])

    # ─── F. Daily PnL (Best/Worst) ────────────────────────────────────────
    st.markdown("#### F. Daily PnL Distribution")
    daily = fdf.groupby('date').agg(
        trades=('pnl', 'count'),
        wins=('win', 'sum'),
        pnl_pts=('pnl', 'sum'),
    ).reset_index()
    daily['wr_pct'] = (daily['wins'] / daily['trades'] * 100).round(1)

    cD1, cD2, cD3, cD4 = st.columns(4)
    pos_days = (daily['pnl_pts'] > 0).sum()
    neg_days = (daily['pnl_pts'] < 0).sum()
    flat_days = (daily['pnl_pts'] == 0).sum()
    cD1.metric("Days Profitable", f"{pos_days} / {len(daily)}",
               f"{100*pos_days/len(daily):.0f}%")
    cD2.metric("Days Neutral/Flat", f"{flat_days}", "no PnL")
    cD3.metric("Best Day", f"{daily['pnl_pts'].max():+.0f} pts",
               daily.loc[daily['pnl_pts'].idxmax(), 'date'].strftime('%Y-%m-%d'))
    cD4.metric("Worst Day", f"{daily['pnl_pts'].min():+.0f} pts",
               daily.loc[daily['pnl_pts'].idxmin(), 'date'].strftime('%Y-%m-%d'))

    # ─── G. Direction × Session Matrix ────────────────────────────────────
    st.markdown("#### G. Direction × Session WR Matrix")
    dir_matrix = fdf.groupby(['sess', 'dir']).agg(
        n=('pnl', 'count'),
        wins=('win', 'sum'),
        pnl=('pnl', 'sum'),
    ).reset_index()
    dir_matrix['wr_pct'] = (dir_matrix['wins'] / dir_matrix['n'] * 100).round(1)
    dir_matrix['dir_label'] = dir_matrix['dir'].apply(lambda x: 'LONG' if x == 1 else 'SHORT')
    dir_pivot_wr = dir_matrix.pivot(index='sess', columns='dir_label', values='wr_pct').fillna(0)
    dir_pivot_pnl = dir_matrix.pivot(index='sess', columns='dir_label', values='pnl').fillna(0)
    dir_pivot_n = dir_matrix.pivot(index='sess', columns='dir_label', values='n').fillna(0).astype(int)

    cG1, cG2, cG3 = st.columns(3)
    with cG1:
        st.markdown("**Win Rate %**")
        st.dataframe(dir_pivot_wr, use_container_width=True)
    with cG2:
        st.markdown("**Net PnL pts**")
        st.dataframe(dir_pivot_pnl.round(0).astype(int), use_container_width=True)
    with cG3:
        st.markdown("**Trade Count**")
        st.dataframe(dir_pivot_n, use_container_width=True)

    # ─── H. Weekday Performance ────────────────────────────────────────────
    st.markdown("#### H. Weekday Performance")
    wd_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Sunday']
    wd_grp = fdf.groupby('weekday').agg(
        n=('pnl', 'count'),
        wins=('win', 'sum'),
        pnl=('pnl', 'sum'),
        avg_pnl=('pnl', 'mean'),
    ).reset_index()
    wd_grp['wr_pct'] = (wd_grp['wins'] / wd_grp['n'] * 100).round(1)
    wd_grp['weekday'] = pd.Categorical(wd_grp['weekday'], categories=wd_order, ordered=True)
    wd_grp = wd_grp.sort_values('weekday').reset_index(drop=True)
    wd_grp['pnl_usd'] = (wd_grp['pnl'] * (lot_size / 0.01)).round(0)
    wd_disp = wd_grp[['weekday', 'n', 'wr_pct', 'pnl', 'pnl_usd', 'avg_pnl']].copy()
    wd_disp.columns = ['Weekday', 'Trades', 'WR %', 'PnL pts', 'PnL $', 'Avg PnL/trade']
    st.dataframe(wd_disp, use_container_width=True, hide_index=True)

    fig_wd = go.Figure()
    colors_wd = [COLORS['success'] if v >= 0 else COLORS['danger'] for v in wd_grp['pnl']]
    fig_wd.add_trace(go.Bar(x=wd_grp['weekday'], y=wd_grp['pnl'], marker_color=colors_wd,
                             text=[f"{v:+.0f}" for v in wd_grp['pnl']], textposition='outside'))
    fig_wd.update_layout(height=320, margin=dict(t=30, b=20),
                         xaxis_title='Weekday', yaxis_title='Net PnL (pts)',
                         title='Weekday Net PnL distribution',
                         plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                         font_color=COLORS['text'])
    st.plotly_chart(fig_wd, use_container_width=True)

    # ─── I. Streak Analysis ────────────────────────────────────────────────
    st.markdown("#### I. Streak Analysis (consecutive W/L)")
    sorted_t = fdf.sort_values(['date', 'tm_in']).reset_index(drop=True)
    streaks = []
    cur_type = None; cur_len = 0; max_w = 0; max_l = 0
    for _, t in sorted_t.iterrows():
        is_w = t['win']
        if is_w and cur_type == 'W':
            cur_len += 1
        elif (not is_w) and cur_type == 'L':
            cur_len += 1
        else:
            if cur_type == 'W': max_w = max(max_w, cur_len)
            elif cur_type == 'L': max_l = max(max_l, cur_len)
            cur_type = 'W' if is_w else 'L'
            cur_len = 1
    if cur_type == 'W': max_w = max(max_w, cur_len)
    elif cur_type == 'L': max_l = max(max_l, cur_len)

    cS1, cS2, cS3, cS4 = st.columns(4)
    cS1.metric("Max Consec Wins", str(max_w), "single streak")
    cS2.metric("Max Consec Losses", str(max_l), "single streak")
    cS3.metric("Avg Win Streak", f"{(fdf['win'].astype(int).groupby((~fdf['win']).cumsum()).cumsum().max()):.1f}")
    cS4.metric("Mental Reality", f"{max_l} losses possible", "size for worst streak")

    # ─── J. Hour-of-Day Distribution ───────────────────────────────────────
    st.markdown("#### J. Entry Hour-of-Day Distribution")
    hour_grp = fdf.groupby('entry_hour').agg(
        n=('pnl', 'count'),
        wins=('win', 'sum'),
        pnl=('pnl', 'sum'),
    ).reset_index()
    hour_grp['wr_pct'] = (hour_grp['wins'] / hour_grp['n'] * 100).round(1)

    fig_hr = make_subplots(specs=[[{"secondary_y": True}]])
    fig_hr.add_trace(go.Bar(x=hour_grp['entry_hour'], y=hour_grp['n'],
                             name='Trades', marker_color=COLORS['border'], opacity=0.7), secondary_y=False)
    fig_hr.add_trace(go.Scatter(x=hour_grp['entry_hour'], y=hour_grp['pnl'],
                                 name='PnL pts', line=dict(color=COLORS['success'], width=3)), secondary_y=True)
    fig_hr.update_layout(height=350, margin=dict(t=30, b=20),
                         title='Trade volume + PnL per ET hour-of-day',
                         plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                         font_color=COLORS['text'])
    fig_hr.update_xaxes(title='ET Hour', tickmode='linear', dtick=1)
    fig_hr.update_yaxes(title='Trade count', secondary_y=False)
    fig_hr.update_yaxes(title='PnL pts', secondary_y=True)
    st.plotly_chart(fig_hr, use_container_width=True)

    # ─── K. Exit Reason Distribution per Session ──────────────────────────
    st.markdown("#### K. Exit Reason Distribution per Session")
    reason_pivot = fdf.groupby(['sess', 'reason']).size().unstack(fill_value=0)
    reason_pct = reason_pivot.div(reason_pivot.sum(axis=1), axis=0) * 100
    cR1, cR2 = st.columns(2)
    with cR1:
        st.markdown("**Trade Count by Exit Reason**")
        st.dataframe(reason_pivot, use_container_width=True)
    with cR2:
        st.markdown("**% of Total per Session**")
        st.dataframe(reason_pct.round(1), use_container_width=True)


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║ List of Trades (footer)                                                ║
# ╚═══════════════════════════════════════════════════════════════════════╝
st.markdown("---")
with st.expander(f"📋 List of Trades ({len(fdf)} filtered, sorted by date)", expanded=False):
    show_df = fdf[['date', 'sess', 'dir', 'tm_in', 'entry', 'sp', 'tp', 'risk_pts', 'reason', 'pnl', 'cum_pnl_pts']].copy()
    show_df['dir'] = show_df['dir'].apply(lambda x: 'LONG' if x == 1 else 'SHORT')
    show_df['date'] = show_df['date'].dt.strftime('%Y-%m-%d')
    show_df['tm_in'] = show_df['tm_in'].apply(lambda x: f"{x//60:02d}:{x%60:02d}")
    show_df.columns = ['Date', 'Session', 'Dir', 'Entry Time', 'Entry $', 'SL $', 'TP $', 'Risk pts', 'Exit', 'PnL pts', 'Cumul pts']
    st.dataframe(show_df, use_container_width=True, hide_index=True, height=400)
