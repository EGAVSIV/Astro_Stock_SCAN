import time
import math
import datetime
import requests
import pandas as pd
import swisseph as swe
import matplotlib
import streamlit as st
from matplotlib.figure import Figure
import mplfinance as mpf

matplotlib.use("Agg")

# ---------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------
st.set_page_config(page_title="Planetary Aspects & Stock Scanner — Web", layout="wide")

# GitHub data source
GITHUB_DIR_API = "https://api.github.com/repos/EGAVSIV/Stock_Scanner_With_ASTA_Parameters/contents/stock_data_D"

# swisseph
swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)

# Astrology constants
NAK_DEG = 13 + 1/3
ZODIACS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]

PLANETS = {
    "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY,
    "Venus": swe.VENUS, "Mars": swe.MARS, "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN, "Rahu": swe.TRUE_NODE
}

ASPECTS = {
    "Opposition": {
        "Aries": "Libra","Taurus":"Scorpio","Gemini":"Sagittarius","Cancer":"Capricorn",
        "Leo":"Aquarius","Virgo":"Pisces","Libra":"Aries","Scorpio":"Taurus",
        "Sagittarius":"Gemini","Capricorn":"Cancer","Aquarius":"Leo","Pisces":"Virgo"
    },
    "Conjunction": {z:z for z in ZODIACS}
}

# ---------------------------------------------------------------------
# HELPER FUNCS
# ---------------------------------------------------------------------
def get_sidereal_lon(jd, code):
    res = swe.calc_ut(jd, code)
    lon = res[0][0]
    speed = res[0][3]
    ayan = swe.get_ayanamsa_ut(jd)
    return (lon - ayan) % 360, speed

def get_zodiac(x):
    return ZODIACS[int(x//30)%12]

def load_parquet_from_github(url):
    return pd.read_parquet(url, engine="pyarrow")

def analyze_symbol(df, aspect_dates):
    results=[]
    for ds in aspect_dates:
        d=datetime.datetime.strptime(ds,"%d-%m-%Y").date()
        mask=df.index.date==d
        if not mask.any():continue
        idx=df.index[mask][0]
        cls=float(df.loc[idx,"close"])
        pos=df.index.get_loc(idx)
        w=df.iloc[pos+1:pos+11]
        if w.empty: continue
        pct_max=(w["close"].max()-cls)/cls*100
        pct_min=(w["close"].min()-cls)/cls*100
        results.append({
            "aspect_date": ds,
            "close":cls,
            "max10":float(w["close"].max()),
            "min10":float(w["close"].min()),
            "pct_max":pct_max,
            "pct_min":pct_min
        })
    return results

# ---------------------------------------------------------------------
# STATE INIT
# ---------------------------------------------------------------------
if "aspect_dates" not in st.session_state:
    st.session_state["aspect_dates"]=[]
if "scan_results" not in st.session_state:
    st.session_state["scan_results"]=pd.DataFrame()

# ---------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------
st.title("Planetary Aspects & Stock Scanner — Web")

tabs = st.tabs(["Aspects","Scan","Charts"])

# ---------------------------------------------------------------------
# TAB 1 – Aspects
# ---------------------------------------------------------------------
with tabs[0]:

    p1 = st.selectbox("Planet 1", list(PLANETS.keys()))
    p2 = st.selectbox("Planet 2", list(PLANETS.keys()))
    asp = st.selectbox("Aspect", list(ASPECTS.keys()))
    years_back = st.number_input("Years Back",1,50,10)
    years_fwd  = st.number_input("Years Forward",1,50,5)

    if st.button("Find Aspect Dates"):

        today=datetime.datetime.now()
        jd=swe.julday(today.year,today.month,today.day,today.hour+today.minute/60)

        results=[]
        for i in range(-365*years_back,365*years_fwd):
            lon1,_=get_sidereal_lon(jd+i,PLANETS[p1])
            lon2,_=get_sidereal_lon(jd+i,PLANETS[p2])
            if ASPECTS[asp][get_zodiac(lon1)]==get_zodiac(lon2):
                y,m,d,_ = swe.revjul(jd+i)
                results.append(f"{d:02d}-{m:02d}-{y}")

        st.session_state.aspect_dates = results
        st.write(results)

# ---------------------------------------------------------------------
# TAB 2 – SCAN
# ---------------------------------------------------------------------
with tabs[1]:
    if st.button("Run Scan"):

        if not st.session_state.aspect_dates:
            st.warning("Compute aspects first!")
            st.stop()

        files = requests.get(GITHUB_DIR_API).json()
        all_results=[]

        with st.spinner("Downloading from GitHub..."):
            for f in files:
                if f["name"].endswith(".parquet"):

                    sym=f["name"].replace(".parquet","")
                    url=f["download_url"]

                    df=load_parquet_from_github(url)
                    if "datetime" in df:
                        df=df.set_index(pd.to_datetime(df["datetime"]))
                    df=df.sort_index()

                    items=analyze_symbol(df,st.session_state.aspect_dates)

                    for it in items:
                        if it["pct_max"]>=10 or it["pct_min"]<=-10:
                            all_results.append({
                                "symbol":sym,
                                **it
                            })

        st.session_state.scan_results=pd.DataFrame(all_results)

    st.dataframe(st.session_state.scan_results)

# ---------------------------------------------------------------------
# TAB 3 – Charts
# ---------------------------------------------------------------------
with tabs[2]:
    df = st.session_state.scan_results
    if df.empty:
        st.info("Run scan first.")
    else:
        symbol=st.selectbox("Symbol",sorted(df.symbol.unique()))
        date = st.selectbox("Aspect Date", df[df.symbol==symbol]["aspect_date"].unique())

        # load data again
        files=requests.get(GITHUB_DIR_API).json()
        url=[f["download_url"] for f in files if f["name"]==symbol+".parquet"][0]
        ddf=load_parquet_from_github(url)
        ddf=ddf.set_index(pd.to_datetime(ddf["datetime"]))

        start=datetime.datetime.strptime(date,"%d-%m-%Y").date()-datetime.timedelta(days=20)
        end  =start+datetime.timedelta(days=40)
        w=ddf[(ddf.index.date>=start)&(ddf.index.date<=end)]

        fig=Figure(figsize=(8,3))
        ax=fig.add_subplot(111)
        mpf.plot(w[["open","high","low","close"]], type="candle", ax=ax)
        st.pyplot(fig)
