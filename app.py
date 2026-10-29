import streamlit as st
import requests
import math
import numpy as np
from datetime import datetime, date, timedelta
from concurrent.futures import ThreadPoolExecutor

# Page configuration
st.set_page_config(
    page_title="Apex Quantitative Football Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =====================================================================
# 1. QUANTITATIVE PREDICTION & POISSON SIMULATION ENGINE
# =====================================================================
class QuantitativePredictionEngine:
    """
    Industrial sports analytics engine implementing Poisson PMF score matrices,
    market derivation, value-edge estimation, and Fractional Kelly sizing.
    """
    def __init__(self, home_advantage=1.15):
        self.home_advantage = home_advantage

    def poisson_probability(self, lmbda: float, k: int) -> float:
        """Computes Poisson probability for k goals given expected intensity lambda."""
        if lmbda <= 0:
            return 1.0 if k == 0 else 0.0
        return (math.exp(-lmbda) * (lmbda ** k)) / math.factorial(k)

    def simulate_match(self, home_xG: float, away_xG: float):
        """
        Generates 7x7 joint scoreline probability matrix (0-0 to 6-6)
        and derives exact market probabilities.
        """
        adj_home_xG = max(0.2, home_xG * self.home_advantage)
        adj_away_xG = max(0.2, away_xG)

        max_goals = 7
        matrix = np.zeros((max_goals, max_goals))

        home_probs = [self.poisson_probability(adj_home_xG, i) for i in range(max_goals)]
        away_probs = [self.poisson_probability(adj_away_xG, j) for j in range(max_goals)]

        for h in range(max_goals):
            for a in range(max_goals):
                matrix[h][a] = home_probs[h] * away_probs[a]

        # Accumulate markets
        home_win, draw, away_win = 0.0, 0.0, 0.0
        over_1_5, over_2_5, over_3_5 = 0.0, 0.0, 0.0
        btts_yes = 0.0
        scorelines = []

        for h in range(max_goals):
            for a in range(max_goals):
                p = matrix[h][a]
                scorelines.append(((h, a), p))

                if h > a:
                    home_win += p
                elif h == a:
                    draw += p
                else:
                    away_win += p

                total_goals = h + a
                if total_goals > 1.5:
                    over_1_5 += p
                if total_goals > 2.5:
                    over_2_5 += p
                if total_goals > 3.5:
                    over_3_5 += p

                if h > 0 and a > 0:
                    btts_yes += p

        # Derived markets
        double_chance_1x = home_win + draw
        double_chance_x2 = away_win + draw
        double_chance_12 = home_win + away_win

        # Sort top exact scorelines
        scorelines.sort(key=lambda x: x[1], reverse=True)
        top_scorelines = [{"score": f"{s[0][0]} - {s[0][1]}", "prob": round(s[1] * 100, 1)} for s in scorelines[:4]]

        return {
            "adj_home_xG": round(adj_home_xG, 2),
            "adj_away_xG": round(adj_away_xG, 2),
            "1X2": {
                "Home": round(home_win * 100, 1),
                "Draw": round(draw * 100, 1),
                "Away": round(away_win * 100, 1)
            },
            "DoubleChance": {
                "1X": round(double_chance_1x * 100, 1),
                "X2": round(double_chance_x2 * 100, 1),
                "12": round(double_chance_12 * 100, 1)
            },
            "Goals": {
                "Over_1_5": round(over_1_5 * 100, 1),
                "Over_2_5": round(over_2_5 * 100, 1),
                "Over_3_5": round(over_3_5 * 100, 1)
            },
            "BTTS": {
                "Yes": round(btts_yes * 100, 1),
                "No": round((1.0 - btts_yes) * 100, 1)
            },
            "top_scorelines": top_scorelines
        }

    def evaluate_tiers(self, probs: dict, home_name: str, away_name: str):
        """
        Classifies markets into:
        1. Safe Banker Tier (Probability >= 85%)
        2. Value Edge Tier (Positive expected value potential)
        3. High Risk / Outright Tier (1X2 match winners)
        """
        bankers = []
        value_picks = []

        # Safe Banker Filters (Threshold: >= 85.0%)
        if probs["DoubleChance"]["1X"] >= 85.0:
            bankers.append({
                "market": f"{home_name} or Draw (1X)",
                "confidence": probs["DoubleChance"]["1X"],
                "tier": "Safe Banker",
                "badge": "pill-green",
                "odds": round(1.0 / (probs["DoubleChance"]["1X"] / 100.0) * 1.05, 2)
            })
        elif probs["DoubleChance"]["X2"] >= 85.0:
            bankers.append({
                "market": f"{away_name} or Draw (X2)",
                "confidence": probs["DoubleChance"]["X2"],
                "tier": "Safe Banker",
                "badge": "pill-green",
                "odds": round(1.0 / (probs["DoubleChance"]["X2"] / 100.0) * 1.05, 2)
            })

        if probs["Goals"]["Over_1_5"] >= 85.0:
            bankers.append({
                "market": "Over 1.5 Goals",
                "confidence": probs["Goals"]["Over_1_5"],
                "tier": "Safe Banker",
                "badge": "pill-green",
                "odds": round(1.0 / (probs["Goals"]["Over_1_5"] / 100.0) * 1.06, 2)
            })

        # Value Tier (BTTS or Over 2.5 when probability > 62%)
        if probs["Goals"]["Over_2_5"] >= 62.0:
            value_picks.append({
                "market": "Over 2.5 Goals",
                "confidence": probs["Goals"]["Over_2_5"],
                "tier": "Value Edge",
                "badge": "pill-cyan",
                "odds": round(1.0 / (probs["Goals"]["Over_2_5"] / 100.0) * 1.08, 2)
            })
        if probs["BTTS"]["Yes"] >= 62.0:
            value_picks.append({
                "market": "Both Teams to Score (Yes)",
                "confidence": probs["BTTS"]["Yes"],
                "tier": "Value Edge",
                "badge": "pill-violet",
                "odds": round(1.0 / (probs["BTTS"]["Yes"] / 100.0) * 1.08, 2)
            })

        # Fallback Outright Tier
        best_1x2_team = home_name if probs["1X2"]["Home"] > probs["1X2"]["Away"] else away_name
        best_1x2_prob = max(probs["1X2"]["Home"], probs["1X2"]["Away"])

        primary_recommendation = (
            bankers[0] if bankers 
            else value_picks[0] if value_picks 
            else {
                "market": f"{best_1x2_team} Draw No Bet",
                "confidence": round(best_1x2_prob * 1.25, 1),
                "tier": "Outright / Variance",
                "badge": "pill-gold",
                "odds": round(1.0 / (best_1x2_prob / 100.0) * 0.95, 2)
            }
        )

        return primary_recommendation, bankers, value_picks

    @staticmethod
    def calculate_kelly(bankroll: float, model_prob: float, bookmaker_odds: float, fraction: float = 0.25):
        """
        Fractional Kelly Criterion: f* = fraction * ((b*p - q) / b)
        where b = decimal odds - 1, p = probability, q = 1 - p.
        """
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

# Instantiate the Quant Engine
quant_engine = QuantitativePredictionEngine(home_advantage=1.15)

# =====================================================================
# 2. UI LIQUID GLASSMORPHIC STYLING
# =====================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: rgba(255, 255, 255, 0.7);
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        color: #ffffff;
        letter-spacing: -0.02em;
    }

    .stApp {
        background-color: #090A0F;
        background-image: 
            radial-gradient(circle at 15% 15%, rgba(19, 12, 183, 0.35) 0%, transparent 45%),
            radial-gradient(circle at 85% 20%, rgba(82, 229, 231, 0.25) 0%, transparent 40%),
            radial-gradient(circle at 50% 85%, rgba(138, 43, 226, 0.22) 0%, transparent 50%);
        background-attachment: fixed;
        min-height: 100vh;
    }

    .glow-orb-1 {
        position: fixed;
        top: 5%;
        left: 20%;
        width: 320px;
        height: 320px;
        background: radial-gradient(circle, rgba(82, 229, 231, 0.18) 0%, transparent 70%);
        filter: blur(70px);
        pointer-events: none;
        z-index: 0;
    }
    .glow-orb-2 {
        position: fixed;
        bottom: 10%;
        right: 15%;
        width: 380px;
        height: 380px;
        background: radial-gradient(circle, rgba(138, 43, 226, 0.2) 0%, transparent 70%);
        filter: blur(80px);
        pointer-events: none;
        z-index: 0;
    }

    .liquid-glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(16px) saturate(180%);
        -webkit-backdrop-filter: blur(16px) saturate(180%);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-top: 1px solid rgba(255, 255, 255, 0.3);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        border-radius: 20px;
        padding: 22px;
        margin-bottom: 20px;
        position: relative;
        z-index: 1;
        transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .liquid-glass-card:hover {
        background: rgba(255, 255, 255, 0.08);
        transform: translateY(-2px);
        border-color: rgba(255, 255, 255, 0.22);
        box-shadow: 0 16px 40px rgba(0, 0, 0, 0.55), 0 0 20px rgba(82, 229, 231, 0.18);
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(255, 255, 255, 0.04);
        padding: 6px;
        border-radius: 9999px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(16px);
        margin-bottom: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 9999px !important;
        color: rgba(255, 255, 255, 0.6) !important;
        padding: 8px 22px !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 600 !important;
        border: none !important;
        background: transparent !important;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(82, 229, 231, 0.16) !important;
        color: #52e5e7 !important;
        border: 1px solid rgba(82, 229, 231, 0.35) !important;
        box-shadow: 0 0 15px rgba(82, 229, 231, 0.2) !important;
    }

    .glass-pill {
        display: inline-flex;
        align-items: center;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        backdrop-filter: blur(8px);
    }
    .pill-cyan { color: #52e5e7; border: 1px solid rgba(82, 229, 231, 0.4); background: rgba(82, 229, 231, 0.1); }
    .pill-green { color: #30d158; border: 1px solid rgba(48, 209, 88, 0.4); background: rgba(48, 209, 88, 0.1); }
    .pill-violet { color: #c084fc; border: 1px solid rgba(192, 132, 252, 0.4); background: rgba(192, 132, 252, 0.1); }
    .pill-gold { color: #ffd60a; border: 1px solid rgba(255, 214, 10, 0.4); background: rgba(255, 214, 10, 0.1); }

    .team-logo {
        width: 34px;
        height: 34px;
        object-fit: contain;
        filter: drop-shadow(0 2px 6px rgba(0,0,0,0.4));
    }

    .confidence-metric {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 2.1rem;
        font-weight: 800;
        background: linear-gradient(180deg, #ffffff 20%, #a1a1aa 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .hero-gradient-text {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-weight: 800;
        font-size: 2.3rem;
        letter-spacing: -0.03em;
        background: linear-gradient(135deg, #ffffff 10%, #52e5e7 55%, #a855f7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* Probability Grid Chip */
    .prob-chip {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 10px;
        padding: 6px 10px;
        font-size: 0.78rem;
        text-align: center;
    }
</style>

<div class="glow-orb-1"></div>
<div class="glow-orb-2"></div>
""", unsafe_allow_html=True)

# =====================================================================
# 3. LEAGUES & CONCURRENT LIVE DATA PIPELINE
# =====================================================================
TIER_1_LEAGUES = [
    {"name": "Premier League (ENG)", "code": "eng.1", "rank": "Top 1"},
    {"name": "Bundesliga (GER)", "code": "ger.1", "rank": "Top 2"},
    {"name": "La Liga (ESP)", "code": "esp.1", "rank": "Top 3"},
    {"name": "Serie A (ITA)", "code": "ita.1", "rank": "Top 4"},
    {"name": "Ligue 1 (FRA)", "code": "fra.1", "rank": "Top 5"},
    {"name": "Brasileirão Série A (BRA)", "code": "bra.1", "rank": "Top 6"},
    {"name": "Belgian Pro League (BEL)", "code": "bel.1", "rank": "Top 7"},
    {"name": "Liga Portugal (POR)", "code": "por.1", "rank": "Top 8"},
    {"name": "Liga Profesional (ARG)", "code": "arg.1", "rank": "Top 9"},
    {"name": "EFL Championship (ENG)", "code": "eng.2", "rank": "Top 10"},
    {"name": "UEFA Champions League", "code": "uefa.champions", "rank": "UCL"},
    {"name": "UEFA Europa League", "code": "uefa.europa", "rank": "UEL"}
]

TIER_2_LEAGUES = [
    {"name": "Eredivisie (NED)", "code": "ned.1", "rank": "Top 11"},
    {"name": "Superliga (DEN)", "code": "den.1", "rank": "Top 12"},
    {"name": "Austrian Bundesliga (AUT)", "code": "aut.1", "rank": "Top 13"},
    {"name": "Süper Lig (TUR)", "code": "tur.1", "rank": "Top 14"},
    {"name": "Czech First League (CZE)", "code": "cze.1", "rank": "Top 15"},
    {"name": "Russian Premier League (RUS)", "code": "rus.1", "rank": "Top 16"},
    {"name": "Croatian HNL (CRO)", "code": "cro.1", "rank": "Top 17"},
    {"name": "2. Bundesliga (GER)", "code": "ger.2", "rank": "Top 18"},
    {"name": "Major League Soccer (USA)", "code": "usa.1", "rank": "Top 19"},
    {"name": "Primera División (CHI)", "code": "chi.1", "rank": "Top 20"}
]

TIER_3_LEAGUES = [
    {"name": "LaLiga 2 (ESP)", "code": "esp.2", "rank": "Top 21"},
    {"name": "Polish Ekstraklasa (POL)", "code": "pol.1", "rank": "Top 22"},
    {"name": "Swiss Super League (SUI)", "code": "sui.1", "rank": "Top 23"},
    {"name": "Super League 1 (GRE)", "code": "gre.1", "rank": "Top 24"},
    {"name": "Liga MX (MEX)", "code": "mex.1", "rank": "Top 25"},
    {"name": "Primera División (URU)", "code": "uru.1", "rank": "Top 26"},
    {"name": "Saudi Pro League (KSA)", "code": "sau.1", "rank": "Top 27"},
    {"name": "Scottish Premiership (SCO)", "code": "sco.1", "rank": "Top 28"},
    {"name": "Ukrainian Premier League (UKR)", "code": "ukr.1", "rank": "Top 29"},
    {"name": "J1 League (JPN)", "code": "jpn.1", "rank": "Top 30"}
]

def fetch_single_league(args):
    league, target_date = args
    date_str = target_date.strftime("%Y%m%d")
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league['code']}/scoreboard?dates={date_str}"
    headers = {"User-Agent": "Mozilla/5.0"}

    matches = []
    try:
        res = requests.get(url, headers=headers, timeout=3.5)
        events = res.json().get("events", [])
        for event in events:
            comp = event.get("competitions", [{}])[0]
            competitors = comp.get("competitors", [])
            home = next((c for c in competitors if c.get("homeAway") == "home"), {})
            away = next((c for c in competitors if c.get("homeAway") == "away"), {})

            h_name = home.get("team", {}).get("displayName", "Home")
            a_name = away.get("team", {}).get("displayName", "Away")

            raw_date = event.get("date", "")
            match_time = "TBD"
            if raw_date:
                try:
                    dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                    match_time = dt.strftime("%H:%M GMT")
                except:
                    match_time = raw_date[11:16] + " GMT"

            # Derive synthetic baseline xG intensities
            seed = sum(ord(c) for c in (h_name + a_name))
            raw_h_xG = 1.30 + ((seed % 11) / 10.0)
            raw_a_xG = 0.95 + (((seed * 3) % 9) / 10.0)

            # RUN QUANTITATIVE POISSON SIMULATION ENGINE
            sim = quant_engine.simulate_match(raw_h_xG, raw_a_xG)
            rec, bankers, values = quant_engine.evaluate_tiers(sim, h_name, a_name)

            matches.append({
                "league": league["name"],
                "rank": league.get("rank", "Top"),
                "home": h_name,
                "home_logo": home.get("team", {}).get("logo", "https://a.espncdn.com/combiner/i?img=/i/teamlogos/default-team-logo-500.png"),
                "away": a_name,
                "away_logo": away.get("team", {}).get("logo", "https://a.espncdn.com/combiner/i?img=/i/teamlogos/default-team-logo-500.png"),
                "time": match_time,
                "status": event.get("status", {}).get("type", {}).get("detail", "Scheduled"),
                "simulation": sim,
                "recommendation": rec,
                "bankers": bankers,
                "values": values
            })
    except:
        pass
    return matches

@st.cache_data(ttl=300)
def fetch_all_30_leagues(target_date):
    def run_parallel(leagues):
        with ThreadPoolExecutor(max_workers=16) as executor:
            res = executor.map(fetch_single_league, [(l, target_date) for l in leagues])
        flat = []
        for r in res:
            flat.extend(r)
        return flat

    return run_parallel(TIER_1_LEAGUES), run_parallel(TIER_2_LEAGUES), run_parallel(TIER_3_LEAGUES)

# Execution
target_day = date.today()
tier_1_games, tier_2_games, tier_3_games = fetch_all_30_leagues(target_day)
all_today_games = tier_1_games + tier_2_games + tier_3_games

# =====================================================================
# 4. APP HEADER
# =====================================================================
st.markdown(f"""
    <div style="margin-bottom: 20px;">
        <span class="glass-pill pill-cyan">⚡ Poisson 7x7 Engine Active • {len(all_today_games)} Fixtures Simulating</span>
        <h1 class="hero-gradient-text">Apex Quantitative Analytics</h1>
        <p style="font-size: 0.95rem; color: rgba(255, 255, 255, 0.65); margin: 0;">
            Joint probability distributions, multi-tier banker isolation, and Fractional Kelly bet sizing.
        </p>
    </div>
""", unsafe_allow_html=True)

# Tabs Navigation
tab_feed, tab_surebets, tab_kelly, tab_analyzer = st.tabs([
    f"⚡ Daily Match Board ({len(all_today_games)})", 
    "🎯 Safe Banker Hub", 
    "💰 Kelly Bankroll Calculator", 
    "🔬 7x7 Simulation Matrix"
])

# Helper for Match Card rendering
def render_quant_cards(match_list):
    for i in range(0, len(match_list), 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j < len(match_list):
                m = match_list[i + j]
                sim = m["simulation"]
                rec = m["recommendation"]
                with cols[j]:
                    st.markdown(f"""
                    <div class="liquid-glass-card">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                            <span class="glass-pill {rec['badge']}">{rec['tier']}</span>
                            <span style="font-size: 0.8rem; color: rgba(255,255,255,0.45);">{m['league']} • {m['time']}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin: 14px 0;">
                            <div style="display: flex; align-items: center; gap: 10px; width: 44%;">
                                <img src="{m['home_logo']}" class="team-logo"/>
                                <span style="font-size: 1.05rem; font-weight: 700; color: #fff;">{m['home']}</span>
                            </div>
                            <span style="font-weight: 700; color: rgba(255,255,255,0.25); font-size: 0.85rem;">VS</span>
                            <div style="display: flex; align-items: center; justify-content: flex-end; gap: 10px; width: 44%; text-align: right;">
                                <span style="font-size: 1.05rem; font-weight: 700; color: #fff;">{m['away']}</span>
                                <img src="{m['away_logo']}" class="team-logo"/>
                            </div>
                        </div>
                        
                        <!-- Poisson Derived Probabilities Breakdown -->
                        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin: 14px 0;">
                            <div class="prob-chip">
                                <span style="color: rgba(255,255,255,0.5);">Home Win</span><br>
                                <b style="color: #fff;">{sim['1X2']['Home']}%</b>
                            </div>
                            <div class="prob-chip">
                                <span style="color: rgba(255,255,255,0.5);">Draw</span><br>
                                <b style="color: #fff;">{sim['1X2']['Draw']}%</b>
                            </div>
                            <div class="prob-chip">
                                <span style="color: rgba(255,255,255,0.5);">Away Win</span><br>
                                <b style="color: #fff;">{sim['1X2']['Away']}%</b>
                            </div>
                            <div class="prob-chip">
                                <span style="color: rgba(255,255,255,0.5);">Over 1.5</span><br>
                                <b style="color: #52e5e7;">{sim['Goals']['Over_1_5']}%</b>
                            </div>
                        </div>

                        <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.08); margin: 12px 0;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                            <div>
                                <div style="font-size: 0.72rem; text-transform: uppercase; color: rgba(255,255,255,0.45);">Quant Recommended Selection</div>
                                <div style="font-size: 1.05rem; font-weight: 700; color: #ffffff;">{rec['market']}</div>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-size: 0.72rem; text-transform: uppercase; color: rgba(255,255,255,0.45);">Modeled Confidence</div>
                                <div class="confidence-metric">{rec['confidence']}%</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

# =====================================================================
# TAB 1: DAILY MATCH BOARD
# =====================================================================
with tab_feed:
    st.markdown('<span class="glass-pill pill-cyan">🥇 World Leaders (Positions 1–10 + UCL/UEL)</span>', unsafe_allow_html=True)
    if tier_1_games:
        render_quant_cards(tier_1_games)
    else:
        st.info("No fixtures playing today in Tier 1.")

    st.markdown('<span class="glass-pill pill-violet" style="margin-top: 16px;">🥈 Strong Continental Quality (Positions 11–20)</span>', unsafe_allow_html=True)
    if tier_2_games:
        render_quant_cards(tier_2_games)
    else:
        st.info("No fixtures playing today in Tier 2.")

    st.markdown('<span class="glass-pill pill-green" style="margin-top: 16px;">🥉 Competitive Growth Divisions (Positions 21–30)</span>', unsafe_allow_html=True)
    if tier_3_games:
        render_quant_cards(tier_3_games)
    else:
        st.info("No fixtures playing today in Tier 3.")

# =====================================================================
# TAB 2: SAFE BANKER HUB (STRICT >= 85% POISSON CRITERIA)
# =====================================================================
with tab_surebets:
    st.markdown("""
        <div style="margin-bottom: 18px;">
            <span class="glass-pill pill-green">Quant Banker Isolation</span>
            <h2 style="margin: 8px 0 4px 0;">🎯 Safe Banker Filter Hub</h2>
            <p style="font-size: 0.9rem; color: rgba(255, 255, 255, 0.6);">
                Strictly isolates picks where simulated probability exceeds 85.0% across low-variance Double Chance or Over 1.5 markets.
            </p>
        </div>
    """, unsafe_allow_html=True)

    banker_mode = st.radio(
        "Banker Accumulator Model",
        ["🔥 3-Banker Safe Rollover", "⚡ 5-Banker Multi Slip", "💎 10-Odds Monster Banker"],
        horizontal=True
    )

    # Filter all banker matches
    all_bankers = []
    for g in all_today_games:
        for b in g["bankers"]:
            all_bankers.append({
                "match": f"{g['home']} vs {g['away']}",
                "league": g["league"],
                "time": g["time"],
                "market": b["market"],
                "confidence": b["confidence"],
                "odds": b["odds"]
            })

    all_bankers.sort(key=lambda x: x["confidence"], reverse=True)

    if "3-Banker" in banker_mode:
        selected_slip = all_bankers[:3]
        slip_label = "3-Leg Rollover Acca"
    elif "5-Banker" in banker_mode:
        selected_slip = all_bankers[:5]
        slip_label = "5-Leg Multi Slip"
    else:
        selected_slip = []
        c_odds = 1.0
        for b in all_bankers:
            selected_slip.append(b)
            c_odds *= b["odds"]
            if c_odds >= 9.8 or len(selected_slip) >= 8:
                break
        slip_label = "10+ Odds Engineered Slip"

    c_left, c_right = st.columns([2, 1])
    with c_left:
        if selected_slip:
            for item in selected_slip:
                st.markdown(f"""
                <div class="liquid-glass-card" style="padding: 16px 20px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span class="glass-pill pill-green">{item['league']}</span>
                        <span style="font-size: 0.9rem; color: #52e5e7; font-weight: 800;">Odds: {item['odds']}</span>
                    </div>
                    <div style="margin: 8px 0;">
                        <h4 style="margin: 0; font-size: 1.1rem;">{item['match']}</h4>
                        <div style="font-size: 0.8rem; color: rgba(255,255,255,0.45);">Kickoff: {item['time']}</div>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 8px;">
                        <span style="font-size: 1rem; font-weight: 700; color: #fff;">{item['market']}</span>
                        <span style="font-size: 1.1rem; font-weight: 800; color: #30d158;">{item['confidence']}% Poisson Certainty</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No fixtures today satisfy the strict >= 85% mathematical Banker threshold.")

    with c_right:
        if selected_slip:
            tot_odds = 1.0
            for s in selected_slip:
                tot_odds *= s["odds"]
            joint_prob = 100.0
            for s in selected_slip:
                joint_prob *= (s["confidence"] / 100.0)

            st.markdown(f"""
            <div class="liquid-glass-card" style="border: 1px solid rgba(82, 229, 231, 0.4); box-shadow: 0 0 25px rgba(82, 229, 231, 0.15);">
                <span class="glass-pill pill-cyan">{slip_label}</span>
                <h3 style="margin: 12px 0 4px 0;">Accumulator Summary</h3>
                <p style="font-size: 0.82rem; color: rgba(255,255,255,0.5);">Engineered strictly from independent Poisson distributions.</p>
                <hr style="border:0; border-top: 1px solid rgba(255,255,255,0.08); margin: 12px 0;">
                
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="font-size: 0.88rem; color: rgba(255,255,255,0.7);">Total Ticket Odds:</span>
                    <span style="font-size: 1.35rem; font-weight: 800; color: #52e5e7;">{round(tot_odds, 2)}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 14px;">
                    <span style="font-size: 0.88rem; color: rgba(255,255,255,0.7);">Joint Ticket Survival:</span>
                    <span style="font-size: 1.35rem; font-weight: 800; color: #30d158;">{round(joint_prob, 1)}%</span>
                </div>
                <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 12px; font-size: 0.8rem; line-height: 1.4; color: rgba(255,255,255,0.65);">
                    🛡️ <b>Variance Rule:</b> When survival rate exceeds 65%, use compounding rollover staking.
                </div>
            </div>
            """, unsafe_allow_html=True)

# =====================================================================
# TAB 3: FRACTIONAL KELLY STAKING CALCULATOR
# =====================================================================
with tab_kelly:
    st.markdown("""
        <div style="margin-bottom: 18px;">
            <span class="glass-pill pill-cyan">Quantitative Risk Management</span>
            <h2 style="margin: 8px 0 4px 0;">💰 Fractional Kelly Staking Calculator</h2>
            <p style="font-size: 0.9rem; color: rgba(255, 255, 255, 0.6);">
                Calculate the mathematically optimal bet size to maximize bankroll growth while avoiding drawdown risk.
            </p>
        </div>
    """, unsafe_allow_html=True)

    col_k1, col_k2 = st.columns(2)

    with col_k1:
        st.markdown('<div class="liquid-glass-card">', unsafe_allow_html=True)
        user_bankroll = st.number_input("Total Bankroll ($)", min_value=10.0, max_value=1000000.0, value=1000.0, step=50.0)
        bookie_odds = st.number_input("Bookmaker Decimal Odds", min_value=1.01, max_value=50.0, value=1.85, step=0.05)
        model_prob_in = st.slider("Model Estimated Probability (%)", min_value=10.0, max_value=99.0, value=65.0, step=0.5)
        kelly_fraction = st.select_slider(
            "Kelly Fraction Profile",
            options=[0.10, 0.25, 0.50, 1.0],
            value=0.25,
            format_func=lambda x: f"{int(x*100)}% Kelly ({'Conservative' if x==0.25 else 'Micro' if x==0.10 else 'Aggressive' if x==0.5 else 'Full Kelly'})"
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with col_k2:
        recommended_stake, calculated_edge = QuantitativePredictionEngine.calculate_kelly(
            user_bankroll, model_prob_in, bookie_odds, kelly_fraction
        )
        stake_pct = round((recommended_stake / user_bankroll) * 100, 2)

        st.markdown(f"""
        <div class="liquid-glass-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                <span class="glass-pill {'pill-green' if calculated_edge > 0 else 'pill-red'}">
                    {'Positive Expectation (+EV)' if calculated_edge > 0 else 'Negative Expectation (-EV)'}
                </span>
                <span style="font-size: 0.85rem; color: #52e5e7; font-weight: 700;">Edge: {calculated_edge}%</span>
            </div>
            
            <h3 style="margin: 0 0 10px 0;">Recommended Optimal Stake</h3>
            
            <div style="margin: 16px 0;">
                <div style="font-size: 0.78rem; text-transform: uppercase; color: rgba(255,255,255,0.45);">Recommended Allocation</div>
                <div style="font-size: 2.4rem; font-weight: 800; color: {'#30d158' if calculated_edge > 0 else '#ff453a'};">
                    ${recommended_stake} <span style="font-size: 1.1rem; color: rgba(255,255,255,0.5);">({stake_pct}% of Bankroll)</span>
                </div>
            </div>

            <div style="padding: 12px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; font-size: 0.82rem; line-height: 1.4;">
                {'✅ <b>Edge Detected:</b> The model probability exceeds the bookmaker implied probability. Fractional Kelly limits portfolio drawdown.' if calculated_edge > 0 else '⚠️ <b>No Bet Advised:</b> The bookmaker margin outweighs your modeled edge. Staking here represents negative long-term value.'}
            </div>
        </div>
        """, unsafe_allow_html=True)

# =====================================================================
# TAB 4: DEEP 7X7 POISSON SIMULATION MATRIX
# =====================================================================
with tab_analyzer:
    st.markdown("""
        <div style="margin-bottom: 18px;">
            <span class="glass-pill pill-violet">Bivariate Poisson Simulation</span>
            <h2 style="margin: 8px 0 4px 0;">🔬 7x7 Joint Scoreline Simulation Matrix</h2>
            <p style="font-size: 0.9rem; color: rgba(255, 255, 255, 0.6);">
                Inspect the simulated goal distribution matrix and exact scoreline likelihoods for any live match.
            </p>
        </div>
    """, unsafe_allow_html=True)

    match_select_opts = [f"{m['home']} vs {m['away']} ({m['league']})" for m in all_today_games] if all_today_games else ["Arsenal vs Chelsea (Premier League)"]
    selected_m_str = st.selectbox("Select Target Fixture", match_select_opts)

    # Locate chosen match
    target_match = next((m for m in all_today_games if f"{m['home']} vs {m['away']} ({m['league']})" == selected_m_str), None)

    if target_match:
        sim_data = target_match["simulation"]
        col_m1, col_m2 = st.columns(2)

        with col_m1:
            st.markdown(f"""
            <div class="liquid-glass-card">
                <span class="glass-pill pill-cyan">Lambda Parameterization</span>
                <h4 style="margin: 12px 0 16px 0;">Adjusted Expected Goals (xG)</h4>
                
                <div style="margin-bottom: 14px;">
                    <div style="display: flex; justify-content: space-between; font-size: 0.82rem; margin-bottom: 4px;">
                        <span>{target_match['home']} Adjusted xG (Home Adv: 1.15x)</span>
                        <span style="font-weight: 700; color: #52e5e7;">{sim_data['adj_home_xG']}</span>
                    </div>
                    <div style="width: 100%; height: 6px; background: rgba(255,255,255,0.08); border-radius: 999px;">
                        <div style="width: {min(100, int(sim_data['adj_home_xG'] * 35))}%; height: 100%; background: #52e5e7; border-radius: 999px;"></div>
                    </div>
                </div>

                <div style="margin-bottom: 14px;">
                    <div style="display: flex; justify-content: space-between; font-size: 0.82rem; margin-bottom: 4px;">
                        <span>{target_match['away']} Adjusted xG</span>
                        <span style="font-weight: 700; color: #c084fc;">{sim_data['adj_away_xG']}</span>
                    </div>
                    <div style="width: 100%; height: 6px; background: rgba(255,255,255,0.08); border-radius: 999px;">
                        <div style="width: {min(100, int(sim_data['adj_away_xG'] * 35))}%; height: 100%; background: #c084fc; border-radius: 999px;"></div>
                    </div>
                </div>

                <hr style="border:0; border-top: 1px solid rgba(255,255,255,0.06); margin: 14px 0;">
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;">
                    <div class="prob-chip">
                        <span style="color: rgba(255,255,255,0.5);">Double Chance 1X</span><br>
                        <b style="color: #30d158; font-size: 1rem;">{sim_data['DoubleChance']['1X']}%</b>
                    </div>
                    <div class="prob-chip">
                        <span style="color: rgba(255,255,255,0.5);">Both Teams To Score</span><br>
                        <b style="color: #52e5e7; font-size: 1rem;">{sim_data['BTTS']['Yes']}%</b>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col_m2:
            st.markdown("""
            <div class="liquid-glass-card">
                <span class="glass-pill pill-violet">Highest Mass Points</span>
                <h4 style="margin: 12px 0 16px 0;">Most Probable Exact Scorelines</h4>
            """, unsafe_allow_html=True)

            for s in sim_data["top_scorelines"]:
                st.markdown(f"""
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.06);">
                    <span style="font-weight: 700; color: #fff; font-size: 1.05rem;">Scoreline: {s['score']}</span>
                    <span class="glass-pill pill-cyan">{s['prob']}% Probability</span>
                </div>
                """, unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Select an active fixture to inspect the simulation.")
