import datetime
import requests
import pandas as pd
import swisseph as swe
import streamlit as st
import matplotlib
from matplotlib.figure import Figure
import mplfinance as mpf

matplotlib.use("Agg")

#--------------------------------------------------
# CONFIG
#--------------------------------------------------
st.set_page_config(
    page_title="Planet 🪐 Aspect Scanner",
    page_icon="✨",
    layout="wide",
)

THEMES = {
    "Royal Blue": {"bg": "#0E1A2B", "fg": "white", "accent": "#00FFFF"},
    "Sunset Orange": {"bg": "#2E1414", "fg": "white", "accent": "#FF8243"},
    "Emerald Green": {"bg": "#062A20", "fg": "white", "accent": "#00C896"},
    "Dark Mode": {"bg": "#000000", "fg": "#A0A0A0", "accent": "#4F8CFB"},
}

theme = st.sidebar.selectbox("Theme", list(THEMES.keys()))
color = THEMES[theme]

st.markdown(
    f"""
    <style>
    body {{
        background-color: {color['bg']};
        color:{color['fg']};
        font-family: 'Segoe UI', sans-serif;
    }}
    .stButton button {{
        background:{color['accent']};
        color:black;
        border-radius:6px;
        font-size:18px;
        padding:6px 20px;
    }}
    h1,h2,h3 {{
        color:{color['accent']};
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

#--------------------------------------------------
# ASTRO constants
#--------------------------------------------------
swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)

NAK_DEG = 13 + 1/3
ZODIACS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]

PLANETS = {
    "Sun": swe.SUN, "Moon": swe.MOON,
    "Mercury": swe.MERCURY, "Venus": swe.VENUS,
    "Mars": swe.MARS, "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN, "Rahu": swe.TRUE_NODE
}

ASPECTS = {
    "Opposition": {
        "Aries":"Libra","Taurus":"Scorpio","Gemini":"Sagittarius","Cancer":"Capricorn",
        "Leo":"Aquarius","Virgo":"Pisces","Libra":"Aries","Scorpio":"Taurus",
        "Sagittarius":"Gemini","Capricorn":"Cancer","Aquarius":"Leo","Pisces":"Virgo"
    },
    "Conjunction": {z:z for z in ZODIACS},
    "Square":{
        "Aries":"Cancer","Taurus":"Leo","Gemini":"Virgo","Cancer":"Libra",
        "Leo":"Scorpio","Virgo":"Sagittarius","Libra":"Capricorn","Scorpio":"Aquarius",
        "Sagittarius":"Pisces","Capricorn":"Aries","Aquarius":"Taurus","Pisces":"Gemini"
    }
}

# GitHub Data repository
GITHUB_DIR = "https://api.github.com/repos/EGAVSIV/Stock_Scanner_With_ASTA_Parameters/contents/stock_data_D"


#--------------------------------------------------
# ORIGINAL EXACT TKINTER LOGIC
#--------------------------------------------------
def get_sidereal_lon(jd, code):
    res = swe.calc_ut(jd, code)
    lon = res[0][0]
    sp = res[0][3]
    ay = swe.get_ayanamsa_ut(jd)
    return (lon - ay) % 360, sp


def get_zodiac_name(slon):
    return ZODIACS[int(slon // 30)]


def find_aspect_dates(p1, p2, asp, years_back=10, years_fwd=5):
    today = datetime.datetime.now()
    jd0 = swe.julday(today.year, today.month, today.day)

    code1, code2 = PLANETS[p1], PLANETS[p2]
    amap = ASPECTS[asp]

    past = []
    future = []

    for off in range(-365 * years_back, 365 * years_fwd):
        jd = jd0 + off

        lon1, _ = get_sidereal_lon(jd, code1)
        lon2, _ = get_sidereal_lon(jd, code2)

        if amap.get(get_zodiac_name(lon1)) == get_zodiac_name(lon2):
            y, m, d, _ = swe.revjul(jd)
            ds = f"{d:02d}-{m:02d}-{y}"

            if off < 0:
                past.append(ds)
            else:
                future.append(ds)

    def uniq_start(lst):
        out = []
        prev = None
        for d in lst:
            if prev is None or (datetime.datetime.strptime(d, "%d-%m-%Y") -
                                datetime.datetime.strptime(prev, "%d-%m-%Y")).days != 1:
                out.append(d)
            prev = d
        return out

    return uniq_start(past)[-20:], uniq_start(future)[:5]


def load_parquet_from_github(url):
    return pd.read_parquet(url, engine="pyarrow")


#--------------------------------------------------
# UI START
#--------------------------------------------------
st.title("🪐 Planetary Aspect + Stock Scanner")

tab1, tab2, tab3 = st.tabs(["♍ Aspect Finder", "📈 Stock Scanner", "🕯 Chart Viewer"])

#--------------------------------------------------
# TAB 1
#--------------------------------------------------
with tab1:
    c1, c2, c3 = st.columns(3)

    with c1: p1 = st.selectbox("Planet 1", list(PLANETS))
    with c2: asp = st.selectbox("Aspect", list(ASPECTS))
    with c3: p2 = st.selectbox("Planet 2", list(PLANETS))

    if st.button("🔍 Find Dates"):
        past, future = find_aspect_dates(p1, p2, asp)
        st.success(f"Found {len(past)} past & {len(future)} future dates")

        st.subheader("Past Aspect Starts")
        st.write(past)

        st.subheader("Next Aspect Starts")
        st.write(future)

        st.session_state["aspect_list"] = past


#--------------------------------------------------
# TAB 2 – SCANNER
#--------------------------------------------------
with tab2:
    if "aspect_list" not in st.session_state:
        st.warning("Compute aspects first")
        st.stop()

    files = requests.get(GITHUB_DIR).json()
    results = []

    with st.spinner("Scanning GitHub parquet..."):

        for f in files:
            if not f["name"].endswith(".parquet"):
                continue

            sym = f["name"].replace(".parquet", "")
            df = load_parquet_from_github(f["download_url"])

            df = df.set_index(pd.to_datetime(df["datetime"]))
            for ds in st.session_state["aspect_list"]:
                d = datetime.datetime.strptime(ds, "%d-%m-%Y").date()

                mask = df.index.date == d
                if not mask.any(): continue

                idx = df.index[mask][0]
                close = float(df.loc[idx, "close"])
                window = df.iloc[df.index.get_loc(idx)+1: df.index.get_loc(idx)+11]

                if window.empty: continue

                pct = ((window["close"].max() - close) / close) * 100

                if pct >= 10:
                    results.append({"symbol": sym, "date": ds, "gain%": round(pct, 2)})

    out = pd.DataFrame(results)
    st.dataframe(out, use_container_width=True)
    st.session_state["scanner"] = out


#--------------------------------------------------
# TAB 3 – CANDLES
#--------------------------------------------------
with tab3:
    if "scanner" not in st.session_state or st.session_state["scanner"].empty:
        st.info("Run scan first")
        st.stop()

    df = st.session_state["scanner"]
    sym = st.selectbox("Symbol", sorted(df["symbol"].unique()))
    dt = st.selectbox("Aspect Date", df[df.symbol == sym]["date"].unique())

    files = requests.get(GITHUB_DIR).json()
    url = [f["download_url"] for f in files if f["name"] == sym + ".parquet"][0]

    ddf = load_parquet_from_github(url)
    ddf = ddf.set_index(pd.to_datetime(ddf["datetime"]))

    d1 = datetime.datetime.strptime(dt, "%d-%m-%Y").date()
    w = ddf[(ddf.index.date >= d1 - datetime.timedelta(30)) &
            (ddf.index.date <= d1 + datetime.timedelta(30))]

    fig = Figure(figsize=(10, 3))
    ax = fig.add_subplot(111)
    mpf.plot(w[["open", "high", "low", "close"]], ax=ax, type="candle", style="charles")
    st.pyplot(fig)
