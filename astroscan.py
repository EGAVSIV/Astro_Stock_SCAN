import datetime
import time
import math
from typing import List, Tuple
import requests
import pandas as pd
import swisseph as swe
import streamlit as st
import matplotlib
from matplotlib.figure import Figure
import mplfinance as mpf
#import pyswisseph as swe



# ---------------------------------------------------------------------
# MATPLOTLIB BACKEND
# ---------------------------------------------------------------------
matplotlib.use("Agg")

# ---------------------------------------------------------------------
# STREAMLIT PAGE CONFIG
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="Planet Aspects & Stock Scanner_By_Gs_Yadav",
    page_icon="📊",
    layout="wide",
)

# ---------------------------------------------------------------------
# THEMES
# ---------------------------------------------------------------------
THEMES = {
    "Royal Blue": {"bg": "#0E1A2B", "fg": "#FFFFFF", "accent": "#00FFFF"},
    "Sunset Orange": {"bg": "#2E1414", "fg": "#FFFFFF", "accent": "#FF8243"},
    "Emerald Green": {"bg": "#062A20", "fg": "#FFFFFF", "accent": "#00C896"},
    "Dark Mode": {"bg": "#000000", "fg": "#C0C0C0", "accent": "#4F8CFB"},
}

theme_name = st.sidebar.selectbox("Theme", list(THEMES.keys()))
theme = THEMES[theme_name]

st.markdown(
    f"""
    <style>
    body {{
        background-color: {theme['bg']};
        color: {theme['fg']};
        font-family: "Segoe UI", system-ui, -apple-system, BlinkMacSystemFont,
        sans-serif;
    }}
    .stApp {{
        background-color: {theme['bg']};
        color: {theme['fg']};
    }}
    .stButton>button {{
        background: {theme['accent']} !important;
        color: black !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 600 !important;
        padding: 0.4rem 1.3rem !important;
    }}
    .stTabs [data-baseweb="tab-list"] button {{
        font-weight: 600;
        font-size: 0.95rem;
    }}
    h1, h2, h3, h4 {{
        color: {theme['accent']};
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------
# ASTRO CONFIG / CONSTANTS
# ---------------------------------------------------------------------
swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
NAK_DEG = 13 + 1 / 3

ZODIACS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Rahu": swe.TRUE_NODE,
}

ASPECTS = {
    "Opposition": {
        "Aries": "Libra", "Taurus": "Scorpio", "Gemini": "Sagittarius",
        "Cancer": "Capricorn", "Leo": "Aquarius", "Virgo": "Pisces",
        "Libra": "Aries", "Scorpio": "Taurus", "Sagittarius": "Gemini",
        "Capricorn": "Cancer", "Aquarius": "Leo", "Pisces": "Virgo",
    },
    "Conjunction": {z: z for z in ZODIACS},
    "Square": {
        "Aries": "Cancer", "Taurus": "Leo", "Gemini": "Virgo",
        "Cancer": "Libra", "Leo": "Scorpio", "Virgo": "Sagittarius",
        "Libra": "Capricorn", "Scorpio": "Aquarius", "Sagittarius": "Pisces",
        "Capricorn": "Aries", "Aquarius": "Taurus", "Pisces": "Gemini",
    },
    "Trine": {
        "Aries": "Leo", "Taurus": "Virgo", "Gemini": "Libra",
        "Cancer": "Scorpio", "Leo": "Sagittarius", "Virgo": "Capricorn",
        "Libra": "Aquarius", "Scorpio": "Pisces", "Sagittarius": "Aries",
        "Capricorn": "Taurus", "Aquarius": "Gemini", "Pisces": "Cancer",
    },
    "Sextile": {
        "Aries": "Gemini", "Taurus": "Cancer", "Gemini": "Leo",
        "Cancer": "Virgo", "Leo": "Libra", "Virgo": "Scorpio",
        "Libra": "Sagittarius", "Scorpio": "Capricorn",
        "Sagittarius": "Aquarius", "Capricorn": "Pisces",
        "Aquarius": "Aries", "Pisces": "Taurus",
    },
}

# GitHub data folder
GITHUB_DIR_API = \
    "https://api.github.com/repos/EGAVSIV/Stock_Scanner_With_ASTA_Parameters/contents/stock_data_D"

# ---------------------------------------------------------------------
# ORIGINAL TKINTER LOGIC (ported)
# ---------------------------------------------------------------------
def get_sidereal_lon_from_jd(jd: float, planet_code: int):
    """Return sidereal longitude + speed (Lahiri)."""
    res = swe.calc_ut(jd, planet_code)
    if isinstance(res, tuple) and isinstance(res[0], (list, tuple)):
        lon = res[0][0]
        speed = res[0][3]
    elif isinstance(res, (list, tuple)):
        lon = res[0]
        speed = res[3] if len(res) > 3 else 0.0
    else:
        lon = float(res[0])
        speed = float(res[3]) if len(res) > 3 else 0.0

    ayan = swe.get_ayanamsa_ut(jd)
    sid_lon = (lon - ayan) % 360
    return sid_lon, speed

def get_zodiac_name(sid_lon: float) -> str:
    return ZODIACS[int(sid_lon // 30) % 12]

# -------------------- continues --------------------



def find_aspect_dates(
    planet1: str,
    planet2: str,
    aspect_name: str,
    years_back: int = 10,
    years_forward: int = 5,
    limit_past: int = 20,
    limit_future: int = 5,
) -> Tuple[List[str], List[str]]:
    """ EXACT same logic as Tkinter version:
    - step 1 day
    - collect all days where z2 == aspect_map[z1]
    - then compress consecutive dates => only aspect START dates
    """
    today = datetime.datetime.now()
    jd_today = swe.julday(
        today.year,
        today.month,
        today.day,
        today.hour + today.minute / 60.0
    )

    p1 = PLANETS[planet1]
    p2 = PLANETS[planet2]
    aspect_map = ASPECTS[aspect_name]

    results_past = []
    results_future = []

    start_offset = -365 * years_back
    end_offset = 365 * years_forward

    for offset in range(start_offset, end_offset + 1):
        jd = jd_today + offset

        lon1, _ = get_sidereal_lon_from_jd(jd, p1)
        lon2, _ = get_sidereal_lon_from_jd(jd, p2)

        z1 = get_zodiac_name(lon1)
        z2 = get_zodiac_name(lon2)

        if aspect_map.get(z1) == z2:
            y, m, d, hr = swe.revjul(jd)
            date_str = f"{d:02d}-{m:02d}-{y}"
            if offset < 0:
                results_past.append(date_str)
            else:
                results_future.append(date_str)

    def unique_first_past(entries, keep):
        out = []
        prev = None
        for e in entries:
            if prev is None or (
                datetime.datetime.strptime(e, "%d-%m-%Y")
                - datetime.datetime.strptime(prev, "%d-%m-%Y")
            ).days != 1:
                out.append(e)
            prev = e
        return out[-keep:][::-1]

    def unique_first_future(entries, keep):
        out = []
        prev = None
        for e in entries:
            if prev is None or (
                datetime.datetime.strptime(e, "%d-%m-%Y")
                - datetime.datetime.strptime(prev, "%d-%m-%Y")
            ).days != 1:
                out.append(e)
            prev = e
        return out[:keep]

    return (
        unique_first_past(results_past, limit_past),
        unique_first_future(results_future, limit_future),
    )


def load_github_df(url: str) -> pd.DataFrame:
    """ Robust parquet loader:
    - accepts any datetime column name: datetime / date / time / timestamp
    - if index already datetime, uses it
    - filters timeframe == 'D' if exists
    """
    df = pd.read_parquet(url, engine="pyarrow")

    # Find datetime-like column
    datetime_cols = [
        c for c in df.columns
        if c.lower() in ("datetime", "date", "time", "timestamp")
    ]

    if datetime_cols:
        col = datetime_cols[0]
        df.index = pd.to_datetime(df[col])
    else:
        if not isinstance(df.index, pd.DatetimeIndex):
            raise KeyError("No datetime-like column or DatetimeIndex found")
        df.index = pd.to_datetime(df.index)

    if "timeframe" in df.columns:
        df = df[df["timeframe"] == "D"]

    if "close" not in df.columns:
        raise KeyError("No 'close' column in data")

    return df.sort_index()


def analyze_symbol_for_aspect_dates(df: pd.DataFrame, aspect_dates: List[str]):
    """ Exact port of Tkinter logic:
    - For each aspect date, find that candle's close, then next 10 trading candles:
      pct_max, pct_min, max10, min10.
    """
    results = []
    for ds in aspect_dates:
        try:
            d = datetime.datetime.strptime(ds, "%d-%m-%Y").date()
        except Exception:
            continue

        mask = df.index.date == d
        if not mask.any():
            continue

        idx = df.index[mask][0]
        close_on_date = float(df.loc[idx, "close"])
        idx_pos = df.index.get_loc(idx)
        start_pos = idx_pos + 1
        end_pos = start_pos + 10

        window = df.iloc[start_pos:end_pos]
        if window.empty:
            continue

        max_next10 = float(window["close"].max())
        min_next10 = float(window["close"].min())

        pct_max = ((max_next10 - close_on_date) / close_on_date) * 100.0
        pct_min = ((min_next10 - close_on_date) / close_on_date) * 100.0

        results.append({
            "aspect_date": ds,
            "close": close_on_date,
            "max10": max_next10,
            "min10": min_next10,
            "pct_max": pct_max,
            "pct_min": pct_min,
        })

    return results


# ---------------------------------------------------------------------
# SESSION STATE INIT
# ---------------------------------------------------------------------
if "aspect_dates_past" not in st.session_state:
    st.session_state["aspect_dates_past"] = []

if "aspect_dates_future" not in st.session_state:
    st.session_state["aspect_dates_future"] = []

if "scan_results" not in st.session_state:
    st.session_state["scan_results"] = pd.DataFrame()

# ---------------------------------------------------------------------
# MAIN UI
# ---------------------------------------------------------------------
st.title("🪐 Planetary Aspects Vs 💹Stock_By GauravSinghYadav")

tabs = st.tabs(["🌙x☀️Aspects", "📊 Stocks Scan", "📉 Charts"])

# ---------------------------------------------------------------------
# TAB 1 — ASPECTS
# ---------------------------------------------------------------------
with tabs[0]:
    st.subheader("Find Aspect Start Dates (Tkinter Logic)")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        planet1 = st.selectbox("Planet 1", list(PLANETS.keys()), index=0)
    with col2:
        planet2 = st.selectbox("Planet 2", list(PLANETS.keys()), index=1)
    with col3:
        aspect_name = st.selectbox("Aspect", list(ASPECTS.keys()), index=0)
    with col4:
        years_back = st.number_input("Years back", 1, 50, 10)
        years_forward = st.number_input("Years forward", 1, 50, 5)

    if st.button("🔍 Find Aspect Dates"):
        with st.spinner("Computing aspect start dates..."):
            past, future = find_aspect_dates(
                planet1,
                planet2,
                aspect_name,
                years_back=int(years_back),
                years_forward=int(years_forward),
            )
        st.session_state["aspect_dates_past"] = past
        st.session_state["aspect_dates_future"] = future

        st.success(
            f"Found {len(past)} past aspect starts and {len(future)} future aspect starts."
        )

    colA, colB = st.columns(2)

    with colA:
        st.markdown("### Past Aspect Start Dates (most recent first)")
        if st.session_state["aspect_dates_past"]:
            st.write(st.session_state["aspect_dates_past"])
        else:
            st.info("No past aspect dates computed yet.")

    with colB:
        st.markdown("### Future Aspect Start Dates")
        if st.session_state["aspect_dates_future"]:
            st.write(st.session_state["aspect_dates_future"])
        else:
            st.info("No future aspect dates computed yet.")

# ---------------------------------------------------------------------
# TAB 2 — STOCKS SCAN
# ---------------------------------------------------------------------
with tabs[1]:
    st.subheader("Scan Stocks Around Aspect Start Dates")

    aspect_dates = st.session_state["aspect_dates_past"]

    if not aspect_dates:
        st.warning("No aspect dates available. Go to the Aspects tab and compute first.")

    else:
        st.caption(f"Using {len(aspect_dates)} past aspect start dates.")

        if st.button("🚀 Run Stock Scan"):
            files = requests.get(GITHUB_DIR_API).json()
            results = []

            total_files = len([f for f in files if f["name"].endswith(".parquet")])

            with st.spinner("Scanning stocks from GitHub parquet files..."):
                for f in files:
                    name = f.get("name", "")
                    if not name.endswith(".parquet"):
                        continue

                    sym = name.replace(".parquet", "")
                    url = f["download_url"]

                    try:
                        df = load_github_df(url)
                    except Exception:
                        continue

                    items = analyze_symbol_for_aspect_dates(df, aspect_dates)

                    for it in items:
                        if (it["pct_max"] >= 10.0) or (it["pct_min"] <= -10.0):
                            aspect_type = f"{planet1} {aspect_name} {planet2}"
                            move_category = (
                                "😆 >10% Gain" if it["pct_max"] >= 10
                                else "😩 >10% Fall"
                            )

                            results.append({
                                "symbol": sym,
                                "aspect_date": it["aspect_date"],
                                "close": it["close"],
                                "max10": it["max10"],
                                "min10": it["min10"],
                                "pct_max": round(it["pct_max"], 2),
                                "pct_min": round(it["pct_min"], 2),
                                "Aspect": aspect_type,
                                "Move Category": move_category,
                            })

            df_res = pd.DataFrame(results)

            if not df_res.empty:
                df_res["Count"] = df_res.groupby("symbol")["symbol"].transform("count")

            st.session_state["scan_results"] = df_res

            st.success(f"Scan complete. {len(df_res)} qualifying records found.")

        st.markdown("### Scan Results")

        df_res = st.session_state["scan_results"]

        if df_res.empty:
            st.info("No results yet. Run a scan to populate data.")
        else:
            min_hits = st.slider("Show stocks repeating at least N times", 1, 10, 1)
            df_filtered = df_res[df_res["Count"] >= min_hits]

            st.dataframe(df_filtered, use_container_width=True)

            csv = df_filtered.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Download Filtered CSV",
                csv,
                f"aspect_scan_filtered.csv",
                "text/csv"
            )

            st.success(f"Stocks meeting criteria: {df_filtered['symbol'].nunique()}")

# ---------------------------------------------------------------------
# TAB 3 — CHARTS
# ---------------------------------------------------------------------
with tabs[2]:
    st.subheader("Candlestick Chart Around Aspect Date")

    df_res = st.session_state["scan_results"]

    if df_res.empty:
        st.info(
            "No scan results found. Run a scan in the Stocks Scan tab first."
        )
    else:
        symbols = sorted(df_res["symbol"].unique())

        col1, col2 = st.columns(2)

        with col1:
            symbol = st.selectbox("Symbol", symbols)

        df_sym = df_res[df_res["symbol"] == symbol]

        with col2:
            aspect_date = st.selectbox(
                "Aspect Date",
                df_sym["aspect_date"].unique()
            )

        if st.button("📈 Show Chart"):
            files = requests.get(GITHUB_DIR_API).json()
            url = None

            for f in files:
                if f.get("name", "") == f"{symbol}.parquet":
                    url = f["download_url"]
                    break

            if url is None:
                st.error(f"No parquet file found on GitHub for symbol: {symbol}")

            else:
                try:
                    df = load_github_df(url)
                except Exception as e:
                    st.error(f"Error loading data for {symbol}: {e}")
                else:
                    d = datetime.datetime.strptime(aspect_date, "%d-%m-%Y").date()
                    start = d - datetime.timedelta(days=30)
                    end = d + datetime.timedelta(days=40)

                    dfw = df[
                        (df.index.date >= start)
                        & (df.index.date <= end)
                    ]

                    if dfw.empty:
                        st.warning("No OHLC data around this aspect date.")

                    else:
                        required_cols = {"open", "high", "low", "close"}
                        if not required_cols.issubset(dfw.columns):
                            st.error("Missing OHLC columns; cannot plot candles.")

                        else:
                            df_candle = dfw[
                                ["open", "high", "low", "close"]
                            ].copy()

                            fig = Figure(figsize=(10, 4))
                            ax = fig.add_subplot(111)

                            mpf.plot(
                                df_candle,
                                type="candle",
                                ax=ax,
                                style="charles",
                                show_nontrading=True,
                            )

                            ax.set_title(
                                f"{symbol} — Candlestick Chart (around {aspect_date})"
                            )
                            ax.grid(True, alpha=0.3)

                            try:
                                dates = pd.Series(dfw.index)
                                idx_near = dates[dates.dt.date == d]
                                if not idx_near.empty:
                                    ad_idx = idx_near.iloc[0]
                                    y = dfw.loc[ad_idx, "close"]
                                    ax.axvline(
                                        ad_idx,
                                        color="orange",
                                        linestyle="--",
                                        linewidth=1,
                                    )
                                    ax.scatter([ad_idx], [y], color="orange")
                            except Exception:
                                pass

                            st.pyplot(fig)
