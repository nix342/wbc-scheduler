import streamlit as st
import pandas as pd
import re

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

# 2. Sidebar Configuration Controls
st.sidebar.header("1. Your Convention Details")
arrival_date = st.sidebar.date_input("Arrival Date", pd.to_datetime("2026-07-25"))
arrival_time = st.sidebar.slider("Arrival Time (24h Clock)", 0, 23, 18)

st.sidebar.header("2. Filters & Preferences")
exclude_demos = st.sidebar.checkbox("Exclude Demo Rounds", value=True)
rating_cutoff = st.sidebar.slider("Minimum BGG Rating to consider", 1, 10, 7)

st.sidebar.header("3. Upload Data")
uploaded_file = st.sidebar.file_uploader("Upload your BGG Collection CSV", type=["csv"])

if uploaded_file is not None:
    coll = pd.read_csv(uploaded_file)
    coll['rating'] = pd.to_numeric(coll['rating'], errors='coerce')
    
    favs = coll[coll['rating'] >= rating_cutoff].sort_values('rating', ascending=False)
    favs['clean_name'] = favs['objectname'].apply(clean_name)
    
    st.sidebar.header("4. Priority Must-Play Games")
    unique_fav_titles = sorted(favs['objectname'].unique())
    selected_priorities = st.sidebar.multiselect(
        "Select up to 3 'Must-Play' games to schedule first:",
        options=unique_fav_titles,
        max_selections=3
    )
    priority_cleans = [clean_name(title) for title in selected_priorities]

    # 5. Limit Tournament Runs (Optional early exits)
    st.sidebar.header("5. Set Tournament Caps")
    with st.sidebar.expander("Exit Tournaments Early (Optional)"):
        games_to_cap = st.multiselect(
            "Select games you want to limit:",
            options=unique_fav_titles,
            help="Choose games where you only plan to play the first few heats or rounds."
        )
        game_caps = {}
        for g in games_to_cap:
            game_caps[clean_name(g)] = st.number_input(
                f"Max Round/Heat for {g}:",
                min_value=1, max_value=10, value=1, step=1,
                help="The scheduler will drop any round or heat numbering higher than this, including playoffs."
            )
    
    # Match WBC events to collection
    matches = []
    for _, w_row in wbc.iterrows():
        for _, f_row in favs.iterrows():
            if w_row['clean_name'] == f_row['clean_name'] or (len(w_row['clean_name']) > 5 and w_row['clean_name'] in f_row['clean_name']):
                matches.append({**w_row.to_dict(), **f_row.to_dict()})
                break
                
    if not matches:
        st.warning("No matching games found between your favorites and the WBC schedule.")
    else:
        matched = pd.DataFrame(matches)
        
        # Filter by arrival
        arrival_dt = pd.to_datetime(arrival_date)
        matched = matched[~((matched['Date_parsed'] < arrival_dt) | ((matched['Date_parsed'] == arrival_dt) & (matched['Time'] < arrival_time)))]
        
        if exclude_demos:
            matched = matched[~matched['Round/Heat'].astype(str).str.contains('Demo', case=False, na=False)]
            
        # Calculate dynamic max rounds for validation rules
        total_rounds = {}
        for game in wbc['Event'].unique():
            game_events = wbc[wbc['Event'] == game]['Round/Heat'].astype(str)
            max_round = 0
            for ge in game_events:
                m1 = re.search(r'Round (\d+)/(\d+)', ge)
                if m1: max_round = max(max_round, int(m1.group(2)))
                else:
                    m2 = re.search(r'Round (\d+)', ge)
                    if m2: max_round = max(max_round, int(m2.group(1)))
            total_rounds[game] = max_round

        def calculate_priority_tier(row):
            if row['clean_name'] in priority_cleans: return 2
            if 'paths of glory' in row['Event'].lower(): return 1
            if 'combat commander' in row['Event'].lower(): return 1
            return 0

        matched['priority_tier'] = matched.apply(calculate_priority_tier, axis=1)
        matched = matched.sort_values(['priority_tier', 'rating', 'Date_parsed', 'Time'], ascending=[False, False, True, True])
        
        # Algorithmic Scheduling Logic Engine
        schedule = []
        booked = {}
        scheduled_stages = {}
        scheduled_heats = {}
        scheduled_rounds = {}
        
        def get_round_number(stage_str):
            m = re.search(r'Round (\d+)', str(stage_str))
            return int(m.group(1)) if m else None

        def is_elimination(stage_str):
            return bool(re.search(r'quarterfinal|semifinal|final', str(stage_str), re.IGNORECASE))

        # Helper function to grab numbers out of 'Round 2/5' or 'Heat 1/3'
        def get_stage_number(stage_str):
            m = re.search(r'(?:Round|Heat)\s*(\d+)', str(stage_str), re.IGNORECASE)
            return int(m.group(1)) if m else None

        for _, row in matched.iterrows():
            date = row['Date']
            start = row['Time']
            end = start + row['Duration']
            game = row['Event']
            stage = row['Round/Heat']
            tier = row['priority_tier']
            
            # --- ENFORCE EARLY EXIT TOURNAMENT CAPS ---
            if row['clean_name'] in game_caps:
                stage_num = get_stage_number(stage)
                # If it's a higher round/heat number, or an advanced playoff round, skip it!
                if (stage_num is not None and stage_num > game_caps[row['clean_name']]) or is_elimination(stage):
                    continue

            if game not in scheduled_stages:
                scheduled_stages[game] = []
                scheduled_heats[game] = 0
                scheduled_rounds[game] = 0
                
            past_stages = scheduled_stages[game]
            stage_str_lower = str(stage).lower()
            
            # Skip progression check for forced manual priorities
            if tier < 2:
                r_num = get_round_number(stage)
                if r_num is not None and r_num > 1:
                    if not any(get_round_number(ps) == r_num - 1 for ps in past_stages): continue
                if is_elimination(stage):
                    has_two_heats = scheduled_heats[game] >= 2
                    expected_rounds = total_rounds.get(game, 0)
                    has_all_rounds = expected_rounds > 0 and scheduled_rounds[game] >= expected_rounds
                    if not (has_two_heats or has_all_rounds): continue

            if date not in booked: booked[date] = []
            
            conflict = False
            row_elim = is_elimination(stage)
            for b_start, b_end, b_stage, b_tier, b_game in booked[date]:
                if max(start, b_start) < min(end, b_end):
                    b_elim = is_elimination(b_stage)
                    if game == b_game and tier > 0: continue
                    if not (row_elim or b_elim): conflict = True; break
                        
            if not conflict:
                booked[date].append((start, end, stage, tier, game))
                schedule.append(row)
                scheduled_stages[game].append(stage)
                if 'heat' in stage_str_lower: scheduled_heats[game] += 1
                if 'round' in stage_str_lower and 'mulligan' not in stage_str_lower: scheduled_rounds[game] += 1

        output_df = pd.DataFrame(schedule).sort_values(['Date_parsed', 'Time'])
        
        # Display Final Table
        st.subheader("Your Personalized Itinerary")
        st.dataframe(
            output_df[['Date', 'Day Code', 'Time', 'Duration', 'Event', 'Round/Heat', 'Location', 'GM']],
            use_container_width=True
        )
        
        csv = output_df[['Date', 'Day Code', 'Time', 'Duration', 'Event', 'Round/Heat', 'Location', 'GM']].to_csv(index=False).encode('utf-8')
        st.download_button("Download Schedule as CSV", data=csv, file_name="wbc_itinerary.csv", mime="text/csv")
else:
    st.info("👈 Please upload your personal boardgame collection CSV in the sidebar to populate your options!")
