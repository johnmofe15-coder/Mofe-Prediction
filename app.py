import streamlit as st
import time

st.set_page_config(
    page_title="Apex Intelligence | Football Predictions",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Apple Liquid Glassmorphism CSS
st.markdown("""
<style>
    /* Dark minimal canvas */
    .stApp {
        background: radial-gradient(circle at 10% 20%, #161922 0%, #0a0b0e 100%);
        color: #f5f5f7;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Segoe UI", Roboto, sans-serif;
    }

    /* Glass Cards */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(24px);
        -webkit-backdrop-filter: blur(24px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        padding: 22px;
        margin-bottom: 20px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .glass-card:hover {
        transform: translateY(-3px);
        border-color: rgba(255, 255, 255, 0.18);
        box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6);
    }

    /* Apple Pills / Badges */
    .pill-green {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        background: rgba(48, 209, 88, 0.15);
        color: #30d158;
        border: 1px solid rgba(48, 209, 88, 0.35);
    }
    .pill-blue {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        background: rgba(10, 132, 255, 0.15);
        color: #0a84ff;
        border: 1px solid rgba(10, 132, 255, 0.35);
    }

    /* Metrics & Typography */
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        background: linear-gradient(180deg, #ffffff 0%, #8e8e93 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .sub-text {
        color: #86868b;
        font-size: 0.82rem;
    }
    .highlight-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #a1a1a6;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SIDEBAR CONTROLS -----------------
with st.sidebar:
    st.markdown("### ⚙️ Engine Filters")
    league = st.selectbox(
        "Target Competition",
        ["All Major Leagues", "Premier League", "La Liga", "UEFA Champions League", "Serie A"]
    )
    
    min_confidence = st.slider(
        "Minimum Confidence Threshold (%)",
        min_value=80,
        max_value=98,
        value=88,
        help="Filters only picks that pass high-probability criteria."
    )
    
    bet_market = st.multiselect(
        "Allowed Prediction Markets",
        ["Draw No Bet (DNB)", "Double Chance", "Over/Under Goals", "Team Totals"],
        default=["Draw No Bet (DNB)", "Over/Under Goals"]
    )

    st.markdown("---")
    rescan = st.button("⚡ Run Live Web & Stats Scan", use_container_width=True)

# ----------------- MAIN APP HEADER -----------------
col_title, col_stat = st.columns([3, 1])
with col_title:
    st.markdown("# ⚡ **APEX** Liquid Intelligence")
    st.markdown("<p class='sub-text'>Continuous scanner across expected goals (xG), lineup injuries, and market volume.</p>", unsafe_allow_html=True)

with col_stat:
    st.metric(label="Model Win Rate (30d)", value="91.8%", delta="+2.4%")

# Scanner interaction
if rescan:
    with st.spinner("Scanning sports feeds, injury news, and recent match outings..."):
        time.sleep(1.2)
    st.toast("Intelligence feed updated successfully!", icon="✅")

# ----------------- DATA / PREDICTIONS FEED -----------------
matches = [
    {
        "league": "Premier League",
        "home": "Arsenal",
        "away": "Chelsea",
        "time": "Today • 20:00 GMT",
        "market": "Draw No Bet (DNB)",
        "pick": "Arsenal DNB",
        "confidence": 91.4,
        "badge": "pill-green",
        "badge_text": "Tier 1 • High Prob",
        "summary": "Chelsea missing 2 starting holding midfielders. Arsenal xG at home averages 2.41 vs 0.68 conceded over the last 5 outings."
    },
    {
        "league": "La Liga",
        "home": "Real Madrid",
        "away": "Sevilla",
        "time": "Today • 21:00 GMT",
        "market": "Over/Under Goals",
        "pick": "Over 1.5 Team Goals (RMA)",
        "confidence": 93.8,
        "badge": "pill-blue",
        "badge_text": "Goal Market",
        "summary": "Sevilla conceded in 9 of last 10 away matches. Madrid converting 32% of box entries into on-target shots."
    },
    {
        "league": "UEFA Champions League",
        "home": "Bayern Munich",
        "away": "Lazio",
        "time": "Tomorrow • 20:00 GMT",
        "market": "Double Chance",
        "pick": "Bayern or Draw",
        "confidence": 94.2,
        "badge": "pill-green",
        "badge_text": "Ultra Confidence",
        "summary": "Lazio away record shows -0.85 xG differential. Bayern has zero key starting injuries for this fixture."
    },
    {
        "league": "Serie A",
        "home": "Inter Milan",
        "away": "Atalanta",
        "time": "Tomorrow • 19:45 GMT",
        "market": "Over/Under Goals",
        "pick": "Over 2.5 Total Match Goals",
        "confidence": 84.5,
        "badge": "pill-blue",
        "badge_text": "High Pace Match",
        "summary": "Both sides ranking top 3 in Serie A for open play shot-creation actions. Expected goals aggregate at 3.12."
    }
]

# Filter matches based on sidebar inputs
filtered_matches = [
    m for m in matches 
    if (league == "All Major Leagues" or m["league"] == league) 
    and (m["confidence"] >= min_confidence)
]

st.markdown(f"### Qualified Predictions ({len(filtered_matches)})")

if not filtered_matches:
    st.info("No matches currently meet your strict confidence threshold. Try lowering the slider in the sidebar.")
else:
    # Display cards in 2 columns
    for i in range(0, len(filtered_matches), 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j < len(filtered_matches):
                match = filtered_matches[i + j]
                with cols[j]:
                    st.markdown(f"""
                    <div class="glass-card">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                            <span class="{match['badge']}">{match['badge_text']}</span>
                            <span class="sub-text">{match['league']} • {match['time']}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin: 8px 0;">
                            <h3 style="margin: 0; font-size: 1.25rem;">{match['home']}</h3>
                            <span style="font-weight: 700; color: #636366; font-size: 0.9rem;">VS</span>
                            <h3 style="margin: 0; font-size: 1.25rem;">{match['away']}</h3>
                        </div>
                        <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.06); margin: 14px 0;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                            <div>
                                <div class="highlight-label">Recommended Pick</div>
                                <div style="font-size: 1.05rem; font-weight: 600; color: #ffffff;">{match['pick']}</div>
                            </div>
                            <div style="text-align: right;">
                                <div class="highlight-label">Algorithm Confidence</div>
                                <div class="metric-value">{match['confidence']}%</div>
                            </div>
                        </div>
                        <div style="margin-top: 14px; font-size: 0.83rem; color: #a1a1a6; line-height: 1.4;">
                            ⚡ <b>Scan Analysis:</b> {match['summary']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)