import pandas as pd
import re
from utils import is_valid_round

def generate_itinerary(wbc, favs, selected_priorities, games_to_exclude, games_to_cap, game_caps, 
                       arrival_date, arrival_time, departure_date, departure_time, 
                       exclude_demos, exclude_juniors, exclude_no_round, 
                       schedule_philosophy, fill_gaps):
    
    output_df = pd.DataFrame()

    # --- INITIAL MATCHING ---
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
        return False, "warning", "No matching games found between your selections and the WBC schedule.", output_df

    matched = pd.DataFrame(matches)
    
    # --- TIME & EXCLUSION FILTERING ---
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
    if exclude_juniors:
        matched = matched[~matched['Event'].astype(str).str.contains('Junior', case=False, na=False)]
        matched = matched[~matched['Round/Heat'].astype(str).str.contains('Junior', case=False, na=False)]
    if exclude_no_round:
        matched = matched[matched['Round/Heat'].apply(is_valid_round)]
    
    if matched.empty:
        return False, "warning", "Your constraints (or arrival/departure times) removed all remaining games from consideration!", output_df

    # --- TOURNAMENT PREP ---
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
        
        if use_variety_pass and 'heat' in stage_str_lower and scheduled_heats[game] >= 1: continue

        if row['Event'] in game_caps:
            stage_num = get_round_number(stage)
            if (stage_num is not None and stage_num > game_caps[row['Event']]) or is_elimination(stage): continue
        
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
                if (stage_num is not None and stage_num > game_caps[row['Event']]) or is_elimination(stage): continue

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
            game_str_lower = str(game).lower()
            
            if game in games_to_exclude: continue
            if exclude_demos and 'demo' in stage_str_lower: continue
            if exclude_juniors and ('junior' in stage_str_lower or 'junior' in game_str_lower): continue
            if exclude_no_round and not is_valid_round(stage): continue
            if not is_within_convention_window(row): continue
            
            if row['Event'] in game_caps:
                stage_num = get_round_number(stage)
                if (stage_num is not None and stage_num > game_caps[row['Event']]): continue
            
            if is_elimination(stage): continue
            r_num = get_round_number(stage)
            if r_num is not None and r_num > 1 and 'heat' not in stage_str_lower: continue
                
            if game not in scheduled_stages:
                scheduled_stages[game] = []
                scheduled_heats[game] = 0
                scheduled_rounds[game] = 0
                
            if use_variety_pass and 'heat' in stage_str_lower and scheduled_heats[game] >= 1: continue
                
            if date not in booked: booked[date] = []
            
            conflict = False
            for b_start, b_end, b_stage, b_tier, b_game in booked[date]:
                if max(start, b_start) < min(end, b_end):
                    conflict = True
                    break
                    
            if not conflict:
                booked[date].append((start, end, stage, -1, game))
                schedule.append(row.to_dict())
                scheduled_stages[game].append(stage)
                if 'heat' in stage_str_lower: scheduled_heats[game] += 1
                if 'round' in stage_str_lower and 'mulligan' not in stage_str_lower: scheduled_rounds[game] += 1

    if not schedule:
        return False, "warning", "All matching games either conflicted or hit tournament caps. No schedule could be generated.", output_df
        
    output_df = pd.DataFrame(schedule).sort_values(['Date_parsed', 'Time'])
    return True, "success", "Success! Your custom itinerary is ready below.", output_df
