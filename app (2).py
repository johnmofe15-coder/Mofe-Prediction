import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson

st.set_page_config(page_title="Universal Match Predictor", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOM CSS FOR DARK MODE / SPORTY THEME ---
st.markdown("""
    <style>
    .main { background-color: #0f172a; color: #f8fafc; }
    .stButton>button { background-color: #10b981; color: white; border-radius: 8px; font-weight: bold; width: 100%; border: none; }
    .stButton>button:hover { background-color: #059669; color: white; }
    .metric-card { background-color: #1e293b; border-radius: 10px; padding: 15px; border-left: 5px solid #10b981; margin-bottom: 10px; }
    div[data-testid="stExpander"] { background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

st.title("🎯 Universal Algorithmic Match Predictor")
st.caption("A pure mathematical inference engine utilizing Poisson Distribution & Exponential Weighting to spot market edges.")

# --- SIDEBAR: LEAGUE REGISTRY & MODEL HYPERPARAMETERS ---
with st.sidebar:
    st.header("⚙️ Engine Configuration")
    
    # Pre-populate with realistic benchmark data for testing before live API integration
    sport_type = st.radio("1. Select Sport Concept", ["Football (Low Scoring)", "Basketball (High Scoring)"])
    
    st.markdown("---")
    st.subheader("2. Model Parameters")
    form_weight = st.slider("Historical Form Weight (Recency Bias)", 0.1, 1.0, 0.7, step=0.05)
    home_advantage_mult = st.slider("Home Field Advantage Multiplier", 1.0, 1.5, 1.15, step=0.05)
    
    st.markdown("---")
    st.subheader("3. Market Filter")
    min_edge = st.slider("Minimum Required Market Edge (%)", 0.0, 15.0, 3.5, step=0.5)

# --- ENGINE ENGINE CORE MATHEMATICS ---
def calculate_poisson_probabilities(home_expected, away_expected, max_goals=6):
    """Calculates exact scoreline matrices using discrete Poisson distributions."""
    home_probs = [poisson.pmf(i, home_expected) for i in range(max_goals)]
    away_probs = [poisson.pmf(i, away_expected) for i in range(max_goals)]
    
    # Outer product to create score matrix
    score_matrix = np.outer(home_probs, away_probs)
    
    home_win_p = np.sum(np.tril(score_matrix, -1))
    draw_p = np.sum(np.diag(score_matrix))
    away_win_p = np.sum(np.triu(score_matrix, 1))
    
    # Over/Under 2.5 goals calculation
    under_25_p = score_matrix[0,0] + score_matrix[0,1] + score_matrix[0,2] + \
                 score_matrix[1,0] + score_matrix[1,1] + score_matrix[2,0]
    over_25_p = 1.0 - under_25_p
    
    return float(home_win_p), float(draw_p), float(away_win_p), float(over_25_p)

# --- HISTORICAL DATABASE (MOCK INGESTION LAYER) ---
# In production, replace this block with an API request to your data provider
def fetch_historical_baseline(sport):
    if "Football" in sport:
        # Columns: Team, Avg Goals Scored, Avg Goals Conceded
        data = {
            "Team": ["Arsenal", "Man City", "Liverpool", "Chelsea", "Man United", "Tottenham"],
            "Avg_Scored": [2.2, 2.4, 2.1, 1.8, 1.4, 1.7],
            "Avg_Conceded": [0.9, 1.0, 1.1, 1.4, 1.5, 1.6],
            "Bookie_Home_Odds": [1.65, 1.45, 1.80, 2.40, 2.90, 2.15]
        }
        league_avg_scored = 1.5
    else:
        # Basketball scaling (using scaled factor ratings to match Poisson domain boundaries)
        data = {
            "Team": ["Lakers", "Celtics", "Warriors", "Suns", "Bucks", "Heat"],
            "Avg_Scored": [4.2, 4.5, 4.3, 4.0, 3.9, 3.7],
            "Avg_Conceded": [3.9, 3.6, 4.1, 3.9, 3.8, 3.5],
            "Bookie_Home_Odds": [1.91, 1.40, 1.75, 2.10, 1.85, 2.30]
        }
        league_avg_scored = 4.0
        
    return pd.DataFrame(data), league_avg_scored

# --- RUN ENGINE PIPELINE ---
df_teams, league_avg = fetch_historical_baseline(sport_type)

st.subheader("🗓️ Today's Algorithmic Slate & Value Screener")

# Pairwise match engine generation
matches = [
    ("Arsenal", "Chelsea", df_teams.iloc[0], df_teams.iloc[3]),
    ("Man City", "Liverpool", df_teams.iloc[1], df_teams.iloc[2]),
    ("Man United", "Tottenham", df_teams.iloc[4], df_teams.iloc[5])
]

parsed_predictions = []

for home_name, away_name, home_stats, away_stats in matches:
    # 1. Fundamental Attack/Defense Matrix Modeling
    home_attack = home_stats["Avg_Scored"] / league_avg
    away_defense = away_stats["Avg_Conceded"] / league_avg
    away_attack = away_stats["Avg_Scored"] / league_avg
    home_defense = home_stats["Avg_Conceded"] / league_avg
    
    # 2. Apply Home Advantage Adjustments & Hyperparameters
    home_exp = home_attack * home_defense * league_avg * home_advantage_mult * form_weight
    away_exp = away_attack * away_defense * league_avg * (2.0 - home_advantage_mult) * form_weight
    
    # 3. Process Statistical Math Core
    h_win, draw, a_win, over_25 = calculate_poisson_probabilities(home_exp, away_exp)
    
    # 4. Market Price Calibration & Edge Calculation
    bookie_odds = home_stats["Bookie_Home_Odds"]
    implied_prob = 1 / bookie_odds
    edge = (h_win - implied_prob) * 100
    
    parsed_predictions.append({
        "Fixture": f"{home_name} vs {away_name}",
        "Model Home Win %": round(h_win * 100, 1),
        "Market Home Odds": bookie_odds,
        "Implied Probability %": round(implied_prob * 100, 1),
        "Calculated Edge %": round(edge, 1),
        "Proj. Scoreline": f"{round(home_exp,1)} - {round(away_exp,1)}",
        "Over 2.5 Goals %": round(over_25 * 100, 1)
    })

df_output = pd.DataFrame(parsed_predictions)

# Apply runtime UI filtering based on the configurations set in sidebar
df_filtered = df_output[df_output["Calculated Edge %"] >= min_edge]

if not df_filtered.empty:
    st.dataframe(
        df_filtered.style.background_gradient(subset=["Calculated Edge %"], cmap="YlGn"),
        use_container_width=True,
        hide_index=True
    )
    
    st.markdown("---")
    st.subheader("🔍 Individual Match Deep Dive Analysis")
    for _, row in df_filtered.iterrows():
        with st.expander(f"Analysis Breakdown: {row['Fixture']}"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Model Win Expectancy", f"{row['Model Home Win %']}%")
            with col2:
                st.metric("Quantified Alpha Edge", f"{row['Calculated Edge %']}%")
            with col3:
                st.metric("Expected Performance Score", row["Proj. Scoreline"])
else:
    st.warning("⚠️ High Volatility Detected: No fixtures currently present a mathematical edge matching your minimum criteria.")

st.markdown("<br><hr><center><small>System Running Pure Mathematical Inference Framework • No Gut Instincts</small></center>", unsafe_allow_html=True)
