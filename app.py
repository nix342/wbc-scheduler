import streamlit as st
import pandas as pd
import re
import time

st.set_page_config(page_title="WBC 2026 Custom Scheduler", layout="wide")

# ---------------------------------------------------------
# --- RICH TEXT HEADER ---
# ---------------------------------------------------------
st.markdown("<h1 style='text-align: center; color: #cd7f32;'>🎲 WBC 2026 Scheduler</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-size: 18px;'>Upload your BGG Collection to generate a personalized convention itinerary!</p>", unsafe_allow_html=True)
st.divider()

# ---------------------------------------------------------
# --- THE MASTER UI SLOT ---
# ---------------------------------------------------------
status_area = st.empty()

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
# --- SIDEBAR CONTROLS ---
# ---------------------------------------------------------

st.sidebar.header("1. Upload Data")
uploaded_file = st.sidebar.file_uploader("Upload your BGG Collection CSV", type=["csv"])

st.sidebar.header("2. Your Convention Details")
arrival_date = st.sidebar.date_input("Arrival Date", pd.to_datetime("2026-07-25"))
arrival_time = st.sidebar.slider("Arrival Time (24h Clock)", 0, 23, 18)

departure_date = st.sidebar.date_input("Departure Date", pd.to_datetime("2026-08-02"))
departure_time = st.sidebar.slider("Departure Time (24h Clock)", 0, 23, 15)

unique_wbc_events = sorted(wbc['Event'].dropna().unique())

st.sidebar.header("3. Priority Must-Play Games")
selected_priorities = st.sidebar.multiselect(
    "Select up to 3 'Must-Play' games to schedule first:",
    options=unique_wbc_events,
    max_selections=3
)

# ---------------------------------------------------------
# --- CONSOLIDATED ADVANCED FILTERS ---
# ---------------------------------------------------------
st.sidebar.header("4. Filters & Preferences")
with st.sidebar.expander("⚙️ Advanced Scheduling Filters", expanded=False):
    
    st.markdown("**Tournament Limits & Exclusions**")
    games_to_exclude = st.multiselect(
        "Skip specific games:",
        options=unique_wbc_events,
        help="These games will NOT be scheduled, even if they have a high BGG rating."
    )
    
    games_to_cap = st.multiselect(
        "Limit tournament runs for:",
        options=unique_wbc_events,
        help="Choose games where you only plan to play the first few heats or rounds."
    )
    
    game_caps = {}
    for g in games_to_cap:
        game_caps[g] = st.number_input(
            f"Max Round/Heat for {g}:",
            min_value=1, max_value=10, value=1, step=1
        )
        
    st.divider()
    
    st.markdown("**Algorithm Preferences**")
    exclude_demos = st.checkbox("Exclude Demo Rounds", value=True)
    fill_gaps = st.checkbox("Fill Empty Time Slots", value=False, help="Automatically suggest other available convention games during your downtime.")
    rating_cutoff = st.slider("Minimum BGG Rating to consider", 1, 10, 7)
    schedule_philosophy = st.radio(
        "Scheduling Strategy Preference",
        options=[
            "Maximize Playoff Chances (Prioritize repeat heats)", 
            "Maximize Variety (Prioritize single heats of many games)"
        ],
        index=0
    )


# ---------------------------------------------------------
# --- LOGIC ENGINE ---
# ---------------------------------------------------------
if uploaded_file is None:
    status_area.info("👈 Please upload your personal boardgame collection CSV in the sidebar to populate your options!")
else:
    coll = pd.read_csv(uploaded_file)
    coll['rating'] = pd.to_numeric(coll['rating'], errors='coerce')
    
    favs = coll[coll['rating'] >= rating_cutoff].sort_values('rating', ascending=False)
    favs['clean_name'] = favs['objectname'].apply(clean_name)
    
    status_message = ""
    status_type = ""
    success_flag = False

    with status_area.container():
        with st.spinner('Crunching the convention matrix! Building your conflict-free itinerary...'):
            
            matches = []
            for _, w_row in wbc.iterrows():
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
                    
            if not matches:
                status_message = "No matching games found between your favorites/priorities and the WBC schedule."
                status_type = "warning"
            else:
                matched = pd.DataFrame(matches)
                
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
                    
                    # --- PASS 1: Priority & Playoff ---
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
                            schedule.append(row.to_dict())
                            scheduled_stages[game].append(stage)
                            if 'heat' in stage_str_lower: scheduled_heats[game] += 1
                            if 'round' in stage_str_lower and 'mulligan' not in stage_str_lower: scheduled_rounds[game] += 1

                    # --- PASS 2: Variety Filler ---
                    if use_variety_pass:
                        for _, row in matched.iterrows():
                            if any(r['Event'] == row['Event'] and r['Round/Heat'] == row['Round/Heat'] for r in schedule): continue
                            
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
                                schedule.append(row.to_dict())
                                scheduled_stages[game].append(stage)
                                if 'heat' in stage_str_lower: scheduled_heats[game] += 1
                                if 'round' in stage_str_lower and 'mulligan' not in stage_str_lower: scheduled_rounds[game] += 1

                    # --- PASS 3: GAP FILLERS ---
                    if fill_gaps:
                        wbc_filler = wbc.sort_values(['Date_parsed', 'Time'])
                        for _, row in wbc_filler.iterrows():
                            date = row['Date']
                            start = row['Time']
                            end = start + row['Duration']
                            game = row['Event']
                            stage = row['Round/Heat']
                            stage_str_lower = str(stage).lower()
                            
                            if game in games_to_exclude: continue
                            if exclude_demos and 'demo' in stage_str_lower: continue
                            if not is_within_convention_window(row): continue
                            
                            if row['Event'] in game_caps:
                                stage_num = get_round_number(stage)
                                if (stage_num is not None and stage_num > game_caps[row['Event']]):
                                    continue
                            
                            if is_elimination(stage): continue
                            r_num = get_round_number(stage)
                            if r_num is not None and r_num > 1 and 'heat' not in stage_str_lower:
                                continue
                                
                            if date not in booked: booked[date] = []
                            
                            conflict = False
                            for b_start, b_end, b_stage, b_tier, b_game in booked[date]:
                                if max(start, b_start) < min(end, b_end):
                                    conflict = True
                                    break
                                    
                            if not conflict:
                                booked[date].append((start, end, stage, -1, game))
                                schedule.append(row.to_dict())

                    if not schedule:
                        status_message = "All matching games either conflicted or hit tournament caps. No schedule could be generated."
                        status_type = "warning"
                    else:
                        output_df = pd.DataFrame(schedule).sort_values(['Date_parsed', 'Time'])
                        status_message = "Success! Your custom itinerary is ready below."
                        status_type = "success"
                        success_flag = True

    if status_type == "warning":
        status_area.warning(status_message)
    elif status_type == "success":
        status_area.success(status_message)

    if success_flag:
        
        import altair as alt

        st.subheader("Your Personalized Itinerary")
        
        main_tab1, main_tab2, main_tab3 = st.tabs(["📊 Visual Schedule", "📋 Tabular Data", "📈 Custom Metrics"])
        
        def format_hhmm(t):
            if pd.isna(t): return ""
            h = int(t) % 24
            m = int(round((t - int(t)) * 60))
            return f"{h:02d}{m:02d}"

        with main_tab1:
            viz_df = output_df.copy()
            
            def get_border_color(stage):
                s = str(stage).lower()
                if 'quarterfinal' in s: return '#cd7f32' 
                if 'semifinal' in s: return '#c0c0c0'     
                if 'final' in s: return '#ffd700'         
                return 'transparent'
                
            viz_df['Border_Color'] = viz_df['Round/Heat'].apply(get_border_color)
            
            viz_df['Logical Date'] = viz_df.apply(
                lambda row: row['Date_parsed'] - pd.Timedelta(days=1) if row['Time'] < 8 else row['Date_parsed'], 
                axis=1
            )
            
            viz_df['Plot Time'] = viz_df.apply(lambda row: row['Time'] + 24 if row['Time'] < 8 else row['Time'], axis=1)
            viz_df['Plot End Time'] = viz_df['Plot Time'] + viz_df['Duration']
            
            viz_df['Start Time'] = viz_df['Time'].apply(format_hhmm)
            viz_df['End Time'] = ((viz_df['Time'] + viz_df['Duration']) % 24).apply(format_hhmm)
            
            viz_df['Formatted Date'] = viz_df['Logical Date'].dt.strftime('%A, %b %d')
            unique_dates = viz_df.sort_values('Logical Date')['Formatted Date'].unique()
            
            if len(unique_dates) > 0:
                day_tabs = st.tabs(list(unique_dates))
                
                for idx, selected_date in enumerate(unique_dates):
                    with day_tabs[idx]:
                        day_df = viz_df[viz_df['Formatted Date'] == selected_date]
                        
                        base_chart = alt.Chart(day_df).encode(
                            x2='Plot End Time',
                            y=alt.Y('Event', sort=alt.EncodingSortField(field="Plot Time", order="ascending"), title=""),
                            color=alt.Color('Event', legend=None),
                            tooltip=['Event', 'Round/Heat', 'Location', 'Start Time', 'End Time', 'Duration']
                        ).properties(
                            width=800
                        )

                        x_scale = alt.Scale(domain=[8, 26], clamp=True)
                        label_expr = "datum.value >= 24 ? (datum.value - 24 < 10 ? '0' + (datum.value - 24) : (datum.value - 24)) + '00' : (datum.value < 10 ? '0' + datum.value : datum.value) + '00'"
                        
                        bottom_axis_chart = base_chart.mark_bar(cornerRadius=4, height=20).encode(
                            x=alt.X('Plot Time', title='Time (HHMM)', scale=x_scale, 
                                    axis=alt.Axis(orient='bottom', tickCount=18, labelExpr=label_expr)),
                            stroke=alt.Stroke('Border_Color:N', scale=None),
                            strokeWidth=alt.condition(alt.datum.Border_Color != 'transparent', alt.value(3), alt.value(0))
                        )

                        top_axis_chart = base_chart.mark_bar(opacity=0).encode(
                            x=alt.X('Plot Time', title='', scale=x_scale, 
                                    axis=alt.Axis(orient='top', tickCount=18, labelExpr=label_expr))
                        )

                        chart = alt.layer(bottom_axis_chart, top_axis_chart).resolve_scale(
                            x='independent'
                        ).interactive()

                        st.altair_chart(chart, use_container_width=True)
            else:
                st.info("No events scheduled yet. Adjust your filters or constraints!")

        with main_tab2:
            table_df = output_df[['Date', 'Day Code', 'Time', 'Duration', 'Event', 'Round/Heat', 'Location', 'GM']].copy()
            table_df['Time'] = table_df['Time'].apply(format_hhmm)
            
            st.dataframe(
                table_df, 
                use_container_width=True,
                hide_index=True 
            )
            
        with main_tab3:
            st.markdown("### Convention Stats")
            
            total_events = len(output_df)
            unique_games = output_df['Event'].nunique()
            total_hours = output_df['Duration'].sum()
            
            if 'rating' in output_df.columns:
                avg_rating = output_df['rating'].mean()
            else:
                avg_rating = None

            col1, col2, col3, col4 = st.columns(4)
            
            col1.metric(label="Total Sessions", value=total_events)
            col2.metric(label="Unique Games", value=unique_games)
            col3.metric(label="Total Hours", value=f"{total_hours:g} hrs")
            
            if pd.notna(avg_rating):
                col4.metric(label="Avg BGG Rating", value=f"{avg_rating:.1f}")
            else:
                col4.metric(label="Avg BGG Rating", value="N/A")
                
            st.divider()
            
            if not output_df.empty:
                most_played = output_df['Event'].value_counts().idxmax()
                most_played_count = output_df['Event'].value_counts().max()
                st.markdown(f"**🏅 Most Played Game:** {most_played} ({most_played_count} scheduled sessions)")

        st.divider()
        st.markdown("### Export Your Schedule")
        
        csv_df = output_df[['Date', 'Day Code', 'Time', 'Duration', 'Event', 'Round/Heat', 'Location', 'GM']].copy()
        csv_df['Time'] = csv_df['Time'].apply(format_hhmm)
        standard_csv = csv_df.to_csv(index=False).encode('utf-8')
        
        gcal_df = pd.DataFrame()
        gcal_df['Subject'] = output_df['Event'] + " (" + output_df['Round/Heat'].astype(str) + ")"
        
        start_dts = output_df['Date_parsed'] + pd.to_timedelta(output_df['Time'], unit='h')
        end_dts = output_df['Date_parsed'] + pd.to_timedelta(output_df['Time'] + output_df['Duration'], unit='h')
        
        gcal_df['Start Date'] = start_dts.dt.strftime('%m/%d/%Y')
        gcal_df['Start Time'] = start_dts.dt.strftime('%I:%M %p')
        gcal_df['End Date'] = end_dts.dt.strftime('%m/%d/%Y')
        gcal_df['End Time'] = end_dts.dt.strftime('%I:%M %p')
        gcal_df['All Day Event'] = 'False'
        
        gcal_df['Description'] = 'GM: ' + output_df.get('GM', 'TBD').fillna('TBD').astype(str)
        gcal_df['Location'] = output_df.get('Location', 'TBD').fillna('TBD').astype(str)
        
        gcal_csv = gcal_df.to_csv(index=False).encode('utf-8')
        
        colA, colB = st.columns(2)
        with colA:
            st.download_button(
                label="📥 Download Standard CSV",
                data=standard_csv,
                file_name="wbc_itinerary.csv",
                mime="text/csv",
                use_container_width=True
            )
        with colB:
            st.download_button(
                label="📅 Download Google Calendar Sync",
                data=gcal_csv,
                file_name="wbc_gcal_import.csv",
                mime="text/csv",
                use_container_width=True
            )
            
        st.caption("*To import into Google Calendar: Open Google Calendar on a desktop > Click the Gear Icon (Settings) > Select 'Import & Export' > Upload `wbc_gcal_import.csv`.*")
