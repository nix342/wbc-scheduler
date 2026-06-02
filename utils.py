import pandas as pd
import re
import streamlit as st
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / 'data'
ENRICHED_CSV = DATA_DIR / 'wbc2026_enriched.csv'
RAW_CSV = DATA_DIR / 'wbc2026.csv'

def _read_wbc_csv(path, use_raw_format=False):
    if use_raw_format:
        return pd.read_csv(path, skiprows=5)
    return pd.read_csv(path)

@st.cache_data
def load_wbc_schedule():
    csv_path = ENRICHED_CSV if ENRICHED_CSV.exists() else RAW_CSV
    if csv_path == ENRICHED_CSV:
        df = _read_wbc_csv(csv_path)
        if 'Time' not in df.columns:
            df = _read_wbc_csv(csv_path, use_raw_format=True)
    else:
        df = _read_wbc_csv(csv_path, use_raw_format=True)

    df.columns = df.columns.str.strip()
    if 'Time' not in df.columns or 'Duration' not in df.columns or 'Date' not in df.columns:
        raise ValueError(f"Unable to load WBC schedule from {csv_path}: expected columns not found.")

    df['Time'] = pd.to_numeric(df['Time'], errors='coerce')
    df['Duration'] = pd.to_numeric(df['Duration'], errors='coerce')
    df['Date_parsed'] = pd.to_datetime(df['Date'], format='%m/%d/%y', errors='coerce')
    return df.dropna(subset=['Time', 'Duration', 'Date_parsed'])

def clean_name(name):
    return re.sub(r'[^a-z0-9]', '', str(name).lower()) if pd.notna(name) else ""

def is_valid_round(row):
    stage_str = row['Round/Heat']
    event_str = row['Event']
    s = str(stage_str).lower()
    e = str(event_str).lower()
    
    # Exception 1: Juniors events are valid games, even if they lack round info
    if 'junior' in s or 'junior' in e: return True
    # Exception 2: Demos are valid games
    if 'demo' in s: return True 
    
    if pd.isna(stage_str) or s.strip() in ['', 'nan', 'none']: return False
    if bool(re.search(r'\d', s)): return True
    if bool(re.search(r'quarterfinal|semifinal|final|mulligan', s)): return True

    return False

def format_hhmm(t):
    if pd.isna(t): return ""
    h = int(t) % 24
    m = int(round((t - int(t)) * 60))
    return f"{h:02d}{m:02d}"

def get_border_color(row):
    stage = str(row['Round/Heat']).lower()
    game = str(row['Event']).lower()
    
    # 1. Explicitly check for specific event types FIRST
    if 'junior' in stage or 'junior' in game: return '#00FF00' # Green for Juniors
    if 'demo' in stage: return '#FFFFFF'                       # White for Demos
    
    # 2. THEN check if it lacks round info (Seminars/Meetings)
    if not is_valid_round(row): return '#0000FF'               # Blue for Seminars/Meetings
    
    # 3. Finally, check for Playoffs
    if 'quarterfinal' in stage: return '#cd7f32' 
    if 'semifinal' in stage: return '#c0c0c0'     
    if 'final' in stage: return '#ffd700'         
    return 'transparent'
