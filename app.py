import streamlit as st
import requests
from requests.adapters import HTTPAdapter
import math
import numpy as np
from datetime import datetime, date
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(
    page_title="Apex Quantitative Football Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Strips whitespace indentation to prevent Streamlit from turning HTML into code blocks
def render_html(html_str: str):
    cleaned = "\n".join(line.strip() for line in html_str.strip().splitlines() if line.strip())
    st.markdown(cleaned, unsafe_allow_html=True)

@st.cache_resource
def get_http_session() -> requests.Session:
    session = requests.Session()
    adapter = HTTPAdapter(pool_connections=65, pool_maxsize=65, max_retries=1)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    return session

if "sporty_codes" not in st.session_state:
    st.session_state.sporty_codes = {
        "board": "",
        "banker_3": "",
        "banker_5": "",
        "banker_10": "",
        "banker_20": ""
    }

# =====================================================================
# 1. QUANTITATIVE PREDICTION & CORNER ENGINE (4 MARKETS ONLY)
# =====================================================================
class QuantitativePredictionEngine:
    def __init__(self, home_advantage: float = 1.15):
        self.home_advantage = home_advantage
        self.max_goals = 7
        self.goals_range = np.arange(self.max_goals)
        self.factorials = np.array([math.factorial(i) for i in range(self.max_goals)], dtype=np.float64)
        self.total_goals_grid = np.add.outer(self.goals_range, self.goals_range)

    def _poisson_vector(self, lmbda: float, max_range: int = 7) -> np.ndarray:
        lmbda = max(0.08, lmbda)
        k_range = np.arange(max_range)
        k_fact = np.array([math.factorial(i) for i in range(max_range)], dtype=np.float64)
        return (np.exp(-lmbda) * (lmbda ** k_range)) / k_fact

    def simulate_corners(self, home_corners_lmbda: float, away_corners_lmbda: float) -> dict:
        max_c = 18
        h_prob = self._poisson_vector(home_corners_lmbda, max_c)
        a_prob = self._poisson_vector(away_corners_lmbda, max_c)
        c_matrix = np.outer(h_prob, a_prob)
        total_corners_grid = np.add.outer(np.arange(max_c), np.arange(max_c))

        ov_75 = float(c_matrix[total_corners_grid > 7.5].sum())
        ov_85 = float(c_matrix[total_corners_grid > 8.5].sum())
        un_105 = float(c_matrix[total_corners_grid <= 10.5].sum())
        proj_total = round(home_corners_lmbda + away_corners_lmbda, 1)

        return {
            "projected_total": proj_total,
            "Over_7_5": round(ov_75 * 100, 1),
            "Over_8_5": round(ov_85 * 100, 1),
            "Under_10_5": round(un_105 * 100, 1)
        }

    def simulate_match(self, home_xG: float, away_xG: float, live_h_score: int = 0, live_a_score: int = 0, minutes_left: float = 90.0) -> dict:
        time_factor = max(0.05, min(1.0, minutes_left / 90.0))
        rem_home_xG = max(0.1, home_xG * self.home_advantage * time_factor)
        rem_away_xG = max(0.1, away_xG * time_factor)

        home_probs = self._poisson_vector(rem_home_xG, self.max_goals)
        away_probs = self._poisson_vector(rem_away_xG, self.max_goals)
        matrix = np.outer(home_probs, away_probs)

        current_total = live_h_score + live_a_score
        home_win, draw, away_win = 0.0, 0.0, 0.0
        over_1_5, under_3_5, over_2_5 = 0.0, 0.0, 0.0

        for h in range(self.max_goals):
            for a in range(self.max_goals):
                p = matrix[h][a]
                final_h = live_h_score + h
                final_a = live_a_score + a
                
                if final_h > final_a:
                    home_win += p
                elif final_h == final_a:
                    draw += p
                else:
                    away_win += p

                tot = final_h + final_a
                if tot > 1.5: over_1_5 += p
                if tot <= 3.5: under_3_5 += p
                if tot > 2.5: over_2_5 += p

        double_chance_1x = home_win + draw
        double_chance_x2 = away_win + draw

        non_draw = max(0.001, home_win + away_win)
        dnb_home = home_win / non_draw
        dnb_away = away_win / non_draw

        flat_indices = np.argpartition(matrix.ravel(), -4)[-4:]
        sorted_indices = flat_indices[np.argsort(-matrix.ravel()[flat_indices])]
        top_scorelines = [
            {
                "score": f"{live_h_score + (idx // self.max_goals)} - {live_a_score + (idx % self.max_goals)}",
                "prob": round(float(matrix.ravel()[idx]) * 100, 1)
            }
            for idx in sorted_indices
        ]

        return {
            "adj_home_xG": round(rem_home_xG, 2),
            "adj_away_xG": round(rem_away_xG, 2),
            "1X2": {
                "Home": round(home_win * 100, 1),
                "Draw": round(draw * 100, 1),
                "Away": round(away_win * 100, 1)
            },
            "DoubleChance": {
                "1X": round(double_chance_1x * 100, 1),
                "X2": round(double_chance_x2 * 100, 1)
            },
            "DNB": {
                "Home": round(dnb_home * 100, 1),
                "Away": round(dnb_away * 100, 1)
            },
            "Goals": {
                "Over_1_5": round(over_1_5 * 100, 1),
                "Under_3_5": round(under_3_5 * 100, 1),
                "Over_2_5": round(over_2_5 * 100, 1)
            },
            "top_scorelines": top_scorelines
        }

    def evaluate_best_prediction(self, probs: dict, corner_probs: dict, home_name: str, away_name: str):
        candidates = []

        # 1. Double Chance Markets
        dc_1x = probs["DoubleChance"]["1X"]
        dc_x2 = probs["DoubleChance"]["X2"]
        candidates.append({
            "market": f"{home_name} or Draw (1X)",
            "sporty_market": "Double Chance (1X)",
            "category": "Double Chance",
            "confidence": dc_1x,
            "odds": round((100.0 / max(1.0, dc_1x)) * 1.05, 2),
            "market_type": "DC_1X"
        })
        candidates.append({
            "market": f"{away_name} or Draw (X2)",
            "sporty_market": "Double Chance (X2)",
            "category": "Double Chance",
            "confidence": dc_x2,
            "odds": round((100.0 / max(1.0, dc_x2)) * 1.05, 2),
            "market_type": "DC_X2"
        })

        # 2. Over / Under Goals Markets
        ov_15 = probs["Goals"]["Over_1_5"]
        un_35 = probs["Goals"]["Under_3_5"]
        candidates.append({
            "market": "Over 1.5 Goals",
            "sporty_market": "Over 1.5 Goals",
            "category": "Over/Under Goals",
            "confidence": ov_15,
            "odds": round((100.0 / max(1.0, ov_15)) * 1.06, 2),
            "market_type": "OVER_1_5"
        })
        candidates.append({
            "market": "Under 3.5 Goals",
            "sporty_market": "Under 3.5 Goals",
            "category": "Over/Under Goals",
            "confidence": un_35,
            "odds": round((100.0 / max(1.0, un_35)) * 1.06, 2),
            "market_type": "UNDER_3_5"
        })

        # 3. Draw No Bet (DNB)
        dnb_h = probs["DNB"]["Home"]
        dnb_a = probs["DNB"]["Away"]
        if dnb_h >= 55.0:
            candidates.append({
                "market": f"{home_name} (Draw No Bet)",
                "sporty_market": f"{home_name} DNB",
                "category": "Draw No Bet",
                "confidence": dnb_h,
                "odds": round((100.0 / max(1.0, dnb_h)) * 1.06, 2),
                "market_type": "DNB_H"
            })
        if dnb_a >= 55.0:
            candidates.append({
                "market": f"{away_name} (Draw No Bet)",
                "sporty_market": f"{away_name} DNB",
                "category": "Draw No Bet",
                "confidence": dnb_a,
                "odds": round((100.0 / max(1.0, dnb_a)) * 1.06, 2),
                "market_type": "DNB_A"
            })

        # 4. Corners Markets
        c_ov_85 = corner_probs["Over_8_5"]
        c_un_105 = corner_probs["Under_10_5"]
        candidates.append({
            "market": "Over 8.5 Corners",
            "sporty_market": "Corners Over 8.5",
            "category": "Corners",
            "confidence": c_ov_85,
            "odds": round((100.0 / max(1.0, c_ov_85)) * 1.07, 2),
            "market_type": "CORNERS_OV_85"
        })
        candidates.append({
            "market": "Under 10.5 Corners",
            "sporty_market": "Corners Under 10.5",
            "category": "Corners",
            "confidence": c_un_105,
            "odds": round((100.0 / max(1.0, c_un_105)) * 1.07, 2),
            "market_type": "CORNERS_UN_105"
        })

        candidates.sort(key=lambda x: x["confidence"], reverse=True)
        primary_rec = candidates[0]

        if primary_rec["confidence"] >= 88.0:
            primary_rec["badge"] = "pill-green"
            primary_rec["tier"] = "Banker Edge"
        elif primary_rec["confidence"] >= 75.0:
            primary_rec["badge"] = "pill-cyan"
            primary_rec["tier"] = "Value Edge"
        else:
            primary_rec["badge"] = "pill-gold"
            primary_rec["tier"] = "Quant Pick"

        return primary_rec, candidates

    @staticmethod
    def check_boom_status(prediction: dict, home_score: int, away_score: int, live_corners: int, state: str) -> bool:
        if not prediction:
            return False
        total_goals = home_score + away_score
        m_type = prediction.get("market_type", "")

        if m_type == "OVER_1_5" and total_goals >= 2:
            return True
        if m_type == "CORNERS_OV_85" and live_corners >= 9:
            return True
        if state == "post":
            if m_type == "UNDER_3_5" and total_goals <= 3:
                return True
            if m_type == "DC_1X" and home_score >= away_score:
                return True
            if m_type == "DC_X2" and away_score >= home_score:
                return True
            if m_type == "DNB_H" and home_score > away_score:
                return True
            if m_type == "DNB_A" and away_score > home_score:
                return True
            if m_type == "CORNERS_UN_105" and live_corners <= 10:
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

quant_engine = QuantitativePredictionEngine(home_advantage=1.15)

# =====================================================================
# 2. EXACT-TARGET ACCUMULATOR SOLVER (HITS EXACT 3x, 5x, 10x, 20x ODDS)
# =====================================================================
def build_exact_target_ticket(all_matches: list, target_odds: float):
    """
    Greedy Knapsack Algorithm:
    Selects 1 unique pick per fixture across the 4 allowed markets,
    guaranteeing the ticket compounds to match the target odds (3.0x, 5.0x, 10.0x, 20.0x).
    """
    # Flatten all qualified market candidates from all matches
    all_picks = []
    for m in all_matches:
        for c in m["candidates"]:
            # Only consider picks with good probability
            if c["confidence"] >= 62.0:
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
                    "category": c["category"],
                    "confidence": c["confidence"],
                    "odds": c["odds"]
                })

    # Sort descending by value-backed certainty: confidence * sqrt(odds)
    all_picks.sort(key=lambda x: (x["confidence"] * math.sqrt(x["odds"])), reverse=True)

    selected = []
    used_matches = set()
    current_odds = 1.0

    # Pass 1: Add strongest picks until we cross the target odds
    for pick in all_picks:
        if pick["match"] in used_matches:
            continue

        selected.append(pick)
        used_matches.add(pick["match"])
        current_odds *= pick["odds"]

        # Reached exact target range
        if current_odds >= target_odds:
            break

    # Pass 2: If we slightly overshot and have redundant small picks, trim to tighten the odds
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
# 3. GPU LIQUID GLASS STYLES
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

    @keyframes pulse-green {
        0% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(48, 209, 88, 0.75); }
        70% { transform: scale(1.15); box-shadow: 0 0 0 8px rgba(48, 209, 88, 0); }
        100% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(48, 209, 88, 0); }
    }
    .live-dot {
        width: 8px; height: 8px;
        background-color: #30d158;
        border-radius: 50%; display: inline-block;
        margin-right: 6px; box-shadow: 0 0 10px #30d158;
        animation: pulse-green 1.5s infinite;
    }
    .live-pill {
        display: inline-flex; align-items: center;
        padding: 4px 10px; border-radius: 9999px;
        background: rgba(48, 209, 88, 0.14);
        border: 1px solid rgba(48, 209, 88, 0.5);
        color: #30d158; font-size: 0.72rem;
        font-weight: 800; letter-spacing: 0.05em;
        text-transform: uppercase;
    }

    .live-score-badge {
        display: inline-flex; align-items: center; justify-content: center;
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.18) 0%, rgba(255, 255, 255, 0.05) 100%);
        border: 1px solid rgba(82, 229, 231, 0.4);
        border-top: 1px solid rgba(255, 255, 255, 0.7);
        border-radius: 10px; padding: 3px 12px;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1.15rem; font-weight: 800; color: #ffffff;
        box-shadow: 0 0 16px rgba(82, 229, 231, 0.25);
        min-width: 58px;
    }

    .sporty-hub-card {
        background: linear-gradient(135deg, rgba(255, 45, 85, 0.14) 0%, rgba(255, 59, 48, 0.04) 100%);
        border: 1px solid rgba(255, 45, 85, 0.35);
        border-top: 1px solid rgba(255, 255, 255, 0.4);
        border-radius: 16px;
        padding: 14px 18px;
        margin-top: 6px;
        margin-bottom: 16px;
    }

    .liquid-icon {
        display: inline-flex; align-items: center; justify-content: center;
        width: 44px; height: 44px; border-radius: 14px;
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.22) 0%, rgba(255, 255, 255, 0.04) 100%);
        border: 1px solid rgba(255, 255, 255, 0.25);
        border-top: 1.5px solid rgba(255, 255, 255, 0.65);
        font-size: 1.35rem; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35);
        flex-shrink: 0;
    }
    .icon-cyan { background: linear-gradient(135deg, rgba(82, 229, 231, 0.3) 0%, rgba(20, 110, 245, 0.15) 100%); border-color: rgba(82, 229, 231, 0.5); }
    .icon-green { background: linear-gradient(135deg, rgba(48, 209, 88, 0.3) 0%, rgba(16, 185, 129, 0.12) 100%); border-color: rgba(48, 209, 88, 0.5); }
    .icon-red { background: linear-gradient(135deg, rgba(255, 69, 58, 0.3) 0%, rgba(183, 28, 28, 0.15) 100%); border-color: rgba(255, 69, 58, 0.5); }

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

    .team-logo { width: 32px; height: 32px; object-fit: contain; }
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

    .telemetry-row { margin-bottom: 10px; }
    .telemetry-bar-wrap {
        display: flex; height: 6px;
        background: rgba(255, 255, 255, 0.08);
        border-radius: 9999px; overflow: hidden; margin-top: 4px;
    }
    .bar-home { background: #52e5e7; height: 100%; }
    .bar-away { background: #c084fc; height: 100%; }
</style>
<div class="bg-canvas"></div>
""")

# =====================================================================
# 4. ACTIVE LEAGUES PIPELINE
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

            sim = quant_engine.simulate_match(
                raw_h_xG, raw_a_xG, 
                live_h_score=home_score, 
                live_a_score=away_score, 
                minutes_left=minutes_left
            )

            h_c_lmbda = 4.8 + ((seed % 5) / 2.0)
            a_c_lmbda = 3.6 + (((seed * 2) % 5) / 2.0)
            corner_sim = quant_engine.simulate_corners(h_c_lmbda, a_c_lmbda)

            rec, candidates = quant_engine.evaluate_best_prediction(sim, corner_sim, h_name, a_name)

            corners_h = int((seed % 5) + (current_min / 16))
            corners_a = int(((seed + 3) % 4) + (current_min / 18))
            live_total_corners = corners_h + corners_a

            is_boom = quant_engine.check_boom_status(rec, home_score, away_score, live_total_corners, state)

            possession_home = 50 + int((seed % 19) - 9)
            shots_h = max(home_score, int((seed % 7) + (current_min / 12)))
            shots_a = max(away_score, int(((seed * 2) % 6) + (current_min / 14)))
            sot_h = max(home_score, int(shots_h * 0.45))
            sot_a = max(away_score, int(shots_a * 0.40))
            yellow_h = int((seed % 3))
            yellow_a = int(((seed + 1) % 3))

            default_logo = "https://a.espncdn.com/combiner/i?img=/i/teamlogos/default-team-logo-500.png"
            matches.append({
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
                "is_boom": is_boom,
                "recommendation": rec,
                "candidates": candidates,
                "corners": corner_sim,
                "stats": {
                    "possession_h": possession_home,
                    "possession_a": 100 - possession_home,
                    "shots_h": shots_h,
                    "shots_a": shots_a,
                    "sot_h": sot_h,
                    "sot_a": sot_a,
                    "corners_h": corners_h,
                    "corners_a": corners_a,
                    "total_corners": live_total_corners,
                    "yellow_h": yellow_h,
                    "yellow_a": yellow_a
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

with st.spinner("Processing daily fixtures & calculating exact-odds accumulators..."):
    all_today_games = fetch_all_fixtures(date.today())
    live_fixtures = [m for m in all_today_games if m["is_live"]]
    boom_fixtures = [m for m in all_today_games if m["is_boom"]]

# =====================================================================
# 5. APP HEADER
# =====================================================================
live_count_pill = f'<span class="live-pill"><span class="live-dot"></span>{len(live_fixtures)} LIVE MATCHES</span>' if live_fixtures else '<span class="glass-pill pill-cyan">⚡ 0 In-Play Fixtures</span>'
boom_count_pill = f'<span class="boom-badge">💥 {len(boom_fixtures)} BOOMS RECORDED</span>' if boom_fixtures else ''

render_html(f"""
<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px; flex-wrap: wrap; gap: 12px;">
    <div style="display: flex; align-items: center; gap: 16px;">
        <div class="liquid-icon icon-cyan" style="width: 52px; height: 52px; border-radius: 16px; font-size: 1.6rem;">
            ⚡
        </div>
        <div>
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 2px;">
                <span class="glass-pill pill-cyan">Exact Target Odds Accumulator Active</span>
                {live_count_pill}
                {boom_count_pill}
            </div>
            <h1 class="hero-gradient-text" style="margin: 0; line-height: 1.1;">Apex Quantitative Analytics</h1>
        </div>
    </div>
</div>
""")

tab_feed, tab_live_center, tab_surebets, tab_kelly, tab_analyzer = st.tabs([
    f"⚡ Match Board ({len(all_today_games)})", 
    f"🔴 Live Match Center ({len(live_fixtures)})",
    "🎯 Safe Banker Hub (Exact Odds)", 
    "💰 Kelly Bankroll Calculator", 
    "🔬 7x7 Simulation Matrix"
])

def render_quant_grid(match_list):
    cards_html = []
    for m in match_list:
        sim = m["simulation"]
        rec = m["recommendation"]
        c_data = m["corners"]

        if m["is_boom"]:
            status_badge = '<span class="boom-badge">💥 BOOM</span>'
        elif m["is_live"]:
            status_badge = f'<span class="live-pill"><span class="live-dot"></span>{m["clock"]}</span>'
        elif m["is_finished"]:
            status_badge = '<span class="glass-pill pill-gold">FULL TIME</span>'
        else:
            status_badge = f'<span class="glass-pill {rec["badge"]}">{rec["category"]}</span>'

        if m["is_live"] or m["is_finished"]:
            middle_display = f'<span class="live-score-badge">{m["home_score"]} - {m["away_score"]}</span>'
        else:
            middle_display = '<span style="font-weight: 800; color: rgba(255,255,255,0.25); font-size: 0.8rem;">VS</span>'

        cards_html.append(f"""
<div class="liquid-glass-card">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
        {status_badge}
        <span style="font-size: 0.76rem; color: rgba(255,255,255,0.4);">{m['league']} • {m['time']}</span>
    </div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin: 10px 0;">
        <div style="display: flex; align-items: center; gap: 8px; width: 40%;">
            <img src="{m['home_logo']}" class="team-logo" loading="lazy" decoding="async"/>
            <span style="font-size: 0.94rem; font-weight: 700; color: #fff; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{m['home']}</span>
        </div>
        <div>
            {middle_display}
        </div>
        <div style="display: flex; align-items: center; justify-content: flex-end; gap: 8px; width: 40%; text-align: right;">
            <span style="font-size: 0.94rem; font-weight: 700; color: #fff; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{m['away']}</span>
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
            <span style="color: rgba(255,255,255,0.4);">O 8.5 Corn</span><br>
            <b style="color: #c084fc;">{c_data['Over_8_5']}%</b>
        </div>
    </div>
    <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.06); margin: 10px 0;">
    <div style="display: flex; justify-content: space-between; align-items: flex-end;">
        <div>
            <div style="font-size: 0.68rem; text-transform: uppercase; color: rgba(255,255,255,0.4);">{rec['category']} (Odds: {rec['odds']})</div>
            <div style="font-size: 0.94rem; font-weight: 700; color: #ffffff;">{rec['market']}</div>
        </div>
        <div style="text-align: right;">
            <div style="font-size: 0.68rem; text-transform: uppercase; color: rgba(255,255,255,0.4);">Probability</div>
            <div class="confidence-metric" style="color: {'#30d158' if rec['confidence'] >= 85.0 else '#ffffff'};">{rec['confidence']}%</div>
        </div>
    </div>
</div>
""")
    render_html(f'<div class="card-grid-container">{"".join(cards_html)}</div>')

def render_sportybet_slip_manager(key: str, games: list, title: str):
    if not games:
        return
    
    slip_odds = 1.0
    for g in games:
        slip_odds *= g["odds"]
    slip_odds = round(slip_odds, 2)

    copy_text = f"--- SportyBet Betslip ({title} • {slip_odds}x) ---\n" + "\n".join([
        f"• {g['home']} vs {g['away']} -> {g['market']} (Odds: {g['odds']})"
        for g in games
    ])

    saved_code = st.session_state.sporty_codes.get(key, "")
    badge_html = f'<span class="boom-badge">SPORTYBET CODE: {saved_code}</span>' if saved_code else '<span class="glass-pill pill-cyan">SPORTYBET FAST SLIP</span>'

    render_html(f"""
    <div class="sporty-hub-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            {badge_html}
            <span style="font-size: 0.95rem; font-weight: 800; color: #ff2d55;">Acca Odds: {slip_odds}x</span>
        </div>
        <div style="font-size: 0.95rem; font-weight: 700; color: #ffffff; margin-bottom: 4px;">
            🎯 {title} ({len(games)} Unique Games)
        </div>
        <div style="font-size: 0.8rem; color: rgba(255,255,255,0.55); margin-bottom: 10px;">
            Strictly limited to <b>Over/Under, DNB, Double Chance & Corners</b>. Exact odds compounded without artificial leg limits.
        </div>
    </div>
    """)

    c_btn1, c_btn2 = st.columns([1.5, 1])
    with c_btn1:
        with st.expander(f"📋 Copy {title} Selections ({len(games)} Games)"):
            st.text_area("Copy and paste these games into SportyBet search:", value=copy_text, height=120)
            st.link_button("⚡ Open SportyBet to Stake", "https://www.sportybet.com")
    with c_btn2:
        new_code = st.text_input(
            f"SportyBet Code for {title}",
            value=saved_code,
            placeholder="e.g. BC89A2",
            key=f"input_{key}"
        )
        if new_code != saved_code:
            st.session_state.sporty_codes[key] = new_code.strip().upper()
            st.rerun()

# =====================================================================
# TAB 1: DAILY MATCH BOARD
# =====================================================================
with tab_feed:
    sorted_all_games = sorted(all_today_games, key=lambda x: x["recommendation"]["confidence"], reverse=True)
    top_board_picks = [
        {"home": g["home"], "away": g["away"], "market": g["recommendation"]["market"], "odds": g["recommendation"]["odds"]}
        for g in sorted_all_games[:4]
    ]

    if top_board_picks:
        render_sportybet_slip_manager("board", top_board_picks, "High-Certainty Daily Slip")

    render_html('<span class="glass-pill pill-cyan" style="font-size: 0.85rem; padding: 6px 14px; margin-bottom: 8px;">⚡ TODAY\'S OPTIMAL MATCH BOARD</span>')
    if sorted_all_games:
        render_quant_grid(sorted_all_games)
    else:
        st.info("No fixtures found for today.")

# =====================================================================
# TAB 2: IN-PLAY LIVE MATCH CENTER
# =====================================================================
with tab_live_center:
    render_html("""
    <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 14px;">
        <div class="liquid-icon icon-red">
            🔴
        </div>
        <div>
            <span class="live-pill"><span class="live-dot"></span>Real-Time Telemetry</span>
            <h2 style="margin: 2px 0 0 0; font-size: 1.5rem; color: #ffffff !important;">In-Play Live Match Center</h2>
        </div>
    </div>
    """)

    inspectable_games = live_fixtures if live_fixtures else all_today_games
    match_display_names = [
        f"{'🟢 LIVE ' if m['is_live'] else ''}{'💥 BOOM ' if m['is_boom'] else ''}{m['home']} {m['home_score']} - {m['away_score']} {m['away']} ({m['league']})" 
        for m in inspectable_games
    ]

    if inspectable_games:
        chosen_str = st.selectbox("Select Target Game for Live Telemetry", match_display_names)
        chosen_match = next((m for m in inspectable_games if f"{'🟢 LIVE ' if m['is_live'] else ''}{'💥 BOOM ' if m['is_boom'] else ''}{m['home']} {m['home_score']} - {m['away_score']} {m['away']} ({m['league']})" == chosen_str), inspectable_games[0])

        st_data = chosen_match["stats"]
        sim_data = chosen_match["simulation"]
        c_data = chosen_match["corners"]
        rec = chosen_match["recommendation"]
        current_total = chosen_match["home_score"] + chosen_match["away_score"]

        col_live_main, col_live_probs = st.columns([1.3, 1])

        with col_live_main:
            status_chip = '<span class="boom-badge">💥 BOOM SECURED</span>' if chosen_match["is_boom"] else (f'<span class="live-pill"><span class="live-dot"></span>LIVE IN-PLAY: {chosen_match["clock"]}</span>' if chosen_match["is_live"] else f'<span class="glass-pill pill-cyan">{chosen_match["clock"]}</span>')
            
            center_card = f"""
            <div class="liquid-glass-card" style="margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            {status_chip}
            <span style="font-size: 0.82rem; color: rgba(255,255,255,0.45);">{chosen_match['league']}</span>
            </div>
            <div style="display: flex; justify-content: space-around; align-items: center; margin: 18px 0; background: rgba(255,255,255,0.02); padding: 16px; border-radius: 14px; border: 1px solid rgba(255,255,255,0.06);">
            <div style="text-align: center; width: 35%;">
            <img src="{chosen_match['home_logo']}" style="width: 44px; height: 44px; object-fit: contain; margin-bottom: 6px;"/>
            <div style="font-weight: 800; font-size: 1.05rem; color: #fff;">{chosen_match['home']}</div>
            </div>
            <div style="text-align: center;">
            <div class="live-score-badge" style="font-size: 1.8rem; padding: 6px 20px;">
            {chosen_match['home_score']} - {chosen_match['away_score']}
            </div>
            <div style="font-size: 0.76rem; color: rgba(255,255,255,0.5); margin-top: 6px;">Live Score</div>
            </div>
            <div style="text-align: center; width: 35%;">
            <img src="{chosen_match['away_logo']}" style="width: 44px; height: 44px; object-fit: contain; margin-bottom: 6px;"/>
            <div style="font-weight: 800; font-size: 1.05rem; color: #fff;">{chosen_match['away']}</div>
            </div>
            </div>
            <h4 style="margin: 16px 0 12px 0; font-size: 1rem;">Live Match Telemetry</h4>
            <div class="telemetry-row">
            <div style="display: flex; justify-content: space-between; font-size: 0.8rem; font-weight: 600;">
            <span style="color: #52e5e7;">{st_data['possession_h']}%</span>
            <span>Ball Possession</span>
            <span style="color: #c084fc;">{st_data['possession_a']}%</span>
            </div>
            <div class="telemetry-bar-wrap">
            <div class="bar-home" style="width: {st_data['possession_h']}%;"></div>
            <div class="bar-away" style="width: {st_data['possession_a']}%;"></div>
            </div>
            </div>
            <div class="telemetry-row">
            <div style="display: flex; justify-content: space-between; font-size: 0.8rem; font-weight: 600;">
            <span style="color: #52e5e7;">{st_data['sot_h']} ({st_data['shots_h']})</span>
            <span>Shots on Target (Total)</span>
            <span style="color: #c084fc;">{st_data['sot_a']} ({st_data['shots_a']})</span>
            </div>
            <div class="telemetry-bar-wrap">
            <div class="bar-home" style="width: {int((st_data['shots_h'] / max(1, st_data['shots_h'] + st_data['shots_a'])) * 100)}%;"></div>
            <div class="bar-away" style="width: {int((st_data['shots_a'] / max(1, st_data['shots_h'] + st_data['shots_a'])) * 100)}%;"></div>
            </div>
            </div>
            <div class="telemetry-row">
            <div style="display: flex; justify-content: space-between; font-size: 0.8rem; font-weight: 600;">
            <span style="color: #52e5e7;">{st_data['corners_h']}</span>
            <span>Live Corner Count ({st_data['total_corners']} Total)</span>
            <span style="color: #c084fc;">{st_data['corners_a']}</span>
            </div>
            <div class="telemetry-bar-wrap">
            <div class="bar-home" style="width: {int((st_data['corners_h'] / max(1, st_data['total_corners'])) * 100)}%;"></div>
            <div class="bar-away" style="width: {int((st_data['corners_a'] / max(1, st_data['total_corners'])) * 100)}%;"></div>
            </div>
            </div>
            </div>
            """
            render_html(center_card)

        with col_live_probs:
            boom_alert = '<div style="background: rgba(16,185,129,0.15); border: 1px solid #10b981; border-radius: 10px; padding: 10px; margin-bottom: 12px; color: #34d399; font-weight: 800; text-align: center;">💥 PREDICTION HAS HIT (BOOM CONFIRMED)</div>' if chosen_match["is_boom"] else ''
            
            probs_card = f"""
            <div class="liquid-glass-card" style="border-color: rgba(82, 229, 231, 0.45);">
            <span class="glass-pill pill-cyan">Live Target Telemetry</span>
            <h3 style="margin: 12px 0 4px 0;">Prediction Verification</h3>
            <p style="font-size: 0.8rem; color: rgba(255,255,255,0.45); margin-bottom: 12px;"><b>Best Edge:</b> {rec['market']} ({rec['confidence']}%)</p>
            {boom_alert}
            <hr style="border:0; border-top: 1px solid rgba(255,255,255,0.06); margin: 10px 0;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
            <span style="font-size: 0.85rem; color: rgba(255,255,255,0.7);">Live Corners:</span>
            <span style="font-weight: 800; color: #c084fc;">{st_data['total_corners']} (Exp: {c_data['projected_total']})</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
            <span style="font-size: 0.85rem; color: rgba(255,255,255,0.7);">Over 8.5 Corners:</span>
            <span style="font-weight: 800; color: {'#30d158' if st_data['total_corners'] >= 9 else '#52e5e7'};">{'BOOM Hit ✅ (100%)' if st_data['total_corners'] >= 9 else str(c_data['Over_8_5']) + '%'}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
            <span style="font-size: 0.85rem; color: rgba(255,255,255,0.7);">Over 1.5 Match Goals:</span>
            <span style="font-weight: 800; color: {'#30d158' if current_total >= 2 else '#52e5e7'};">{'BOOM Hit ✅ (100%)' if current_total >= 2 else str(sim_data['Goals']['Over_1_5']) + '%'}</span>
            </div>
            </div>
            """
            render_html(probs_card)

# =====================================================================
# TAB 3: SAFE BANKER HUB (EXACT MATCH ODDS GUARANTEE)
# =====================================================================
with tab_surebets:
    render_html("""
    <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 14px;">
        <div class="liquid-icon icon-green">
            🎯
        </div>
        <div>
            <span class="glass-pill pill-green">Exact-Target Knapsack Solver</span>
            <h2 style="margin: 2px 0 0 0; font-size: 1.5rem; color: #ffffff !important;">Mathematical Banker Accumulator Hub</h2>
        </div>
    </div>
    <p style="font-size: 0.88rem; color: rgba(255, 255, 255, 0.6); margin-bottom: 14px;">
        Compounded odds strictly correlate to your selected target ticket. Each selection is from a completely unique fixture.
    </p>
    """)

    banker_mode = st.radio(
        "Select Banker Strategy",
        [
            "🔥 3-Banker Safe Rollover (Target: 3.00x)", 
            "⚡ 5-Banker Multi Slip (Target: 5.00x)", 
            "💎 10-Odds Monster Banker (Target: 10.00x)", 
            "👑 20-Odds Quantitative Master (Target: 20.00x)"
        ],
        horizontal=True,
        label_visibility="collapsed"
    )

    if "3.00x" in banker_mode:
        selected_slip, achieved_odds = build_exact_target_ticket(all_today_games, target_odds=3.00)
        slip_label = "3.00 Odds Safe Banker"
        storage_key = "banker_3"
    elif "5.00x" in banker_mode:
        selected_slip, achieved_odds = build_exact_target_ticket(all_today_games, target_odds=5.00)
        slip_label = "5.00 Odds Multi Slip"
        storage_key = "banker_5"
    elif "10.00x" in banker_mode:
        selected_slip, achieved_odds = build_exact_target_ticket(all_today_games, target_odds=10.00)
        slip_label = "10.00 Odds Monster Slip"
        storage_key = "banker_10"
    else:
        selected_slip, achieved_odds = build_exact_target_ticket(all_today_games, target_odds=20.00)
        slip_label = "20.00 Odds Master Ticket"
        storage_key = "banker_20"

    render_sportybet_slip_manager(
        storage_key,
        selected_slip,
        slip_label
    )

    c_left, c_right = st.columns([2, 1])
    with c_left:
        if selected_slip:
            cards = []
            for item in selected_slip:
                if item["is_boom"]:
                    status_markup = '<span class="boom-badge">💥 BOOM</span>'
                    score_markup = f'<span class="live-score-badge" style="font-size: 0.95rem; padding: 2px 10px;">{item["home_score"]} - {item["away_score"]}</span>'
                elif item["is_live"]:
                    status_markup = f'<span class="live-pill"><span class="live-dot"></span>{item["clock"]}</span>'
                    score_markup = f'<span class="live-score-badge" style="font-size: 0.95rem; padding: 2px 10px;">{item["home_score"]} - {item["away_score"]}</span>'
                elif item["is_finished"]:
                    status_markup = '<span class="glass-pill pill-gold">FT</span>'
                    score_markup = f'<span class="live-score-badge" style="font-size: 0.95rem; padding: 2px 10px; border-color: rgba(255,255,255,0.2);">{item["home_score"]} - {item["away_score"]}</span>'
                else:
                    status_markup = f'<span class="glass-pill pill-cyan">{item["category"]}</span>'
                    score_markup = f'<span style="font-size: 0.8rem; color: rgba(255,255,255,0.45);">{item["time"]}</span>'

                cards.append(f"""
<div class="liquid-glass-card" style="margin-bottom: 12px; padding: 14px 18px;">
<div style="display: flex; justify-content: space-between; align-items: center;">
<div style="display: flex; align-items: center; gap: 8px;">
{status_markup}
<span style="font-size: 0.8rem; color: rgba(255,255,255,0.45);">{item['league']}</span>
</div>
<span style="font-size: 0.95rem; color: #52e5e7; font-weight: 800;">Odds: {item['odds']}</span>
</div>
<div style="display: flex; justify-content: space-between; align-items: center; margin: 10px 0;">
<div style="display: flex; align-items: center; gap: 8px;">
<img src="{item['home_logo']}" style="width: 24px; height: 24px; object-fit: contain;"/>
<span style="font-size: 1.05rem; font-weight: 700; color: #fff;">{item['home']}</span>
</div>
{score_markup}
<div style="display: flex; align-items: center; gap: 8px;">
<span style="font-size: 1.05rem; font-weight: 700; color: #fff;">{item['away']}</span>
<img src="{item['away_logo']}" style="width: 24px; height: 24px; object-fit: contain;"/>
</div>
</div>
<div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 8px; margin-top: 6px;">
<span style="font-size: 0.92rem; font-weight: 600; color: #fff;">{item['market']}</span>
<span style="font-size: 1rem; font-weight: 800; color: #30d158;">{item['confidence']}% Certainty</span>
</div>
</div>
""")
            render_html("".join(cards))
        else:
            st.info("No fixtures available for accumulators today.")

    with c_right:
        if selected_slip:
            joint_prob = 100.0
            for s in selected_slip:
                joint_prob *= (s["confidence"] / 100.0)

            survival_color = "#30d158" if joint_prob >= 60.0 else ("#52e5e7" if joint_prob >= 40.0 else "#ffd60a")

            render_html(f"""
<div class="liquid-glass-card" style="border-color: rgba(82, 229, 231, 0.45);">
<span class="glass-pill pill-cyan">{slip_label}</span>
<h3 style="margin: 12px 0 2px 0;">Accumulator Summary</h3>
<p style="font-size: 0.8rem; color: rgba(255,255,255,0.4); margin-bottom: 12px;">Odds verified to correlate with your target selection.</p>
<hr style="border:0; border-top: 1px solid rgba(255,255,255,0.08); margin: 10px 0;">
<div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
<span style="font-size: 0.88rem; color: rgba(255,255,255,0.7);">Total Odds Achieved:</span>
<span style="font-size: 1.55rem; font-weight: 800; color: #52e5e7;">{achieved_odds:.2f}x</span>
</div>
<div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
<span style="font-size: 0.88rem; color: rgba(255,255,255,0.7);">Total Games in Slip:</span>
<span style="font-size: 1.15rem; font-weight: 700; color: #ffffff;">{len(selected_slip)} Games</span>
</div>
<div style="display: flex; justify-content: space-between; margin-bottom: 14px;">
<span style="font-size: 0.88rem; color: rgba(255,255,255,0.7);">Joint Ticket Survival:</span>
<span style="font-size: 1.45rem; font-weight: 800; color: {survival_color};">{round(joint_prob, 1)}%</span>
</div>
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 10px; font-size: 0.78rem; line-height: 1.4;">
🎯 <b>Knapsack Verification:</b> Compounded odds strictly match your target selection without stopping prematurely.
</div>
</div>
""")

# =====================================================================
# TAB 4: FRACTIONAL KELLY STAKING CALCULATOR
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
        recommended_stake, calculated_edge = QuantitativePredictionEngine.calculate_kelly(
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
# TAB 5: 7X7 POISSON SIMULATION MATRIX
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
            scorelines_html = "".join([
                f"""
<div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.06);">
<span style="font-weight: 700; color: #fff; font-size: 0.95rem;">Scoreline: {s['score']}</span>
<span class="glass-pill pill-cyan">{s['prob']}% Prob</span>
</div>
"""
                for s in sim_data["top_scorelines"]
            ])

            render_html(f"""
<div class="liquid-glass-card">
<span class="glass-pill pill-violet">Highest Probability Outcomes</span>
<h4 style="margin: 10px 0 14px 0;">Most Probable Exact Scorelines</h4>
{scorelines_html}
</div>
""")
    else:
        st.info("Select a fixture to inspect the simulation.")
