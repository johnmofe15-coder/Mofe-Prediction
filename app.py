import streamlit as st
import requests
from requests.adapters import HTTPAdapter
import math
import numpy as np
from datetime import datetime, date, timedelta
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(
    page_title="Apex Quantitative Football Intelligence",
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
    adapter = HTTPAdapter(pool_connections=40, pool_maxsize=40, max_retries=3)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*"
    })
    return session

if "sportybet_ng_codes" not in st.session_state:
    st.session_state.sportybet_ng_codes = {
        "master_ticket": "VFUBGJ",
        "3_odds": "VFUBGJ",
        "5_odds": "C5JEQK",
        "10_odds": "B2WCRA",
        "20_odds": "KFG5BM"
    }

LEAGUE_TEMPO = {
    "ger.1": 3.20, "ned.1": 3.15, "nor.1": 3.05, "eng.1": 2.95,
    "bel.1": 2.85, "tur.1": 2.80, "ger.2": 2.90, "uefa.champions": 3.00,
    "eng.2": 2.55, "fra.1": 2.60, "esp.1": 2.55, "ita.1": 2.55,
    "usa.1": 2.85, "mex.1": 2.70, "sau.1": 2.90, "jpn.1": 2.50
}

# =====================================================================
# 1. QUANTITATIVE PREDICTION ENGINE (OVER 0.5 PERMANENTLY REMOVED)
# =====================================================================
class AntiTrapEngine:
    def __init__(self, home_advantage: float = 1.15):
        self.home_advantage = home_advantage
        self.max_goals = 7
        self.goals_range = np.arange(self.max_goals)
        self.factorials = np.array([math.factorial(i) for i in range(self.max_goals)], dtype=np.float64)

    def _poisson_vector(self, lmbda: float, max_range: int = 7) -> np.ndarray:
        lmbda = max(0.05, lmbda)
        k_range = np.arange(max_range)
        k_fact = np.array([math.factorial(i) for i in range(max_range)], dtype=np.float64)
        return (np.exp(-lmbda) * (lmbda ** k_range)) / k_fact

    def simulate_match(self, h_xG: float, a_xG: float, live_h: int = 0, live_a: int = 0, mins_left: float = 90.0) -> dict:
        tf = max(0.05, min(1.0, mins_left / 90.0))
        adj_h = max(0.1, h_xG * self.home_advantage * tf)
        adj_a = max(0.1, a_xG * tf)

        h_probs = self._poisson_vector(adj_h, self.max_goals)
        a_probs = self._poisson_vector(adj_a, self.max_goals)
        matrix = np.outer(h_probs, a_probs)

        h_win, draw, a_win = 0.0, 0.0, 0.0
        ov_15, ov_25, un_35 = 0.0, 0.0, 0.0

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
                if tot > 2.5: ov_25 += p
                if tot <= 3.5: un_35 += p

        dc_1x = h_win + draw
        dc_x2 = a_win + draw
        dc_12 = h_win + a_win

        non_draw = max(0.001, h_win + a_win)
        dnb_h = h_win / non_draw
        dnb_a = a_win / non_draw

        return {
            "adj_home_xG": round(adj_h, 2),
            "adj_away_xG": round(adj_a, 2),
            "1X2": {"Home": round(h_win * 100, 1), "Draw": round(draw * 100, 1), "Away": round(a_win * 100, 1)},
            "DoubleChance": {"1X": round(dc_1x * 100, 1), "X2": round(dc_x2 * 100, 1), "12": round(dc_12 * 100, 1)},
            "DNB": {"Home": round(dnb_h * 100, 1), "Away": round(dnb_a * 100, 1)},
            "Goals": {"Over_1_5": round(ov_15 * 100, 1), "Over_2_5": round(ov_25 * 100, 1), "Under_3_5": round(un_35 * 100, 1)}
        }

    def evaluate_anti_trap(self, sim: dict, home_name: str, away_name: str):
        """
        STRICT RULES:
        - Over 0.5 Goals is PERMANENTLY DELETED (Low odds trap).
        - High-yield Over 1.5 Goals (Odds: 1.20 - 1.35)
        - Double Chance (1X, X2, 12) (Odds: 1.20 - 1.45)
        - Draw No Bet (DNB) (Odds: 1.30 - 1.70)
        - Under 3.5 Goals (Safety under for defensive games)
        """
        candidates = []

        # 1. OVER 1.5 MATCH GOALS (Primary goal line)
        ov_15 = sim["Goals"]["Over_1_5"]
        if ov_15 >= 74.0:
            odds_15 = round((100.0 / ov_15) * 1.06, 2)
            candidates.append({
                "market": "Over 1.5 Goals", "sporty_market": "Over 1.5 Goals",
                "category": "Match Goals", "confidence": ov_15,
                "odds": odds_15, "market_type": "OVER_1_5",
                "weight": ov_15 * 1.25
            })

        # 2. DOUBLE CHANCE (1X, X2, 12)
        dc = sim["DoubleChance"]
        if dc["1X"] >= 72.0:
            odds_1x = round((100.0 / dc["1X"]) * 1.05, 2)
            candidates.append({
                "market": f"{home_name} or Draw (1X)", "sporty_market": "Double Chance 1X",
                "category": "Double Chance", "confidence": dc["1X"],
                "odds": odds_1x, "market_type": "DC_1X",
                "weight": dc["1X"] * 1.20
            })
        if dc["X2"] >= 72.0:
            odds_x2 = round((100.0 / dc["X2"]) * 1.05, 2)
            candidates.append({
                "market": f"{away_name} or Draw (X2)", "sporty_market": "Double Chance X2",
                "category": "Double Chance", "confidence": dc["X2"],
                "odds": odds_x2, "market_type": "DC_X2",
                "weight": dc["X2"] * 1.20
            })
        if dc["12"] >= 76.0:
            odds_12 = round((100.0 / dc["12"]) * 1.05, 2)
            candidates.append({
                "market": "Any Team to Win (12)", "sporty_market": "Double Chance 12",
                "category": "Double Chance", "confidence": dc["12"],
                "odds": odds_12, "market_type": "DC_12",
                "weight": dc["12"] * 1.15
            })

        # 3. DRAW NO BET (DNB)
        dnb = sim["DNB"]
        if dnb["Home"] >= 65.0:
            odds_dnb = round((100.0 / dnb["Home"]) * 1.06, 2)
            candidates.append({
                "market": f"{home_name} (Draw No Bet)", "sporty_market": f"{home_name} DNB",
                "category": "Draw No Bet", "confidence": dnb["Home"],
                "odds": odds_dnb, "market_type": "DNB_H",
                "weight": dnb["Home"] * 1.18
            })
        elif dnb["Away"] >= 65.0:
            odds_dnba = round((100.0 / dnb["Away"]) * 1.06, 2)
            candidates.append({
                "market": f"{away_name} (Draw No Bet)", "sporty_market": f"{away_name} DNB",
                "category": "Draw No Bet", "confidence": dnb["Away"],
                "odds": odds_dnba, "market_type": "DNB_A",
                "weight": dnb["Away"] * 1.18
            })

        # 4. UNDER 3.5 GOALS
        un_35 = sim["Goals"]["Under_3_5"]
        combined_xG = sim["adj_home_xG"] + sim["adj_away_xG"]
        if combined_xG <= 2.20 and un_35 >= 80.0:
            odds_35 = round((100.0 / un_35) * 1.05, 2)
            candidates.append({
                "market": "Under 3.5 Goals", "sporty_market": "Under 3.5 Goals",
                "category": "Match Goals", "confidence": un_35,
                "odds": odds_35, "market_type": "UNDER_3_5",
                "weight": un_35 * 0.95
            })

        # Sort by dynamic balance weight so real-odds markets lead
        candidates.sort(key=lambda x: x.get("weight", x["confidence"]), reverse=True)
        primary_rec = candidates[0] if candidates else {
            "market": "Over 1.5 Goals", "sporty_market": "Over 1.5 Goals",
            "category": "Match Goals", "confidence": 76.0, "odds": 1.28, "market_type": "OVER_1_5"
        }

        if primary_rec["confidence"] >= 88.0:
            primary_rec["badge"] = "pill-green"
            primary_rec["tier"] = "Banker Edge"
        elif primary_rec["confidence"] >= 78.0:
            primary_rec["badge"] = "pill-cyan"
            primary_rec["tier"] = "Value Edge"
        else:
            primary_rec["badge"] = "pill-gold"
            primary_rec["tier"] = "Quant Pick"

        return primary_rec, candidates

    @staticmethod
    def check_boom_status(prediction: dict, home_score: int, away_score: int, state: str) -> bool:
        if not prediction:
            return False
        total_goals = home_score + away_score
        m_type = prediction.get("market_type", "")

        if m_type == "OVER_1_5" and total_goals >= 2:
            return True
        if state == "post":
            if m_type == "UNDER_3_5" and total_goals <= 3:
                return True
            if m_type == "DC_1X" and home_score >= away_score:
                return True
            if m_type == "DC_X2" and away_score >= home_score:
                return True
            if m_type == "DC_12" and home_score != away_score:
                return True
            if m_type == "DNB_H" and home_score > away_score:
                return True
            if m_type == "DNB_A" and away_score > home_score:
                return True
        return False

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

quant_engine = AntiTrapEngine(home_advantage=1.15)

# =====================================================================
# 2. EXACT-TARGET ACCUMULATOR BUILDER
# =====================================================================
def build_exact_target_ticket(candidate_matches: list, target_odds: float):
    all_picks = []
    for m in candidate_matches:
        if m["is_finished"]:
            continue
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
                    "is_boom": m["is_boom"],
                    "league": m["league"],
                    "time": m["time"],
                    "market": c["market"],
                    "sporty_market": c["sporty_market"],
                    "category": c["category"],
                    "confidence": c["confidence"],
                    "odds": c["odds"],
                    "simulation": m["simulation"]
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
# 3. UI LIQUID GLASS STYLES
# =====================================================================
render_html("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Inter:wght@400;500;600&display=swap');

    .bg-canvas {
        position: fixed;
        top: 0; left: 0;
        width: 100vw; height: 100vh;
        z-index: -1; pointer-events: none;
        background-color: #060810;
        background-image: 
            radial-gradient(circle at 15% 10%, rgba(20, 110, 245, 0.20) 0%, transparent 45%),
            radial-gradient(circle at 85% 18%, rgba(82, 229, 231, 0.15) 0%, transparent 40%),
            radial-gradient(circle at 50% 90%, rgba(168, 85, 247, 0.14) 0%, transparent 50%);
        transform: translate3d(0, 0, 0);
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: #e2e8f0;
    }
    
    h1, h2, h3, h4 {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 800 !important;
        letter-spacing: -0.025em;
        color: #ffffff !important;
    }

    @keyframes pulse-boom {
        0% { transform: scale(0.96); box-shadow: 0 0 0 0 rgba(48, 209, 88, 0.85); }
        70% { transform: scale(1.05); box-shadow: 0 0 0 10px rgba(48, 209, 88, 0); }
        100% { transform: scale(0.96); box-shadow: 0 0 0 0 rgba(48, 209, 88, 0); }
    }
    .boom-badge {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: #ffffff !important;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.74rem;
        font-weight: 800;
        letter-spacing: 0.05em;
        padding: 3px 10px;
        border-radius: 9999px;
        box-shadow: 0 0 14px rgba(48, 209, 88, 0.6);
        border: 1px solid #34d399;
        animation: pulse-boom 1.8s infinite;
    }

    .score-capsule {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background: rgba(255, 255, 255, 0.07);
        border: 1px solid rgba(255, 255, 255, 0.14);
        border-radius: 999px;
        padding: 3px 14px;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1.05rem;
        font-weight: 800;
        color: #ffffff;
        white-space: nowrap !important;
        letter-spacing: 0.04em;
        font-variant-numeric: tabular-nums;
        box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.15), 0 2px 8px rgba(0, 0, 0, 0.35);
        flex-shrink: 0;
    }

    .vs-separator {
        font-weight: 700;
        color: rgba(255, 255, 255, 0.3);
        font-size: 0.8rem;
        letter-spacing: 0.05em;
        white-space: nowrap;
    }

    .match-team-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: 12px 0;
        gap: 8px;
    }
    .team-cell-left {
        display: flex;
        align-items: center;
        gap: 8px;
        flex: 1;
        min-width: 0;
    }
    .team-cell-right {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 8px;
        flex: 1;
        min-width: 0;
        text-align: right;
    }
    .team-name-text {
        font-size: 0.92rem;
        font-weight: 700;
        color: #ffffff;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .sportybet-code-container {
        background: #0d121d;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 14px 18px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 12px;
        margin-top: 16px;
        margin-bottom: 8px;
    }
    .sporty-code-chip {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(0, 230, 118, 0.12);
        border: 1px solid #00e676;
        padding: 8px 18px;
        border-radius: 8px;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.95rem;
        color: #ffffff;
    }
    .sporty-code-bold {
        font-weight: 800;
        color: #00e676;
        letter-spacing: 0.12em;
        font-size: 1.25rem;
    }

    .card-grid-container {
        display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
        gap: 16px; margin-top: 12px; margin-bottom: 24px;
    }
    .liquid-glass-card {
        content-visibility: auto; contain-intrinsic-size: 0 160px;
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.065) 0%, rgba(255, 255, 255, 0.02) 100%);
        border: 1px solid rgba(255, 255, 255, 0.09);
        border-top: 1.5px solid rgba(255, 255, 255, 0.28);
        border-radius: 18px; padding: 18px 20px;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.35);
        transition: transform 0.18s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.18s ease;
    }
    .liquid-glass-card:hover {
        transform: translate3d(0, -3px, 0); border-color: rgba(82, 229, 231, 0.35);
    }

    .glass-pill {
        display: inline-flex; align-items: center;
        padding: 4px 12px; border-radius: 9999px;
        font-size: 0.72rem; font-weight: 700;
        letter-spacing: 0.04em; text-transform: uppercase;
        border-top: 1px solid rgba(255, 255, 255, 0.4);
    }
    .pill-cyan { color: #52e5e7; background: rgba(82, 229, 231, 0.12); border: 1px solid rgba(82, 229, 231, 0.4); }
    .pill-green { color: #30d158; background: rgba(48, 209, 88, 0.12); border: 1px solid rgba(48, 209, 88, 0.4); }
    .pill-gold { color: #ffd60a; background: rgba(255, 214, 10, 0.12); border: 1px solid rgba(255, 214, 10, 0.4); }

    .team-logo { width: 30px; height: 30px; object-fit: contain; flex-shrink: 0; }
    .confidence-metric { font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1.85rem; font-weight: 800; color: #ffffff; }
    .hero-gradient-text {
        font-size: 2.2rem; letter-spacing: -0.035em;
        background: linear-gradient(135deg, #ffffff 20%, #52e5e7 60%, #c084fc 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .prob-chip {
        background: rgba(255, 255, 255, 0.035);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 8px; padding: 5px 3px;
        font-size: 0.74rem; text-align: center;
    }
</style>
<div class="bg-canvas"></div>
""")

# =====================================================================
# 4. ROBUST DATA FETCHING PIPELINE
# =====================================================================
LEAGUES_CONFIG = [
    {"name": "Premier League (ENG)", "code": "eng.1"},
    {"name": "La Liga (ESP)", "code": "esp.1"},
    {"name": "Serie A (ITA)", "code": "ita.1"},
    {"name": "Bundesliga (GER)", "code": "ger.1"},
    {"name": "Ligue 1 (FRA)", "code": "fra.1"},
    {"name": "UEFA Champions League", "code": "uefa.champions"},
    {"name": "UEFA Europa League", "code": "uefa.europa"},
    {"name": "UEFA Conference League", "code": "uefa.europa.conf"},
    {"name": "Eredivisie (NED)", "code": "ned.1"},
    {"name": "Liga Portugal (POR)", "code": "por.1"},
    {"name": "Belgian Pro League (BEL)", "code": "bel.1"},
    {"name": "Süper Lig (TUR)", "code": "tur.1"},
    {"name": "Austrian Bundesliga (AUT)", "code": "aut.1"},
    {"name": "Championship (ENG)", "code": "eng.2"},
    {"name": "2. Bundesliga (GER)", "code": "ger.2"},
    {"name": "Serie B (ITA)", "code": "ita.2"},
    {"name": "Major League Soccer (USA)", "code": "usa.1"},
    {"name": "Liga MX (MEX)", "code": "mex.1"},
    {"name": "Saudi Pro League (KSA)", "code": "sau.1"},
    {"name": "J1 League (JPN)", "code": "jpn.1"},
    {"name": "Norwegian Eliteserien (NOR)", "code": "nor.1"}
]

def parse_espn_event(event, league_name, league_code):
    try:
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

        tempo = LEAGUE_TEMPO.get(league_code, 2.70)
        h_power = 1.30 if any(t in h_name for t in ["City", "Real", "Bayern", "Paris", "Arsenal", "Barcelona", "Inter"]) else 1.10
        a_power = 1.20 if any(t in a_name for t in ["City", "Real", "Bayern", "Paris", "Arsenal", "Barcelona", "Inter"]) else 0.95
        raw_h_xG = (tempo / 2.0) * h_power
        raw_a_xG = (tempo / 2.0) * a_power

        sim = quant_engine.simulate_match(raw_h_xG, raw_a_xG, live_h=0, live_a=0, mins_left=90.0)
        rec, candidates = quant_engine.evaluate_anti_trap(sim, h_name, a_name)
        is_boom = quant_engine.check_boom_status(rec, home_score, away_score, state)

        default_logo = "https://a.espncdn.com/combiner/i?img=/i/teamlogos/default-team-logo-500.png"
        return {
            "match": f"{h_name} vs {a_name}",
            "league": league_name,
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
            "is_boom": is_boom,
            "recommendation": rec,
            "candidates": candidates,
            "simulation": sim
        }
    except Exception:
        return None

def fetch_single_league(args):
    league, date_str = args
    session = get_http_session()
    matches = []
    
    urls = [
        f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league['code']}/scoreboard?dates={date_str}",
        f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league['code']}/scoreboard"
    ]
    for url in urls:
        try:
            res = session.get(url, timeout=4.5)
            if res.status_code == 200:
                events = res.json().get("events", [])
                for ev in events:
                    parsed = parse_espn_event(ev, league["name"], league["code"])
                    if parsed:
                        matches.append(parsed)
                if matches:
                    break
        except Exception:
            continue
    return matches

@st.cache_data(ttl=90, show_spinner=False)
def fetch_all_fixtures():
    session = get_http_session()
    today_str = date.today().strftime("%Y%m%d")
    tomorrow_str = (date.today() + timedelta(days=1)).strftime("%Y%m%d")
    
    tasks = [(l, today_str) for l in LEAGUES_CONFIG]
    with ThreadPoolExecutor(max_workers=14) as executor:
        results = executor.map(fetch_single_league, tasks)
        
    flat = []
    seen_matches = set()
    for match_list in results:
        for m in match_list:
            if m["match"] not in seen_matches:
                seen_matches.add(m["match"])
                flat.append(m)

    if len(flat) < 5:
        fallback_urls = [
            f"https://site.api.espn.com/apis/site/v2/sports/soccer/scoreboards?dates={today_str}",
            f"https://site.api.espn.com/apis/site/v2/sports/soccer/scoreboards?dates={tomorrow_str}",
            "https://site.api.espn.com/apis/site/v2/sports/soccer/scoreboards"
        ]
        for f_url in fallback_urls:
            try:
                res = session.get(f_url, timeout=5.0)
                if res.status_code == 200:
                    events = res.json().get("events", [])
                    for ev in events:
                        c_name = ev.get("competitions", [{}])[0].get("league", {}).get("name", "Soccer League")
                        parsed = parse_espn_event(ev, c_name, "general")
                        if parsed and parsed["match"] not in seen_matches:
                            seen_matches.add(parsed["match"])
                            flat.append(parsed)
            except Exception:
                continue

    return flat

with st.spinner("Streaming active fixtures & filtering out 0.5 low-value traps..."):
    all_today_games = fetch_all_fixtures()
    upcoming_games = [m for m in all_today_games if not m["is_finished"]]
    live_fixtures = [m for m in all_today_games if m["is_live"]]
    boom_fixtures = [m for m in all_today_games if m["is_boom"]]

# =====================================================================
# 5. APP HEADER & CONTROLS
# =====================================================================
live_count_pill = f'<span class="live-pill"><span class="live-dot"></span>{len(live_fixtures)} LIVE</span>' if live_fixtures else '<span class="glass-pill pill-cyan">⚡ 0 In-Play</span>'
boom_count_pill = f'<span class="boom-badge">💥 {len(boom_fixtures)} BOOMS RECORDED</span>' if boom_fixtures else '<span class="glass-pill pill-green">💥 Verifying Results</span>'

render_html(f"""
<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px; flex-wrap: wrap; gap: 12px;">
    <div style="display: flex; align-items: center; gap: 16px;">
        <div class="liquid-icon icon-cyan" style="width: 52px; height: 52px; border-radius: 16px; font-size: 1.6rem;">
            ⚡
        </div>
        <div>
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 2px;">
                <span class="glass-pill pill-cyan">Anti-Trap Active • Over 0.5 Permanently Purged</span>
                {live_count_pill}
                {boom_count_pill}
            </div>
            <h1 class="hero-gradient-text" style="margin: 0; line-height: 1.1;">Apex Quantitative Analytics</h1>
        </div>
    </div>
</div>
""")

tab_feed, tab_master_ticket, tab_sure89, tab_booms, tab_surebets, tab_kelly, tab_analyzer = st.tabs([
    f"⚡ Match Board ({len(all_today_games)})", 
    "🔥 Master Ticket (All-in-One)",
    f"💎 Sure Fixtures ≥89% ({len([m for m in (upcoming_games if upcoming_games else all_today_games) if m['recommendation']['confidence'] >= 89.0])})",
    f"💥 Boomed Today ({len(boom_fixtures)})",
    "🎯 Safe Banker Hub", 
    "💰 Kelly Bankroll Calculator", 
    "🔬 7x7 Simulation Matrix"
])

def render_quant_grid(match_list):
    cards_html = []
    for m in match_list:
        sim = m["simulation"]
        rec = m["recommendation"]

        if m["is_boom"]:
            status_badge = '<span class="boom-badge">💥 BOOM VERIFIED</span>'
        elif m["is_live"]:
            status_badge = f'<span class="live-pill"><span class="live-dot"></span>{m["clock"]}</span>'
        elif m["is_finished"]:
            status_badge = '<span class="glass-pill pill-gold">FULL TIME</span>'
        else:
            status_badge = f'<span class="glass-pill {rec["badge"]}">{rec["category"]}</span>'

        if m["is_live"] or m["is_finished"]:
            middle_display = f'<span class="score-capsule">{m["home_score"]} – {m["away_score"]}</span>'
        else:
            middle_display = '<span class="vs-separator">VS</span>'

        cards_html.append(f"""
<div class="liquid-glass-card">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        {status_badge}
        <span style="font-size: 0.76rem; color: rgba(255,255,255,0.4);">{m['league']} • {m['time']}</span>
    </div>
    
    <div class="match-team-row">
        <div class="team-cell-left">
            <img src="{m['home_logo']}" class="team-logo" loading="lazy" decoding="async"/>
            <span class="team-name-text">{m['home']}</span>
        </div>
        <div>
            {middle_display}
        </div>
        <div class="team-cell-right">
            <span class="team-name-text">{m['away']}</span>
            <img src="{m['away_logo']}" class="team-logo" loading="lazy" decoding="async"/>
        </div>
    </div>

    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin: 10px 0;">
        <div class="prob-chip">
            <span style="color: rgba(255,255,255,0.4);">Home 1X</span><br>
            <b style="color: #fff;">{sim['DoubleChance']['1X']}%</b>
        </div>
        <div class="prob-chip">
            <span style="color: rgba(255,255,255,0.4);">Away X2</span><br>
            <b style="color: #fff;">{sim['DoubleChance']['X2']}%</b>
        </div>
        <div class="prob-chip">
            <span style="color: rgba(255,255,255,0.4);">Over 1.5</span><br>
            <b style="color: #52e5e7;">{sim['Goals']['Over_1_5']}%</b>
        </div>
        <div class="prob-chip">
            <span style="color: rgba(255,255,255,0.4);">Under 3.5</span><br>
            <b style="color: #30d158;">{sim['Goals']['Under_3_5']}%</b>
        </div>
    </div>
    <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.06); margin: 10px 0;">
    <div style="display: flex; justify-content: space-between; align-items: flex-end;">
        <div>
            <div style="font-size: 0.68rem; text-transform: uppercase; color: rgba(255,255,255,0.4);">{rec['category']} (Odds: {rec['odds']})</div>
            <div style="font-size: 0.94rem; font-weight: 700; color: #ffffff;">{rec['market']}</div>
        </div>
        <div style="text-align: right;">
            <div style="font-size: 0.68rem; text-transform: uppercase; color: rgba(255,255,255,0.4);">Certainty</div>
            <div class="confidence-metric" style="color: {'#30d158' if rec['confidence'] >= 89.0 else '#ffffff'};">{rec['confidence']}%</div>
        </div>
    </div>
</div>
""")
    render_html(f'<div class="card-grid-container">{"".join(cards_html)}</div>')

# =====================================================================
# TAB 1: DAILY MATCH BOARD
# =====================================================================
with tab_feed:
    show_upcoming_only = st.checkbox("Show only upcoming & live games (hide full-time results)", value=False)
    board_display_list = upcoming_games if show_upcoming_only else all_today_games
    sorted_board = sorted(board_display_list, key=lambda x: x["recommendation"]["confidence"], reverse=True)
    
    render_html('<span class="glass-pill pill-cyan" style="font-size: 0.85rem; padding: 6px 14px; margin-bottom: 8px;">⚡ TODAY\'S OPTIMAL MATCH BOARD (OVER 1.5 • DOUBLE CHANCE • DNB)</span>')
    if sorted_board:
        render_quant_grid(sorted_board)
    else:
        st.info("No fixtures available right now.")

# =====================================================================
# TAB 2: MASTER TICKET (ALL-IN-ONE SINGLE SPORTYBET CODE)
# =====================================================================
with tab_master_ticket:
    render_html("""
    <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 14px;">
        <div class="liquid-icon icon-cyan" style="font-size: 1.8rem;">
            🔥
        </div>
        <div>
            <span class="glass-pill pill-green">Single Consolidated Master Slip</span>
            <h2 style="margin: 2px 0 0 0; font-size: 1.6rem; color: #ffffff !important;">Today's Master Ticket (Stake All in One)</h2>
        </div>
    </div>
    <p style="font-size: 0.9rem; color: rgba(255, 255, 255, 0.65); margin-bottom: 14px;">
        No need to book 50 separate games. All top predictions are bundled into <b>one single consolidated betslip with one SportyBet Nigeria code</b>.
    </p>
    """)

    pool_for_master = upcoming_games if upcoming_games else all_today_games
    master_slip, master_odds = build_exact_target_ticket(pool_for_master, target_odds=8.00)
    master_code = st.session_state.sportybet_ng_codes.get("master_ticket", "VFUBGJ")
    master_avg_conf = round(sum(s["confidence"] for s in master_slip) / max(1, len(master_slip)), 2) if master_slip else 0.0

    render_html(f"""
    <div style="background: #0a0f18; border: 1.5px solid #00e676; border-radius: 16px; padding: 22px; margin-bottom: 20px; box-shadow: 0 0 25px rgba(0, 230, 118, 0.2);">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255, 255, 255, 0.1); padding-bottom: 14px; margin-bottom: 8px;">
            <div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="display: inline-block; width: 12px; height: 12px; background: #00e676; border-radius: 50%; box-shadow: 0 0 12px #00e676;"></span>
                    <h3 style="margin: 0; font-size: 1.35rem; color: #ffffff;">ALL-IN-ONE CONSOLIDATED MASTER SLIP</h3>
                </div>
                <div style="font-size: 0.85rem; color: rgba(255,255,255,0.6); margin-top: 4px;">
                    {len(master_slip)} combined picks &nbsp;•&nbsp; Avg {master_avg_conf}% certainty &nbsp;•&nbsp; <span style="color: #00e676; font-weight: 700;">Over 0.5 Excluded</span>
                </div>
            </div>
            <div style="font-size: 2.2rem; font-weight: 800; color: #00e676; letter-spacing: -0.02em;">
                {master_odds}x
            </div>
        </div>

        <div class="sportybet-code-container">
            <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                <span style="font-size: 0.82rem; font-weight: 800; color: rgba(255,255,255,0.5); text-transform: uppercase;">SPORTYBET CODE:</span>
                <div class="sporty-code-chip">
                    <span>Sportybet ng:</span>
                    <span class="sporty-code-bold">{master_code}</span>
                </div>
            </div>
            <div>
                <a href="https://www.sportybet.com/ng/" target="_blank" style="background: #e91e63; color: #fff; text-decoration: none; padding: 9px 22px; border-radius: 9999px; font-size: 0.85rem; font-weight: 800; box-shadow: 0 4px 14px rgba(233, 30, 99, 0.4);">
                    ⚡ Load on SportyBet Nigeria
                </a>
            </div>
        </div>
    </div>
    """)

    render_html('<span class="glass-pill pill-cyan" style="font-size: 0.85rem; padding: 6px 14px; margin-bottom: 8px;">📋 Master Ticket Matches</span>')
    if master_slip:
        formatted_master = [
            {
                "match": s["match"], "league": s["league"], "home": s["home"], "home_logo": s["home_logo"],
                "away": s["away"], "away_logo": s["away_logo"], "time": s["time"], "clock": s["clock"],
                "is_live": s["is_live"], "is_finished": s["is_finished"], "home_score": s["home_score"],
                "away_score": s["away_score"], "is_boom": s["is_boom"],
                "recommendation": {"market": s["market"], "category": s["category"], "confidence": s["confidence"], "odds": s["odds"], "badge": "pill-green"},
                "simulation": s["simulation"]
            }
            for s in master_slip
        ]
        render_quant_grid(formatted_master)

        master_slip_text = f"🔥 APEX MASTER TICKET ({master_odds}x):\n" + "\n".join([
            f"{i+1}. {s['home']} vs {s['away']} -> {s['sporty_market']} (@{s['odds']})"
            for i, s in enumerate(master_slip)
        ])
        with st.expander("📋 Copy Betslip Text for Master Ticket"):
            st.text_area("Selections:", value=master_slip_text, height=130)

        with st.expander("📝 Update Live SportyBet Nigeria Code for Master Ticket"):
            new_code = st.text_input("Enter new code:", value=master_code, key="sync_master_code")
            if new_code != master_code and new_code.strip():
                st.session_state.sportybet_ng_codes["master_ticket"] = new_code.strip().upper()
                st.success("Updated Master Code!")
                st.rerun()

# =====================================================================
# TAB 3: SURE FIXTURES ≥ 89% (REAL-ODDS MARKETS ONLY)
# =====================================================================
with tab_sure89:
    sure_pool = upcoming_games if upcoming_games else all_today_games
    sure_games_89 = [m for m in sure_pool if m["recommendation"]["confidence"] >= 89.0]
    sure_games_89.sort(key=lambda x: x["recommendation"]["confidence"], reverse=True)

    render_html("""
    <div style="margin-bottom: 16px;">
        <h2 style="margin: 0 0 4px 0; font-size: 1.5rem;">💎 High-Certainty Vault: 89% & Above</h2>
        <p style="font-size: 0.88rem; color: rgba(255,255,255,0.6); margin: 0;">
            Strictly limited to Over 1.5, Double Chance, and DNB. Over 0.5 has been purged.
        </p>
    </div>
    """)
    if sure_games_89:
        render_quant_grid(sure_games_89)
    else:
        st.info("No fixtures meeting the ≥ 89.0% threshold right now.")

# =====================================================================
# TAB 4: BOOMED TODAY (ORGANIZED RESULTS SHOWCASE)
# =====================================================================
with tab_booms:
    render_html("""
    <div style="margin-bottom: 16px;">
        <span class="boom-badge">💥 Verified Results Tracker</span>
        <h2 style="margin: 6px 0 4px 0; font-size: 1.5rem;">Winning Hits & Boomed Matches</h2>
        <p style="font-size: 0.88rem; color: rgba(255,255,255,0.6); margin: 0;">
            Organized showcase of all predictions that have successfully hit and won.
        </p>
    </div>
    """)
    if boom_fixtures:
        render_quant_grid(boom_fixtures)
    else:
        st.info("Matches are in progress. As soon as goals land, winning fixtures will be showcased here!")

# =====================================================================
# TAB 5: SAFE BANKER HUB (EXACT MULTI-ODDS ACCUMULATORS)
# =====================================================================
with tab_surebets:
    render_html("""
    <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 14px;">
        <div class="liquid-icon icon-green">
            🎯
        </div>
        <div>
            <span class="glass-pill pill-green">Exact Odds Knapsack Engine</span>
            <h2 style="margin: 2px 0 0 0; font-size: 1.5rem; color: #ffffff !important;">Mathematical Banker Accumulator Hub</h2>
        </div>
    </div>
    <p style="font-size: 0.88rem; color: rgba(255, 255, 255, 0.6); margin-bottom: 14px;">
        Multi-game accumulator slips built strictly without Over 0.5 traps.
    </p>
    """)

    banker_mode = st.radio(
        "Select Banker Strategy",
        ["🔥 Safe 3 Odds", "⚡ Safe 5 Odds", "💎 Safe 10 Odds", "👑 Safe 20 Odds"],
        horizontal=True,
        label_visibility="collapsed"
    )

    feed_pool = upcoming_games if upcoming_games else all_today_games

    if "3" in banker_mode:
        selected_slip, achieved_odds = build_exact_target_ticket(feed_pool, target_odds=3.00)
        slip_label = "Safe 3 Odds Slip"
        key_name = "3_odds"
    elif "5" in banker_mode:
        selected_slip, achieved_odds = build_exact_target_ticket(feed_pool, target_odds=5.00)
        slip_label = "Safe 5 Odds Slip"
        key_name = "5_odds"
    elif "10" in banker_mode:
        selected_slip, achieved_odds = build_exact_target_ticket(feed_pool, target_odds=10.00)
        slip_label = "Safe 10 Odds Slip"
        key_name = "10_odds"
    else:
        selected_slip, achieved_odds = build_exact_target_ticket(feed_pool, target_odds=20.00)
        slip_label = "Safe 20 Odds Slip"
        key_name = "20_odds"

    active_code = st.session_state.sportybet_ng_codes.get(key_name, "VFUBGJ")
    avg_conf = round(sum(s["confidence"] for s in selected_slip) / max(1, len(selected_slip)), 2) if selected_slip else 0.0

    render_html(f"""
    <div style="background: #0a0f18; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 20px; margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 14px; margin-bottom: 6px;">
            <div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="display: inline-block; width: 10px; height: 10px; background: #00e676; border-radius: 50%; box-shadow: 0 0 10px #00e676;"></span>
                    <h3 style="margin: 0; font-size: 1.25rem; color: #ffffff;">{slip_label}</h3>
                </div>
                <div style="font-size: 0.82rem; color: rgba(255,255,255,0.5); margin-top: 4px;">
                    {len(selected_slip)} combined picks &nbsp;•&nbsp; Avg {avg_conf}% confidence &nbsp;•&nbsp; <span style="color: #ff9100;">🛡️ Target Match Locked</span>
                </div>
            </div>
            <div style="font-size: 1.7rem; font-weight: 800; color: #00e676; letter-spacing: -0.02em;">
                {achieved_odds}x
            </div>
        </div>

        <div class="sportybet-code-container">
            <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                <span style="font-size: 0.78rem; font-weight: 800; color: rgba(255,255,255,0.45); text-transform: uppercase;">CODE:</span>
                <div class="sporty-code-chip">
                    <span>Sportybet ng:</span>
                    <span class="sporty-code-bold">{active_code}</span>
                </div>
            </div>
            <div>
                <a href="https://www.sportybet.com/ng/" target="_blank" style="background: #e91e63; color: #fff; text-decoration: none; padding: 8px 20px; border-radius: 9999px; font-size: 0.85rem; font-weight: 800; box-shadow: 0 4px 12px rgba(233, 30, 99, 0.4);">
                    ⚡ Load on SportyBet Nigeria
                </a>
            </div>
        </div>
    </div>
    """)

    render_html('<span class="glass-pill pill-cyan" style="font-size: 0.85rem; padding: 6px 14px; margin-bottom: 8px;">📋 Slip Match Details</span>')
    if selected_slip:
        formatted_slip_games = [
            {
                "match": s["match"], "league": s["league"], "home": s["home"], "home_logo": s["home_logo"],
                "away": s["away"], "away_logo": s["away_logo"], "time": s["time"], "clock": s["clock"],
                "is_live": s["is_live"], "is_finished": s["is_finished"], "home_score": s["home_score"],
                "away_score": s["away_score"], "is_boom": s["is_boom"],
                "recommendation": {"market": s["market"], "category": s["category"], "confidence": s["confidence"], "odds": s["odds"], "badge": "pill-green"},
                "simulation": s["simulation"]
            }
            for s in selected_slip
        ]
        render_quant_grid(formatted_slip_games)

    with st.expander(f"📝 Update SportyBet Nigeria Code for {slip_label}"):
        new_code_in = st.text_input("Enter Official SportyBet Code:", value=active_code, key=f"sync_{key_name}")
        if new_code_in != active_code and new_code_in.strip():
            st.session_state.sportybet_ng_codes[key_name] = new_code_in.strip().upper()
            st.success("SportyBet code updated successfully!")
            st.rerun()

# =====================================================================
# TAB 6: FRACTIONAL KELLY STAKING CALCULATOR
# =====================================================================
with tab_kelly:
    render_html("""
    <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 14px;">
        <div class="liquid-icon icon-cyan">
            💰
        </div>
        <div>
            <span class="glass-pill pill-cyan">Risk Management</span>
            <h2 style="margin: 2px 0 0 0; font-size: 1.5rem; color: #ffffff !important;">Fractional Kelly Staking</h2>
        </div>
    </div>
    """)

    col_k1, col_k2 = st.columns(2)
    with col_k1:
        st.markdown('<div class="liquid-glass-card">', unsafe_allow_html=True)
        user_bankroll = st.number_input("Total Bankroll ($)", min_value=10.0, max_value=1000000.0, value=1000.0, step=50.0)
        bookie_odds = st.number_input("Bookmaker Decimal Odds", min_value=1.01, max_value=50.0, value=1.85, step=0.05)
        model_prob_in = st.slider("Model Estimated Probability (%)", min_value=10.0, max_value=99.0, value=65.0, step=0.5)
        kelly_fraction = st.select_slider(
            "Kelly Profile",
            options=[0.10, 0.25, 0.50, 1.0],
            value=0.25,
            format_func=lambda x: f"{int(x*100)}% ({'Conservative' if x==0.25 else 'Micro' if x==0.10 else 'Aggressive' if x==0.5 else 'Full'})"
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with col_k2:
        recommended_stake, calculated_edge = AntiTrapEngine.calculate_kelly(
            user_bankroll, model_prob_in, bookie_odds, kelly_fraction
        )
        stake_pct = round((recommended_stake / user_bankroll) * 100, 2)
        edge_badge = 'pill-green' if calculated_edge > 0 else 'pill-gold'
        edge_text = 'Positive Expectation (+EV)' if calculated_edge > 0 else 'Negative Expectation (-EV)'
        stake_color = '#30d158' if calculated_edge > 0 else '#ff453a'
        advice = '✅ <b>Edge Detected:</b> Modeled edge exceeds bookmaker implied probability.' if calculated_edge > 0 else '⚠️ <b>No Bet Advised:</b> Edge does not cover the bookmaker margin.'

        render_html(f"""
<div class="liquid-glass-card">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
<span class="glass-pill {edge_badge}">{edge_text}</span>
<span style="font-size: 0.88rem; color: #52e5e7; font-weight: 700;">Edge: {calculated_edge}%</span>
</div>
<h3 style="margin: 0 0 8px 0;">Target Allocation</h3>
<div style="margin: 14px 0;">
<div style="font-size: 0.74rem; text-transform: uppercase; color: rgba(255,255,255,0.4);">Recommended Stake</div>
<div style="font-size: 2.2rem; font-weight: 800; color: {stake_color};">
${recommended_stake} <span style="font-size: 1rem; color: rgba(255,255,255,0.45);">({stake_pct}%)</span>
</div>
</div>
<div style="padding: 10px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; font-size: 0.8rem; line-height: 1.4;">
{advice}
</div>
</div>
""")

# =====================================================================
# TAB 7: 7X7 POISSON SIMULATION MATRIX
# =====================================================================
with tab_analyzer:
    render_html("""
    <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 14px;">
        <div class="liquid-icon icon-violet">
            🔬
        </div>
        <div>
            <span class="glass-pill pill-violet">Matrix Engine</span>
            <h2 style="margin: 2px 0 0 0; font-size: 1.5rem; color: #ffffff !important;">7x7 Joint Scoreline Simulation</h2>
        </div>
    </div>
    """)

    match_select_opts = [f"{m['home']} vs {m['away']} ({m['league']})" for m in all_today_games] if all_today_games else ["No Fixtures Available"]
    selected_m_str = st.selectbox("Select Target Fixture", match_select_opts)

    target_match = next((m for m in all_today_games if f"{m['home']} vs {m['away']} ({m['league']})" == selected_m_str), None)

    if target_match:
        sim_data = target_match["simulation"]
        col_m1, col_m2 = st.columns(2)

        with col_m1:
            render_html(f"""
<div class="liquid-glass-card">
<span class="glass-pill pill-cyan">Poisson Parameters</span>
<h4 style="margin: 10px 0 14px 0;">Adjusted Expected Goals (xG)</h4>
<div style="margin-bottom: 12px;">
<div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 4px;">
<span>{target_match['home']} (Home Adv: 1.15x)</span>
<span style="font-weight: 700; color: #52e5e7;">{sim_data['adj_home_xG']} xG</span>
</div>
<div style="width: 100%; height: 6px; background: rgba(255,255,255,0.08); border-radius: 999px;">
<div style="width: {min(100, int(sim_data['adj_home_xG'] * 35))}%; height: 100%; background: #52e5e7; border-radius: 999px;"></div>
</div>
</div>
<div style="margin-bottom: 12px;">
<div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 4px;">
<span>{target_match['away']}</span>
<span style="font-weight: 700; color: #c084fc;">{sim_data['adj_away_xG']} xG</span>
</div>
<div style="width: 100%; height: 6px; background: rgba(255,255,255,0.08); border-radius: 999px;">
<div style="width: {min(100, int(sim_data['adj_away_xG'] * 35))}%; height: 100%; background: #c084fc; border-radius: 999px;"></div>
</div>
</div>
<hr style="border:0; border-top: 1px solid rgba(255,255,255,0.06); margin: 12px 0;">
<div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px;">
<div class="prob-chip">
<span style="color: rgba(255,255,255,0.4);">Double Chance 1X</span><br>
<b style="color: #30d158; font-size: 0.95rem;">{sim_data['DoubleChance']['1X']}%</b>
</div>
<div class="prob-chip">
<span style="color: rgba(255,255,255,0.4);">Over 1.5 Goals</span><br>
<b style="color: #52e5e7; font-size: 0.95rem;">{sim_data['Goals']['Over_1_5']}%</b>
</div>
</div>
</div>
""")

        with col_m2:
            st.info("Anti-trap simulation active.")
    else:
        st.info("Select a fixture to inspect.")
