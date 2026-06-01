import streamlit as st
import pandas as pd
import json
import altair as alt
from streamlit_javascript import st_javascript
import streamlit.components.v1 as components

# --- Import our separated logic! ---
from utils import load_wbc_schedule, clean_name, format_hhmm, get_border_color
from engine import generate_itinerary

st.set_page_config(page_title="WBC 2026 Custom Scheduler", layout="wide")

# ---------------------------------------------------------
# --- RICH TEXT HEADER ---
# ---------------------------------------------------------
st.markdown("<h1 style='text-align: center; color: #cd7f32;'>🎲 WBC 2026 Scheduler</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-size: 18px;'>Upload your BGG Collection or select your Top 10 games to generate a personalized itinerary!</p>", unsafe_allow_html=True)
st.divider()

# ---------------------------------------------------------
# --- BROWSER LOCAL STORAGE BOOTSTRAP ---
# ---------------------------------------------------------
ls_result = st_javascript("localStorage.getItem('wbc_prefs') || 'NONE';")

if "prefs" not in st.session_state:
    if ls_result == 0:
        st.stop()  
    elif ls_result == "NONE":
        st.session_state.prefs = {}
    else:
        try:
            st.session_state.prefs = json.loads(ls_result)
        except:
            st.session_state.prefs = {}

prefs = st.session_state.prefs

status_area = st.empty()

# Load global data using util functions
wbc = load_wbc_schedule()
unique_wbc_events = sorted(wbc['Event'].dropna().unique())
wbc['clean_name'] = wbc['Event'].apply(clean_name)

# ---------------------------------------------------------
# --- SIDEBAR CONTROLS ---
# ---------------------------------------------------------

st.sidebar.header("1. Choose Input Method")
def_method = prefs.get("input_method", "Upload BGG Collection CSV")

input_method = st.sidebar.radio(
    "How do you want to build your list?",
    options=["Upload BGG Collection CSV", "Select Top 10 Games manually"],
    index=0 if def_method == "Upload BGG Collection CSV" else 1
)

top10_games = []
uploaded_file = None
rating_cutoff = 7

if input_method == "Select Top 10 Games manually":
    def_top10 = [g for g in prefs.get("top10", []) if g in unique_wbc_events]
    
    selected_games = st.sidebar.multiselect(
        "🔍 Search & Select Games (Max 10):",
        options=unique_wbc_events,
        default=def_top10,
        max_selections=10
    )
    
    ordered_games = [g for g in def_top10 if g in selected_games]
    ordered_games += [g for g in selected_games if g not in ordered_games]
    
    if len(ordered_games) > 1:
        st.sidebar.caption("↕️ **Edit the Rank numbers below** to instantly reorder your priorities (1 = Highest Priority).")
        rank_df = pd.DataFrame({
            "Rank": list(range(1, len(ordered_games) + 1)),
            "Game": ordered_games
        })
        
        edited_rank_df = st.sidebar.data_editor(
            rank_df,
            column_config={
                "Rank": st.column_config.NumberColumn("Rank", min_value=1, max_value=99, step=1, width="small"),
                "Game": st.column_config.TextColumn("Game", disabled=True)
            },
            hide_index=True,
            use_container_width=True
        )
        top10_games = edited_rank_df.sort_values("Rank")["Game"].tolist()
    else:
        top10_games = ordered_games
        
else:
    uploaded_file = st.sidebar.file_uploader("Upload your BGG Collection CSV", type=["csv"])
    def_rate = int(prefs.get("rate", 7))
    rating_cutoff = st.sidebar.slider("Minimum BGG Rating to consider", 1, 10, def_rate, help="Games below this BGG rating will be ignored.")

st.sidebar.header("2. Your Convention Details")
def_arr_date = pd.to_datetime(prefs.get("arr_date", "2026-07-25"))
arrival_date = st.sidebar.date_input("Arrival Date", def_arr_date)

def_arr_time = int(prefs.get("arr_time", 9))
arrival_time = st.sidebar.slider("Arrival Time (24h Clock)", 0, 23, def_arr_time)

def_dep_date = pd.to_datetime(prefs.get("dep_date", "2026-08-02"))
departure_date = st.sidebar.date_input("Departure Date", def_dep_date)

def_dep_time = int(prefs.get("dep_time", 15))
departure_time = st.sidebar.slider("Departure Time (24h Clock)", 0, 23, def_dep_time)

st.sidebar.header("3. Priority Must-Play Games")

if input_method == "Select Top 10 Games manually" and not prefs.get("pri_saved_flag", False):
    def_pri = top10_games[:3]
else:
    def_pri = [g for g in prefs.get("pri", []) if g in unique_wbc_events]
    
selected_priorities = st.sidebar.multiselect(
    "Select up to 3 'Must-Play' games to schedule first:",
    options=unique_wbc_events,
    default=def_pri,
    max_selections=3,
    help="These games will be forced into your schedule before anything else!"
)

st.sidebar.header("4. Filters & Preferences")
with st.sidebar.expander("⚙️ Advanced Scheduling Filters", expanded=False):
    
    st.markdown("**Tournament Limits & Exclusions**")
    def_excl = [g for g in prefs.get("excl", []) if g in unique_wbc_events]
    games_to_exclude = st.multiselect(
        "Skip specific games:",
        options=unique_wbc_events,
        default=def_excl,
        help="These games will NOT be scheduled, even if they have open slots."
    )
    
    def_cap = [g for g in prefs.get("cap", []) if g in unique_wbc_events]
    games_to_cap = st.multiselect(
        "Limit tournament runs for:",
        options=unique_wbc_events,
        default=def_cap,
        help="Choose games where you only plan to play the first few heats or rounds."
    )
    
    game_caps = {}
    saved_caps = prefs.get("c_caps", {})
    for g in games_to_cap:
        def_cap_val = int(saved_caps.get(g, 1))
        game_caps[g] = st.number_input(
            f"Max Round/Heat for {g}:",
            min_value=1, max_value=10, value=def_cap_val, step=1
        )
        
    st.divider()
    
    st.markdown("**Algorithm Preferences**")
    def_demo = prefs.get("demo", True)
    exclude_demos = st.checkbox("Exclude Demo Rounds", value=def_demo)
    
    def_juniors = prefs.get("juniors", True)
    exclude_juniors = st.checkbox("Exclude Juniors Events", value=def_juniors)
    
    def_no_round = prefs.get("no_round", True)
    exclude_no_round = st.checkbox("Exclude Seminars & Meetings", value=def_no_round, help="Skips events without formal heats, such as board meetings or open gaming.")
    
    def_fill = prefs.get("fill", False)
    fill_gaps = st.checkbox("Fill Empty Time Slots", value=def_fill, help="Automatically suggest other available convention games during your downtime.")
    
    options = [
        "Maximize Playoff Chances (Prioritize repeat heats)", 
        "Maximize Variety (Prioritize single heats of many games)"
    ]
    def_phil = int(prefs.get("phil", 0))
    schedule_philosophy = st.radio(
        "Scheduling Strategy Preference",
        options=options,
        index=def_phil
    )

st.sidebar.divider()

if st.sidebar.button("💾 Save Settings to Browser", use_container_width=True):
    new_prefs = {
        "input_method": input_method,
        "top10": top10_games,
        "rate": rating_cutoff,
        "arr_date": arrival_date.strftime("%Y-%m-%d"),
        "arr_time": arrival_time,
        "dep_date": departure_date.strftime("%Y-%m-%d"),
        "dep_time": departure_time,
        "pri": selected_priorities,
        "pri_saved_flag": True,
        "excl": games_to_exclude,
        "cap": games_to_cap,
        "c_caps": game_caps,
        "demo": exclude_demos,
        "juniors": exclude_juniors,     
        "no_round": exclude_no_round,   
        "fill": fill_gaps,
        "phil": options.index(schedule_philosophy)
    }
    js_code = f"localStorage.setItem('wbc_prefs', JSON.stringify({json.dumps(new_prefs)}));"
    st_javascript(js_code)
    st.sidebar.success("Saved! Your settings will auto-load next time.")

if st.sidebar.button("🗑️ Clear Form & Reset Defaults", use_container_width=True):
    components.html("<script>localStorage.removeItem('wbc_prefs'); window.parent.location.reload();</script>", height=0)
    st.stop()


# ---------------------------------------------------------
# --- TRIGGER LOGIC ENGINE ---
# ---------------------------------------------------------
proceed = False
favs = pd.DataFrame()

if input_method == "Select Top 10 Games manually":
    if not top10_games and not selected_priorities:
        status_area.info("👈 Please select your Top 10 or Priority games in the sidebar to generate a schedule!")
    else:
        favs = pd.DataFrame({
            'objectname': top10_games,
            'rating': [10.0 - (i * 0.1) for i in range(len(top10_games))]
        })
        favs['clean_name'] = favs['objectname'].apply(clean_name)
        proceed = True
else:
    if uploaded_file is None and not selected_priorities:
        status_area.info("👈 Please upload your BGG CSV or select Priority games in the sidebar to generate a schedule!")
    else:
        if uploaded_file is not None:
            coll = pd.read_csv(uploaded_file)
            coll['rating'] = pd.to_numeric(coll['rating'], errors='coerce')
            favs = coll[coll['rating'] >= rating_cutoff].sort_values('rating', ascending=False)
            favs['clean_name'] = favs['objectname'].apply(clean_name)
        else:
            favs = pd.DataFrame(columns=['objectname', 'clean_name', 'rating'])
        proceed = True

if proceed:
    with status_area.container():
        with st.spinner('Crunching the convention matrix! Building your conflict-free itinerary...'):
            
            success_flag, status_type, status_message, output_df = generate_itinerary(
                wbc, favs, selected_priorities, games_to_exclude, games_to_cap, game_caps, 
                arrival_date, arrival_time, departure_date, departure_time, 
                exclude_demos, exclude_juniors, exclude_no_round, 
                schedule_philosophy, fill_gaps
            )

    if status_type == "warning":
        status_area.warning(status_message)
    elif status_type == "success":
        status_area.success(status_message)

    if success_flag:
        st.subheader("Your Personalized Itinerary")
        
        main_tab1, main_tab2, main_tab3 = st.tabs(["📊 Visual Schedule", "📋 Tabular Data", "📈 Custom Metrics"])
        
        with main_tab1:
            viz_df = output_df.copy()
            
            viz_df['Border_Color'] = viz_df.apply(get_border_color, axis=1)
            
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
            
            safe_palette = [
                '#E6194B', '#F58231', '#FFE119', '#911EB4', '#F032E6',
                '#800000', '#9A6324', '#808000', '#E6BEFF', '#FFD8B1',
                '#FABEBE', '#A9A9A9', '#FF9999', '#CC0000', '#FFCC00',
                '#CC99FF', '#990099', '#660066', '#330033', '#FF6600'
            ]
            
            if len(unique_dates) > 0:
                day_tabs = st.tabs(list(unique_dates))
                
                for idx, selected_date in enumerate(unique_dates):
                    with day_tabs[idx]:
                        day_df = viz_df[viz_df['Formatted Date'] == selected_date]
                        
                        base_chart = alt.Chart(day_df).encode(
                            x2='Plot End Time',
                            y=alt.Y('Event', sort=alt.EncodingSortField(field="Plot Time", order="ascending"), title=""),
                            color=alt.Color('Event', scale=alt.Scale(range=safe_palette), legend=None),
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
            
            # Create a clean Subject line that drops the parenthesis if the Round is empty
            def clean_gcal_subject(row):
                r = str(row['Round/Heat'])
                if pd.isna(row['Round/Heat']) or r.strip() in ['', 'nan', 'none']:
                    return str(row['Event'])
                return f"{row['Event']} ({row['Round/Heat']})"
                
            st.dataframe(
                table_df, 
                use_container_width=True,
                hide_index=True 
            )
            
        with main_tab3:
            stats_df = output_df.copy()
            
            # Calculate Logical Date so late-night games count towards the correct previous day
            stats_df['Logical Date'] = stats_df.apply(
                lambda row: row['Date_parsed'] - pd.Timedelta(days=1) if row['Time'] < 8 else row['Date_parsed'], 
                axis=1
            )
            stats_df['Formatted Date'] = stats_df['Logical Date'].dt.strftime('%A, %b %d')
            
            total_events = len(stats_df)
            unique_games = stats_df['Event'].nunique()
            total_hours = stats_df['Duration'].sum()

            col1, col2, col3, col4 = st.columns(4)
            
            col1.metric(label="Total Sessions", value=total_events)
            col2.metric(label="Unique Games", value=unique_games)
            col3.metric(label="Total Hours", value=f"{total_hours:g} hrs")
            
            if input_method == "Select Top 10 Games manually":
                if top10_games:
                    top10_played = stats_df[stats_df['Event'].isin(top10_games)]['Event'].nunique()
                    col4.metric(label="Top 10 Games Scheduled", value=f"{top10_played} / {len(top10_games)}")
                else:
                    col4.metric(label="Top 10 Games Scheduled", value="0 / 0")
            else:
                if 'rating' in stats_df.columns:
                    avg_rating = stats_df['rating'].mean()
                else:
                    avg_rating = None
                if pd.notna(avg_rating):
                    col4.metric(label="Avg BGG Rating", value=f"{avg_rating:.1f}")
                else:
                    col4.metric(label="Avg BGG Rating", value="N/A")
                
            st.divider()
            
            if not stats_df.empty:
                # --- WRITTEN SUMMARY ---
                st.markdown("### 📝 Schedule Summary")
                first_event = stats_df.iloc[0]
                last_event = stats_df.iloc[-1]
                
                # Calculations for achievements and summary
                time_spent_by_game = stats_df.groupby('Event')['Duration'].sum()
                most_time_game = time_spent_by_game.idxmax()
                most_time_hours = time_spent_by_game.max()
                
                hours_per_day = stats_df.groupby('Formatted Date')['Duration'].sum()
                ironman_day = hours_per_day.idxmax()
                ironman_hours = hours_per_day.max()

                most_played = stats_df['Event'].value_counts().idxmax()
                most_played_count = stats_df['Event'].value_counts().max()
                
                start_day = first_event['Formatted Date']
                start_game = first_event['Event']
                end_day = last_event['Formatted Date']
                end_game = last_event['Event']
                
                summary_text = f"Your WBC 2026 adventure kicks off on **{start_day}** with **{start_game}**. "
                summary_text += f"Over the convention, you'll spend **{total_hours:g} hours** at the tables across **{total_events} sessions**, playing **{unique_games} unique games**. "
                summary_text += f"Your primary focus will be **{most_time_game}**, commanding {most_time_hours:g} hours of your time. "
                summary_text += f"Pace yourself for **{ironman_day}**—that will be your heaviest day with {ironman_hours:g} hours of tabletop action! "
                summary_text += f"Your schedule officially wraps up on **{end_day}** with **{end_game}**. Good luck and roll high!"
                
                st.info(summary_text)
                st.divider()
                
                # --- ACHIEVEMENTS ---
                st.markdown("### 🏅 Convention Accolades")
                colA, colB = st.columns(2)
                
                with colA:
                    st.markdown(f"**⏳ Biggest Time Sink:** {most_time_game} ({most_time_hours:g} hours)")
                    st.markdown(f"**🔁 Most Played Game:** {most_played} ({most_played_count} sessions)")
                    
                    longest_session_idx = stats_df['Duration'].idxmax()
                    longest_session_game = stats_df.loc[longest_session_idx, 'Event']
                    longest_session_hours = stats_df.loc[longest_session_idx, 'Duration']
                    st.markdown(f"**🏃 Marathon Session:** {longest_session_game} ({longest_session_hours:g} hour block)")
                
                with colB:
                    games_per_day = stats_df.groupby('Formatted Date').size()
                    busiest_day_games = games_per_day.idxmax()
                    busiest_day_count = games_per_day.max()
                    st.markdown(f"**🐝 Busiest Day:** {busiest_day_games} ({busiest_day_count} sessions)")
                    
                    st.markdown(f"**💪 Ironman Day:** {ironman_day} ({ironman_hours:g} hours scheduled)")
                    
                    unique_games_per_day = stats_df.groupby('Formatted Date')['Event'].nunique()
                    most_variety_day = unique_games_per_day.idxmax()
                    most_variety_count = unique_games_per_day.max()
                    st.markdown(f"**🎨 Most Variety:** {most_variety_day} ({most_variety_count} different games)")

        st.divider()
        st.markdown("### Export Your Schedule")
        
        csv_df = output_df[['Date', 'Day Code', 'Time', 'Duration', 'Event', 'Round/Heat', 'Location', 'GM']].copy()
        csv_df['Time'] = csv_df['Time'].apply(format_hhmm)
        standard_csv = csv_df.to_csv(index=False).encode('utf-8')
        
        gcal_df = pd.DataFrame()
        gcal_df['Subject'] = output_df.apply(clean_gcal_subject, axis=1)
        
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
