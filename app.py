"""VADM Research Terminal: a generic dashboard for delivery-enabled NSE symbols."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from vadm.backtest import run_backtest
from vadm.config import StrategyConfig
from vadm.features import build_features
from vadm.fundamentals import attach_point_in_time_pe, extract_annual_fundamentals
from vadm.market_data import fetch_eod2

st.set_page_config(page_title="VADM Research Terminal", page_icon="📈", layout="wide")
st.markdown("""<style>
 .stApp {background:#0b0f14;color:#e6edf3}.block-container{max-width:1500px;padding-top:1.5rem}
 [data-testid='stMetric']{background:#111820;border:1px solid #273341;padding:12px;border-radius:8px}
</style>""", unsafe_allow_html=True)


def chart(data: pd.DataFrame, trades: pd.DataFrame) -> go.Figure:
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=.03, row_heights=[.62,.20,.18], specs=[[{"secondary_y": False}],[{}],[{"secondary_y": True}]])
    fig.add_trace(go.Candlestick(x=data.index, open=data.open, high=data.high, low=data.low, close=data.close, name="Price", increasing_line_color="#31c48d", decreasing_line_color="#f05252"), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data.sma_fast, name="SMA 20", line=dict(color="#fbbf24", width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data.sma_entry, name="SMA 50", line=dict(color="#60a5fa", width=1)), row=1, col=1)
    if not trades.empty:
        fig.add_trace(go.Scatter(x=trades.entry_date, y=trades.entry_price, mode="markers", name="Entry", marker=dict(symbol="triangle-up", size=12, color="#22c55e"), customdata=trades[["bars"]], hovertemplate="Entry %{x}<br>Price ₹%{y:.2f}<extra></extra>"), row=1, col=1)
        fig.add_trace(go.Scatter(x=trades.exit_date, y=trades.exit_price, mode="markers", name="Exit", marker=dict(symbol="triangle-down", size=12, color="#ef4444"), text=trades.reason, hovertemplate="Exit %{x}<br>Price ₹%{y:.2f}<br>%{text}<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Bar(x=data.index, y=data.volume, name="Volume", marker_color="#64748b"), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data.delivery_pct, name="Delivery %", line=dict(color="#a78bfa", width=1)), row=3, col=1, secondary_y=False)
    fig.add_trace(go.Scatter(x=data.index, y=data.vadm_percentile * 100, name="VADM rank", line=dict(color="#f59e0b", width=1)), row=3, col=1, secondary_y=True)
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0b0f14", plot_bgcolor="#0b0f14", height=780, hovermode="x unified", xaxis_rangeslider_visible=False, legend=dict(orientation="h", y=1.02), margin=dict(l=10,r=10,t=50,b=0))
    fig.update_yaxes(title="₹ Price", row=1, col=1); fig.update_yaxes(title="Volume", row=2, col=1); fig.update_yaxes(title="Delivery %", row=3, col=1); fig.update_yaxes(title="VADM rank", range=[0,100], row=3, col=1, secondary_y=True)
    return fig


st.title("VADM Research Terminal")
st.caption("Stock-agnostic, point-in-time valuation × delivery research. Signals execute only on the following session's open.")
with st.sidebar:
    st.header("Data")
    symbol = st.text_input("NSE symbol", "HDFCBANK").upper().replace(".NS", "")
    workbook = st.file_uploader("Annual fundamentals (.xlsx)", type="xlsx")
    st.header("Signal & risk controls")
    lookback = st.number_input("Historical lookback", 126, 756, 252, 21)
    cheap = st.slider("Cheap P/E percentile", .05, .50, .35, .05)
    delivery = st.slider("High delivery percentile", .50, .95, .70, .05)
    entry = st.slider("VADM entry percentile", .70, .99, .90, .01)
    max_hold = st.number_input("Maximum holding days", 5, 252, 63)
    stop = st.slider("Initial ATR stop", 1.0, 5.0, 2.0, .25)
    trail = st.slider("Trailing ATR stop", 1.0, 6.0, 3.0, .25)
    run = st.button("Run research", type="primary", use_container_width=True)

if not run:
    st.info("Upload the stock's annual-fundamentals workbook, set the NSE symbol, then run the research.")
    st.stop()
if workbook is None:
    st.error("Annual fundamentals workbook is required to calculate point-in-time P/E.")
    st.stop()
config = StrategyConfig(percentile_lookback=int(lookback), cheap_pe_percentile=cheap, high_delivery_percentile=delivery, vadm_entry_percentile=entry, max_holding_days=int(max_hold), stop_atr_multiple=stop, trailing_atr_multiple=trail)
try:
    annual = extract_annual_fundamentals(workbook)
    market = fetch_eod2(symbol)
    data = build_features(attach_point_in_time_pe(market, annual, config.filing_lag_days), config)
    result = run_backtest(data, config)
except Exception as exc:
    st.error(str(exc)); st.stop()

c1,c2,c3,c4 = st.columns(4)
c1.metric("Trades", result.metrics["trades"]); c2.metric("Win rate", f"{result.metrics['win_rate']:.1%}"); c3.metric("Strategy return", f"{result.metrics['total_return']:.1%}"); c4.metric("Maximum drawdown", f"{result.metrics['max_drawdown']:.1%}")
tab_chart, tab_trades, tab_research, tab_data = st.tabs(["Trading chart", "Trades", "Research checks", "Data"])
with tab_chart:
    st.plotly_chart(chart(data, result.trades), use_container_width=True, config={"scrollZoom": True, "displaylogo": False, "modeBarButtonsToAdd": ["drawline", "drawopenpath", "drawrect", "drawcircle", "eraseshape"]})
    st.caption("Green markers are actual next-open entries. Red markers are actual exits; the hover label states the exit reason.")
with tab_trades:
    if result.trades.empty: st.warning("No completed trades for this stock and parameter set.")
    else:
        table = result.trades.copy(); table["return"] = table["return"].map("{:.2%}".format); table["entry_price"] = table["entry_price"].map("₹{:.2f}".format); table["exit_price"] = table["exit_price"].map("₹{:.2f}".format)
        st.dataframe(table, use_container_width=True, hide_index=True)
with tab_research:
    st.line_chart(result.equity_curve["equity"])
    st.write("No-lookahead rules: delivery/P-E signal is observed after close, order is placed at next session open; ATR stops use intraday OHLC and assume the worse price when an opening gap crosses the stop.")
with tab_data:
    st.write({"company": annual.attrs.get("company"), "annual_observations": len(annual), "market_sessions": len(market), "valid_feature_sessions": int(data.vadm_percentile.notna().sum())})
    st.dataframe(data.tail(250), use_container_width=True)
