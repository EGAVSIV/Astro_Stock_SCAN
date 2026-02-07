# ============================================================
# 📊 Advanced Cycle Based Stock Scanner (Bar-Based)
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
    page_title="📊 Advanced Cycle Scanner",
    page_icon="📈",
    layout="wide",
)

st.title("📊 Advanced Cycle Based Stock Scanner")
st.caption("Bar-Based | Threshold | Historical Cycle Scan | Parquet")

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
# FIND NEAREST NEXT TRADING DAY
# ============================================================
def get_next_trading_index(df, date):
    dates = df.index[df.index.date >= date]
    if dates.empty:
        return None
    return dates[0]

# ============================================================
# CORE ANALYSIS FUNCTION
# ============================================================
def analyze_cycles(
    df: pd.DataFrame,
    symbol: str,
    start_date: datetime.date,
    cycle: int,
    threshold_pos: float,
    threshold_neg: float,
    years_back: int,
):
    results = []

    for y in range(years_back + 1):
        shifted_date = datetime.date(
            start_date.year - y,
            start_date.month,
            start_date.day
        )

        start_idx = get_next_trading_index(df, shifted_date)
        if start_idx is None:
            continue

        start_pos = df.index.get_loc(start_idx)
        target_pos = start_pos + cycle

        if target_pos >= len(df):
            continue

        end_idx = df.index[target_pos]

        start_close = float(df.loc[start_idx, "close"])
        end_close = float(df.loc[end_idx, "close"])

        pct = ((end_close - start_close) / start_close) * 100

        if (
            (threshold_pos is not None and pct >= threshold_pos)
            or (threshold_neg is not None and pct <= -threshold_neg)
        ):
            results.append({
                "symbol": symbol,
                "base_year": shifted_date.year,
                "cycle_days": cycle,
                "start_date": start_idx.date(),
                "end_date": end_idx.date(),
                "start_close": round(start_close, 2),
                "end_close": round(end_close, 2),
                "pct_change": round(pct, 2),
                "direction": "UP" if pct > 0 else "DOWN",
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
st.subheader("⚙️ Scan Configuration")

col1, col2, col3, col4 = st.columns(4)

with col1:
    start_date = st.date_input("📅 Start Date")

with col2:
    cycle = st.selectbox(
        "🔁 Select Cycle (Bars)",
        [21, 42, 63, 84, 105, 126, 147]
    )

with col3:
    threshold_pos = st.number_input(
        "📈 Positive Threshold %",
        min_value=0.0,
        max_value=30.0,
        value=6.0,
        step=0.5
    )

with col4:
    threshold_neg = st.number_input(
        "📉 Negative Threshold %",
        min_value=0.0,
        max_value=30.0,
        value=6.0,
        step=0.5
    )

years_back = st.slider("⏪ Years to Scan Back", 1, 10, 5)

# ============================================================
# RUN SCAN
# ============================================================
if st.button("🚀 Run Cycle Scan"):
    files = requests.get(GITHUB_DIR_API).json()
    all_results = []

    with st.spinner("Scanning stocks (bar-based logic)..."):
        for f in files:
            if not f["name"].endswith(".parquet"):
                continue

            symbol = f["name"].replace(".parquet", "")
            url = f["download_url"]

            try:
                df = load_github_df(url)
            except Exception:
                continue

            res = analyze_cycles(
                df=df,
                symbol=symbol,
                start_date=start_date,
                cycle=cycle,
                threshold_pos=threshold_pos,
                threshold_neg=threshold_neg,
                years_back=years_back
            )

            all_results.extend(res)

    st.session_state["scan_results"] = pd.DataFrame(all_results)

# ============================================================
# RESULTS
# ============================================================
df_res = st.session_state["scan_results"]

if df_res.empty:
    st.info("No results found.")
else:
    st.subheader("📌 Summary")

    summary = (
        df_res
        .groupby("symbol")
        .agg(
            Occurrences=("symbol", "count"),
            Avg_Move=("pct_change", "mean"),
            Max_Gain=("pct_change", "max"),
            Max_Loss=("pct_change", "min"),
        )
        .reset_index()
    )

    min_occ = st.slider("Minimum Occurrences", 1, 10, 1)
    summary = summary[summary["Occurrences"] >= min_occ]

    st.dataframe(summary, use_container_width=True)

    st.subheader("📋 Detailed Events")
    filtered = df_res[df_res["symbol"].isin(summary["symbol"])]
    st.dataframe(filtered, use_container_width=True)

    csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Download CSV",
        csv,
        "cycle_scan_results.csv",
        "text/csv"
    )

# ============================================================
# CHART
# ============================================================
st.markdown("---")
st.subheader("📈 Cycle Event Chart")

if not filtered.empty:
    sym = st.selectbox("Symbol", filtered["symbol"].unique())
    row = filtered[filtered["symbol"] == sym].iloc[0]

    files = requests.get(GITHUB_DIR_API).json()
    url = next(
        f["download_url"]
        for f in files
        if f["name"] == f"{sym}.parquet"
    )

    df = load_github_df(url)

    dfw = df[
        (df.index.date >= row["start_date"] - datetime.timedelta(days=30)) &
        (df.index.date <= row["end_date"] + datetime.timedelta(days=30))
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

    ax.axvline(pd.Timestamp(row["start_date"]), color="blue", linestyle="--")
    ax.axvline(pd.Timestamp(row["end_date"]), color="red", linestyle="--")

    st.pyplot(fig)

# ============================================================
# FOOTER
# ============================================================
st.markdown("""
---
**Designed by:**  
**Gaurav Singh Yadav**  
Quant | Cycles | Bar-Based Logic  
Built with ❤️ in Python & Streamlit
""")
