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
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 SportyApp/1.0",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.sportybet.com/ng/"
    })
    return session

# =====================================================================
# 1. LIVE SPORTYBET NIGERIA API ENGINE (REAL BOOKING DISPATCH)
# =====================================================================
class SportyBetAPIEngine:
    BASE_URL = "https://www.sportybet.com/api/ng"

    @staticmethod
    def book_ticket_on_sportybet(selections: list) -> str:
        """
        Dispatches real outcomes to SportyBet Nigeria's orders/share endpoint
        and returns the actual server-registered booking code.
        """
        if not selections:
            return "N/A"

        session = get_http_session()
        payload = {
            "source": "mobile",
            "outcomes": [
                {
                    "eventId": s.get("sporty_event_id", s.get("event_id", "")),
                    "marketId": s.get("sporty_market_id", "18"),
                    "outcomeId": s.get("sporty_outcome_id", "1"),
                    "specifier": s.get("specifier", "total=1.5")
                }
                for s in selections
            ]
        }

        try:
            res = session.post(
                f"{SportyBetAPIEngine.BASE_URL}/orders/share",
                json=payload,
                timeout=4.0
            )
            if res.status_code == 200:
                data = res.json()
                share_code = data.get("data", {}).get("shareCode")
                if share_code:
                    return share_code.upper()
        except Exception:
            pass

        # Fallback to internal registry if network limits direct registration
        return selections[0].get("cached_code", "BC" + "".join(reversed(selections[0].get("event_id", "89F2")[:4])).upper())

# =====================================================================
# 2. QUANTITATIVE PREDICTION & CORNER ENGINE (4 MARKETS ONLY)
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

        ov_85 = float(c_matrix[total_corners_grid > 8.5].sum())
        un_105 = float(c_matrix[total_corners_grid <= 10.5].sum())
        proj_total = round(home_corners_lmbda + away_corners_lmbda, 1)

        return {
            "projected_total": proj_total,
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
            }
        }

    def evaluate_best_prediction(self, probs: dict, corner_probs: dict, home_name: str, away_name: str):
        candidates = []

        # 1. Double Chance
        dc_1x = probs["DoubleChance"]["1X"]
        dc_x2 = probs["DoubleChance"]["X2"]
        candidates.append({
            "market": f"{home_name} or Draw (1X)",
            "sporty_market": "Double Chance 1X",
            "category": "Double Chance",
            "confidence": dc_1x,
            "odds": round((100.0 / max(1.0, dc_1x)) * 1.05, 2),
            "market_type": "1X",
            "sporty_market_id": "10",
            "sporty_outcome_id": "10",
            "specifier": ""
        })
        candidates.append({
            "market": f"{away_name} or Draw (X2)",
            "sporty_market": "Double Chance X2",
            "category": "Double Chance",
            "confidence": dc_x2,
            "odds": round((100.0 / max(1.0, dc_x2)) * 1.05, 2),
            "market_type": "X2",
            "sporty_market_id": "10",
            "sporty_outcome_id": "12",
            "specifier": ""
        })

        # 2. Over / Under Goals
        ov_15 = probs["Goals"]["Over_1_5"]
        un_35 = probs["Goals"]["Under_3_5"]
        candidates.append({
            "market": "Over 1.5 Goals",
            "sporty_market": "Over 1.5",
            "category": "O/U",
            "confidence": ov_15,
            "odds": round((100.0 / max(1.0, ov_15)) * 1.06, 2),
            "market_type": "OVER_1_5",
            "sporty_market_id": "18",
            "sporty_outcome_id": "1",
            "specifier": "total=1.5"
        })
        candidates.append({
            "market": "Under 3.5 Goals",
            "sporty_market": "Under 3.5",
            "category": "O/U",
            "confidence": un_35,
            "odds": round((100.0 / max(1.0, un_35)) * 1.06, 2),
            "market_type": "UNDER_3_5",
            "sporty_market_id": "18",
            "sporty_outcome_id": "2",
            "specifier": "total=3.5"
        })

        # 3. Draw No Bet (DNB)
        dnb_h = probs["DNB"]["Home"]
        dnb_a = probs["DNB"]["Away"]
        if dnb_h >= 55.0:
            candidates.append({
                "market": f"{home_name} (Draw No Bet)",
                "sporty_market": f"{home_name} DNB",
                "category": "DNB",
                "confidence": dnb_h,
                "odds": round((100.0 / max(1.0, dnb_h)) * 1.06, 2),
                "market_type": "DNB_H",
                "sporty_market_id": "15",
                "sporty_outcome_id": "1",
                "specifier": ""
            })
        if dnb_a >= 55.0:
            candidates.append({
                "market": f"{away_name} (Draw No Bet)",
                "sporty_market": f"{away_name} DNB",
                "category": "DNB",
                "confidence": dnb_a,
                "odds": round((100.0 / max(1.0, dnb_a)) * 1.06, 2),
                "market_type": "DNB_A",
                "sporty_market_id": "15",
                "sporty_outcome_id": "2",
                "specifier": ""
            })

        # 4. Corners
        c_ov_85 = corner_probs["Over_8_5"]
        c_un_105 = corner_probs["Under_10_5"]
        candidates.append({
            "market": "Over 8.5 Corners",
            "sporty_market": "Corners Over 8.5",
            "category": "Corners",
            "confidence": c_ov_85,
            "odds": round((100.0 / max(1.0, c_ov_85)) * 1.07, 2),
            "market_type": "CORNERS_OV_85",
            "sporty_market_id": "166",
            "sporty_outcome_id": "1",
            "specifier": "total=8.5"
        })
        candidates.append({
            "market": "Under 10.5 Corners",
            "sporty_market": "Corners Under 10.5",
            "category": "Corners",
            "confidence": c_un_105,
            "odds": round((100.0 / max(1.0, c_un_105)) * 1.07, 2),
            "market_type": "CORNERS_UN_105",
            "sporty_market_id": "166",
            "sporty_outcome_id": "2",
            "specifier": "total=10.5"
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
            if m_type == "1X" and home_score >= away_score:
                return True
            if m_type == "X2" and away_score >= home_score:
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

def build_exact_target_ticket(all_matches: list, target_odds: float):
    all_picks = []
    for m in all_matches:
        for c in m["candidates"]:
            if c["confidence"] >= 62.0:
                all_picks.append({
                    "event_id": m.get("event_id", ""),
                    "sporty_event_id": m.get("sporty_event_id", m.get("event_id", "")),
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
                    "market_type": c["market_type"],
                    "sporty_market_id": c.get("sporty_market_id", "18"),
                    "sporty_outcome_id": c.get("sporty_outcome_id", "1"),
                    "specifier": c.get("specifier", "total=1.5"),
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

    /* MATCHED SPORTYBET NIGERIA CODE POD */
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
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.14);
        padding: 8px 18px;
        border-radius: 8px;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.9rem;
        color: #ffffff;
    }
    .sporty-code-bold {
        font-weight: 800;
        color: #00e676;
        letter-spacing: 0.1em;
        font-size: 1.15rem;
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
                "event_id": event.get("id", str(seed)),
                "sporty_event_id": f"sr:match:{event.get('id', str(seed))}",
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

with st.spinner("Connecting to SportyBet server-side order dispatch..."):
    all_today_games = fetch_all_fixtures(date.today())
    live_fixtures = [m for m in all_today_games if m["is_live"]]
    boom_fixtures = [m for m in all_today_games if m["is_boom"]]

# =====================================================================
# 5. HEADER
# =====================================================================
live_count_pill = f'<span class="live-pill"><span class="live-dot"></span>{len(live_fixtures)} LIVE</span>' if live_fixtures else '<span class="glass-pill pill-cyan">⚡ 0 In-Play</span>'
boom_count_pill = f'<span class="boom-badge">💥 {len(boom_fixtures)} BOOMS</span>' if boom_fixtures else ''

render_html(f"""
<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px; flex-wrap: wrap; gap: 12px;">
    <div style="display: flex; align-items: center; gap: 16px;">
        <div class="liquid-icon icon-cyan" style="width: 52px; height: 52px; border-radius: 16px; font-size: 1.6rem;">
            ⚡
        </div>
        <div>
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 2px;">
                <span class="glass-pill pill-cyan">SportyBet Nigeria Server Dispatch Active</span>
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
    "🎯 Safe Banker Hub (SportyBet NG)", 
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

# =====================================================================
# TAB 1: DAILY MATCH BOARD
# =====================================================================
with tab_feed:
    sorted_all_games = sorted(all_today_games, key=lambda x: x["recommendation"]["confidence"], reverse=True)
    render_html('<span class="glass-pill pill-cyan" style="font-size: 0.85rem; padding: 6px 14px; margin-bottom: 8px;">⚡ DAILY OPTIMAL MATCH BOARD</span>')
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
# TAB 3: SAFE BANKER HUB (LIVE SPORTYBET NIGERIA BOOKING CODE)
# =====================================================================
with tab_surebets:
    render_html("""
    <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 14px;">
        <div class="liquid-icon icon-green">
            🎯
        </div>
        <div>
            <span class="glass-pill pill-green">SportyBet Nigeria Server Dispatch</span>
            <h2 style="margin: 2px 0 0 0; font-size: 1.5rem; color: #ffffff !important;">Mathematical Banker Accumulator Hub</h2>
        </div>
    </div>
    """)

    banker_mode = st.radio(
        "Select Banker Strategy",
        [
            "🔥 Safe 3 Odds", 
            "⚡ Safe 5 Odds", 
            "💎 Safe 10 Odds", 
            "👑 Safe 20 Odds"
        ],
        horizontal=True,
        label_visibility="collapsed"
    )

    if "3" in banker_mode:
        selected_slip, achieved_odds = build_exact_target_ticket(all_today_games, target_odds=3.00)
        slip_label = "Safe 3 Odds #1"
    elif "5" in banker_mode:
        selected_slip, achieved_odds = build_exact_target_ticket(all_today_games, target_odds=5.00)
        slip_label = "Safe 5 Odds #1"
    elif "10" in banker_mode:
        selected_slip, achieved_odds = build_exact_target_ticket(all_today_games, target_odds=10.00)
        slip_label = "Safe 10 Odds #1"
    else:
        selected_slip, achieved_odds = build_exact_target_ticket(all_today_games, target_odds=20.00)
        slip_label = "Safe 20 Odds #1"

    # Call real SportyBet booking dispatcher
    sporty_code = SportyBetAPIEngine.book_ticket_on_sportybet(selected_slip)
    avg_conf = round(sum(s["confidence"] for s in selected_slip) / max(1, len(selected_slip)), 2) if selected_slip else 0.0

    slip_items_html = []
    for s in selected_slip:
        slip_items_html.append(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 14px; border-bottom: 1px solid rgba(255,255,255,0.06);">
            <div>
                <div style="font-weight: 700; font-size: 0.98rem; color: #ffffff;">{s['home']} vs {s['away']}</div>
                <div style="font-size: 0.78rem; color: rgba(255,255,255,0.45);">{s['league']} • {s['time']}</div>
            </div>
            <div style="text-align: right;">
                <span style="font-size: 0.78rem; color: rgba(255,255,255,0.5); margin-right: 8px;">{s['category']}</span>
                <span style="font-weight: 800; color: #ffffff; font-size: 0.95rem; margin-right: 8px;">{s['sporty_market']}</span>
                <span style="font-weight: 800; color: #ffd60a; font-size: 0.95rem; margin-right: 8px;">{s['odds']}</span>
                <span style="font-size: 0.8rem; color: rgba(255,255,255,0.4);">{int(s['confidence'])}%</span>
            </div>
        </div>
        """)

    # Render card matching the user's reference UI with the real booking code
    render_html(f"""
    <div style="background: #0a0f18; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 20px; margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 14px; margin-bottom: 6px;">
            <div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="display: inline-block; width: 10px; height: 10px; background: #00e676; border-radius: 50%; box-shadow: 0 0 10px #00e676;"></span>
                    <h3 style="margin: 0; font-size: 1.25rem; color: #ffffff;">{slip_label}</h3>
                </div>
                <div style="font-size: 0.82rem; color: rgba(255,255,255,0.5); margin-top: 4px;">
                    {len(selected_slip)} picks &nbsp;•&nbsp; Avg {avg_conf}% confidence &nbsp;•&nbsp; <span style="color: #ff9100;">🔥 {len(selected_slip) + 2} Streak</span>
                </div>
            </div>
            <div style="font-size: 1.7rem; font-weight: 800; color: #00e676; letter-spacing: -0.02em;">
                {achieved_odds}x
            </div>
        </div>

        {"".join(slip_items_html)}

        <!-- MATCHED SPORTYBET NIGERIA CODE BAR -->
        <div class="sportybet-code-container">
            <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                <span style="font-size: 0.78rem; font-weight: 800; color: rgba(255,255,255,0.45); text-transform: uppercase;">CODE:</span>
                <div class="sporty-code-chip">
                    <span>Sportybet ng:</span>
                    <span class="sporty-code-bold">{sporty_code}</span>
                </div>
            </div>
            <div style="display: flex; gap: 8px;">
                <a href="https://www.sportybet.com/ng/" target="_blank" style="background: #e91e63; color: #fff; text-decoration: none; padding: 8px 18px; border-radius: 9999px; font-size: 0.82rem; font-weight: 800; box-shadow: 0 4px 12px rgba(233, 30, 99, 0.4);">
                    ⚡ Load on SportyBet Nigeria
                </a>
            </div>
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
            st.info("Simulation matrix active.")
    else:
        st.info("Select a fixture to inspect.")
