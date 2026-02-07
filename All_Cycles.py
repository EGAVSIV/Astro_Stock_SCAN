# ============================================================
# 📊 ADVANCED AUTO CYCLE + PRICE-TIME EQUALITY ENGINE
# ============================================================

import requests
import pandas as pd
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

# ============================================================
# CONFIG
# ============================================================
st.set_page_config("Cycle + Price-Time Engine", layout="wide")
st.title("📊 Advanced Cycle + Price–Time Equality Engine")
st.caption("Dominant Cycle | Energy Build-up | Explosion Probability")

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

# ============================================================
# DOMINANT CYCLE
# ============================================================
def dominant_cycle(df, symbol, threshold, max_cycle):
    closes = df["close"].values
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
                "Avg_%Move": round(avg_move, 2),
                "Bull_Prob": round((np.array(moves) > 0).mean() * 100, 1),
                "Bear_Prob": round((np.array(moves) < 0).mean() * 100, 1),
                "Strength": round(strength, 2),
            }

    return best

# ============================================================
# PRICE–TIME EQUALITY + ENERGY BUILDUP
# ============================================================
def price_time_equality(df, cycle, tolerance=0.015):
    if len(df) < cycle + 5:
        return False, "Normal", None

    price_now = df["close"].iloc[-1]
    price_then = df["close"].iloc[-cycle]

    diff_pct = abs(price_now - price_then) / price_then

    if diff_pct <= tolerance:
        recent_vol = df["close"].pct_change().rolling(10).std().iloc[-1]
        past_vol = df["close"].pct_change().rolling(30).std().iloc[-1]

        if recent_vol < past_vol:
            return True, "Compressed", diff_pct

    return False, "Normal", diff_pct

# ============================================================
# UI
# ============================================================
col1, col2 = st.columns(2)

with col1:
    threshold = st.slider("Significant Move Threshold (%)", 3.0, 20.0, 7.0)

with col2:
    max_cycle = st.slider("Max Cycle Length (Bars)", 10, 200, 150, step=5)

# ============================================================
# RUN
# ============================================================
if st.button("🚀 Run Cycle + Energy Scan"):
    files = requests.get(GITHUB_DIR_API).json()
    results = []

    for f in files:
        if not f["name"].endswith(".parquet"):
            continue

        symbol = f["name"].replace(".parquet", "")
        df = load_df(f["download_url"])

        dom = dominant_cycle(df, symbol, threshold, max_cycle)
        if not dom:
            continue

        pte, energy, diff = price_time_equality(df, dom["Cycle_Bars"])

        # Explosion Bias
        if dom["Bull_Prob"] > dom["Bear_Prob"]:
            bias = "Bullish"
            base_prob = dom["Bull_Prob"]
        else:
            bias = "Bearish"
            base_prob = dom["Bear_Prob"]

        # Boost probability if energy built
        explosion_prob = base_prob + 15 if pte else base_prob

        results.append({
            "Symbol": symbol,
            "Cycle_Bars": dom["Cycle_Bars"],
            "Avg_%Move": dom["Avg_%Move"],
            "Bull_Prob": dom["Bull_Prob"],
            "Bear_Prob": dom["Bear_Prob"],
            "PTE_Zone": pte,
            "Energy_State": energy,
            "Explosion_Bias": bias,
            "Explosion_Prob_%": min(explosion_prob, 95)
        })

    df_final = pd.DataFrame(results)

    st.subheader("⚡ Price–Time Equality Explosion Scanner")
    st.dataframe(
        df_final.sort_values(
            ["PTE_Zone", "Explosion_Prob_%"],
            ascending=[False, False]
        ),
        use_container_width=True
    )

# ============================================================
# FOOTER
# ============================================================
st.markdown("""
---
🧠 **Market Truth**  
When **price equals price after time**,  
👉 movement = 0  
👉 energy = stored  
👉 **EXPLOSION is inevitable**

This engine finds those zones.
""")
