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
    # --- SPINNER & LOGIC ENGINE ---
    # ---------------------------------------------------------
    # Create variables to hold the final status state
    status_message = ""
    status_type = ""
    success_flag = False

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
                
        # --- ROBUST SAFETY CHECK 1 ---
        if not matches:
            status_message = "No matching games found between your favorites/priorities and the WBC schedule."
            status_type = "warning"
        else:
            matched = pd.DataFrame(matches)
            
            # --- TIME FILTERING (Arrival & Departure) ---
            arrival_dt = pd.to_datetime(arrival_date)
            departure_dt = pd.to_datetime(departure_date)
            
            def is_within_convention_window(row):
                if row['Date_parsed'] < arrival_dt: return False
                if row['Date_parsed'] == arrival_dt and row['Time'] < arrival_time: return False
                event_end_time = row['Time'] + row['Duration']
                if row['Date_parsed'] > departure_dt: return False
                if row['Date_parsed'] == departure_dt and event_end_time > departure_time: return False
                return True
                
            matched = matched[matched.apply(is_within_convention_window, axis=1)]
            
            if exclude_demos:
                matched = matched[~matched['Round/Heat'].astype(str).str.contains('Demo', case=False, na=False)]
            
            # --- ROBUST SAFETY CHECK 2 ---
            if matched.empty:
                status_message = "Your arrival/departure constraints removed all remaining games from consideration!"
                status_type = "warning"
            else:
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
                    if row['Event'] in selected_priorities: return 2
                    return 0

                matched['priority_tier'] = matched.apply(calculate_priority_tier, axis=1)
                matched = matched.sort_values(['priority_tier', 'rating', 'Date_parsed', 'Time'], ascending=[False, False, True, True])
                
                schedule = []
                booked = {}
                scheduled_stages = {}
                scheduled_heats = {}
                scheduled_rounds = {}
                
                def get_round_number(stage_str):
                    m = re.search(r'(?:Round|Heat)\s*(\d+)', str(stage_str), re.IGNORECASE)
                    return int(m.group(1)) if m else None

                def is_elimination(stage_str):
                    return bool(re.search(r'quarterfinal|semifinal|final', str(stage_str), re.IGNORECASE))

                use_variety_pass = "Maximize Variety" in schedule_philosophy
                
                # --- PASS 1 ---
                for _, row in matched.iterrows():
                    date = row['Date']
                    start = row['Time']
                    end = start + row['Duration']
                    game = row['Event']
                    stage = row['Round/Heat']
                    tier = row['priority_tier']
                    
                    if game not in scheduled_stages:
                        scheduled_stages[game] = []
                        scheduled_heats[game] = 0
                        scheduled_rounds[game] = 0
                        
                    past_stages = scheduled_stages[game]
                    stage_str_lower = str(stage).lower()
                    
                    if use_variety_pass and 'heat' in stage_str_lower and scheduled_heats[game] >= 1:
                        continue

                    if row['Event'] in game_caps:
                        stage_num = get_round_number(stage)
                        if (stage_num is not None and stage_num > game_caps[row['Event']]) or is_elimination(stage):
                            continue
                    
                    if tier < 2:
                        r_num = get_round_number(stage)
                        if r_num is not None and r_num > 1 and 'heat' not in stage_str_lower:
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

                # --- PASS 2 (Filler for Variety Mode) ---
                if use_variety_pass:
                    for _, row in matched.iterrows():
                        if any(r.name == row.name for r in schedule): continue
                        
                        date = row['Date']
                        start = row['Time']
                        end = start + row['Duration']
                        game = row['Event']
                        stage = row['Round/Heat']
                        tier = row['priority_tier']
                        stage_str_lower = str(stage).lower()
                        past_stages = scheduled_stages[game]

                        if row['Event'] in game_caps:
                            stage_num = get_round_number(stage)
                            if (stage_num is not None and stage_num > game_caps[row['Event']]) or is_elimination(stage):
                                continue

                        if tier < 2:
                            r_num = get_round_number(stage)
                            if r_num is not None and r_num > 1 and 'heat' not in stage_str_lower:
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

                # --- ROBUST SAFETY CHECK 3 ---
                if not schedule:
                    status_message = "All matching games either conflicted or hit tournament caps. No schedule could be generated."
                    status_type = "warning"
                else:
                    output_df = pd.DataFrame(schedule).sort_values(['Date_parsed', 'Time'])
                    status_message = "Success! Your custom itinerary is ready below."
                    status_type = "success"
                    success_flag = True

    # ----------------------------------------------------
    # --- RENDER FINAL MESSAGE EXACTLY WHERE SPINNER WAS ---
    # ----------------------------------------------------
    if status_type == "warning":
        st.warning(status_message)
    elif status_type == "success":
        st.success(status_message)

    # --- ONLY SHOW CHARTS IF WE SUCCESSFULLY MATCHED DATA ---
    if success_flag:
        
        # ----------------------------------------------------
        # OUTPUT DISPLAY (Tabs for Visual & Tabular)
        # ----------------------------------------------------
        import altair as alt

        st.subheader("Your Personalized Itinerary")
        
        main_tab1, main_tab2 = st.tabs(["📊 Visual Schedule", "📋 Tabular Data"])
        
        def format_hhmm(t):
            if pd.isna(t): return ""
            h = int(t) % 24
            m = int(round((t - int(t)) *
