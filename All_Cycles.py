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
st.caption("Start Date → Fixed Cycle → Sequential Gain/Loss")

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
# CORE CYCLE LOGIC (UNCHANGED)
# ============================================================
def calculate_cycles(df, symbol, start_date, cycle_len):
    results = []

    start_date = pd.to_datetime(start_date)

    if start_date not in df.index:
        future_dates = df.index[df.index > start_date]
        if len(future_dates) == 0:
            return pd.DataFrame()
        start_date = future_dates[0]

    i = df.index.get_loc(start_date)
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
            "Start_Close": round(s.close, 2),
            "End_Close": round(e.close, 2),
            "Gain_%": round(gain_pct, 2)
        })

        cycle_no += 1
        i = i + cycle_len + 1

    return pd.DataFrame(results)

# ============================================================
# UI INPUTS
# ============================================================
stocks = load_stock_list()
min_date, max_date = get_global_date_range(stocks)

col1, col2, col3 = st.columns(3)

with col1:
    select_all = st.checkbox("✅ Select ALL Stocks")

    if select_all:
        selected_stocks = list(stocks.keys())
    else:
        selected_stocks = st.multiselect(
            "📌 Select Stocks",
            list(stocks.keys())
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

    all_cycles = []

    for symbol in selected_stocks:
        df = load_df(stocks[symbol])
        res = calculate_cycles(df, symbol, start_date, cycle_len)
        if not res.empty:
            all_cycles.append(res)

    if not all_cycles:
        st.warning("No sufficient data for selected inputs.")
    else:
        final_df = pd.concat(all_cycles, ignore_index=True)

        st.subheader("📊 Cycle-wise Gain / Loss")
        st.dataframe(final_df, use_container_width=True)

        # ====================================================
        # 📈 DETAILED SUMMARY
        # ====================================================
        st.markdown("## 📈 Detailed Summary")

        total_cycles = len(final_df)
        avg_gain = round(final_df["Gain_%"].mean(), 2)

        pos_5  = (final_df["Gain_%"] > 5).sum()
        pos_10 = (final_df["Gain_%"] > 10).sum()
        pos_15 = (final_df["Gain_%"] > 15).sum()
        pos_20 = (final_df["Gain_%"] > 20).sum()

        neg_5  = (final_df["Gain_%"] < -5).sum()
        neg_10 = (final_df["Gain_%"] < -10).sum()
        neg_15 = (final_df["Gain_%"] < -15).sum()
        neg_20 = (final_df["Gain_%"] < -20).sum()

        c1, c2 = st.columns(2)

        with c1:
            st.metric("Total Cycles", total_cycles)
            st.metric("Average Gain %", avg_gain)

            st.markdown("### ✅ Positive Cycles")
            st.write(f"> 5%  : {pos_5}")
            st.write(f"> 10% : {pos_10}")
            st.write(f"> 15% : {pos_15}")
            st.write(f"> 20% : {pos_20}")

        with c2:
            st.markdown("### ❌ Negative Cycles")
            st.write(f"< -5%  : {neg_5}")
            st.write(f"< -10% : {neg_10}")
            st.write(f"< -15% : {neg_15}")
            st.write(f"< -20% : {neg_20}")

        # ====================================================
        # CSV DOWNLOAD
        # ====================================================
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
🧠 **How to use this summary**
- High `>10%` count → aggressive cycle
- High `<-10%` count → strict stop-loss needed
- Balance tells **long / short suitability**

This is **cycle quality analysis**, not just stats.
""")
