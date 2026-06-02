import streamlit as st
import pandas as pd
import json
from streamlit_javascript import st_javascript
import streamlit.components.v1 as components

def render_sidebar(unique_wbc_events, prefs):
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
            options=unique_wbc_events, default=def_top10, max_selections=10
        )
        
        ordered_games = [g for g in def_top10 if g in selected_games]
        ordered_games += [g for g in selected_games if g not in ordered_games]
        
        if len(ordered_games) > 1:
            st.sidebar.caption("↕️ **Edit the Rank numbers below** to instantly reorder your priorities (1 = Highest Priority).")
            rank_df = pd.DataFrame({"Rank": list(range(1, len(ordered_games) + 1)), "Game": ordered_games})
            edited_rank_df = st.sidebar.data_editor(
                rank_df,
                column_config={
                    "Rank": st.column_config.NumberColumn("Rank", min_value=1, max_value=99, step=1, width="small"),
                    "Game": st.column_config.TextColumn("Game", disabled=True)
                },
                hide_index=True, use_container_width=True
            )
            top10_games = edited_rank_df.sort_values("Rank")["Game"].tolist()
        else:
            top10_games = ordered_games
    else:
        uploaded_file = st.sidebar.file_uploader("Upload your BGG Collection CSV", type=["csv"])
        def_rate = int(prefs.get("rate", 7))
        rating_cutoff = st.sidebar.slider("Minimum BGG Rating to consider", 1, 10, def_rate, help="Games below this rating will be ignored.")

    st.sidebar.header("2. Your Convention Details")
    arrival_date = st.sidebar.date_input("Arrival Date", pd.to_datetime(prefs.get("arr_date", "2026-07-25")))
    arrival_time = st.sidebar.slider("Arrival Time (24h Clock)", 0, 23, int(prefs.get("arr_time", 9)))
    departure_date = st.sidebar.date_input("Departure Date", pd.to_datetime(prefs.get("dep_date", "2026-08-02")))
    departure_time = st.sidebar.slider("Departure Time (24h Clock)", 0, 23, int(prefs.get("dep_time", 15)))

    st.sidebar.header("3. Priority Must-Play Games")
    if input_method == "Select Top 10 Games manually" and not prefs.get("pri_saved_flag", False):
        def_pri = top10_games[:3]
    else:
        def_pri = [g for g in prefs.get("pri", []) if g in unique_wbc_events]
        
    selected_priorities = st.sidebar.multiselect(
        "Select up to 3 'Must-Play' games to schedule first:",
        options=unique_wbc_events, default=def_pri, max_selections=3
    )

    st.sidebar.header("4. Filters & Preferences")
    with st.sidebar.expander("⚙️ Advanced Scheduling Filters", expanded=False):
        st.markdown("**Tournament Limits & Exclusions**")
        games_to_exclude = st.multiselect("Skip specific games:", options=unique_wbc_events, default=[g for g in prefs.get("excl", []) if g in unique_wbc_events])
        games_to_cap = st.multiselect("Limit tournament runs for:", options=unique_wbc_events, default=[g for g in prefs.get("cap", []) if g in unique_wbc_events])
        
        game_caps = {}
        saved_caps = prefs.get("c_caps", {})
        for g in games_to_cap:
            game_caps[g] = st.number_input(f"Max Round/Heat for {g}:", min_value=1, max_value=10, value=int(saved_caps.get(g, 1)), step=1)
            
        st.divider()
        st.markdown("**Algorithm Preferences**")
        exclude_demos = st.checkbox("Exclude Demo Rounds", value=prefs.get("demo", True))
        exclude_juniors = st.checkbox("Exclude Juniors Events", value=prefs.get("juniors", True))
        exclude_no_round = st.checkbox("Exclude Seminars & Meetings", value=prefs.get("no_round", True))
        fill_gaps = st.checkbox("Fill Empty Time Slots", value=prefs.get("fill", False))
        
        options = ["Maximize Playoff Chances (Prioritize repeat heats)", "Maximize Variety (Prioritize single heats of many games)"]
        schedule_philosophy = st.radio("Scheduling Strategy Preference", options=options, index=int(prefs.get("phil", 0)))

    st.sidebar.divider()
    if st.sidebar.button("💾 Save Settings to Browser", use_container_width=True):
        new_prefs = {
            "input_method": input_method, "top10": top10_games, "rate": rating_cutoff,
            "arr_date": arrival_date.strftime("%Y-%m-%d"), "arr_time": arrival_time,
            "dep_date": departure_date.strftime("%Y-%m-%d"), "dep_time": departure_time,
            "pri": selected_priorities, "pri_saved_flag": True, "excl": games_to_exclude,
            "cap": games_to_cap, "c_caps": game_caps, "demo": exclude_demos,
            "juniors": exclude_juniors, "no_round": exclude_no_round, 
            "fill": fill_gaps, "phil": options.index(schedule_philosophy)
        }
        st_javascript(f"localStorage.setItem('wbc_prefs', JSON.stringify({json.dumps(new_prefs)}));")
        st.sidebar.success("Saved! Your settings will auto-load next time.")

    if st.sidebar.button("🗑️ Clear Form & Reset Defaults", use_container_width=True):
        components.html("<script>localStorage.removeItem('wbc_prefs'); window.parent.location.reload();</script>", height=0)
        st.stop()

    return {
        "input_method": input_method, "top10_games": top10_games, "uploaded_file": uploaded_file, "rating_cutoff": rating_cutoff,
        "arrival_date": arrival_date, "arrival_time": arrival_time, "departure_date": departure_date, "departure_time": departure_time,
        "selected_priorities": selected_priorities, "games_to_exclude": games_to_exclude, "games_to_cap": games_to_cap, "game_caps": game_caps,
        "exclude_demos": exclude_demos, "exclude_juniors": exclude_juniors, "exclude_no_round": exclude_no_round,
        "schedule_philosophy": schedule_philosophy, "fill_gaps": fill_gaps
    }
