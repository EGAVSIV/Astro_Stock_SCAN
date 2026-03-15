import datetime
import requests
import pandas as pd
import swisseph as swe
import streamlit as st
import matplotlib
import base64
import hashlib

# ------------------------------------------------------------
# STREAMLIT CONFIG
# ------------------------------------------------------------
st.set_page_config(
    page_title="🪐 Nakshatra Conjunction Stock Scanner",
    page_icon="🪐",
    layout="wide"
)

# ------------------------------------------------------------
# LOGIN SYSTEM
# ------------------------------------------------------------
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
            st.error("Invalid Credentials")

    st.stop()

# ------------------------------------------------------------
# ASTRO CONFIG
# ------------------------------------------------------------
swe.set_sid_mode(swe.SIDM_LAHIRI)

NAK_DEG = 13 + 1/3

PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Rahu": swe.MEAN_NODE
}

NAKSHATRAS = [
"Ashwini","Bharani","Krittika","Rohini","Mrigashira",
"Ardra","Punarvasu","Pushya","Ashlesha",
"Magha","Purva Phalguni","Uttara Phalguni",
"Hasta","Chitra","Swati","Vishakha",
"Anuradha","Jyeshtha","Mula",
"Purva Ashadha","Uttara Ashadha",
"Shravana","Dhanishta","Shatabhisha",
"Purva Bhadrapada","Uttara Bhadrapada","Revati"
]

# ------------------------------------------------------------
# PLANET POSITION
# ------------------------------------------------------------
def get_sidereal_lon(jd, planet):

    res = swe.calc_ut(jd, planet)

    try:
        lon = res[0][0]
    except:
        lon = res[0]

    ayan = swe.get_ayanamsa_ut(jd)

    return (lon - ayan) % 360


def get_nakshatra(lon):

    nak_index = int(lon // NAK_DEG)

    nak = NAKSHATRAS[nak_index]

    pada = int((lon % NAK_DEG) / (NAK_DEG/4)) + 1

    return nak, pada


# ------------------------------------------------------------
# FIND NAKSHATRA CONJUNCTION
# ------------------------------------------------------------
def find_nakshatra_conjunction_dates(
        planet1,
        planet2,
        years_back=20,
        years_forward=5):

    today = datetime.datetime.now()

    jd_today = swe.julday(
        today.year,
        today.month,
        today.day
    )

    p1 = PLANETS[planet1]
    p2 = PLANETS[planet2]

    past = []
    future = []

    start = -365 * years_back
    end = 365 * years_forward

    prev_match = False

    for offset in range(start, end):

        jd = jd_today + offset

        lon1 = get_sidereal_lon(jd, p1)
        lon2 = get_sidereal_lon(jd, p2)

        nak1,_ = get_nakshatra(lon1)
        nak2,_ = get_nakshatra(lon2)

        match = nak1 == nak2

        if match and not prev_match:

            y,m,d,_ = swe.revjul(jd)

            date_str = f"{d:02d}-{m:02d}-{y}"

            if offset < 0:
                past.append(date_str)
            else:
                future.append(date_str)

        prev_match = match

    return past[-20:], future[:5]


# ------------------------------------------------------------
# STOCK DATA LOADER
# ------------------------------------------------------------
GITHUB_DATA = "https://api.github.com/repos/EGAVSIV/Stock_Scanner_With_ASTA_Parameters/contents/stock_data_D"


def load_stock(url):

    df = pd.read_parquet(url)

    df.index = pd.to_datetime(df["datetime"])

    return df


# ------------------------------------------------------------
# STOCK ANALYSIS
# ------------------------------------------------------------
def analyze_stock(df, dates):

    results = []

    for ds in dates:

        d = datetime.datetime.strptime(ds,"%d-%m-%Y").date()

        mask = df.index.date == d

        if not mask.any():
            continue

        idx = df.index[mask][0]

        close = df.loc[idx,"close"]

        window = df.loc[idx:].iloc[1:16]

        if window.empty:
            continue

        max_move = (window["close"].max()-close)/close*100
        min_move = (window["close"].min()-close)/close*100

        results.append({

            "date":ds,
            "close":close,
            "max_move":round(max_move,2),
            "min_move":round(min_move,2)

        })

    return results


# ------------------------------------------------------------
# UI
# ------------------------------------------------------------
st.title("🪐 Nakshatra Conjunction Stock Scanner")

col1,col2 = st.columns(2)

with col1:
    planet1 = st.selectbox("Planet 1", list(PLANETS.keys()))

with col2:
    planet2 = st.selectbox("Planet 2", list(PLANETS.keys()), index=1)


years_back = st.slider("Years Back",5,40,20)

if st.button("Find Nakshatra Conjunction Dates"):

    past,future = find_nakshatra_conjunction_dates(
        planet1,
        planet2,
        years_back
    )

    st.session_state["dates"] = past

    st.success("Events Found")

    st.write("Past Events")

    st.write(past)

    st.write("Future Events")

    st.write(future)


# ------------------------------------------------------------
# STOCK SCAN
# ------------------------------------------------------------
if "dates" in st.session_state:

    if st.button("Run Stock Scan"):

        files = requests.get(GITHUB_DATA).json()

        results = []

        for f in files:

            name = f["name"]

            if not name.endswith(".parquet"):
                continue

            symbol = name.replace(".parquet","")

            url = f["download_url"]

            try:
                df = load_stock(url)
            except:
                continue

            events = analyze_stock(df, st.session_state["dates"])

            for e in events:

                if e["max_move"]>10 or e["min_move"]<-10:

                    results.append({

                        "symbol":symbol,
                        "date":e["date"],
                        "max_move":e["max_move"],
                        "min_move":e["min_move"]

                    })

        df_res = pd.DataFrame(results)

        st.dataframe(df_res)

        st.success(f"{df_res['symbol'].nunique()} Stocks Found")
