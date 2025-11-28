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

# ---------------------------------------------------------------------
# MATPLOTLIB BACKEND
# ---------------------------------------------------------------------
matplotlib.use("Agg")

# ---------------------------------------------------------------------
# STREAMLIT PAGE CONFIG
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
    "Emerald Green": {"bg": "#062A20", "fg": "#FFFFFF", "accent": "#00C"Emerald Green": {"bg": "#062A20", "fg": "#FFFFFF", "accent": "#00C896"},
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
        font-family: "Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
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

NAK_DEG = 13 + 1/3

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
GITHUB_DIR_API = "https://api.github.com/repos/EGAVSIV/Stock_Scanner_With_ASTA_Parameters/contents/stock_data_D"

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
    sign_index = int(sid_lon // 30) % 12
    return ZODIACS[sign_index]


def find_aspect_dates(
    planet1: str,
    planet2: str,
    aspect_name: str,
    years_back: int = 10,
    years_forward: int = 5,
    limit_past: int = 20,
    limit_future: int = 5,
) -> Tuple[List[str], List[str]]:

    today = datetime.datetime.now()
    jd_today = swe.julday(
        today.year, today.month, today.day,
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
        unique_first_future(results_future, limit_future)
    )
