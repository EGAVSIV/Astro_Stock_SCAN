import datetime
import json
import requests
import pandas as pd
import swisseph as swe

# ---------------------------------------------------------------------
# CONFIG & CONSTANTS
# ---------------------------------------------------------------------
swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)

ZODIACS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

PLANETS = {
    "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY,
    "Venus": swe.VENUS, "Mars": swe.MARS, "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN, "Rahu": swe.MEAN_NODE, "Ketu": "KETU"
}

ASPECTS = {
    "Opposition": {"Aries": "Libra", "Taurus": "Scorpio", "Gemini": "Sagittarius", "Cancer": "Capricorn", "Leo": "Aquarius", "Virgo": "Pisces", "Libra": "Aries", "Scorpio": "Taurus", "Sagittarius": "Gemini", "Capricorn": "Cancer", "Aquarius": "Leo", "Pisces": "Virgo"},
    "Conjunction": {z: z for z in ZODIACS},
    "Square": {"Aries": "Cancer", "Taurus": "Leo", "Gemini": "Virgo", "Cancer": "Libra", "Leo": "Scorpio", "Virgo": "Sagittarius", "Libra": "Capricorn", "Scorpio": "Aquarius", "Sagittarius": "Pisces", "Capricorn": "Aries", "Aquarius": "Taurus", "Pisces": "Gemini"},
    "Trine": {"Aries": "Leo", "Taurus": "Virgo", "Gemini": "Libra", "Cancer": "Scorpio", "Leo": "Sagittarius", "Virgo": "Capricorn", "Libra": "Aquarius", "Scorpio": "Pisces", "Sagittarius": "Aries", "Capricorn": "Taurus", "Aquarius": "Gemini", "Pisces": "Cancer"},
    "Sextile": {"Aries": "Gemini", "Taurus": "Cancer", "Gemini": "Leo", "Cancer": "Virgo", "Leo": "Libra", "Virgo": "Scorpio", "Libra": "Sagittarius", "Scorpio": "Capricorn", "Sagittarius": "Aquarius", "Capricorn": "Pisces", "Aquarius": "Aries", "Pisces": "Taurus"}
}

GITHUB_DIR_API = "https://api.github.com/repos/EGAVSIV/Stock_Scanner_With_ASTA_Parameters/contents/stock_data_D"

# ---------------------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------------------
def get_sidereal_lon_from_jd(jd, planet_code):
    if planet_code == "KETU":
        rahu_res = swe.calc_ut(jd, swe.MEAN_NODE)
        rahu_lon = rahu_res[0][0] if isinstance(rahu_res[0], (list, tuple)) else rahu_res[0]
        rahu_speed = rahu_res[0][3] if isinstance(rahu_res[0], (list, tuple)) else rahu_res[3]
        ayan = swe.get_ayanamsa_ut(jd)
        return ((rahu_lon - ayan) % 360 + 180) % 360, rahu_speed

    res = swe.calc_ut(jd, planet_code)
    lon = res[0][0] if isinstance(res[0], (list, tuple)) else res[0]
    speed = res[0][3] if isinstance(res[0], (list, tuple)) else res[3]
    ayan = swe.get_ayanamsa_ut(jd)
    return (lon - ayan) % 360, speed

def get_zodiac_name(sid_lon: float) -> str:
    return ZODIACS[int(sid_lon // 30) % 12]

def find_zodiac_aspect_events(planet1, planet2, aspect_name, years_back=5, years_forward=2):
    events = []
    today = datetime.datetime.now()
    jd_today = swe.julday(today.year, today.month, today.day, today.hour + today.minute/60)

    p1, p2 = PLANETS[planet1], PLANETS[planet2]
    prev_state = False

    for h in range(-years_back * 365 * 24, years_forward * 365 * 24, 1):
        jd = jd_today + h / 24
        lon1, _ = get_sidereal_lon_from_jd(jd, p1)
        lon2, _ = get_sidereal_lon_from_jd(jd, p2)
        z1, z2 = get_zodiac_name(lon1), get_zodiac_name(lon2)

        current_state = (z2 == ASPECTS[aspect_name].get(z1))
        if not prev_state and current_state:
            y, m, d, hr = swe.revjul(jd)
            events.append({
                "date": f"{d:02d}-{m:02d}-{y}",
                "time": f"{int(hr):02d}:{int((hr - int(hr)) * 60):02d}",
                "planet1": planet1, "zodiac1": z1,
                "planet2": planet2, "zodiac2": z2,
                "aspect": aspect_name
            })
        prev_state = current_state

    return events

def analyze_symbol(df, aspect_dates, lookahead_days=15):
    results = []
    for ds in aspect_dates:
        try:
            d = datetime.datetime.strptime(ds, "%d-%m-%Y").date()
        except Exception:
            continue

        mask = df.index.date == d
        if not mask.any(): continue

        idx = df.index[mask][0]
        close_on_date = float(df.loc[idx, "close"])
        idx_pos = df.index.get_loc(idx)
        window = df.iloc[idx_pos + 1 : idx_pos + 1 + lookahead_days]
        
        if window.empty: continue

        pct_max = ((float(window["close"].max()) - close_on_date) / close_on_date) * 100
        pct_min = ((float(window["close"].min()) - close_on_date) / close_on_date) * 100

        results.append({
            "aspect_date": ds,
            "close": close_on_date,
            "pct_max": round(pct_max, 2),
            "pct_min": round(pct_min, 2)
        })
    return results

def run_pipeline():
    print("Computing Aspect Events...")
    aspect_events = find_zodiac_aspect_events("Jupiter", "Saturn", "Trine", years_back=5, years_forward=2)
    aspect_dates = [e["date"] for e in aspect_events]

    print(f"Scanning stock data across {len(aspect_dates)} aspect dates...")
    files = requests.get(GITHUB_DIR_API).json()
    scan_results = []

    for f in files:
        if not f.get("name", "").endswith(".parquet"): continue
        sym = f["name"].replace(".parquet", "")
        
        try:
            df = pd.read_parquet(f["download_url"], engine="pyarrow")
            dt_col = [c for c in df.columns if c.lower() in ("datetime", "date", "time")][0]
            df.index = pd.to_datetime(df[dt_col])
            df = df.sort_index()
            
            items = analyze_symbol(df, aspect_dates)
            for it in items:
                if it["pct_max"] >= 10.0 or it["pct_min"] <= -10.0:
                    scan_results.append({
                        "symbol": sym,
                        "aspect_date": it["aspect_date"],
                        "close": it["close"],
                        "pct_max": it["pct_max"],
                        "pct_min": it["pct_min"],
                        "direction": "UP" if it["pct_max"] >= 10 else "DOWN"
                    })
        except Exception:
            continue

    output_payload = {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "aspect_events": aspect_events,
        "scan_results": scan_results
    }

    with open("scan_results.json", "w") as out_file:
        json.dump(output_payload, out_file, indent=4)

    print("Success! Updated scan_results.json.")

if __name__ == "__main__":
    run_pipeline()
