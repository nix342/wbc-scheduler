import streamlit as st
import pandas as pd
import json
from streamlit_javascript import st_javascript

from utils import load_wbc_schedule, clean_name
from engine import generate_itinerary
from sidebar import render_sidebar
from views import render_visual_schedule, render_tabular_data, render_metrics_and_summary, render_export_section

st.set_page_config(page_title="WBC 2026 Custom Scheduler", layout="wide")

# --- UI HEADER ---
st.markdown("<h1 style='text-align: center; color: #cd7f32;'>🎲 WBC 2026 Scheduler</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-size: 18px;'>Upload your BGG Collection or select your Top 10 games to generate a personalized itinerary!</p>", unsafe_allow_html=True)
st.divider()

# --- INIT BROWSER CACHE ---
ls_result = st_javascript("localStorage.getItem('wbc_prefs') || 'NONE';")
if "prefs" not in st.session_state:
    if ls_result == 0: st.stop()  
    elif ls_result == "NONE": st.session_state.prefs = {}
    else:
        try: st.session_state.prefs = json.loads(ls_result)
        except: st.session_state.prefs = {}

# --- LOAD DATA ---
wbc = load_wbc_schedule()
unique_wbc_events = sorted(wbc['Event'].dropna().unique())
wbc['clean_name'] = wbc['Event'].apply(clean_name)
status_area = st.empty()

# --- RENDER SIDEBAR & GET INPUTS ---
user_inputs = render_sidebar(unique_wbc_events, st.session_state.prefs)

# --- PRE-PROCESS USER FAVORITES ---
proceed = False
favs = pd.DataFrame()
owned_games_clean = [] # <--- Initialize the empty list

if user_inputs["input_method"] == "Select Top 10 Games manually":
    if not user_inputs["top10_games"] and not user_inputs["selected_priorities"]:
        status_area.info("👈 Please select your Top 10 or Priority games in the sidebar to generate a schedule!")
    else:
        favs = pd.DataFrame({
            'objectname': user_inputs["top10_games"],
            'rating': [10.0 - (i * 0.1) for i in range(len(user_inputs["top10_games"]))]
        })
        favs['clean_name'] = favs['objectname'].apply(clean_name)
        proceed = True
else:
    if user_inputs["uploaded_file"] is None and not user_inputs["selected_priorities"]:
        status_area.info("👈 Please upload your BGG CSV or select Priority games in the sidebar to generate a schedule!")
    else:
        if user_inputs["uploaded_file"] is not None:
            coll = pd.read_csv(user_inputs["uploaded_file"])
            
            # --- NEW: Extract Owned Games for the Packing List ---
            if 'own' in coll.columns:
                owned_games_clean = coll[coll['own'] == 1]['objectname'].apply(clean_name).tolist()
            else:
                owned_games_clean = coll['objectname'].apply(clean_name).tolist()
                
            coll['rating'] = pd.to_numeric(coll['rating'], errors='coerce')
            favs = coll[coll['rating'] >= user_inputs["rating_cutoff"]].sort_values('rating', ascending=False)
            favs['clean_name'] = favs['objectname'].apply(clean_name)
        else:
            favs = pd.DataFrame(columns=['objectname', 'clean_name', 'rating'])
        proceed = True
        
# --- RUN ENGINE & RENDER VIEWS ---
if proceed:
    with status_area.container():
        with st.spinner('Crunching the convention matrix! Building your conflict-free itinerary...'):
            
            # Pass our parsed logic exactly as the engine expects it
            success_flag, status_type, status_message, output_df = generate_itinerary(
                wbc, favs, user_inputs["selected_priorities"], user_inputs["games_to_exclude"], 
                user_inputs["games_to_cap"], user_inputs["game_caps"], user_inputs["arrival_date"], 
                user_inputs["arrival_time"], user_inputs["departure_date"], user_inputs["departure_time"], 
                user_inputs["exclude_demos"], user_inputs["exclude_juniors"], user_inputs["exclude_no_round"], 
                user_inputs["schedule_philosophy"], user_inputs["fill_gaps"]
            )

    if status_type == "warning": status_area.warning(status_message)
    elif status_type == "success": status_area.success(status_message)

    if success_flag:
        st.subheader("Your Personalized Itinerary")
        main_tab1, main_tab2, main_tab3 = st.tabs(["📊 Visual Schedule", "📋 Tabular Data", "📈 Custom Metrics"])
        
        with main_tab1: render_visual_schedule(output_df)
        with main_tab2: render_tabular_data(output_df)
        with main_tab3: render_metrics_and_summary(output_df, user_inputs["input_method"], user_inputs["top10_games"], owned_games_clean)
            
        render_export_section(output_df)
