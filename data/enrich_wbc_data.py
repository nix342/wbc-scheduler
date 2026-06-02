import pandas as pd
import difflib
from pathlib import Path

# --- Configuration ---
DATA_DIR = Path(__file__).resolve().parent
WBC_CSV = DATA_DIR / 'wbc2026.csv'
BGG_CSV = DATA_DIR / 'boardgames_ranks.csv'
OUTPUT_CSV = DATA_DIR / 'wbc2026_enriched.csv'

def main():
    print("Loading datasets...")
    # Load WBC schedule, skipping the first 5 metadata rows
    df_wbc = pd.read_csv(WBC_CSV, skiprows=5)
    df_bgg = pd.read_csv(BGG_CSV)
    
    # Pre-clean for easier matching
    df_bgg['name_lower'] = df_bgg['name'].str.lower().str.strip()

    name_mapping = {}
    
    # Filter for actual games
    games_df = df_wbc[df_wbc['Round/Heat'].notna() & (df_wbc['Round/Heat'] != '--')]
    unique_wbc_games = games_df['Event'].dropna().unique()

    # Manual fixes for naming discrepancies between WBC and BGG
    manual_overrides = {
        '18xx': None, # Generic genre, no specific BGG entry
        'Amun Re': 'Amun-Re',
        'Through the Ages': 'Through the Ages: A New Story of Civilization',
        'Five Tribes': 'Five Tribes: The Djinns of Naqala',
        'Formula De': 'Formula D',
        'Castles of Burgundy': 'The Castles of Burgundy',
        'Hannibal: Rome vs Carthage': 'Hannibal: Rome vs. Carthage',
        'Ra!': 'Ra',
        "Star Wars: Queen's Gambit": "Star Wars: The Queen's Gambit",
        'Panzerblitz': 'PanzerBlitz',
        'Euphrat & Tigris': 'Tigris & Euphrates',
        "Freeman's Farm": "Freeman's Farm 1777",
        'B-17': 'B-17: Queen of the Skies',
        'Great Campaigns of the ACW': None # Series, not a single game
    }

    print("Matching games to BGG Database...")
    for game in unique_wbc_games:
        # 1. Check Manual Overrides
        if game in manual_overrides:
            bgg_name = manual_overrides[game]
            if bgg_name is None:
                name_mapping[game] = None
                continue
            match = df_bgg[df_bgg['name'] == bgg_name]
            if not match.empty:
                name_mapping[game] = match.sort_values('usersrated', ascending=False).iloc[0]['id']
            else:
                name_mapping[game] = None
            continue

        # 2. Check Exact Match
        exact_match = df_bgg[df_bgg['name'] == game]
        if not exact_match.empty:
            best_id = exact_match.sort_values('usersrated', ascending=False).iloc[0]['id']
            name_mapping[game] = best_id
            continue
            
        # 3. Check Case-Insensitive Exact Match
        ci_match = df_bgg[df_bgg['name_lower'] == game.lower()]
        if not ci_match.empty:
            best_id = ci_match.sort_values('usersrated', ascending=False).iloc[0]['id']
            name_mapping[game] = best_id
            continue
        
        # 4. Fuzzy Matching (Restricted to top 10,000 most rated games to avoid obscure false positives)
        top_games = df_bgg.sort_values('usersrated', ascending=False).head(10000)
        matches = difflib.get_close_matches(game, top_games['name'].astype(str), n=1, cutoff=0.75)
        
        if matches:
            matched_name = matches[0]
            best_id = top_games[top_games['name'] == matched_name].iloc[0]['id']
            name_mapping[game] = best_id
        else:
            name_mapping[game] = None 

    # Build the stats payload
    bgg_info = []
    for wbc_name, bgg_id in name_mapping.items():
        if pd.notna(bgg_id):
            row = df_bgg[df_bgg['id'] == bgg_id].iloc[0]
            bgg_info.append({
                'Event': wbc_name,
                'BGG_ID': int(bgg_id),
                'BGG_Name': row['name'],
                'BGG_Rank': int(row['rank']) if pd.notna(row['rank']) else None,
                'BGG_Rating': row['average']
            })
        else:
            bgg_info.append({
                'Event': wbc_name,
                'BGG_ID': None,
                'BGG_Name': None,
                'BGG_Rank': None,
                'BGG_Rating': None
            })

    stats_df = pd.DataFrame(bgg_info)

    # Merge stats back into the main WBC schedule
    final_df = df_wbc.merge(stats_df, on='Event', how='left')
    
    # Drop any duplicate rows created by the merge
    final_df = final_df.drop_duplicates()

    # Save to disk
    final_df.to_csv(OUTPUT_CSV, index=False)
    print(f"Success! Enriched schedule saved to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()