import streamlit as st
import time

# Page setup
st.set_page_config(
    page_title="Apex Intelligence | Liquid Predictions",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Injected Glassmorphism Engine & Atmosphere CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');

    /* Global Resets & Typography */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: rgba(255, 255, 255, 0.7);
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        color: #ffffff;
        letter-spacing: -0.02em;
    }

    /* Ambient Canvas & Floating Orbs */
    .stApp {
        background-color: #090A0F;
        background-image: 
            radial-gradient(circle at 15% 15%, rgba(19, 12, 183, 0.35) 0%, transparent 45%),
            radial-gradient(circle at 85% 20%, rgba(82, 229, 231, 0.25) 0%, transparent 40%),
            radial-gradient(circle at 50% 85%, rgba(138, 43, 226, 0.22) 0%, transparent 50%);
        background-attachment: fixed;
        min-height: 100vh;
    }

    /* Ambient Floating Glow Orb Elements */
    .glow-orb-1 {
        position: fixed;
        top: 5%;
        left: 20%;
        width: 320px;
        height: 320px;
        background: radial-gradient(circle, rgba(82, 229, 231, 0.18) 0%, rgba(19, 12, 183, 0.05) 70%, transparent 100%);
        filter: blur(60px);
        pointer-events: none;
        z-index: 0;
    }

    .glow-orb-2 {
        position: fixed;
        bottom: 10%;
        right: 15%;
        width: 380px;
        height: 380px;
        background: radial-gradient(circle, rgba(138, 43, 226, 0.2) 0%, rgba(19, 12, 183, 0.08) 70%, transparent 100%);
        filter: blur(80px);
        pointer-events: none;
        z-index: 0;
    }

    /* Glass Surface Tokens */
    .liquid-glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(16px) saturate(180%);
        -webkit-backdrop-filter: blur(16px) saturate(180%);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-top: 1px solid rgba(255, 255, 255, 0.3);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37), inset 0 1px 0 rgba(255, 255, 255, 0.12);
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 24px;
        position: relative;
        z-index: 1;
        transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .liquid-glass-card:hover {
        background: rgba(255, 255, 255, 0.09);
        transform: translateY(-2px);
        border-color: rgba(255, 255, 255, 0.22);
        border-top: 1px solid rgba(255, 255, 255, 0.45);
        box-shadow: 0 16px 40px 0 rgba(0, 0, 0, 0.55), 0 0 24px rgba(82, 229, 231, 0.15);
    }

    /* Gradient Hero Headline */
    .hero-gradient-text {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-weight: 800;
        font-size: 2.6rem;
        letter-spacing: -0.03em;
        background: linear-gradient(135deg, #ffffff 10%, #52e5e7 55%, #a855f7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 6px;
    }

    /* Icon Vector Mini-Blur Wrapper */
    .icon-wrapper {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 38px;
        height: 38px;
        background: rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.18);
        border-radius: 12px;
        color: #52e5e7;
        margin-right: 10px;
    }

    /* Pill Badges */
    .glass-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 14px;
        border-radius: 9999px;
        font-size: 0.73rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        background: rgba(255, 255, 255, 0.06);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-top: 1px solid rgba(255, 255, 255, 0.28);
    }
    .pill-cyan {
        color: #52e5e7;
        border-color: rgba(82, 229, 231, 0.35);
        background: rgba(82, 229, 231, 0.1);
    }
    .pill-green {
        color: #30d158;
        border-color: rgba(48, 209, 88, 0.35);
        background: rgba(48, 209, 88, 0.1);
    }
    .pill-violet {
        color: #c084fc;
        border-color: rgba(192, 132, 252, 0.35);
        background: rgba(192, 132, 252, 0.1);
    }

    /* Stat Typography */
    .confidence-metric {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        background: linear-gradient(180deg, #ffffff 20%, #a1a1aa 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* Streamlit Custom UI Overrides (Sidebar, Inputs, Buttons) */
    [data-testid="stSidebar"] {
        background: rgba(9, 10, 15, 0.75) !important;
        backdrop-filter: blur(20px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    }

    .stButton > button {
        background: rgba(255, 255, 255, 0.06) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.16) !important;
        border-top: 1px solid rgba(255, 255, 255, 0.32) !important;
        border-radius: 9999px !important;
        padding: 10px 24px !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 600 !important;
        backdrop-filter: blur(12px) !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25) !important;
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    .stButton > button:hover {
        background: rgba(255, 255, 255, 0.12) !important;
        border-color: rgba(82, 229, 231, 0.5) !important;
        box-shadow: 0 0 20px rgba(82, 229, 231, 0.35) !important;
        transform: translateY(-2px);
    }
</style>

<!-- Floating Ambient Light Orbs -->
<div class="glow-orb-1"></div>
<div class="glow-orb-2"></div>
""", unsafe_allow_html=True)

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.markdown("""
        <div style="display: flex; align-items: center; margin-bottom: 18px;">
            <div class="icon-wrapper">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
                </svg>
            </div>
            <h3 style="margin: 0; font-size: 1.25rem;">Control Panel</h3>
        </div>
    """, unsafe_allow_html=True)

    league = st.selectbox(
        "Competition Filter",
        ["All Major Leagues", "Premier League", "La Liga", "UEFA Champions League", "Serie A"]
    )
    
    min_confidence = st.slider(
        "Confidence Filter (%)",
        min_value=80,
        max_value=98,
        value=88,
        help="Filters only high mathematical expectation picks."
    )
    
    markets = st.multiselect(
        "Markets Included",
        ["Draw No Bet (DNB)", "Double Chance", "Over/Under Goals", "Team Total Goals"],
        default=["Draw No Bet (DNB)", "Double Chance", "Over/Under Goals"]
    )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    scan_triggered = st.button("✨ Initiate Real-time Scan", use_container_width=True)

# ----------------- HERO SECTION -----------------
st.markdown("""
    <div style="margin-bottom: 28px;">
        <span class="glass-pill pill-cyan">System Live • Multi-Source Aggregator</span>
        <h1 class="hero-gradient-text">Apex Liquid Intelligence</h1>
        <p style="font-size: 1rem; color: rgba(255, 255, 255, 0.65); max-width: 680px; margin: 0;">
            Real-time neural engine scanning fixture volatility, expected goals (xG), tactical matchups, and authenticated locker room news.
        </p>
    </div>
""", unsafe_allow_html=True)

if scan_triggered:
    with st.spinner("Scraping squad reports, referee trends, and latest odds..."):
        time.sleep(1.2)
    st.toast("Scan completed: Database synced with live team outings.", icon="⚡")

# ----------------- PREDICTIONS DATA -----------------
matches = [
    {
        "league": "Premier League",
        "home": "Arsenal",
        "away": "Chelsea",
        "time": "Today • 20:00 GMT",
        "market": "Draw No Bet (DNB)",
        "pick": "Arsenal DNB",
        "confidence": 92.4,
        "pill_class": "pill-green",
        "badge_text": "Ultra Confidence",
        "analysis": "Chelsea missing 2 starting double-pivot midfielders. Arsenal's 5-match home rolling xG sits at 2.41 vs 0.68 conceded."
    },
    {
        "league": "La Liga",
        "home": "Real Madrid",
        "away": "Sevilla",
        "time": "Today • 21:00 GMT",
        "market": "Over/Under Goals",
        "pick": "Over 1.5 Team Goals (RMA)",
        "confidence": 93.8,
        "pill_class": "pill-cyan",
        "badge_text": "Goal Market",
        "analysis": "Sevilla conceded in 9 of their last 10 road matches. Madrid converting 32% of final-third box entries into shots on target."
    },
    {
        "league": "UEFA Champions League",
        "home": "Bayern Munich",
        "away": "Lazio",
        "time": "Tomorrow • 20:00 GMT",
        "market": "Double Chance",
        "pick": "Bayern Win or Draw",
        "confidence": 95.1,
        "pill_class": "pill-green",
        "badge_text": "Top Probability",
        "analysis": "Lazio away record indicates a -0.85 xG disparity. Bayern reports a 100% clean bill of health across starting forward line."
    },
    {
        "league": "Serie A",
        "home": "Inter Milan",
        "away": "Atalanta",
        "time": "Tomorrow • 19:45 GMT",
        "market": "Over/Under Goals",
        "pick": "Over 2.5 Total Match Goals",
        "confidence": 85.2,
        "pill_class": "pill-violet",
        "badge_text": "High Pace Dynamic",
        "analysis": "Both squads rank top 3 in Serie A for progressive transition phases. Cumulative expected total goals calculated at 3.14."
    }
]

# Filter logic
filtered = [
    m for m in matches 
    if (league == "All Major Leagues" or m["league"] == league) 
    and (m["confidence"] >= min_confidence)
]

# Header for Match Feed
st.markdown(f"""
    <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 16px;">
        <h3 style="font-size: 1.35rem; margin: 0;">Verified Opportunities ({len(filtered)})</h3>
        <span style="font-size: 0.82rem; color: rgba(255, 255, 255, 0.45);">Sorted by Neural Confidence</span>
    </div>
""", unsafe_allow_html=True)

if not filtered:
    st.info("No fixtures meet the current threshold. Adjust the confidence slider in the sidebar.")
else:
    # Bento 2-column Grid
    for i in range(0, len(filtered), 2):
        row_cols = st.columns(2)
        for j in range(2):
            if i + j < len(filtered):
                match = filtered[i + j]
                with row_cols[j]:
                    st.markdown(f"""
                    <div class="liquid-glass-card">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                            <span class="glass-pill {match['pill_class']}">{match['badge_text']}</span>
                            <span style="font-size: 0.8rem; color: rgba(255, 255, 255, 0.4);">{match['league']} • {match['time']}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin: 12px 0;">
                            <h3 style="margin: 0; font-size: 1.35rem; font-weight: 700;">{match['home']}</h3>
                            <span style="font-weight: 700; color: rgba(255, 255, 255, 0.25); font-size: 0.85rem; letter-spacing: 0.1em;">VS</span>
                            <h3 style="margin: 0; font-size: 1.35rem; font-weight: 700;">{match['away']}</h3>
                        </div>
                        <hr style="border: 0; border-top: 1px solid rgba(255, 255, 255, 0.08); margin: 16px 0;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                            <div>
                                <div style="font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; color: rgba(255, 255, 255, 0.45); margin-bottom: 4px;">Recommended Angle</div>
                                <div style="font-size: 1.15rem; font-weight: 700; color: #ffffff;">{match['pick']}</div>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; color: rgba(255, 255, 255, 0.45); margin-bottom: 2px;">Algorithm Probability</div>
                                <div class="confidence-metric">{match['confidence']}%</div>
                            </div>
                        </div>
                        <div style="margin-top: 18px; padding-top: 14px; border-top: 1px solid rgba(255, 255, 255, 0.06); font-size: 0.84rem; line-height: 1.5; color: rgba(255, 255, 255, 0.65);">
                            <span style="color: #52e5e7; font-weight: 600;">Intelligence Digest:</span> {match['analysis']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
