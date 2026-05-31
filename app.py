import streamlit as st
import pandas as pd
import re
import time

st.set_page_config(page_title="WBC 2026 Custom Scheduler", layout="wide")
st.title("WBC 2026 Conflict-Free Tournament Scheduler")
st.write("Upload your BoardGameGeek collection CSV to generate a personalized, priority-driven itinerary!")

# 1. Load the master schedule
@st.cache_data
def load_wbc_schedule():
    df = pd.read_csv('wbc2026.csv', skiprows=5)
    df['Time'] = pd.to_numeric(df['Time'], errors='coerce')
    df['Duration'] = pd.to_numeric(df['Duration'], errors='coerce')
    df['Date_parsed'] = pd.to_datetime(df['Date'], format='%m/%d/%y', errors='coerce')
    return df.dropna(subset=['Time', 'Duration', 'Date_parsed'])

wbc = load_wbc_schedule()

def clean_name(name):
    return re.sub(r'[^a-z0-9]', '', str(name).lower()) if pd.notna(name) else ""

wbc['clean_name'] = wbc['Event'].apply(clean_name)

# ---------------------------------------------------------
# 2. Sidebar Configuration Controls
# ---------------------------------------------------------
st.sidebar.header("1. Your Convention Details")
arrival_date = st.sidebar.date_input("Arrival Date", pd.to_datetime("2026-07-25"))
arrival_time = st.sidebar.slider("Arrival Time (24h Clock)", 0, 23, 18)

departure_date = st.sidebar.date_input("Departure Date", pd.to_datetime("2026-08-02"))
departure_time = st.sidebar.slider("Departure Time (24h Clock)", 0, 23, 15)

st.sidebar.header("2. Filters & Preferences")
exclude_demos = st.sidebar.checkbox("Exclude Demo Rounds", value=True)
rating_cutoff = st.sidebar.slider("Minimum BGG Rating to consider", 1, 10, 7)

schedule_philosophy = st.sidebar.radio(
    "Scheduling Strategy Preference",
    options=[
        "Maximize Playoff Chances (Prioritize multiple heats of the same games)", 
        "Maximize Variety (Prioritize single heats of many different games)"
    ],
    index=0,
    help="Playoff mode fills your schedule with repeat heats to unlock finals. Variety mode spreads your time across as many unique titles as possible."
)

st.sidebar.header("3. Upload Data")
uploaded_file = st.sidebar.file_uploader("Upload your BGG Collection CSV", type=["csv"])

if uploaded_file is not None:
    coll = pd.read_csv(uploaded_file)
    coll['rating'] = pd.to_numeric(coll['rating'], errors='coerce')
    
    favs = coll[coll['rating'] >= rating_cutoff].sort_values('rating', ascending=False)
    favs['clean_name'] = favs['objectname'].apply(clean_name)
    
    # ---------------------------------------------------------
    # 4. Dynamic Priority Multiselect
    # ---------------------------------------------------------
    st.sidebar.header("4. Priority Must-Play Games")
    unique_wbc_events = sorted(wbc['Event'].dropna().unique())
    selected_priorities = st.sidebar.multiselect(
        "Select up to 3 'Must-Play' games to schedule first:",
        options=unique_wbc_events,
        max_selections=3
    )
    
    # ---------------------------------------------------------
    # 5. Limit Tournament Runs
    # ---------------------------------------------------------
    st.sidebar.header("5. Set Tournament Caps")
    with st.sidebar.expander("Exit Tournaments Early (Optional)"):
        games_to_cap = st.multiselect(
            "Select games you want to limit:",
            options=unique_wbc_events,
            help="Choose games where you only plan to play the first few heats or rounds."
        )
        game_caps = {}
        for g in games_to_cap:
            game_caps[g] = st.number_input(
                f"Max Round/Heat for {g}:",
                min_value=1, max_value=10, value=1, step=1
            )
            
    # ---------------------------------------------------------
    # 6. Exclude Games (The "Ban" List)
    # ---------------------------------------------------------
    st.sidebar.header("6. Exclude Games")
    with st.sidebar.expander("Skip specific games (Optional)"):
        games_to_exclude = st.multiselect(
            "Select games to completely ignore:",
            options=unique_wbc_events,
            help="These games will NOT be scheduled, even if they have a high BGG rating."
        )

    # ---------------------------------------------------------
    # --- SPINNER START ---
    # ---------------------------------------------------------
    with st.spinner('Crunching the convention matrix! Building your conflict-free itinerary...'):
        
        matches = []
        for _, w_row in wbc.iterrows():
            
            # If the game is on the ban list, skip matching it entirely!
            if w_row['Event'] in games_to_exclude:
                continue
                
            is_priority = w_row['Event'] in selected_priorities
            matched_fav = False
            
            for _, f_row in favs.iterrows():
                if w_row['clean_name'] == f_row['clean_name'] or (len(w_row['clean_name']) > 5 and w_row['clean_name'] in f_row['clean_name']):
                    matches.append({**w_row.to_dict(), **f_row.to_dict()})
                    matched_fav = True
                    break
                    
            if not matched_fav and is_priority:
                priority_match = w_row.to_dict()
                priority_match['rating'] = 10.0
                matches.append(priority_match)
                
        # --- ROBUST SAFETY CHECK 1: Did we find any games at all? ---
        if not matches:
            st.warning("No matching games found between your favorites/priorities and the WBC schedule.")
            success_flag = False
        else:
            matched = pd.DataFrame(matches)
            
            # --- TIME FILTERING (Arrival & Departure) ---
            arrival_dt = pd.to_datetime(arrival
