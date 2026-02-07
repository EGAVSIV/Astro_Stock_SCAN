# ============================================================
# 📊 AUTO CYCLE IDENTIFIER (HISTORICAL)
# ============================================================

import requests
import pandas as pd
import streamlit as st
import numpy as np

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(
    page_title="📊 Auto Cycle Identifier",
    layout="wide"
)

st.title("📊 Auto Cycle Identifier (Historical Data)")
st.caption("Automatically discovers dominant stock cycles using bar-based analysis")

GITHUB_DIR_API = (
    "https://api.github.com/repos/EGAVSIV/"
    "Stock_Scanner_With_ASTA_Parameters/contents/stock_data_D"
)

# ============================================================
# DATA LOADER (ROBUST)
# ============================================================
def load_df(url):
    df = pd.read_parquet(url)

    if isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    else:
        for c in df.columns:
            if c.lower() in ("date", "datetime", "timestamp"):
                df.index = pd.to_datetime(df[c], errors="coerce")
                break

    df = df[~df.index.isna()]
    df = df.sort_index()

    if "close" not in df.columns:
        raise ValueError("No close price")

    return df

# ============================================================
# CYCLE DETECTION ENGINE
# ============================================================
def detect_cycles(df, symbol, min_cycle=10, max_cycle=150, threshold=7.0):
    closes = df["close"].values
    dates = df.index

    results = []

    for cycle in range(min_cycle, max_cycle + 1, 5):
        moves = []
        ranges = []

        for i in range(len(closes) - cycle):
            start = closes[i]
            end = closes[i + cycle]
            pct = ((end - start) / start) * 100

            if abs(pct) >= threshold:
                moves.append(pct)
                ranges.append((dates[i].date(), dates[i + cycle].date()))

        if len(moves) >= 5:  # meaningful repetition
            results.append({
                "Symbol": symbol,
                "Cycle_Bars": cycle,
                "Occurrences": len(moves),
                "Avg_%Move": round(np.mean(moves), 2),
                "First_Cycle": f"{ranges[0][0]} → {ranges[0][1]}",
                "Last_Cycle": f"{ranges[-1][0]} → {ranges[-1][1]}"
            })

    return results

# ============================================================
# UI CONTROLS
# ============================================================
col1, col2 = st.columns(2)

with col1:
    threshold = st.slider(
        "Significant Move Threshold (%)",
        3.0, 20.0, 7.0, step=0.5
    )

with col2:
    max_cycle = st.slider(
        "Max Cycle Length (Bars)",
        50, 200, 150, step=10
    )

# ============================================================
# RUN ANALYSIS
# ============================================================
if st.button("🚀 Run Auto Cycle Detection"):
    files = requests.get(GITHUB_DIR_API).json()
    all_cycles = []

    with st.spinner("Analyzing historical cycles..."):
        for f in files:
            if not f["name"].endswith(".parquet"):
                continue

            symbol = f["name"].replace(".parquet", "")
            try:
                df = load_df(f["download_url"])
                cycles = detect_cycles(
                    df,
                    symbol,
                    min_cycle=10,
                    max_cycle=max_cycle,
                    threshold=threshold
                )
                all_cycles.extend(cycles)
            except Exception:
                continue

    if all_cycles:
        result_df = pd.DataFrame(all_cycles)

        st.success(f"✅ {result_df['Symbol'].nunique()} stocks cycle identified")

        st.subheader("📌 Identified Stock Cycles")
        st.dataframe(
            result_df.sort_values(
                ["Occurrences", "Avg_%Move"],
                ascending=False
            ),
            use_container_width=True
        )

        csv = result_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Download Cycle Data",
            csv,
            "auto_cycle_identified.csv",
            "text/csv"
        )
    else:
        st.warning("No dominant cycles found with current parameters.")

# ============================================================
# FOOTER
# ============================================================
st.markdown("""
---
**Auto Cycle Discovery Engine**  
Bar-based | Data-driven | No assumptions  
Built for serious market cycle research 📈
""")
