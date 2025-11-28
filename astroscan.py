import datetime
from typing import List, Tuple

import requests
import pandas as pd
import swisseph as swe
import streamlit as st
import matplotlib
from matplotlib.figure import Figure
import mplfinance as mpf

matplotlib.use("Agg")

# ---------------------------------------------------------------------
# STREAMLIT CONFIG
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="Planetary Aspects & Stock Scanner — Web",
    page_icon="🪐",
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
        font-family: "Segoe UI", system-ui;
    }}
    .stApp {{
        background-color: {theme['bg']};
    }}
    .stButton>button {{
        background: {theme['accent']} !important;
        color: black !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 600 !important;
    }}
    h1, h2, h3 {{
        color: {theme['accent']};
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------
# ASTRO CONSTANTS
# ---------------------------------------------------------------------
swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)

ZODIACS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
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
        "Aries":"Libra","Taurus":"Scorpio","Gemini":"Sagittarius",
        "Cancer":"Capricorn","Leo":"Aquarius","Virgo":"Pisces",
        "Libra":"Aries","Scorpio":"Taurus","Sagittarius":"Gemini",
        "Capricorn":"Cancer","Aquarius":"Leo","Pisces":"Virgo",
    },
    "Conjunction": {z: z for z in ZODIACS},
    "Square": {
        "Aries":"Cancer","Taurus":"Leo","Gemini":"Virgo",
        "Cancer":"Libra","Leo":"Scorpio","Virgo":"Sagittarius",
        "Libra":"Capricorn","Scorpio":"Aquarius","Sagittarius":"Pisces",
        "Capricorn":"Aries","Aquarius":"Taurus","Pisces":"Gemini",
    },
    "Trine": {
        "Aries":"Leo","Taurus":"Virgo","Gemini":"Libra",
        "Cancer":"Scorpio","Leo":"Sagittarius","Virgo":"Capricorn",
        "Libra":"Aquarius","Scorpio":"Pisces","Sagittarius":"Aries",
        "Capricorn":"Taurus","Aquarius":"Gemini","Pisces":"Cancer",
    },
    "Sextile": {
        "Aries":"Gemini","Taurus":"Cancer","Gemini":"Leo",
        "Cancer":"Virgo","Leo":"Libra","Virgo":"Scorpio",
        "Libra":"Sagittarius","Scorpio":"Capricorn",
        "Sagittarius":"Aquarius","Capricorn":"Pisces",
        "Aquarius":"Aries","Pisces":"Taurus",
    },
}

# GitHub parquet files
GITHUB_DIR_API = "https://api.github.com/repos/EGAVSIV/Stock_Scanner_With_ASTA_Parameters/contents/stock_data_D"


# ---------------------------------------------------------------------
# ASTRO FUNCTIONS
# ---------------------------------------------------------------------
def get_sidereal_lon(jd, planet):
    res = swe.calc_ut(jd, planet)

    if isinstance(res, (tuple, list)):
        if isinstance(res[0], (tuple, list)):
            lon = float(res[0][0])
        else:
            lon = float(res[0])
    else:
        lon = float(res)

    ayan = swe.get_ayanamsa_ut(jd)
    return (lon - ayan) % 360



def get_zodiac(lon):
    return ZODIACS[int(lon // 30)]


def find_aspect_dates(p1, p2, asp, years_back=10, years_forward=5):
    today = datetime.datetime.now()
    jd_today = swe.julday(today.year, today.month, today.day)

    asp_map = ASPECTS[asp]
    r_past, r_future = [], []

    for offset in range(-365*years_back, 365*years_forward):
        jd = jd_today + offset
        z1 = get_zodiac(get_sidereal_lon(jd, PLANETS[p1]))
        z2 = get_zodiac(get_sidereal_lon(jd, PLANETS[p2]))

        if asp_map.get(z1)==z2:
            y,m,d,hr = swe.revjul(jd)
            ds = f"{d:02d}-{m:02d}-{y}"

            if offset < 0: r_past.append(ds)
            else: r_future.append(ds)

    def filter_runs(lst):
        f=[]
        prev=None
        for d in lst:
            if prev is None or (
                datetime.datetime.strptime(d,"%d-%m-%Y") -
                datetime.datetime.strptime(prev,"%d-%m-%Y")
            ).days!=1:
                f.append(d)
            prev=d
        return f

    return filter_runs(r_past)[-20:][::-1], filter_runs(r_future)[:5]


# ---------------------------------------------------------------------
# STOCK HANDLING
# ---------------------------------------------------------------------
def load_parquet(url):
    df = pd.read_parquet(url, engine="pyarrow")
    if "datetime" in df.columns:
        df.index=pd.to_datetime(df["datetime"])
    else:
        df.index=pd.to_datetime(df.index)
    return df.sort_index()


def analyze(df, dates):
    out=[]
    for ds in dates:
        d=datetime.datetime.strptime(ds,"%d-%m-%Y").date()
        mask=df.index.date==d
        if not mask.any():continue
        idx=df.index[mask][0]
        close=df.loc[idx,"close"]
        win=df.iloc[df.index.get_loc(idx)+1:df.index.get_loc(idx)+11]

        if win.empty:continue

        mx=win["close"].max()
        mn=win["close"].min()
        out.append({
            "aspect_date":ds,
            "close":close,
            "pct_max":(mx-close)/close*100,
            "pct_min":(mn-close)/close*100,
        })
    return out


# STREAMLIT UI
# ===========================================================
if "aspect_dates" not in st.session_state:
    st.session_state["aspect_dates"]=[]

if "results" not in st.session_state:
    st.session_state["results"]=pd.DataFrame()

st.title("🪐 Planetary Aspects & Stock Scanner")

tabs=st.tabs(["♍ Aspects","📊 Stocks","📈 Charts"])

# TAB 1 -------------------------------------------------------
with tabs[0]:
    c1,c2,c3,c4=st.columns(4)
    p1=c1.selectbox("Planet 1",PLANETS)
    p2=c2.selectbox("Planet 2",PLANETS)
    asp=c3.selectbox("Aspect",ASPECTS)
    yb=c4.number_input("Years back",1,20,10)
    yf=c4.number_input("Years forward",1,20,5)

    if st.button("Find Aspect Start Dates"):
        past,future=find_aspect_dates(p1,p2,asp,yb,yf)
        st.session_state["aspect_dates"]=past
        st.success(f"Found {len(past)} past aspect start dates")
        st.write(past)

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
                            move_category = "😆 >10% Gain" if it["pct_max"] >= 10 else "😩 >10% Fall"

                            results.append(
                                {
                                    "symbol": sym,
                                    "aspect_date": it["aspect_date"],
                                    "close": it["close"],
                                    "max10": it["max10"],
                                    "min10": it["min10"],
                                    "pct_max": round(it["pct_max"], 2),
                                    "pct_min": round(it["pct_min"], 2),
                                    "Aspect": aspect_type,
                                    "Move Category": move_category,
                                }
                            )

            df_res = pd.DataFrame(results)

            # ⭐ ADD SUMMARY COLUMNS
            if not df_res.empty:
                # Count total times appeared
                df_res["Count"] = df_res.groupby("symbol")["symbol"].transform("count")

                # Win / Loss flags
                df_res["Win"] = (df_res["pct_max"] >= 10).astype(int)
                df_res["Loss"] = (df_res["pct_min"] <= -10).astype(int)

                # Grouped results
                summary = df_res.groupby("symbol").agg(
                    Count=("symbol", "count"),
                    Wins=("Win", "sum"),
                    Loss=("Loss", "sum"),
                ).reset_index()

                summary["Win%"] = (summary["Wins"] / summary["Count"] * 100).round(2)
                summary["Loss%"] = (summary["Loss"] / summary["Count"] * 100).round(2)

                # merge summary back to the main DF
                df_res = df_res.merge(summary, on="symbol", how="left")

            st.session_state["scan_results"] = df_res
            st.success(f"Scan complete. {len(df_res)} qualifying records found.")

        st.markdown("### Scan Results")

        df_res = st.session_state["scan_results"]

        if df_res.empty:
            st.info("No results yet. Run a scan to populate data.")
        else:

            # ⭐ MULTIPLE HIT FILTER
            min_hits = st.slider("Show stocks repeating at least N times", 1, 10, 1)
            df_filtered = df_res[df_res["Count"] >= min_hits]

            st.dataframe(df_filtered, use_container_width=True)

            # ⭐ CSV DOWNLOAD button
            csv = df_filtered.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Download Filtered CSV",
                csv,
                f"aspect_scan_filtered.csv",
                "text/csv"
            )

            # ⭐ Summary stats section
            st.subheader("Summary Insights")
            st.write(df_filtered[["symbol","Count","Wins","Loss","Win%","Loss%"]]
                     .drop_duplicates()
                     .sort_values(by="Win%", ascending=False))

            st.success(f"Stocks meeting criteria: {df_filtered['symbol'].nunique()}")

# TAB 3 CHART --------------------------------------------------
with tabs[2]:
    df=st.session_state["results"]
    if df.empty:
        st.info("No results yet")
    else:
        symbols=sorted(df["symbol"].unique())
        s=st.selectbox("Symbol",symbols)
        ad=st.selectbox("Aspect Date",df[df["symbol"]==s]["aspect_date"])

        files=requests.get(GITHUB_DIR_API).json()
        url=[f["download_url"] for f in files if f["name"]==f"{s}.parquet"][0]
        df2=load_parquet(url)

        d=datetime.datetime.strptime(ad,"%d-%m-%Y").date()
        w=df2[(df2.index.date>=d-datetime.timedelta(days=30)) &
              (df2.index.date<=d+datetime.timedelta(days=40))]

        fig=Figure(figsize=(10,4))
        ax=fig.add_subplot(111)
        mpf.plot(
            w[["open","high","low","close"]],
            type="candle",ax=ax,style="charles"
        )
        ax.axvline(w[w.index.date==d].index[0],color="orange")

        st.pyplot(fig)
