# ============================================================
# 📊 MANUAL CYCLE GAIN / LOSS ENGINE
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
st.caption("Start Date → Fixed Cycle → Sequential Gain/Loss")

GITHUB_DIR_API = (
    "https://api.github.com/repos/EGAVSIV/"
    "Stock_Scanner_With_ASTA_Parameters/contents/stock_data_D"
)

# ============================================================
# DATA LOADER
# ============================================================
@st.cache_data(show_spinner=False)
def load_df(url):
    df = pd.read_parquet(url)
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    return df

@st.cache_data(show_spinner=False)
def load_stock_list():
    files = requests.get(GITHUB_DIR_API).json()
    stocks = {
        f["name"].replace(".parquet", ""): f["download_url"]
        for f in files if f["name"].endswith(".parquet")
    }
    return stocks

# ============================================================
# UI INPUTS
# ============================================================
stocks = load_stock_list()

col1, col2, col3 = st.columns(3)

with col1:
    symbol = st.selectbox("📌 Select Stock", list(stocks.keys()))

with col2:
    start_date = st.date_input(
        "📅 Cycle Start Date",
        value=datetime(2025, 1, 1)
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
# CORE CYCLE LOGIC
# ============================================================
def calculate_cycles(df, symbol, start_date, cycle_len):
    results = []

    # --- Ensure datetime ---
    start_date = pd.to_datetime(start_date)

    # --- Adjust start date if not present ---
    if start_date not in df.index:
        future_dates = df.index[df.index > start_date]
        if len(future_dates) == 0:
            return pd.DataFrame()
        start_date = future_dates[0]

    start_idx = df.index.get_loc(start_date)

    cycle_no = 1
    i = start_idx

    while i + cycle_len < len(df):
        start_row = df.iloc[i]
        end_row = df.iloc[i + cycle_len]

        start_close = start_row["close"]
        end_close = end_row["close"]

        gain_pct = ((end_close - start_close) / start_close) * 100

        results.append({
            "Stock": symbol,
            "Cycle_No": cycle_no,
            "Cycle_Length_Bars": cycle_len,
            "Start_Date": start_row.name.date(),
            "End_Date": end_row.name.date(),
            "Start_Close": round(start_close, 2),
            "End_Close": round(end_close, 2),
            "Gain_%": round(gain_pct, 2)
        })

        cycle_no += 1
        i = i + cycle_len + 1   # 👉 next cycle starts AFTER end bar

    return pd.DataFrame(results)

# ============================================================
# RUN
# ============================================================
if st.button("🚀 Calculate Cycles"):

    df = load_df(stocks[symbol])

    cycle_df = calculate_cycles(
        df,
        symbol,
        start_date,
        cycle_len
    )

    if cycle_df.empty:
        st.warning("No sufficient data for selected inputs.")
    else:
        st.subheader(
            f"📈 {symbol} | Cycle Length = {cycle_len} Bars"
        )

        st.dataframe(
            cycle_df,
            use_container_width=True
        )

        # Summary
        st.markdown("### 📊 Summary")
        st.metric(
            "Total Cycles",
            len(cycle_df)
        )
        st.metric(
            "Avg Gain %",
            round(cycle_df["Gain_%"].mean(), 2)
        )
        st.metric(
            "Winning Cycles %",
            round((cycle_df["Gain_%"] > 0).mean() * 100, 1)
        )

# ============================================================
# FOOTER
# ============================================================
st.markdown("""
---
🧠 **Cycle Truth**  
Fixed time + fixed bars  
= **pure time-based market behavior**

This tool shows **what really happened**, cycle by cycle.
""")
