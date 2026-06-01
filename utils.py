import pandas as pd
import re
import streamlit as st

@st.cache_data
def load_wbc_schedule():
    df = pd.read_csv('wbc2026.csv', skiprows=5)
    df['Time'] = pd.to_numeric(df['Time'], errors='coerce')
    df['Duration'] = pd.to_numeric(df['Duration'], errors='coerce')
    df['Date_parsed'] = pd.to_datetime(df['Date'], format='%m/%d/%y', errors='coerce')
    return df.dropna(subset=['Time', 'Duration', 'Date_parsed'])

def clean_name(name):
    return re.sub(r'[^a-z0-9]', '', str(name).lower()) if pd.notna(name) else ""

def is_valid_round(stage_str):
    s = str(stage_str).lower()
    if pd.isna(stage_str) or s.strip() in ['', 'nan', 'none']: return False
    if bool(re.search(r'\d', s)): return True
    if bool(re.search(r'quarterfinal|semifinal|final|mulligan', s)): return True
    if 'demo' in s: return True 
    return False

def format_hhmm(t):
    if pd.isna(t): return ""
    h = int(t) % 24
    m = int(round((t - int(t)) * 60))
    return f"{h:02d}{m:02d}"

def get_border_color(row):
    stage = str(row['Round/Heat']).lower()
    game = str(row['Event']).lower()
    
    if not is_valid_round(row['Round/Heat']): return '#0000FF' # Blue for Seminars/Meetings
    if 'junior' in stage or 'junior' in game: return '#00FF00' # Green for Juniors
    if 'demo' in stage: return '#FFFFFF'                       # White for Demos
    
    if 'quarterfinal' in stage: return '#cd7f32' 
    if 'semifinal' in stage: return '#c0c0c0'     
    if 'final' in stage: return '#ffd700'         
    return 'transparent'
