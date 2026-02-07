# ============================================================
# 📊 ADVANCED AUTO CYCLE ENGINE (LONG + SHORT)
# ============================================================

import requests
import pandas as pd
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

# ============================================================
# CONFIG
# ============================================================
st.set_page_config("Advanced Cycle Engine", layout="wide")
st.title("📊 Advanced Auto Cycle Engine")
st.caption("Dominant Cycle | Heatmap | Forward Probability | Long & Short")

GITHUB_DIR_API = (
    "https://api.github.com/repos/EGAVSIV/"
    "Stock_Scanner_With_ASTA_Parameters/contents/stock_data_D"
)

# ============================================================
# DATA LOADER (ROBUST)
# ============================================================
@st.cache_data(show_spinner=False)
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
# DOMINANT CYCLE DETECTION
# ============================================================
def dominant_cycle(df, symbol, threshold, max_cycle):
    closes = df["close"].values
    dates = df.index

    best = None

    for cycle in range(10, max_cycle + 1, 5):
        moves = []

        for i in range(len(closes) - cycle):
            pct = ((closes[i + cycle] - closes[i]) / closes[i]) * 100
            if abs(pct) >= threshold:
                moves.append(pct)

        if len(moves) < 5:
            continue

        avg_move = np.mean(moves)
        strength = len(moves) * abs(avg_move)

        if best is None or strength > best["Strength"]:
            best = {
                "Symbol": symbol,
                "Cycle_Bars": cycle,
                "Occurrences": len(moves),
                "Avg_%Move": round(avg_move, 2),
                "Bull_Prob": round((np.array(moves) > 0).mean() * 100, 1),
                "Bear_Prob": round((np.array(moves) < 0).mean() * 100, 1),
                "Strength": round(strength, 2),
            }

    return best

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
        "Max Cycle Length (Bars) (Min fixed at 10)",
        min_value=10,
        max_value=200,
        value=150,
        step=5
    )


# ============================================================
# RUN ANALYSIS
# ============================================================
if st.button("🚀 Run Advanced Cycle Analysis"):
    files = requests.get(GITHUB_DIR_API).json()
    dominant = []

    with st.spinner("Discovering dominant cycles..."):
        for f in files:
            if not f["name"].endswith(".parquet"):
                continue

            symbol = f["name"].replace(".parquet", "")
            try:
                df = load_df(f["download_url"])
                res = dominant_cycle(df, symbol, threshold, max_cycle)
                if res:
                    dominant.append(res)
            except Exception:
                continue

    if not dominant:
        st.warning("No dominant cycles found.")
        st.stop()

    df_dom = pd.DataFrame(dominant)
    st.success(f"🧠 Dominant cycles found for {len(df_dom)} stocks")

    # ========================================================
    # TABLE
    # ========================================================
    st.subheader("🧠 Dominant Cycle Per Stock")
    st.dataframe(
        df_dom.sort_values("Strength", ascending=False),
        use_container_width=True
    )

    # ========================================================
    # HEATMAP
    # ========================================================
    st.subheader("📊 Cycle Heatmap (Avg % Move)")

    heat = df_dom.pivot_table(
        index="Symbol",
        columns="Cycle_Bars",
        values="Avg_%Move"
    )

    fig, ax = plt.subplots(figsize=(10, max(4, len(heat) * 0.25)))
    im = ax.imshow(heat, cmap="RdYlGn", aspect="auto")

    ax.set_xticks(range(len(heat.columns)))
    ax.set_xticklabels(heat.columns)
    ax.set_yticks(range(len(heat.index)))
    ax.set_yticklabels(heat.index)

    plt.colorbar(im, ax=ax, label="Avg % Move")
    st.pyplot(fig)

    # ========================================================
    # VISUAL OVERLAY
    # ========================================================
    st.subheader("📈 Cycle Overlay Chart")

    sel = st.selectbox("Select Stock", df_dom["Symbol"].unique())
    row = df_dom[df_dom["Symbol"] == sel].iloc[0]

    file = next(
        f for f in files if f["name"] == f"{sel}.parquet"
    )
    df = load_df(file["download_url"])

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(df.index, df["close"], color="black")

    cycle = int(row["Cycle_Bars"])
    for i in range(0, len(df) - cycle, cycle):
        ax.axvspan(
            df.index[i],
            df.index[i + cycle],
            color="green" if row["Avg_%Move"] > 0 else "red",
            alpha=0.08
        )

    ax.set_title(f"{sel} – Dominant Cycle Overlay ({cycle} bars)")
    st.pyplot(fig)

    # ========================================================
    # FORWARD PROBABILITY
    # ========================================================
    st.subheader("🔮 Forward Cycle Probability")

    st.markdown(f"""
    **Stock:** {sel}  
    **Dominant Cycle:** {row['Cycle_Bars']} bars  

    🟢 **Bullish Probability:** {row['Bull_Prob']}%  
    🔴 **Bearish Probability:** {row['Bear_Prob']}%  
    """)

# ============================================================
# FOOTER
# ============================================================
st.markdown("""
---
**Advanced Cycle Engine**  
Dominant | Long & Short | Probabilistic  
Built for real market research 📈📉
""")
