# ============================================================
# 📊 MANUAL CYCLE GAIN / LOSS ENGINE (MULTI-STOCK + SUMMARY)
# ============================================================

import requests
import pandas as pd
import streamlit as st
from datetime import datetime

# ============================================================
# CONFIG
# ============================================================
st.set_page_config("Manual Cycle Gain Engine", layout="wide")
st.title("📊 Manual Cycle Gain / Loss Calculator")
st.caption("Completed | Running | Upcoming Cycles")

GITHUB_DIR_API = (
    "https://api.github.com/repos/EGAVSIV/"
    "Stock_Scanner_With_ASTA_Parameters/contents/stock_data_D"
)

# ============================================================
# DATA LOADERS
# ============================================================
@st.cache_data(show_spinner=False)
def load_df(url):
    df = pd.read_parquet(url)
    df.index = pd.to_datetime(df.index)
    return df.sort_index()

@st.cache_data(show_spinner=False)
def load_stock_list():
    files = requests.get(GITHUB_DIR_API).json()
    return {
        f["name"].replace(".parquet", ""): f["download_url"]
        for f in files if f["name"].endswith(".parquet")
    }

@st.cache_data(show_spinner=False)
def get_global_date_range(stocks):
    mins, maxs = [], []
    for url in stocks.values():
        df = load_df(url)
        mins.append(df.index.min())
        maxs.append(df.index.max())
    return min(mins), max(maxs)

# ============================================================
# CORE CYCLE LOGIC (COMPLETED CYCLES)
# ============================================================
def calculate_cycles(df, symbol, start_date, cycle_len):
    results = []

    start_date = pd.to_datetime(start_date)

    if start_date not in df.index:
        future_dates = df.index[df.index > start_date]
        if len(future_dates) == 0:
            return pd.DataFrame(), None, None
        start_date = future_dates[0]

    start_idx = df.index.get_loc(start_date)
    i = start_idx
    cycle_no = 1

    while i + cycle_len < len(df):
        s = df.iloc[i]
        e = df.iloc[i + cycle_len]

        gain_pct = ((e.close - s.close) / s.close) * 100

        results.append({
            "Stock": symbol,
            "Cycle_No": cycle_no,
            "Cycle_Length_Bars": cycle_len,
            "Start_Date": s.name.date(),
            "End_Date": e.name.date(),
            "Gain_%": round(gain_pct, 2)
        })

        cycle_no += 1
        i = i + cycle_len + 1

    # ================= RUNNING CYCLE =================
    running = None
    upcoming = None

    if i < len(df):
        s = df.iloc[i]
        last = df.iloc[-1]

        running_gain = ((last.close - s.close) / s.close) * 100
        expected_end_idx = min(i + cycle_len, len(df) - 1)

        running = {
            "Stock": symbol,
            "Start_Date": s.name.date(),
            "Expected_End_Date": df.index[expected_end_idx].date(),
            "Gain_%_So_Far": round(running_gain, 2),
            "Remark": "🟡 Running Cycle"
        }

        # ================= UPCOMING CYCLE =================
        next_start_idx = expected_end_idx + 1
        if next_start_idx < len(df):
            next_end_idx = min(next_start_idx + cycle_len, len(df) - 1)

            upcoming = {
                "Stock": symbol,
                "Start_Date": df.index[next_start_idx].date(),
                "Expected_End_Date": df.index[next_end_idx].date(),
                "Remark": "🔮 Upcoming Cycle"
            }

    return pd.DataFrame(results), running, upcoming

# ============================================================
# UI INPUTS
# ============================================================
stocks = load_stock_list()
min_date, max_date = get_global_date_range(stocks)

col1, col2, col3 = st.columns(3)

with col1:
    select_all = st.checkbox("✅ Select ALL Stocks")
    selected_stocks = list(stocks.keys()) if select_all else st.multiselect(
        "📌 Select Stocks", list(stocks.keys())
    )

with col2:
    start_date = st.date_input(
        "📅 Cycle Start Date",
        value=min_date.date(),
        min_value=min_date.date(),
        max_value=max_date.date()
    )

with col3:
    cycle_len = st.number_input(
        "🔁 Cycle Length (Bars)",
        min_value=1,
        max_value=250,
        value=21,
        step=1
    )

# ============================================================
# RUN
# ============================================================
if st.button("🚀 Calculate Cycles") and selected_stocks:

    completed_all = []
    running_all = []
    upcoming_all = []

    for symbol in selected_stocks:
        df = load_df(stocks[symbol])
        comp, run, up = calculate_cycles(df, symbol, start_date, cycle_len)

        if not comp.empty:
            completed_all.append(comp)
        if run:
            running_all.append(run)
        if up:
            upcoming_all.append(up)

    # ================= COMPLETED =================
    if completed_all:
        final_df = pd.concat(completed_all, ignore_index=True)

        st.subheader("📊 Completed Cycles")
        st.dataframe(final_df, use_container_width=True)

        # ================= SUMMARY =================
        st.markdown("## 📈 Detailed Summary")

        st.metric("Total Cycles", len(final_df))
        st.metric("Average Gain %", round(final_df["Gain_%"].mean(), 2))

    # ================= RUNNING =================
    if running_all:
        st.subheader("🟡 Running Cycles (Not Completed)")
        st.dataframe(pd.DataFrame(running_all), use_container_width=True)

    # ================= UPCOMING =================
    if upcoming_all:
        st.subheader("🔮 Upcoming Cycles")
        st.dataframe(pd.DataFrame(upcoming_all), use_container_width=True)

    # ================= CSV DOWNLOAD =================
    if completed_all:
        csv_data = final_df.to_csv(index=False)

        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name="cycle_gain_analysis.csv",
            mime="text/csv"
        )

# ============================================================
# FOOTER
# ============================================================
st.markdown("""
---
🧠 **Interpretation**
- 🟡 Running cycle → manage risk, avoid fresh entries
- 🔮 Upcoming cycle → prepare watchlist & alerts
- Completed cycles → validate cycle strength

This adds **time awareness** to cycle trading.
""")
