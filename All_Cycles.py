# ============================================================
# 📊 Cycle Based Stock Scanner (Parquet | No Astrology)
# Designed by: Gaurav Singh Yadav
# ============================================================

import datetime
import requests
import pandas as pd
import streamlit as st
import matplotlib
from matplotlib.figure import Figure
import mplfinance as mpf

matplotlib.use("Agg")

# ============================================================
# STREAMLIT CONFIG
# ============================================================
st.set_page_config(
    page_title="📊 Cycle Based Stock Scanner",
    page_icon="📈",
    layout="wide",
)

st.title("📊 Cycle Based Stock Scanner (Pure Price & Time)")
st.caption("Exact N-th Bar Cycle Analysis | Parquet Data | Threshold Based")

# ============================================================
# GITHUB PARQUET DIRECTORY
# ============================================================
GITHUB_DIR_API = (
    "https://api.github.com/repos/EGAVSIV/"
    "Stock_Scanner_With_ASTA_Parameters/contents/stock_data_D"
)

# ============================================================
# DATA LOADER
# ============================================================
def load_github_df(url: str) -> pd.DataFrame:
    df = pd.read_parquet(url, engine="pyarrow")

    datetime_cols = [
        c for c in df.columns
        if c.lower() in ("datetime", "date", "time", "timestamp")
    ]

    if datetime_cols:
        df.index = pd.to_datetime(df[datetime_cols[0]])
    else:
        df.index = pd.to_datetime(df.index)

    if "timeframe" in df.columns:
        df = df[df["timeframe"] == "D"]

    required = {"open", "high", "low", "close"}
    if not required.issubset(df.columns):
        raise ValueError("Missing OHLC columns")

    return df.sort_index()

# ============================================================
# CORE CYCLE ANALYSIS
# ============================================================
def analyze_symbol_for_cycles(
    df: pd.DataFrame,
    symbol: str,
    start_date: datetime.date,
    cycles: list,
    threshold: float
):
    results = []

    if start_date not in df.index.date:
        return results

    start_idx = df.index[df.index.date == start_date][0]
    start_pos = df.index.get_loc(start_idx)
    start_close = float(df.loc[start_idx, "close"])

    for c in cycles:
        target_pos = start_pos + c
        if target_pos >= len(df):
            continue

        target_idx = df.index[target_pos]
        target_close = float(df.iloc[target_pos]["close"])

        pct_change = ((target_close - start_close) / start_close) * 100

        if pct_change >= threshold or pct_change <= -threshold:
            results.append({
                "symbol": symbol,
                "cycle_days": c,
                "start_date": start_date,
                "end_date": target_idx.date(),
                "start_close": round(start_close, 2),
                "end_close": round(target_close, 2),
                "pct_change": round(pct_change, 2),
                "direction": "UP" if pct_change > 0 else "DOWN",
            })

    return results

# ============================================================
# SESSION STATE
# ============================================================
if "scan_results" not in st.session_state:
    st.session_state["scan_results"] = pd.DataFrame()

# ============================================================
# UI CONTROLS
# ============================================================
st.subheader("⚙️ Scan Settings")

col1, col2, col3 = st.columns(3)

with col1:
    start_date = st.date_input("📅 Start Date")

with col2:
    threshold = st.slider(
        "📏 Threshold % Move",
        min_value=2.0,
        max_value=20.0,
        value=6.0,
        step=0.5
    )

with col3:
    cycles = st.multiselect(
        "🔁 Cycle Days",
        [21, 42, 63, 84, 105, 126, 147],
        default=[21, 42, 63]
    )

# ============================================================
# RUN SCAN
# ============================================================
if st.button("🚀 Run Cycle Scan"):
    files = requests.get(GITHUB_DIR_API).json()
    all_results = []

    with st.spinner("Scanning Parquet files..."):
        for f in files:
            if not f["name"].endswith(".parquet"):
                continue

            symbol = f["name"].replace(".parquet", "")
            url = f["download_url"]

            try:
                df = load_github_df(url)
            except Exception:
                continue

            res = analyze_symbol_for_cycles(
                df=df,
                symbol=symbol,
                start_date=start_date,
                cycles=cycles,
                threshold=threshold
            )

            all_results.extend(res)

    st.session_state["scan_results"] = pd.DataFrame(all_results)

# ============================================================
# RESULTS
# ============================================================
df_res = st.session_state["scan_results"]

if df_res.empty:
    st.info("No scan results yet.")
else:
    st.subheader("📌 Summary (Occurrence Based)")

    summary = (
        df_res
        .groupby("symbol")
        .agg(
            Occurrences=("symbol", "count"),
            Avg_Move=("pct_change", "mean"),
            Max_Gain=("pct_change", "max"),
            Max_Loss=("pct_change", "min")
        )
        .reset_index()
    )

    min_occ = st.slider("Minimum Occurrences", 1, 10, 1)
    summary = summary[summary["Occurrences"] >= min_occ]

    st.dataframe(summary, use_container_width=True)

    st.subheader("📋 Detailed Cycle Events")
    df_filtered = df_res[df_res["symbol"].isin(summary["symbol"])]
    st.dataframe(df_filtered, use_container_width=True)

    csv = df_filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Download CSV",
        csv,
        "cycle_scan_results.csv",
        "text/csv"
    )

# ============================================================
# CHART SECTION
# ============================================================
st.markdown("---")
st.subheader("📈 Cycle Event Chart")

if not df_res.empty:
    symbols = sorted(df_filtered["symbol"].unique())

    col1, col2 = st.columns(2)

    with col1:
        sel_symbol = st.selectbox("Symbol", symbols)

    with col2:
        sel_row = df_filtered[df_filtered["symbol"] == sel_symbol]
        sel_event = st.selectbox(
            "Cycle Event",
            sel_row.index,
            format_func=lambda x: (
                f"{sel_row.loc[x,'start_date']} → "
                f"{sel_row.loc[x,'cycle_days']} Days"
            )
        )

    if st.button("📊 Show Chart"):
        row = sel_row.loc[sel_event]
        files = requests.get(GITHUB_DIR_API).json()

        url = None
        for f in files:
            if f["name"] == f"{sel_symbol}.parquet":
                url = f["download_url"]
                break

        if url:
            df = load_github_df(url)

            d0 = row["start_date"]
            d1 = row["end_date"]

            dfw = df[
                (df.index.date >= d0 - datetime.timedelta(days=30)) &
                (df.index.date <= d1 + datetime.timedelta(days=30))
            ]

            fig = Figure(figsize=(10, 4))
            ax = fig.add_subplot(111)

            mpf.plot(
                dfw[["open", "high", "low", "close"]],
                type="candle",
                ax=ax,
                style="charles",
                show_nontrading=True
            )

            ax.axvline(pd.Timestamp(d0), color="blue", linestyle="--", label="Start")
            ax.axvline(pd.Timestamp(d1), color="red", linestyle="--", label="Cycle End")
            ax.legend()

            st.pyplot(fig)

# ============================================================
# FOOTER
# ============================================================
st.markdown("""
---
**Designed by:**  
**Gaurav Singh Yadav**  
Quant | Cycles | Price Action  
Built with ❤️ using Python & Streamlit
""")
