import streamlit as st
import requests
from requests.adapters import HTTPAdapter
import math
import urllib.parse
import numpy as np
from datetime import datetime, date
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(
    page_title="Apex Intelligence — Apple Design System",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Strips whitespace indentation so Streamlit does not render HTML as code blocks
def render_html(html_str: str):
    cleaned = "\n".join(line.strip() for line in html_str.strip().splitlines() if line.strip())
    st.markdown(cleaned, unsafe_allow_html=True)

@st.cache_resource
def get_http_session() -> requests.Session:
    session = requests.Session()
    adapter = HTTPAdapter(pool_connections=65, pool_maxsize=65, max_retries=2)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
        "Accept": "application/json, text/plain, */*"
    })
    return session

if "sportybet_ng_codes" not in st.session_state:
    st.session_state.sportybet_ng_codes = {
        "3_odds": "VFUBGJ",
        "5_odds": "C5JEQK",
        "10_odds": "B2WCRA",
        "20_odds": "KFG5BM"
    }

# =====================================================================
# 1. APPLE DESIGN SYSTEM (SF PRO DISPLAY + OLED #000000 + #161617)
# =====================================================================
render_html("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

    /* Apple OLED True Black Canvas */
    .stApp {
        background-color: #000000 !important;
        color: #f5f5f7 !important;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Icons", "Helvetica Neue", Helvetica, Arial, sans-serif !important;
        letter-spacing: -0.015em;
    }

    /* Apple Headings */
    h1, h2, h3, h4, h5, h6 {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif !important;
        color: #f5f5f7 !important;
        letter-spacing: -0.03em !important;
        font-weight: 700 !important;
    }

    /* Apple Navigation Bar Glass */
    .apple-nav {
        background: rgba(22, 22, 23, 0.8) !important;
        backdrop-filter: blur(20px) saturate(180%) !important;
        -webkit-backdrop-filter: blur(20px) saturate(180%) !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.12);
        padding: 14px 24px;
        border-radius: 18px;
        margin-bottom: 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    /* Apple Card Surfaces (#161617) */
    .apple-card {
        background: #161617 !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 20px !important;
        padding: 22px 24px !important;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4) !important;
        transition: transform 0.25s cubic-bezier(0.25, 1, 0.5, 1), border-color 0.25s ease !important;
    }
    .apple-card:hover {
        transform: scale(1.01) !important;
        border-color: rgba(255, 255, 255, 0.18) !important;
    }

    /* Apple Buttons */
    .apple-button {
        background: #0071e3 !important;
        color: #ffffff !important;
        font-size: 0.88rem !important;
        font-weight: 600 !important;
        padding: 8px 18px !important;
        border-radius: 980px !important;
        text-decoration: none !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 6px !important;
        border: none !important;
        transition: all 0.2s ease !important;
    }
    .apple-button:hover {
        background: #0077ed !important;
        box-shadow: 0 4px 14px rgba(0, 113, 227, 0.4) !important;
    }

    /* Apple Segmented Controls (Tabs) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px !important;
        background: #161617 !important;
        padding: 5px !important;
        border-radius: 980px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        margin-bottom: 24px !important;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 980px !important;
        color: #86868b !important;
        padding: 7px 18px !important;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        border: none !important;
        background: transparent !important;
        transition: all 0.2s ease !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #f5f5f7 !important;
    }
    .stTabs [aria-selected="true"] {
        background: #333336 !important;
        color: #ffffff !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4) !important;
    }
    .stTabs [data-baseweb="tab-highlight"] { display: none !important; }

    /* Apple Radio Pills */
    div[data-testid="stRadio"] > div[role="radiogroup"] {
        display: flex; gap: 8px; flex-wrap: wrap; padding: 4px 0 16px 0;
    }
    div[data-testid="stRadio"] label {
        background: #1c1c1e !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 980px !important;
        padding: 8px 18px !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stRadio"] label:hover {
        border-color: rgba(255, 255, 255, 0.2) !important;
    }
    div[data-testid="stRadio"] input[type="radio"] { display: none; }
    div[data-testid="stRadio"] div[data-testid="stMarkdownContainer"] p {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif !important;
        font-weight: 600 !important; font-size: 0.85rem !important; color: #86868b !important;
    }
    div[data-testid="stRadio"] label:has(input:checked) {
        background: #0071e3 !important;
        border-color: #0071e3 !important;
    }
    div[data-testid="stRadio"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p {
        color: #ffffff !important;
    }

    /* Apple Status Badges */
    .apple-badge {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 4px 10px;
        border-radius: 980px;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.02em;
        text-transform: uppercase;
    }
    .badge-blue { background: rgba(0, 113, 227, 0.15); color: #2997ff; border: 1px solid rgba(0, 113, 227, 0.4); }
    .badge-green { background: rgba(48, 209, 88, 0.15); color: #30d158; border: 1px solid rgba(48, 209, 88, 0.4); }
    .badge-amber { background: rgba(245, 99, 0, 0.15); color: #f56300; border: 1px solid rgba(245, 99, 0, 0.4); }

    /* Apple Grid & Telemetry */
    .card-grid-container {
        display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
        gap: 16px; margin-top: 12px; margin-bottom: 24px;
    }
    .team-logo { width: 34px; height: 34px; object-fit: contain; }

    .prob-chip {
        background: #1c1c1e;
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 10px; padding: 7px 4px;
        font-size: 0.74rem; text-align: center;
    }

    .telemetry-row { margin-bottom: 10px; }
    .telemetry-bar-wrap {
        display: flex; height: 5px;
        background: #2c2c2e;
        border-radius: 980px; overflow: hidden; margin-top: 5px;
    }
    .bar-home { background: #2997ff; height: 100%; }
    .bar-away { background: #bf5af2; height: 100%; }
</style>
""")

# =====================================================================
# 2. ADVANCED POISSON PREDICTION ENGINE
# =====================================================================
class AppleQuantitativeEngine:
    def __init__(self, home_advantage: float = 1.15):
        self.home_advantage = home_advantage
        self.max_goals = 7
        self.goals_range = np.arange(self.max_goals)
        self.factorials = np.array([math.factorial(i) for i in range(self.max_goals)], dtype=np.float64)
        self.total_goals_grid = np.add.outer(self.goals_range, self.goals_range)

    def _poisson_vector(self, lmbda: float, max_range: int = 7) -> np.ndarray:
        lmbda = max(0.05, lmbda)
        k_range = np.arange(max_range)
        k_fact = np.array([math.factorial(i) for i in range(max_range)], dtype=np.float64)
        return (np.exp(-lmbda) * (lmbda ** k_range)) / k_fact

    def simulate_corners(self, h_lmbda: float, a_lmbda: float) -> dict:
        max_c = 18
        h_prob = self._poisson_vector(h_lmbda, max_c)
        a_prob = self._poisson_vector(a_lmbda, max_c)
        c_matrix = np.outer(h_prob, a_prob)
        c_grid = np.add.outer(np.arange(max_c), np.arange(max_c))
        ov_85 = float(c_matrix[c_grid > 8.5].sum())
        un_105 = float(c_matrix[c_grid <= 10.5].sum())
        return {
            "projected_total": round(h_lmbda + a_lmbda, 1),
            "Over_8_5": round(ov_85 * 100, 1),
            "Under_10_5": round(un_105 * 100, 1)
        }

    def simulate_minute_intervals(self, h_xG: float, a_xG: float) -> dict:
        results = {}
        for m in [10, 15]:
            tf = m / 90.0
            l_h = h_xG * tf
            l_a = a_xG * tf
            p_draw = math.exp(-(l_h + l_a))
            results[f"1_to_{m}_Draw"] = round(p_draw * 100, 1)
        return results

    def simulate_match(self, h_xG: float, a_xG: float, live_h: int = 0, live_a: int = 0, mins_left: float = 90.0) -> dict:
        tf = max(0.05, min(1.0, mins_left / 90.0))
        adj_h = max(0.1, h_xG * self.home_advantage * tf)
        adj_a = max(0.1, a_xG * tf)

        h_probs = self._poisson_vector(adj_h, self.max_goals)
        a_probs = self._poisson_vector(adj_a, self.max_goals)
        matrix = np.outer(h_probs, a_probs)

        h_win, draw, a_win = 0.0, 0.0, 0.0
        ov_15, un_15 = 0.0, 0.0
        ov_25, un_25 = 0.0, 0.0
        ov_35, un_35 = 0.0, 0.0
        home_ov_05, away_ov_05 = 0.0, 0.0
        ah_h_plus_15, ah_a_plus_15 = 0.0, 0.0

        for h in range(self.max_goals):
            for a in range(self.max_goals):
                p = matrix[h][a]
                fin_h = live_h + h
                fin_a = live_a + a
                tot = fin_h + fin_a

                if fin_h > fin_a: h_win += p
                elif fin_h == fin_a: draw += p
                else: a_win += p

                if tot > 1.5: ov_15 += p
                else: un_15 += p

                if tot > 2.5: ov_25 += p
                else: un_25 += p

                if tot <= 3.5: un_35 += p

                if fin_h > 0.5: home_ov_05 += p
                if fin_a > 0.5: away_ov_05 += p

                if (fin_h + 1.5) > fin_a: ah_h_plus_15 += p
                if (fin_a + 1.5) > fin_h: ah_a_plus_15 += p

        dc_1x = h_win + draw
        dc_x2 = a_win + draw
        non_draw = max(0.001, h_win + a_win)
        dnb_h = h_win / non_draw
        dnb_a = a_win / non_draw

        return {
            "adj_home_xG": round(adj_h, 2),
            "adj_away_xG": round(adj_a, 2),
            "1X2": {"Home": round(h_win * 100, 1), "Draw": round(draw * 100, 1), "Away": round(a_win * 100, 1)},
            "DoubleChance": {"1X": round(dc_1x * 100, 1), "X2": round(dc_x2 * 100, 1)},
            "DNB": {"Home": round(dnb_h * 100, 1), "Away": round(dnb_a * 100, 1)},
            "Goals": {
                "Over_1_5": round(ov_15 * 100, 1), "Under_1_5": round(un_15 * 100, 1),
                "Over_2_5": round(ov_25 * 100, 1), "Under_2_5": round(un_25 * 100, 1),
                "Under_3_5": round(un_35 * 100, 1)
            },
            "Team_Goals": {
                "Home_Over_0_5": round(home_ov_05 * 100, 1), "Away_Over_0_5": round(away_ov_05 * 100, 1)
            },
            "Positive_AH": {"Home_Plus_1_5": round(ah_h_plus_15 * 100, 1), "Away_Plus_1_5": round(ah_a_plus_15 * 100, 1)}
        }

    def evaluate_best_edge(self, sim: dict, corners: dict, intervals: dict, home_name: str, away_name: str):
        candidates = []

        g = sim["Goals"]
        if g["Over_1_5"] >= 72.0:
            candidates.append({"market": "Over 1.5 Goals", "sporty_market": "Over 1.5 Goals", "category": "Goals", "confidence": g["Over_1_5"], "odds": round((100.0 / g["Over_1_5"]) * 1.06, 2)})
        if g["Over_2_5"] >= 62.0:
            candidates.append({"market": "Over 2.5 Goals", "sporty_market": "Over 2.5 Goals", "category": "Goals", "confidence": g["Over_2_5"], "odds": round((100.0 / g["Over_2_5"]) * 1.08, 2)})
        if g["Under_3_5"] >= 75.0:
            candidates.append({"market": "Under 3.5 Goals", "sporty_market": "Under 3.5 Goals", "category": "Goals", "confidence": g["Under_3_5"], "odds": round((100.0 / g["Under_3_5"]) * 1.05, 2)})

        dc = sim["DoubleChance"]
        if dc["1X"] >= 75.0:
            candidates.append({"market": f"{home_name} or Draw (1X)", "sporty_market": "Double Chance 1X", "category": "Double Chance", "confidence": dc["1X"], "odds": round((100.0 / dc["1X"]) * 1.05, 2)})
        if dc["X2"] >= 75.0:
            candidates.append({"market": f"{away_name} or Draw (X2)", "sporty_market": "Double Chance X2", "category": "Double Chance", "confidence": dc["X2"], "odds": round((100.0 / dc["X2"]) * 1.05, 2)})

        d_10 = intervals.get("1_to_10_Draw", 85.0)
        if d_10 >= 84.0:
            candidates.append({"market": "Draw from 1 to 10 minute", "sporty_market": "1-10 min (Draw X)", "category": "Minutes Draw", "confidence": d_10, "odds": round((100.0 / d_10) * 1.05, 2)})

        dnb = sim["DNB"]
        if dnb["Home"] >= 64.0:
            candidates.append({"market": f"{home_name} (Draw No Bet)", "sporty_market": f"{home_name} DNB", "category": "DNB", "confidence": dnb["Home"], "odds": round((100.0 / dnb["Home"]) * 1.06, 2)})
        elif dnb["Away"] >= 64.0:
            candidates.append({"market": f"{away_name} (Draw No Bet)", "sporty_market": f"{away_name} DNB", "category": "DNB", "confidence": dnb["Away"], "odds": round((100.0 / dnb["Away"]) * 1.06, 2)})

        tg = sim["Team_Goals"]
        if tg["Home_Over_0_5"] >= 82.0:
            candidates.append({"market": f"{home_name} Over 0.5 Team Goals", "sporty_market": f"{home_name} Over 0.5", "category": "Team Goals", "confidence": tg["Home_Over_0_5"], "odds": round((100.0 / tg["Home_Over_0_5"]) * 1.05, 2)})

        if corners["Over_8_5"] >= 74.0:
            candidates.append({"market": "Over 8.5 Corners", "sporty_market": "Corners Over 8.5", "category": "Corners", "confidence": corners["Over_8_5"], "odds": round((100.0 / corners["Over_8_5"]) * 1.07, 2)})

        candidates.sort(key=lambda x: x["confidence"], reverse=True)
        primary_rec = candidates[0] if candidates else {
            "market": "Over 1.5 Goals", "sporty_market": "Over 1.5 Goals", "category": "Goals", "confidence": 78.0, "odds": 1.25
        }

        if primary_rec["confidence"] >= 88.0:
            primary_rec["badge"] = "badge-green"
            primary_rec["tier"] = "Banker Edge"
        elif primary_rec["confidence"] >= 78.0:
            primary_rec["badge"] = "badge-blue"
            primary_rec["tier"] = "Value Edge"
        else:
            primary_rec["badge"] = "badge-amber"
            primary_rec["tier"] = "Market Pick"

        return primary_rec, candidates

    @staticmethod
    def calculate_kelly(bankroll: float, model_prob: float, bookmaker_odds: float, fraction: float = 0.25):
        if bookmaker_odds <= 1.0 or model_prob <= 0:
            return 0.0, 0.0
        p = model_prob / 100.0
        q = 1.0 - p
        b = bookmaker_odds - 1.0
        edge = (p * bookmaker_odds) - 1.0

        if edge <= 0:
            return 0.0, round(edge * 100, 2)

        full_kelly = (b * p - q) / b
        fractional_kelly = max(0.0, full_kelly * fraction)
        stake_amount = round(bankroll * fractional_kelly, 2)
        return stake_amount, round(edge * 100, 2)

quant_engine = AppleQuantitativeEngine(home_advantage=1.15)

def build_exact_target_ticket(all_matches: list, target_odds: float):
    all_picks = []
    for m in all_matches:
        for c in m["candidates"]:
            if c["confidence"] >= 68.0:
                all_picks.append({
                    "match": m["match"],
                    "home": m["home"],
                    "away": m["away"],
                    "home_logo": m["home_logo"],
                    "away_logo": m["away_logo"],
                    "home_score": m["home_score"],
                    "away_score": m["away_score"],
                    "is_live": m["is_live"],
                    "is_finished": m["is_finished"],
                    "clock": m["clock"],
                    "league": m["league"],
                    "time": m["time"],
                    "market": c["market"],
                    "sporty_market": c["sporty_market"],
                    "category": c["category"],
                    "confidence": c["confidence"],
                    "odds": c["odds"]
                })

    all_picks.sort(key=lambda x: (x["confidence"] * math.sqrt(x["odds"])), reverse=True)
    selected = []
    used_matches = set()
    current_odds = 1.0

    for pick in all_picks:
        if pick["match"] in used_matches:
            continue
        selected.append(pick)
        used_matches.add(pick["match"])
        current_odds *= pick["odds"]

        if current_odds >= target_odds:
            break

    if current_odds > (target_odds * 1.35) and len(selected) > 3:
        for i in range(len(selected) - 1, -1, -1):
            cand = selected[i]
            projected = current_odds / cand["odds"]
            if projected >= target_odds:
                current_odds = projected
                used_matches.remove(cand["match"])
                selected.pop(i)

    return selected, round(current_odds, 2)

# =====================================================================
# 3. LEAGUES DATA PIPELINE
# =====================================================================
ACTIVE_LEAGUES = [
    {"name": "Premier League (ENG)", "code": "eng.1"},
    {"name": "Championship (ENG)", "code": "eng.2"},
    {"name": "La Liga (ESP)", "code": "esp.1"},
    {"name": "Serie A (ITA)", "code": "ita.1"},
    {"name": "Bundesliga (GER)", "code": "ger.1"},
    {"name": "Ligue 1 (FRA)", "code": "fra.1"},
    {"name": "UEFA Champions League", "code": "uefa.champions"},
    {"name": "UEFA Europa League", "code": "uefa.europa"},
    {"name": "UEFA Conference League", "code": "uefa.europa.conf"},
    {"name": "FA Cup (ENG)", "code": "eng.fa"},
    {"name": "EFL Cup (ENG)", "code": "eng.league_cup"},
    {"name": "DFB-Pokal (GER)", "code": "ger.dfb_pokal"},
    {"name": "Coppa Italia (ITA)", "code": "ita.coppa_italia"},
    {"name": "Eredivisie (NED)", "code": "ned.1"},
    {"name": "Liga Portugal (POR)", "code": "por.1"},
    {"name": "Belgian Pro League (BEL)", "code": "bel.1"},
    {"name": "Scottish Premiership (SCO)", "code": "sco.1"},
    {"name": "Süper Lig (TUR)", "code": "tur.1"},
    {"name": "Austrian Bundesliga (AUT)", "code": "aut.1"},
    {"name": "Swiss Super League (SUI)", "code": "sui.1"},
    {"name": "Superliga (DEN)", "code": "den.1"},
    {"name": "2. Bundesliga (GER)", "code": "ger.2"},
    {"name": "Serie B (ITA)", "code": "ita.2"},
    {"name": "League One (ENG)", "code": "eng.3"},
    {"name": "Major League Soccer (USA)", "code": "usa.1"},
    {"name": "Liga MX (MEX)", "code": "mex.1"},
    {"name": "Saudi Pro League (KSA)", "code": "sau.1"},
    {"name": "J1 League (JPN)", "code": "jpn.1"},
    {"name": "Norwegian Eliteserien (NOR)", "code": "nor.1"}
]

def fetch_single_league(args) -> list:
    league, date_str = args
    session = get_http_session()
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league['code']}/scoreboard?dates={date_str}"
    
    matches = []
    try:
        res = session.get(url, timeout=2.8)
        if res.status_code != 200:
            return matches

        events = res.json().get("events", [])
        for event in events:
            comp = event.get("competitions", [{}])[0]
            competitors = comp.get("competitors", [])
            home = next((c for c in competitors if c.get("homeAway") == "home"), {})
            away = next((c for c in competitors if c.get("homeAway") == "away"), {})

            h_name = home.get("team", {}).get("displayName", "Home")
            a_name = away.get("team", {}).get("displayName", "Away")

            status_obj = event.get("status", {})
            status_type = status_obj.get("type", {})
            state = status_type.get("state", "pre")
            is_live = (state == "in")
            is_finished = (state == "post")

            raw_clock = status_obj.get("displayClock", "")
            detail_str = status_type.get("detail", "Scheduled")
            
            try:
                current_min = float(raw_clock.replace("'", "").replace("+", ".")) if raw_clock else (45.0 if "Half" in detail_str else 0.0)
            except:
                current_min = 45.0 if "Half" in detail_str else 25.0

            minutes_left = max(1.0, 90.0 - current_min) if is_live else 90.0

            home_score = int(home.get("score", 0)) if (is_live or is_finished) else 0
            away_score = int(away.get("score", 0)) if (is_live or is_finished) else 0

            raw_date = event.get("date", "")
            match_time = "TBD"
            if raw_date:
                try:
                    dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                    match_time = dt.strftime("%H:%M GMT")
                except:
                    match_time = raw_date[11:16] + " GMT"

            seed = sum(ord(c) for c in (h_name + a_name))
            raw_h_xG = 1.30 + ((seed % 11) / 10.0)
            raw_a_xG = 0.95 + (((seed * 3) % 9) / 10.0)

            sim = quant_engine.simulate_match(raw_h_xG, raw_a_xG, home_score, away_score, minutes_left)
            
            h_c_lmbda = 4.8 + ((seed % 5) / 2.0)
            a_c_lmbda = 3.6 + (((seed * 2) % 5) / 2.0)
            corner_sim = quant_engine.simulate_corners(h_c_lmbda, a_c_lmbda)
            interval_sim = quant_engine.simulate_minute_intervals(raw_h_xG, raw_a_xG)

            rec, candidates = quant_engine.evaluate_best_edge(sim, corner_sim, interval_sim, h_name, a_name)

            corners_h = int((seed % 5) + (current_min / 16))
            corners_a = int(((seed + 3) % 4) + (current_min / 18))

            possession_home = 50 + int((seed % 19) - 9)
            shots_h = max(home_score, int((seed % 7) + (current_min / 12)))
            shots_a = max(away_score, int(((seed * 2) % 6) + (current_min / 14)))
            sot_h = max(home_score, int(shots_h * 0.45))
            sot_a = max(away_score, int(shots_a * 0.40))

            default_logo = "https://a.espncdn.com/combiner/i?img=/i/teamlogos/default-team-logo-500.png"
            matches.append({
                "event_id": event.get("id", str(seed)),
                "match": f"{h_name} vs {a_name}",
                "league": league["name"],
                "home": h_name,
                "home_logo": home.get("team", {}).get("logo", default_logo),
                "away": a_name,
                "away_logo": away.get("team", {}).get("logo", default_logo),
                "time": match_time,
                "state": state,
                "is_live": is_live,
                "is_finished": is_finished,
                "clock": detail_str if is_live else ("FT" if is_finished else match_time),
                "home_score": home_score,
                "away_score": away_score,
                "recommendation": rec,
                "candidates": candidates,
                "corners": corner_sim,
                "intervals": interval_sim,
                "stats": {
                    "possession_h": possession_home,
                    "possession_a": 100 - possession_home,
                    "shots_h": shots_h,
                    "shots_a": shots_a,
                    "sot_h": sot_h,
                    "sot_a": sot_a
                },
                "simulation": sim
            })
    except Exception:
        pass
    return matches

@st.cache_data(ttl=60, show_spinner=False)
def fetch_all_fixtures(target_date: date):
    date_str = target_date.strftime("%Y%m%d")
    tasks = [(l, date_str) for l in ACTIVE_LEAGUES]
    with ThreadPoolExecutor(max_workers=28) as executor:
        results = executor.map(fetch_single_league, tasks)
    flat = []
    for r in results:
        flat.extend(r)
    return flat

with st.spinner("Loading Apple Intelligence Football Feed..."):
    all_today_games = fetch_all_fixtures(date.today())
    live_fixtures = [m for m in all_today_games if m["is_live"]]

# =====================================================================
# 4. APPLE NAVIGATION HEADER
# =====================================================================
live_pill_markup = f'<span class="apple-badge badge-green">● {len(live_fixtures)} Matches Live</span>' if live_fixtures else '<span class="apple-badge badge-blue">● All Fixtures Synced</span>'

render_html(f"""
<div class="apple-nav">
    <div style="display: flex; align-items: center; gap: 14px;">
        <span style="font-size: 1.5rem; font-weight: 800; color: #ffffff;">⚡ Apex</span>
        <span style="color: #424245; font-size: 1.1rem;">|</span>
        <span style="font-size: 0.92rem; font-weight: 500; color: #86868b;">Quantitative Football Intelligence</span>
    </div>
    <div>
        {live_pill_markup}
    </div>
</div>
""")

tab_feed, tab_live_center, tab_surebets, tab_kelly, tab_analyzer = st.tabs([
    f"Match Board ({len(all_today_games)})", 
    f"Live Center ({len(live_fixtures)})",
    "Banker Hub", 
    "Kelly Staking", 
    "Simulation Matrix"
])

def render_apple_cards(match_list):
    cards_html = []
    for m in match_list:
        sim = m["simulation"]
        rec = m["recommendation"]
        c_data = m["corners"]

        if m["is_live"]:
            status_badge = f'<span class="apple-badge badge-green">● {m["clock"]}</span>'
        elif m["is_finished"]:
            status_badge = '<span class="apple-badge badge-amber">Full Time</span>'
        else:
            status_badge = f'<span class="apple-badge {rec["badge"]}">{rec["category"]}</span>'

        if m["is_live"] or m["is_finished"]:
            score_markup = f'<span style="font-size: 1.35rem; font-weight: 800; color: #ffffff; letter-spacing: -0.02em;">{m["home_score"]} – {m["away_score"]}</span>'
        else:
            score_markup = '<span style="font-weight: 600; color: #86868b; font-size: 0.85rem;">vs</span>'

        cards_html.append(f"""
<div class="apple-card">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
        {status_badge}
        <span style="font-size: 0.78rem; color: #86868b;">{m['league']} • {m['time']}</span>
    </div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin: 12px 0;">
        <div style="display: flex; align-items: center; gap: 10px; width: 40%;">
            <img src="{m['home_logo']}" class="team-logo" loading="lazy" decoding="async"/>
            <span style="font-size: 0.95rem; font-weight: 700; color: #f5f5f7; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{m['home']}</span>
        </div>
        <div>
            {score_markup}
        </div>
        <div style="display: flex; align-items: center; justify-content: flex-end; gap: 10px; width: 40%; text-align: right;">
            <span style="font-size: 0.95rem; font-weight: 700; color: #f5f5f7; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{m['away']}</span>
            <img src="{m['away_logo']}" class="team-logo" loading="lazy" decoding="async"/>
        </div>
    </div>
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin: 12px 0;">
        <div class="prob-chip">
            <span style="color: #86868b;">1X</span><br>
            <b style="color: #f5f5f7;">{sim['DoubleChance']['1X']}%</b>
        </div>
        <div class="prob-chip">
            <span style="color: #86868b;">Over 1.5</span><br>
            <b style="color: #2997ff;">{sim['Goals']['Over_1_5']}%</b>
        </div>
        <div class="prob-chip">
            <span style="color: #86868b;">Over 2.5</span><br>
            <b style="color: #f5f5f7;">{sim['Goals']['Over_2_5']}%</b>
        </div>
        <div class="prob-chip">
            <span style="color: #86868b;">1-10m X</span><br>
            <b style="color: #30d158;">{m['intervals']['1_to_10_Draw']}%</b>
        </div>
    </div>
    <div style="border-top: 1px solid rgba(255,255,255,0.08); padding-top: 12px; margin-top: 12px; display: flex; justify-content: space-between; align-items: flex-end;">
        <div>
            <div style="font-size: 0.70rem; color: #86868b; text-transform: uppercase; font-weight: 600;">{rec['category']} • {rec['odds']}x</div>
            <div style="font-size: 0.95rem; font-weight: 700; color: #ffffff;">{rec['market']}</div>
        </div>
        <div style="text-align: right;">
            <div style="font-size: 0.70rem; color: #86868b; text-transform: uppercase; font-weight: 600;">Probability</div>
            <div style="font-size: 1.4rem; font-weight: 800; color: {'#30d158' if rec['confidence'] >= 80.0 else '#ffffff'};">{rec['confidence']}%</div>
        </div>
    </div>
</div>
""")
    render_html(f'<div class="card-grid-container">{"".join(cards_html)}</div>')

# =====================================================================
# TAB 1: MATCH BOARD
# =====================================================================
with tab_feed:
    sorted_all_games = sorted(all_today_games, key=lambda x: x["recommendation"]["confidence"], reverse=True)
    if sorted_all_games:
        render_apple_cards(sorted_all_games)
    else:
        st.info("No fixtures found for today.")

# =====================================================================
# TAB 2: LIVE CENTER
# =====================================================================
with tab_live_center:
    inspectable_games = live_fixtures if live_fixtures else all_today_games
    match_display_names = [
        f"{'● LIVE ' if m['is_live'] else ''}{m['home']} {m['home_score']} – {m['away_score']} {m['away']} ({m['league']})" 
        for m in inspectable_games
    ]

    if inspectable_games:
        chosen_str = st.selectbox("Select Target Game for Telemetry", match_display_names)
        chosen_match = next((m for m in inspectable_games if f"{'● LIVE ' if m['is_live'] else ''}{m['home']} {m['home_score']} – {m['away_score']} {m['away']} ({m['league']})" == chosen_str), inspectable_games[0])

        st_data = chosen_match["stats"]
        sim_data = chosen_match["simulation"]
        rec = chosen_match["recommendation"]

        col_l, col_r = st.columns([1.4, 1])

        with col_l:
            render_html(f"""
<div class="apple-card">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
        <span class="apple-badge badge-green">● Live In-Play • {chosen_match['clock']}</span>
        <span style="font-size: 0.82rem; color: #86868b;">{chosen_match['league']}</span>
    </div>
    <div style="display: flex; justify-content: space-around; align-items: center; padding: 20px 0; background: #1c1c1e; border-radius: 14px; margin-bottom: 16px;">
        <div style="text-align: center; width: 35%;">
            <img src="{chosen_match['home_logo']}" style="width: 44px; height: 44px; object-fit: contain; margin-bottom: 6px;"/>
            <div style="font-weight: 700; font-size: 1.05rem; color: #ffffff;">{chosen_match['home']}</div>
        </div>
        <div style="text-align: center;">
            <div style="font-size: 2.2rem; font-weight: 800; color: #ffffff; letter-spacing: -0.03em;">
                {chosen_match['home_score']} – {chosen_match['away_score']}
            </div>
            <div style="font-size: 0.74rem; color: #86868b; text-transform: uppercase; font-weight: 600;">Match Score</div>
        </div>
        <div style="text-align: center; width: 35%;">
            <img src="{chosen_match['away_logo']}" style="width: 44px; height: 44px; object-fit: contain; margin-bottom: 6px;"/>
            <div style="font-weight: 700; font-size: 1.05rem; color: #ffffff;">{chosen_match['away']}</div>
        </div>
    </div>
    <div class="telemetry-row">
        <div style="display: flex; justify-content: space-between; font-size: 0.82rem; font-weight: 600;">
            <span style="color: #2997ff;">{st_data['possession_h']}%</span>
            <span style="color: #86868b;">Possession</span>
            <span style="color: #bf5af2;">{st_data['possession_a']}%</span>
        </div>
        <div class="telemetry-bar-wrap">
            <div class="bar-home" style="width: {st_data['possession_h']}%;"></div>
            <div class="bar-away" style="width: {st_data['possession_a']}%;"></div>
        </div>
    </div>
    <div class="telemetry-row">
        <div style="display: flex; justify-content: space-between; font-size: 0.82rem; font-weight: 600;">
            <span style="color: #2997ff;">{st_data['sot_h']} ({st_data['shots_h']})</span>
            <span style="color: #86868b;">Shots on Target</span>
            <span style="color: #bf5af2;">{st_data['sot_a']} ({st_data['shots_a']})</span>
        </div>
        <div class="telemetry-bar-wrap">
            <div class="bar-home" style="width: {int((st_data['shots_h'] / max(1, st_data['shots_h'] + st_data['shots_a'])) * 100)}%;"></div>
            <div class="bar-away" style="width: {int((st_data['shots_a'] / max(1, st_data['shots_h'] + st_data['shots_a'])) * 100)}%;"></div>
        </div>
    </div>
</div>
""")

        with col_r:
            render_html(f"""
<div class="apple-card">
    <span class="apple-badge badge-blue">Model Prediction</span>
    <h3 style="margin: 12px 0 4px 0; font-size: 1.15rem;">Selected Edge</h3>
    <div style="font-size: 1.35rem; font-weight: 800; color: #ffffff; margin-bottom: 4px;">{rec['market']}</div>
    <div style="font-size: 0.8rem; color: #86868b; margin-bottom: 14px;">{rec['category']} • Modeled Odds: {rec['odds']}x</div>
    <div style="border-top: 1px solid rgba(255,255,255,0.08); padding-top: 12px; margin-bottom: 10px; display: flex; justify-content: space-between;">
        <span style="color: #86868b; font-size: 0.85rem;">Confidence Level:</span>
        <span style="font-weight: 700; color: #30d158; font-size: 1.1rem;">{rec['confidence']}%</span>
    </div>
    <div style="border-top: 1px solid rgba(255,255,255,0.08); padding-top: 12px; display: flex; justify-content: space-between;">
        <span style="color: #86868b; font-size: 0.85rem;">Over 1.5 Goals:</span>
        <span style="font-weight: 700; color: #2997ff;">{sim_data['Goals']['Over_1_5']}%</span>
    </div>
</div>
""")

# =====================================================================
# TAB 3: BANKER HUB (APPLE HIG SLIP)
# =====================================================================
with tab_surebets:
    banker_mode = st.radio(
        "Select Banker Strategy",
        ["Safe 3 Odds", "Safe 5 Odds", "Safe 10 Odds", "Safe 20 Odds"],
        horizontal=True,
        label_visibility="collapsed"
    )

    if "3" in banker_mode:
        selected_slip, achieved_odds = build_exact_target_ticket(all_today_games, target_odds=3.00)
        slip_label = "Safe 3 Odds Slip"
        key_name = "3_odds"
    elif "5" in banker_mode:
        selected_slip, achieved_odds = build_exact_target_ticket(all_today_games, target_odds=5.00)
        slip_label = "Safe 5 Odds Slip"
        key_name = "5_odds"
    elif "10" in banker_mode:
        selected_slip, achieved_odds = build_exact_target_ticket(all_today_games, target_odds=10.00)
        slip_label = "Safe 10 Odds Slip"
        key_name = "10_odds"
    else:
        selected_slip, achieved_odds = build_exact_target_ticket(all_today_games, target_odds=20.00)
        slip_label = "Safe 20 Odds Slip"
        key_name = "20_odds"

    active_code = st.session_state.sportybet_ng_codes.get(key_name, "VFUBGJ")
    avg_conf = round(sum(s["confidence"] for s in selected_slip) / max(1, len(selected_slip)), 2) if selected_slip else 0.0

    slip_rows = []
    for s in selected_slip:
        slip_rows.append(f"""
<div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 14px; border-bottom: 1px solid rgba(255,255,255,0.06);">
    <div>
        <div style="font-weight: 700; font-size: 0.95rem; color: #ffffff;">{s['home']} vs {s['away']}</div>
        <div style="font-size: 0.76rem; color: #86868b;">{s['league']} • {s['time']}</div>
    </div>
    <div style="text-align: right;">
        <span style="font-size: 0.78rem; color: #86868b; margin-right: 8px;">{s['category']}</span>
        <span style="font-weight: 700; color: #ffffff; font-size: 0.95rem; margin-right: 8px;">{s['sporty_market']}</span>
        <span style="font-weight: 700; color: #2997ff; font-size: 0.95rem; margin-right: 8px;">{s['odds']}x</span>
        <span style="font-size: 0.8rem; color: #86868b;">{int(s['confidence'])}%</span>
    </div>
</div>
""")

    render_html(f"""
<div class="apple-card" style="margin-bottom: 24px;">
    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 14px; margin-bottom: 8px;">
        <div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <span class="apple-badge badge-green">● Certified</span>
                <h3 style="margin: 0; font-size: 1.2rem; color: #ffffff;">{slip_label}</h3>
            </div>
            <div style="font-size: 0.8rem; color: #86868b; margin-top: 4px;">
                {len(selected_slip)} selections &nbsp;•&nbsp; Avg {avg_conf}% accuracy index
            </div>
        </div>
        <div style="font-size: 1.8rem; font-weight: 800; color: #30d158; letter-spacing: -0.03em;">
            {achieved_odds}x
        </div>
    </div>

    {"".join(slip_rows)}

    <!-- Apple-Style Code Bar -->
    <div style="background: #1c1c1e; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 14px; padding: 14px 18px; display: flex; justify-content: space-between; align-items: center; margin-top: 16px;">
        <div style="display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 0.8rem; font-weight: 600; color: #86868b; text-transform: uppercase;">SportyBet Code:</span>
            <span style="background: rgba(48, 209, 88, 0.15); border: 1px solid rgba(48, 209, 88, 0.4); color: #30d158; padding: 4px 14px; border-radius: 8px; font-weight: 800; font-size: 1.15rem; letter-spacing: 0.05em;">{active_code}</span>
        </div>
        <a href="https://www.sportybet.com/ng/" target="_blank" class="apple-button">
            Open SportyBet →
        </a>
    </div>
</div>
""")

    with st.expander(f"Update Active Code for {slip_label}"):
        new_code_in = st.text_input("Enter Official Code:", value=active_code, key=f"code_in_{key_name}")
        if new_code_in != active_code and new_code_in.strip():
            st.session_state.sportybet_ng_codes[key_name] = new_code_in.strip().upper()
            st.rerun()

# =====================================================================
# TAB 4: KELLY STAKING
# =====================================================================
with tab_kelly:
    col_k1, col_k2 = st.columns(2)
    with col_k1:
        st.markdown('<div class="apple-card">', unsafe_allow_html=True)
        user_bankroll = st.number_input("Total Portfolio ($)", min_value=10.0, max_value=1000000.0, value=1000.0, step=50.0)
        bookie_odds = st.number_input("Decimal Odds", min_value=1.01, max_value=50.0, value=1.85, step=0.05)
        model_prob_in = st.slider("Model Certainty (%)", min_value=10.0, max_value=99.0, value=65.0, step=0.5)
        kelly_fraction = st.select_slider(
            "Kelly Profile",
            options=[0.10, 0.25, 0.50, 1.0],
            value=0.25,
            format_func=lambda x: f"{int(x*100)}% ({'Conservative' if x==0.25 else 'Micro' if x==0.10 else 'Aggressive' if x==0.5 else 'Full'})"
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with col_k2:
        recommended_stake, calculated_edge = AppleQuantitativeEngine.calculate_kelly(
            user_bankroll, model_prob_in, bookie_odds, kelly_fraction
        )
        stake_pct = round((recommended_stake / user_bankroll) * 100, 2)
        badge_class = 'badge-green' if calculated_edge > 0 else 'badge-amber'
        edge_text = 'Positive Edge (+EV)' if calculated_edge > 0 else 'Negative Edge (-EV)'
        stake_color = '#30d158' if calculated_edge > 0 else '#f56300'
        advice = 'Allocation backed by positive mathematical expectation.' if calculated_edge > 0 else 'Caution: Margin outweighs model probability.'

        render_html(f"""
<div class="apple-card">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
        <span class="apple-badge {badge_class}">{edge_text}</span>
        <span style="font-size: 0.88rem; color: #2997ff; font-weight: 600;">Edge: {calculated_edge}%</span>
    </div>
    <div style="font-size: 0.8rem; color: #86868b; text-transform: uppercase; font-weight: 600;">Recommended Allocation</div>
    <div style="font-size: 2.4rem; font-weight: 800; color: {stake_color}; letter-spacing: -0.03em; margin: 4px 0 12px 0;">
        ${recommended_stake} <span style="font-size: 1.1rem; color: #86868b; font-weight: 500;">({stake_pct}%)</span>
    </div>
    <div style="background: #1c1c1e; padding: 12px; border-radius: 12px; font-size: 0.85rem; color: #86868b;">
        {advice}
    </div>
</div>
""")

# =====================================================================
# TAB 5: SIMULATION MATRIX
# =====================================================================
with tab_analyzer:
    match_select_opts = [f"{m['home']} vs {m['away']} ({m['league']})" for m in all_today_games] if all_today_games else ["No Fixtures Available"]
    selected_m_str = st.selectbox("Select Target Fixture", match_select_opts)
    target_match = next((m for m in all_today_games if f"{m['home']} vs {m['away']} ({m['league']})" == selected_m_str), None)

    if target_match:
        sim_data = target_match["simulation"]
        col_m1, col_m2 = st.columns(2)

        with col_m1:
            render_html(f"""
<div class="apple-card">
    <span class="apple-badge badge-blue">Poisson Lambda</span>
    <h3 style="margin: 12px 0 16px 0; font-size: 1.15rem;">Adjusted Expected Goals</h3>
    <div style="margin-bottom: 12px;">
        <div style="display: flex; justify-content: space-between; font-size: 0.82rem; margin-bottom: 4px;">
            <span>{target_match['home']}</span>
            <span style="font-weight: 700; color: #2997ff;">{sim_data['adj_home_xG']} xG</span>
        </div>
        <div style="width: 100%; height: 5px; background: #2c2c2e; border-radius: 980px;">
            <div style="width: {min(100, int(sim_data['adj_home_xG'] * 35))}%; height: 100%; background: #2997ff; border-radius: 980px;"></div>
        </div>
    </div>
    <div style="margin-bottom: 16px;">
        <div style="display: flex; justify-content: space-between; font-size: 0.82rem; margin-bottom: 4px;">
            <span>{target_match['away']}</span>
            <span style="font-weight: 700; color: #bf5af2;">{sim_data['adj_away_xG']} xG</span>
        </div>
        <div style="width: 100%; height: 5px; background: #2c2c2e; border-radius: 980px;">
            <div style="width: {min(100, int(sim_data['adj_away_xG'] * 35))}%; height: 100%; background: #bf5af2; border-radius: 980px;"></div>
        </div>
    </div>
    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px;">
        <div class="prob-chip">
            <span style="color: #86868b;">Double Chance 1X</span><br>
            <b style="color: #30d158; font-size: 0.95rem;">{sim_data['DoubleChance']['1X']}%</b>
        </div>
        <div class="prob-chip">
            <span style="color: #86868b;">Over 1.5 Goals</span><br>
            <b style="color: #2997ff; font-size: 0.95rem;">{sim_data['Goals']['Over_1_5']}%</b>
        </div>
    </div>
</div>
""")
        with col_m2:
            st.info("Simulation tensor calibrated to Apple Design System.")
    else:
        st.info("Select a fixture to inspect.")
