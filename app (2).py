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
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
        "Accept": "application/json, text/plain, */*"
    })
    return session

if "sportybet_ng_codes" not in st.session_state:
    st.session_state.sportybet_ng_codes = {
        "board_master": "VFUBGJ",
        "stake_5": "C5JEQK",
        "stake_10": "B2WCRA",
        "stake_20": "KFG5BM",
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
# 1. QUANTITATIVE PREDICTION ENGINE (ANTI-1-CUT PROTECTED)
# =====================================================================
class AntiOneCutEngine:
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

    def simulate_corners(self, h_lmbda: float, a_lmbda: float) -> dict:
        max_c = 18
        h_prob = self._poisson_vector(h_lmbda, max_c)
        a_prob = self._poisson_vector(a_lmbda, max_c)
        c_matrix = np.outer(h_prob, a_prob)
        c_grid = np.add.outer(np.arange(max_c), np.arange(max_c))

        ov_75 = float(c_matrix[c_grid > 7.5].sum())
        ov_85 = float(c_matrix[c_grid > 8.5].sum())
        un_115 = float(c_matrix[c_grid <= 11.5].sum())
        return {
            "projected_total": round(h_lmbda + a_lmbda, 1),
            "Over_7_5": round(ov_75 * 100, 1),
            "Over_8_5": round(ov_85 * 100, 1),
            "Under_11_5": round(un_115 * 100, 1)
        }

    def simulate_match(self, h_xG: float, a_xG: float, live_h: int = 0, live_a: int = 0, mins_left: float = 90.0) -> dict:
        tf = max(0.05, min(1.0, mins_left / 90.0))
        adj_h = max(0.1, h_xG * self.home_advantage * tf)
        adj_a = max(0.1, a_xG * tf)

        h_probs = self._poisson_vector(adj_h, self.max_goals)
        a_probs = self._poisson_vector(adj_a, self.max_goals)
        matrix = np.outer(h_probs, a_probs)

        h_win, draw, a_win = 0.0, 0.0, 0.0
        ov_15, un_15 = 0.0, 0.0
        un_35 = 0.0

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
            "Goals": {"Over_1_5": round(ov_15 * 100, 1), "Under_1_5": round(un_15 * 100, 1), "Under_3_5": round(un_35 * 100, 1)}
        }

    def evaluate_anti_one_cut(self, sim: dict, corners: dict, home_name: str, away_name: str):
        candidates = []

        ov_15 = sim["Goals"]["Over_1_5"]
        if ov_15 >= 70.0:
            odds_15 = round((100.0 / ov_15) * 1.06, 2)
            candidates.append({
                "market": "Over 1.5 Goals", "sporty_market": "Over 1.5 Goals",
                "category": "Match Goals", "confidence": ov_15,
                "odds": odds_15, "market_type": "OVER_1_5",
                "score": ov_15 * (odds_15 ** 1.35)
            })

        dc = sim["DoubleChance"]
        if dc["1X"] >= 70.0:
            odds_1x = round((100.0 / dc["1X"]) * 1.05, 2)
            candidates.append({
                "market": f"{home_name} or Draw (1X)", "sporty_market": "Double Chance 1X",
                "category": "Double Chance", "confidence": dc["1X"],
                "odds": odds_1x, "market_type": "DC_1X",
                "score": dc["1X"] * (odds_1x ** 1.35)
            })
        if dc["X2"] >= 70.0:
            odds_x2 = round((100.0 / dc["X2"]) * 1.05, 2)
            candidates.append({
                "market": f"{away_name} or Draw (X2)", "sporty_market": "Double Chance X2",
                "category": "Double Chance", "confidence": dc["X2"],
                "odds": odds_x2, "market_type": "DC_X2",
                "score": dc["X2"] * (odds_x2 ** 1.35)
            })
        if dc["12"] >= 74.0:
            odds_12 = round((100.0 / dc["12"]) * 1.05, 2)
            candidates.append({
                "market": "Any Team to Win (12)", "sporty_market": "Double Chance 12",
                "category": "Double Chance", "confidence": dc["12"],
                "odds": odds_12, "market_type": "DC_12",
                "score": dc["12"] * (odds_12 ** 1.25)
            })

        dnb = sim["DNB"]
        if dnb["Home"] >= 62.0:
            odds_dnb = round((100.0 / dnb["Home"]) * 1.06, 2)
            candidates.append({
                "market": f"{home_name} (Draw No Bet)", "sporty_market": f"{home_name} DNB",
                "category": "Draw No Bet", "confidence": dnb["Home"],
                "odds": odds_dnb, "market_type": "DNB_H",
                "score": dnb["Home"] * (odds_dnb ** 1.25)
            })
        elif dnb["Away"] >= 62.0:
            odds_dnba = round((100.0 / dnb["Away"]) * 1.06, 2)
            candidates.append({
                "market": f"{away_name} (Draw No Bet)", "sporty_market": f"{away_name} DNB",
                "category": "Draw No Bet", "confidence": dnb["Away"],
                "odds": odds_dnba, "market_type": "DNB_A",
                "score": dnb["Away"] * (odds_dnba ** 1.25)
            })

        un_35 = sim["Goals"]["Under_3_5"]
        if un_35 >= 75.0:
            odds_35 = round((100.0 / un_35) * 1.05, 2)
            candidates.append({
                "market": "Under 3.5 Goals", "sporty_market": "Under 3.5 Goals",
                "category": "Safety Under", "confidence": un_35,
                "odds": odds_35, "market_type": "UNDER_3_5",
                "score": un_35 * (odds_35 ** 1.1)
            })

        candidates.sort(key=lambda x: x["score"], reverse=True)
        primary_rec = candidates[0] if candidates else {
            "market": f"{home_name} or Draw (1X)", "sporty_market": "Double Chance 1X",
            "category": "Double Chance", "confidence": 75.0, "odds": 1.25, "market_type": "DC_1X"
        }

        if primary_rec["confidence"] >= 89.0:
            primary_rec["badge"] = "pill-green"
            primary_rec["tier"] = "Ultra Banker (≥89%)"
        elif primary_rec["confidence"] >= 78.0:
            primary_rec["badge"] = "pill-cyan"
            primary_rec["tier"] = "Solid Edge"
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

quant_engine = AntiOneCutEngine(home_advantage=1.15)

# =====================================================================
# 2. CONTINUOUS MULTI-SLIP ACCUMULATOR BUILDER (FIXES "SELECTIONS MADE")
# =====================================================================
def build_all_available_tickets(candidate_matches: list, target_odds: float):
    """
    Continually builds multiple slips from all remaining upcoming matches
    without dropping games or terminating after a single small slip.
    """
    all_picks = []
    for m in candidate_matches:
        if m["is_finished"]:
            continue
        for c
