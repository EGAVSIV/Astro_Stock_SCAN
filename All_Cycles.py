# ============================================================
# 📊 Cycle Intelligence Scanner (FINAL SPEC)
# ============================================================

import datetime
import requests
import pandas as pd
import streamlit as st

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(
    page_title="📊 Cycle Intelligence Scanner",
    layout="wide"
)

st.title("📊 Cycle Intelligence Scanner")
st.caption("Bar-Based | Manual & Predefined Cycles | Auto Analyzer")

GITHUB_DIR_API = (
    "https://api.github.com/repos/EGAVSIV/"
    "Stock_Scanner_With_ASTA_Parameters/contents/stock_data_D"
)

CYCLES = [21, 42, 63, 84, 105, 126, 147]

# ============================================================
# LOAD DATA
# ============================================================
def load_df(url: str) -> pd.DataFrame:
    df = pd.read_parquet(url, engine="pyarrow")

    # 1️⃣ If index is already datetime → use it
    if isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    else:
        # 2️⃣ Try to find datetime-like column
        datetime_cols = [
            c for c in df.columns
            if c.lower() in ("date", "datetime", "time", "timestamp")
        ]

        if not datetime_cols:
            raise ValueError("No datetime column found")

        dt_col = datetime_cols[0]
        df.index = pd.to_datetime(df[dt_col], errors="coerce")

    # 3️⃣ Drop invalid rows
    df = df[~df.index.isna()]

    # 4️⃣ Daily timeframe only (if exists)
    if "timeframe" in df.columns:
        df = df[df["timeframe"] == "D"]

    # 5️⃣ Ensure OHLC exists
    required = {"open", "high", "low", "close"}
    if not required.issubset(df.columns):
        raise ValueError("Missing OHLC columns")

    return df.sort_index()


def next_trading_bar(df, date):
    idx = df.index[df.index.date >= date]
    return idx[0] if len(idx) else None

# ============================================================
# CORE CALC
# ============================================================
def calc_move(df, start_date, bars):
    sidx = next_trading_bar(df, start_date)
    if sidx is None:
        return None

    spos = df.index.get_loc(sidx)
    epos = spos + bars
    if epos >= len(df):
        return None

    eidx = df.index[epos]
    sc = df.loc[sidx, "close"]
    ec = df.loc[eidx, "close"]

    pct = ((ec - sc) / sc) * 100
    return sidx.date(), eidx.date(), round(pct, 2)

# ============================================================
# MODE SELECTION
# ============================================================
mode = st.radio(
    "Select Scan Mode",
    ["Manual Cycle Based", "Predefined Cycle Based", "Auto Cycle Analyzer"]
)

threshold = st.slider(
    "Threshold % (Single Value)",
    -30.0, 30.0, 10.0, step=0.5
)

results = []

# ============================================================
# MANUAL MODE
# ============================================================
if mode == "Manual Cycle Based":
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date")
    with col2:
        end_date = st.date_input("End Date")

    if st.button("Run Manual Scan"):
        files = requests.get(GITHUB_DIR_API).json()

        for f in files:
            if not f["name"].endswith(".parquet"):
                continue

            sym = f["name"].replace(".parquet", "")
            df = load_df(f["download_url"])

            sidx = next_trading_bar(df, start_date)
            eidx = next_trading_bar(df, end_date)
            if not sidx or not eidx:
                continue

            sc = df.loc[sidx, "close"]
            ec = df.loc[eidx, "close"]
            pct = ((ec - sc) / sc) * 100

            if (threshold >= 0 and pct >= threshold) or \
               (threshold < 0 and pct <= threshold):

                results.append({
                    "Symbol": sym,
                    "Start": sidx.date(),
                    "End": eidx.date(),
                    "%Move": round(pct, 2),
                    "Bars": df.index.get_loc(eidx) - df.index.get_loc(sidx)
                })

# ============================================================
# PREDEFINED CYCLE MODE
# ============================================================
elif mode == "Predefined Cycle Based":
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date")
    with col2:
        cycle = st.selectbox("Cycle (Bars)", CYCLES)

    if st.button("Run Cycle Scan"):
        files = requests.get(GITHUB_DIR_API).json()

        for f in files:
            if not f["name"].endswith(".parquet"):
                continue

            sym = f["name"].replace(".parquet", "")
            df = load_df(f["download_url"])

            res = calc_move(df, start_date, cycle)
            if not res:
                continue

            sdt, edt, pct = res
            if (threshold >= 0 and pct >= threshold) or \
               (threshold < 0 and pct <= threshold):

                results.append({
                    "Symbol": sym,
                    "Cycle": cycle,
                    "Start": sdt,
                    "End": edt,
                    "%Move": pct
                })

# ============================================================
# AUTO CYCLE ANALYZER
# ============================================================
else:
    today = datetime.date.today()
    future_dates = [
        today + datetime.timedelta(days=i)
        for i in range(30)
    ]

    if st.button("Run Auto Analyzer (Next 1 Month)"):
        files = requests.get(GITHUB_DIR_API).json()
        occ = []

        for f in files:
            if not f["name"].endswith(".parquet"):
                continue

            sym = f["name"].replace(".parquet", "")
            df = load_df(f["download_url"])

            for d in future_dates:
                for c in CYCLES:
                    res = calc_move(df, d, c)
                    if not res:
                        continue

                    _, _, pct = res
                    if abs(pct) >= abs(threshold):
                        occ.append(sym)

        summary = (
            pd.Series(occ)
            .value_counts()
            .reset_index()
            .rename(columns={"index": "Symbol", 0: "Occurrences"})
        )

        st.subheader("🔥 High Priority Stocks (Next Month Cycles)")
        st.dataframe(summary)

# ============================================================
# DISPLAY RESULTS
# ============================================================
if results:
    df = pd.DataFrame(results)
    st.subheader("📋 Scan Results")
    st.dataframe(df)

    summary = (
        df.groupby("Symbol")
        .size()
        .reset_index(name="Occurrences")
        .sort_values("Occurrences", ascending=False)
    )

    st.subheader("⭐ Best Stocks by Occurrence")
    st.dataframe(summary)
else:
    if mode != "Auto Cycle Analyzer":
        st.info("No stocks matched criteria.")
