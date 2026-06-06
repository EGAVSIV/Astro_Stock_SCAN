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
import base64
import hashlib


def set_bg_image(image_path: str):
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()

    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/png;base64,{encoded}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )



def hash_pwd(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

USERS = st.secrets["users"]

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 Login Required")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        if u in USERS and hash_pwd(p) == USERS[u]:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Invalid credentials")
    st.stop()

# ---------------------------------------------------------------------
# MATPLOTLIB BACKEND
# ---------------------------------------------------------------------
matplotlib.use("Agg")

# ---------------------------------------------------------------------
# STREAMLIT PAGE CONFIG
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="-📊 Planet Aspects & Stock Scanner_By_Gs_Yadav",
    page_icon="🪐",
    layout="wide",
)
set_bg_image("Assets/BG11.png")

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
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]

PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Rahu": swe.MEAN_NODE,
    "Ketu": "KETU"
}

ASPECTS = {
    "Opposition": {
        "Aries": "Libra",
        "Taurus": "Scorpio",
        "Gemini": "Sagittarius",
        "Cancer": "Capricorn",
        "Leo": "Aquarius",
        "Virgo": "Pisces",
        "Libra": "Aries",
        "Scorpio": "Taurus",
        "Sagittarius": "Gemini",
        "Capricorn": "Cancer",
        "Aquarius": "Leo",
        "Pisces": "Virgo",
    },
    "Conjunction": {z: z for z in ZODIACS},
    "Square": {
        "Aries": "Cancer",
        "Taurus": "Leo",
        "Gemini": "Virgo",
        "Cancer": "Libra",
        "Leo": "Scorpio",
        "Virgo": "Sagittarius",
        "Libra": "Capricorn",
        "Scorpio": "Aquarius",
        "Sagittarius": "Pisces",
        "Capricorn": "Aries",
        "Aquarius": "Taurus",
        "Pisces": "Gemini",
    },
    "Trine": {
        "Aries": "Leo",
        "Taurus": "Virgo",
        "Gemini": "Libra",
        "Cancer": "Scorpio",
        "Leo": "Sagittarius",
        "Virgo": "Capricorn",
        "Libra": "Aquarius",
        "Scorpio": "Pisces",
        "Sagittarius": "Aries",
        "Capricorn": "Taurus",
        "Aquarius": "Gemini",
        "Pisces": "Cancer",
    },
    "Sextile": {
        "Aries": "Gemini",
        "Taurus": "Cancer",
        "Gemini": "Leo",
        "Cancer": "Virgo",
        "Leo": "Libra",
        "Virgo": "Scorpio",
        "Libra": "Sagittarius",
        "Scorpio": "Capricorn",
        "Sagittarius": "Aquarius",
        "Capricorn": "Pisces",
        "Aquarius": "Aries",
        "Pisces": "Taurus",
    },
}

# GitHub data folder
GITHUB_DIR_API = (
    "https://api.github.com/repos/EGAVSIV/Stock_Scanner_With_ASTA_Parameters/contents/stock_data_D"
)

# ---------------------------------------------------------------------
# ASTRO HELPERS
# ---------------------------------------------------------------------
def get_sidereal_lon_from_jd(jd, planet_code):

    if planet_code == "KETU":

        rahu_res = swe.calc_ut(jd, swe.MEAN_NODE)

        if isinstance(rahu_res[0], (list, tuple)):
            rahu_lon = rahu_res[0][0]
            rahu_speed = rahu_res[0][3]
        else:
            rahu_lon = rahu_res[0]
            rahu_speed = rahu_res[3]

        ayan = swe.get_ayanamsa_ut(jd)

        rahu_sid = (rahu_lon - ayan) % 360

        ketu_sid = (rahu_sid + 180) % 360

        return ketu_sid, rahu_speed

    res = swe.calc_ut(jd, planet_code)

    if isinstance(res[0], (list, tuple)):
        lon = res[0][0]
        speed = res[0][3]
    else:
        lon = res[0]
        speed = res[3]

    ayan = swe.get_ayanamsa_ut(jd)

    sid_lon = (lon - ayan) % 360

    return sid_lon, speed


def get_zodiac_name(sid_lon: float) -> str:
    return ZODIACS[int(sid_lon // 30) % 12]

def zodiac_aspect_match(
    z1,
    z2,
    aspect_name
):

    target = ASPECTS[aspect_name].get(z1)

    return z2 == target

def find_zodiac_aspect_events(
    planet1,
    planet2,
    aspect_name,
    years_back=10,
    years_forward=5
):

    events = []

    today = datetime.datetime.now()

    jd_today = swe.julday(
        today.year,
        today.month,
        today.day,
        today.hour + today.minute/60
    )

    p1 = PLANETS[planet1]
    p2 = PLANETS[planet2]

    prev_state = False
    start_jd = None

    start_hours = -years_back * 365 * 24
    end_hours = years_forward * 365 * 24

    for h in range(start_hours, end_hours, 1):

        jd = jd_today + h / 24

        lon1, _ = get_sidereal_lon_from_jd(jd, p1)
        lon2, _ = get_sidereal_lon_from_jd(jd, p2)

        z1 = get_zodiac_name(lon1)
        z2 = get_zodiac_name(lon2)

        current_state = zodiac_aspect_match(
            z1,
            z2,
            aspect_name
        )

        if not prev_state and current_state:

            start_jd = jd

            events.append({
                "StartJD": jd,
                "Planet1": planet1,
                "Planet2": planet2,
                "Zodiac1": z1,
                "Zodiac2": z2,
                "Aspect": aspect_name
            })

        prev_state = current_state

    return events
    
def angular_diff(a: float, b: float) -> float:
    d = abs(a - b) % 360
    return min(d, 360 - d)

def find_aspect_dates(
    planet1: str,
    planet2: str,
    aspect_name: str,
    years_back: int = 10,
    years_forward: int = 5,
    limit_past: int = 20,
    limit_future: int = 5,
    orb: float = 1.0,
) -> Tuple[List[str], List[str]]:

    today = datetime.datetime.now()
    jd_today = swe.julday(
        today.year,
        today.month,
        today.day,
        today.hour + today.minute / 60.0,
    )

    p1 = PLANETS[planet1]
    p2 = PLANETS[planet2]

    results_past: List[str] = []
    results_future: List[str] = []

    start_offset = -365 * years_back
    end_offset = 365 * years_forward

    prev_diff = None

    for offset in range(start_offset, end_offset + 1):

        jd = jd_today + offset

        lon1, _ = get_sidereal_lon_from_jd(jd, p1)
        lon2, _ = get_sidereal_lon_from_jd(jd, p2)

        diff = angular_diff(lon1, lon2)

        match = False

        if aspect_name == "Conjunction":
            match = diff <= orb

        elif aspect_name == "Opposition":
            match = abs(diff - 180) <= orb

        elif aspect_name == "Square":
            match = abs(diff - 90) <= orb

        elif aspect_name == "Trine":
            match = abs(diff - 120) <= orb

        elif aspect_name == "Sextile":
            match = abs(diff - 60) <= orb

        if match:
            y, m, d, hr = swe.revjul(jd)
            date_str = f"{d:02d}-{m:02d}-{y}"

            if offset < 0:
                results_past.append(date_str)
            else:
                results_future.append(date_str)

    # Remove consecutive duplicates (aspect windows → keep start only)
    def compress(entries: List[str], keep: int, reverse=False):
        out: List[str] = []
        prev = None

        for e in entries:
            if prev is None or (
                datetime.datetime.strptime(e, "%d-%m-%Y")
                - datetime.datetime.strptime(prev, "%d-%m-%Y")
            ).days != 1:
                out.append(e)
            prev = e

        if reverse:
            return out[-keep:][::-1]
        return out[:keep]

    return (
        compress(results_past, limit_past, reverse=True),
        compress(results_future, limit_future, reverse=False),
    )




# ---------------------------------------------------------------------
# DATA HELPERS
# ---------------------------------------------------------------------
def load_github_df(url: str) -> pd.DataFrame:
    """
    Robust parquet loader:
    - accepts any datetime column name: datetime / date / time / timestamp
    - if index already datetime, uses it
    - filters timeframe == 'D' if exists
    """
    df = pd.read_parquet(url, engine="pyarrow")

    # Find datetime-like column
    datetime_cols = [
        c
        for c in df.columns
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


def analyze_symbol_for_aspect_dates(
    df: pd.DataFrame,
    aspect_dates: List[str],
    lookahead_days: int = 15,
) -> List[dict]:
    results: List[dict] = []

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
        end_pos = start_pos + lookahead_days

        window = df.iloc[start_pos:end_pos]
        if window.empty:
            continue

        max_next = float(window["close"].max())
        min_next = float(window["close"].min())

        pct_max = ((max_next - close_on_date) / close_on_date) * 100
        pct_min = ((min_next - close_on_date) / close_on_date) * 100

        results.append(
            {
                "aspect_date": ds,
                "close": close_on_date,
                "max_n": max_next,
                "min_n": min_next,
                "pct_max": pct_max,
                "pct_min": pct_min,
            }
        )

    return results


# ---------------------------------------------------------------------
# SESSION STATE INIT
# ---------------------------------------------------------------------
if "aspect_dates_past" not in st.session_state:
    st.session_state["aspect_dates_past"] = []

if "aspect_dates_future" not in st.session_state:
    st.session_state["aspect_dates_future"] = []

if "aspect_events" not in st.session_state:
    st.session_state["aspect_events"] = []

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

    st.subheader(
        "Find Aspect Start Dates"
    )

    aspect_mode = st.radio(
        "Aspect Calculation Mode",
        [
            "Zodiac Sign",
            "Degree Based"
        ],
        horizontal=True
    )

    

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

        events = find_zodiac_aspect_events(
            planet1,
            planet2,
            aspect_name,
            int(years_back),
            int(years_forward)
        )

        st.session_state["aspect_events"] = events
        events = st.session_state["aspect_events"]

events = st.session_state["aspect_events"]

if len(events) > 0:

    rows = []

    for e in events:

        y,m,d,hr = swe.revjul(e["StartJD"])

        hour = int(hr)
        minute = int((hr - hour) * 60)

        rows.append({

            "Date":
                f"{d:02d}-{m:02d}-{y}",

            "Time":
                f"{hour:02d}:{minute:02d}",

            "Planet 1":
                e["Planet1"],

            "Zodiac 1":
                e["Zodiac1"],

            "Planet 2":
                e["Planet2"],

            "Zodiac 2":
                e["Zodiac2"],

            "Aspect":
                e["Aspect"]
        })

    df_events = pd.DataFrame(rows)

    st.dataframe(
        df_events,
        use_container_width=True
    )

else:

    st.info(
        "No aspect events found."
    )



# ---------------------------------------------------------------------
# TAB 2 — STOCKS SCAN
# ---------------------------------------------------------------------
with tabs[1]:
    st.subheader("Scan Stocks Around Aspect Start Dates")

    events = st.session_state["aspect_events"]

    aspect_dates = []

    for e in events:

        y,m,d,hr = swe.revjul(e["StartJD"])

        aspect_dates.append(
            f"{d:02d}-{m:02d}-{y}"
        )

    if not aspect_dates:
        st.warning("No aspect dates available. Go to the Aspects tab and compute first.")
    else:
        st.caption(f"Using {len(aspect_dates)} past aspect start dates.")

        if st.button("🚀 Run Stock Scan"):
            files = requests.get(GITHUB_DIR_API).json()
            results: List[dict] = []

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

                    items = analyze_symbol_for_aspect_dates(
                        df,
                        aspect_dates,
                        lookahead_days=15,
                    )

                    for it in items:
                        if (it["pct_max"] >= 10.0) or (it["pct_min"] <= -10.0):
                            aspect_type = f"{planet1} {aspect_name} {planet2}"
                            if it["pct_max"] >= 10:
                                direction = "UP"
                            elif it["pct_min"] <= -10:
                                direction = "DOWN"
                            else:
                                continue

                            results.append(
                                {
                                    "symbol": sym,
                                    "aspect_date": it["aspect_date"],
                                    "close": it["close"],
                                    "pct_max": round(it["pct_max"], 2),
                                    "pct_min": round(it["pct_min"], 2),
                                    "direction": direction,
                                }
                            )

                            df_res = pd.DataFrame(results)
                            st.session_state["scan_results"] = df_res

        st.markdown("### Scan Results")

        df_res = st.session_state["scan_results"]
        if not df_res.empty:
            summary = (
                df_res.groupby("symbol")
                .agg(
                    Checked_Events=("symbol", "count"),
                    Moves_Above_10pct=("direction", "count"),
                    Plus_10pct=("direction", lambda x: (x == "UP").sum()),
                    Minus_10pct=("direction", lambda x: (x == "DOWN").sum()),
                )
                .reset_index()
            )
        else:
            summary = pd.DataFrame()

        if df_res.empty:
            st.info("No results yet. Run a scan to populate data.")
        else:
            min_hits = st.slider(
                "Show stocks with at least N qualifying events",
                1,
                20,
                1,
            )
            summary_filtered = summary[summary["Checked_Events"] >= min_hits]

            symbols_allowed = summary_filtered["symbol"].unique()
            df_filtered = df_res[df_res["symbol"].isin(symbols_allowed)]

            st.markdown("### 📌 Stock Performance Summary (Decision Table)")
            st.dataframe(summary, use_container_width=True)

            st.markdown("### 📋 Individual Aspect Events")
            st.dataframe(df_filtered, use_container_width=True)

            csv = df_filtered.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Download Filtered CSV",
                csv,
                "aspect_scan_filtered.csv",
                "text/csv",
            )

            st.success(f"Stocks meeting criteria: {df_filtered['symbol'].nunique()}")

# ---------------------------------------------------------------------
# TAB 3 — CHARTS
# ---------------------------------------------------------------------
with tabs[2]:
    st.subheader("Candlestick Chart Around Aspect Date")

    df_res = st.session_state["scan_results"]

    if df_res.empty:
        st.info("No scan results found. Run a scan in the Stocks Scan tab first.")
    else:
        symbols = sorted(df_res["symbol"].unique())

        col1, col2 = st.columns(2)

        with col1:
            symbol = st.selectbox("Symbol", symbols)

        df_sym = df_res[df_res["symbol"] == symbol]

        with col2:
            aspect_date = st.selectbox(
                "Aspect Date",
                df_sym["aspect_date"].unique(),
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

# ---------------------------------------------------------------------
# FOOTER
# ---------------------------------------------------------------------
st.markdown(
    """
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">

<div style="line-height: 1.6;">
<b>Designed by:-<br>
Gaurav Singh Yadav</b><br><br>

🩷💛🩵💙🩶💜🤍🤎💖 Built With Love 🫶<br>
Energy | Commodity | Quant Intelligence 📶<br><br>

📱 +91-80039945180 〽️<br>

💬 
<a href="https://wa.me/9180039945180" target="_blank">
<i class="fa fa-whatsapp" style="color:#25D366;"></i> WhatsApp
</a><br>

📧 <a href="mailto:yadav.gauravsingh@gmail.com">yadav.gauravsingh@gmail.com</a> ™️
</div>
""",
    unsafe_allow_html=True,
)
