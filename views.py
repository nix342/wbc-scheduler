import streamlit as st
import pandas as pd
import altair as alt
from utils import format_hhmm, get_border_color, clean_name

def render_visual_schedule(output_df):
    viz_df = output_df.copy()
    viz_df['Border_Color'] = viz_df.apply(get_border_color, axis=1)
    viz_df['Logical Date'] = viz_df.apply(lambda row: row['Date_parsed'] - pd.Timedelta(days=1) if row['Time'] < 8 else row['Date_parsed'], axis=1)
    viz_df['Plot Time'] = viz_df.apply(lambda row: row['Time'] + 24 if row['Time'] < 8 else row['Time'], axis=1)
    viz_df['Plot End Time'] = viz_df['Plot Time'] + viz_df['Duration']
    viz_df['Start Time'] = viz_df['Time'].apply(format_hhmm)
    viz_df['End Time'] = ((viz_df['Time'] + viz_df['Duration']) % 24).apply(format_hhmm)
    viz_df['Formatted Date'] = viz_df['Logical Date'].dt.strftime('%A, %b %d')
    
    unique_dates = viz_df.sort_values('Logical Date')['Formatted Date'].unique()
    safe_palette = ['#E6194B', '#F58231', '#FFE119', '#911EB4', '#F032E6', '#800000', '#9A6324', '#808000', '#E6BEFF', '#FFD8B1', '#FABEBE', '#A9A9A9', '#FF9999', '#CC0000', '#FFCC00', '#CC99FF', '#990099', '#660066', '#330033', '#FF6600']
    
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
                ).properties(width=800)

                x_scale = alt.Scale(domain=[8, 26], clamp=True)
                label_expr = "datum.value >= 24 ? (datum.value - 24 < 10 ? '0' + (datum.value - 24) : (datum.value - 24)) + '00' : (datum.value < 10 ? '0' + datum.value : datum.value) + '00'"
                
                bottom_axis = base_chart.mark_bar(cornerRadius=4, height=20).encode(
                    x=alt.X('Plot Time', title='Time (HHMM)', scale=x_scale, axis=alt.Axis(orient='bottom', tickCount=18, labelExpr=label_expr)),
                    stroke=alt.Stroke('Border_Color:N', scale=None),
                    strokeWidth=alt.condition(alt.datum.Border_Color != 'transparent', alt.value(3), alt.value(0))
                )
                top_axis = base_chart.mark_bar(opacity=0).encode(
                    x=alt.X('Plot Time', title='', scale=x_scale, axis=alt.Axis(orient='top', tickCount=18, labelExpr=label_expr))
                )
                st.altair_chart(alt.layer(bottom_axis, top_axis).resolve_scale(x='independent').interactive(), use_container_width=True)
    else:
        st.info("No events scheduled yet. Adjust your filters or constraints!")

def render_tabular_data(output_df):
    table_df = output_df[['Date', 'Day Code', 'Time', 'Duration', 'Event', 'Round/Heat', 'Location', 'GM']].copy()
    table_df['Time'] = table_df['Time'].apply(format_hhmm)
    st.dataframe(table_df, use_container_width=True, hide_index=True)

def render_metrics_and_summary(output_df, input_method, top10_games, owned_games_clean=None):
    stats_df = output_df.copy()
    
    # Pre-calculate Logical Dates and actual Datetimes right at the top
    stats_df['Logical Date'] = stats_df.apply(lambda row: row['Date_parsed'] - pd.Timedelta(days=1) if row['Time'] < 8 else row['Date_parsed'], axis=1)
    stats_df['Formatted Date'] = stats_df['Logical Date'].dt.strftime('%A, %b %d')
    stats_df['start_dt'] = stats_df['Date_parsed'] + pd.to_timedelta(stats_df['Time'], unit='h')
    stats_df['end_dt'] = stats_df['Date_parsed'] + pd.to_timedelta(stats_df['Time'] + stats_df['Duration'], unit='h')
    
    # Sort chronologically so everything is perfectly ordered
    stats_df = stats_df.sort_values('start_dt').reset_index(drop=True)
    
    # --- True Total Hours Calculation (Merging Overlapping Intervals) ---
    merged_intervals = []
    for _, row in stats_df.iterrows():
        start = row['start_dt']
        end = row['end_dt']
        if not merged_intervals:
            merged_intervals.append([start, end])
        else:
            last_end = merged_intervals[-1][1]
            if start <= last_end:
                merged_intervals[-1][1] = max(last_end, end)
            else:
                merged_intervals.append([start, end])
                
    true_total_hours = sum((iv[1] - iv[0]).total_seconds() for iv in merged_intervals) / 3600.0 if merged_intervals else 0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(label="Total Sessions", value=len(stats_df))
    col2.metric(label="Unique Games", value=stats_df['Event'].nunique())
    col3.metric(label="Total Hours", value=f"{true_total_hours:g} hrs")
    
    if input_method == "Select Top 10 Games manually":
        top10_played = stats_df[stats_df['Event'].isin(top10_games)]['Event'].nunique() if top10_games else 0
        col4.metric(label="Top 10 Games Scheduled", value=f"{top10_played} / {len(top10_games)}")
    else:
        avg_rating = stats_df['rating'].mean() if 'rating' in stats_df.columns else None
        col4.metric(label="Avg BGG Rating", value=f"{avg_rating:.1f}" if pd.notna(avg_rating) else "N/A")
        
    st.divider()
    
    if not stats_df.empty:
        # Calculate the gaps between events
        stats_df['max_end_so_far'] = stats_df['end_dt'].cummax().shift(1)
        stats_df['gap'] = stats_df['start_dt'] - stats_df['max_end_so_far']
        
        max_gap_hours = 0
        gap_start_time = ""
        second_gap_hours = 0
        second_gap_start_time = ""
        is_tuesday_auction = False
        
        if len(stats_df) > 1:
            # Sort all valid gaps from largest to smallest
            valid_gaps = stats_df[stats_df['gap'].dt.total_seconds() > 0].sort_values('gap', ascending=False)
            
            if not valid_gaps.empty:
                first_gap_row = valid_gaps.iloc[0]
                max_gap_hours = first_gap_row['gap'].total_seconds() / 3600.0
                gap_start_dt = pd.to_datetime(first_gap_row['max_end_so_far'])
                gap_start_time = gap_start_dt.strftime('%A %I:%M %p')
                
                # Check if the biggest gap is Tuesday (weekday 1) morning/early afternoon
                if gap_start_dt.weekday() == 1 and gap_start_dt.hour < 14:
                    is_tuesday_auction = True
                    
                if len(valid_gaps) > 1:
                    second_gap_row = valid_gaps.iloc[1]
                    second_gap_hours = second_gap_row['gap'].total_seconds() / 3600.0
                    second_gap_start_time = pd.to_datetime(second_gap_row['max_end_so_far']).strftime('%A %I:%M %p')

        time_spent_by_game = stats_df.groupby('Event')['Duration'].sum()
        most_time_game = time_spent_by_game.idxmax()
        most_time_hours = time_spent_by_game.max()

        # --- WRITTEN SUMMARY ---
        summary_text = f"Your WBC 2026 adventure kicks off on **{stats_df.iloc[0]['Formatted Date']}** with **{stats_df.iloc[0]['Event']}**. "
        summary_text += f"Over the convention, you'll spend **{true_total_hours:g} hours** at the tables across **{len(stats_df)} sessions**, playing **{stats_df['Event'].nunique()} unique games**. "
        summary_text += f"Your primary focus will be **{most_time_game}**, commanding {most_time_hours:g} hours of your time. "
        
        if max_gap_hours > 0:
            if is_tuesday_auction and second_gap_hours > 0:
                summary_text += f"Besides the traditional Tuesday morning break for the auction, your longest break is a **{second_gap_hours:g}-hour** window starting on {second_gap_start_time}. "
            elif is_tuesday_auction:
                summary_text += f"Your longest break perfectly lines up with the traditional Tuesday morning auction ({max_gap_hours:g} hours). "
            else:
                summary_text += f"Make sure to catch your breath during your longest break: a **{max_gap_hours:g}-hour** window starting on {gap_start_time}. "
                
        summary_text += f"Your schedule officially wraps up on **{stats_df.iloc[-1]['Formatted Date']}** with **{stats_df.iloc[-1]['Event']}**. Good luck and roll high!"
        
        st.info(summary_text)
        st.divider()
        
        # --- ACHIEVEMENTS ---
        st.markdown("### 🏅 Convention Accolades")
        colA, colB = st.columns(2)
        with colA:
            st.markdown(f"**⏳ Biggest Time Sink:** {most_time_game} ({most_time_hours:g} hours)")
            st.markdown(f"**🔁 Most Played Game:** {stats_df['Event'].value_counts().idxmax()} ({stats_df['Event'].value_counts().max()} sessions)")
            longest_session = stats_df.loc[stats_df['Duration'].idxmax()]
            st.markdown(f"**🏃 Marathon Session:** {longest_session['Event']} ({longest_session['Duration']:g} hour block)")
        with colB:
            unique_games_per_day = stats_df.groupby('Formatted Date')['Event'].nunique()
            st.markdown(f"**🎨 Most Variety:** {unique_games_per_day.idxmax()} ({unique_games_per_day.max()} different games)")
            
            # Update the UI gap readouts to handle the Tuesday exception
            if max_gap_hours > 0:
                if is_tuesday_auction and second_gap_hours > 0:
                    st.markdown(f"**🛏️ Biggest Time Gaps:** {max_gap_hours:g} hrs (Tuesday Auction) & {second_gap_hours:g} hrs (Starts {second_gap_start_time})")
                else:
                    st.markdown(f"**🛏️ Biggest Time Gap:** {max_gap_hours:g} hours (Starts {gap_start_time})")
            else:
                st.markdown("**🛏️ Biggest Time Gap:** None! Booked solid.")

        # --- PACKING LIST ---
        if input_method == "Upload BGG Collection CSV" and owned_games_clean is not None:
            st.divider()
            st.markdown("### 🎒 Packing List")
            
            scheduled_games = stats_df['Event'].unique()
            packing_list = []
            
            for g in scheduled_games:
                cg = clean_name(g)
                for og in owned_games_clean:
                    if cg == og or (len(cg) > 5 and cg in og):
                        packing_list.append(g)
                        break
                        
            if packing_list:
                st.success("You own these scheduled games! Don't forget to pack them:")
                cols = st.columns(3)
                for idx, game in enumerate(sorted(packing_list)):
                    cols[idx % 3].markdown(f"📦 **{game}**")
            else:
                st.info("You don't own any of the games on your schedule. Travel light!")

def render_export_section(output_df):
    st.divider()
    st.markdown("### Export Your Schedule")
    
    # 1. Standard CSV
    csv_df = output_df[['Date', 'Day Code', 'Time', 'Duration', 'Event', 'Round/Heat', 'Location', 'GM']].copy()
    csv_df['Time'] = csv_df['Time'].apply(format_hhmm)
    standard_csv = csv_df.to_csv(index=False).encode('utf-8')
    
    def clean_gcal_subject(row):
        r = str(row['Round/Heat'])
        if pd.isna(row['Round/Heat']) or r.strip() in ['', 'nan', 'none']: return str(row['Event'])
        return f"{row['Event']} ({row['Round/Heat']})"
        
    # 2. GCal Sync CSV
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

    # 3. Universal Apple/Outlook .ICS File
    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//WBC Scheduler//EN",
        "CALSCALE:GREGORIAN"
    ]
    for _, row in output_df.iterrows():
        s_dt = row['Date_parsed'] + pd.to_timedelta(row['Time'], unit='h')
        e_dt = row['Date_parsed'] + pd.to_timedelta(row['Time'] + row['Duration'], unit='h')
        
        # ICS Time Formatting
        dtstart = s_dt.strftime('%Y%m%dT%H%M%S')
        dtend = e_dt.strftime('%Y%m%dT%H%M%S')
        
        subject = clean_gcal_subject(row).replace(',', '\\,')
        loc = str(row.get('Location', 'TBD')).replace(',', '\\,')
        desc = f"GM: {row.get('GM', 'TBD')}".replace(',', '\\,')
        
        ics_lines.extend([
            "BEGIN:VEVENT",
            f"DTSTART;TZID=America/New_York:{dtstart}",
            f"DTEND;TZID=America/New_York:{dtend}",
            f"SUMMARY:{subject}",
            f"LOCATION:{loc}",
            f"DESCRIPTION:{desc}",
            "BEGIN:VALARM",       # <--- Native 15-Minute Push Notification!
            "TRIGGER:-PT15M",
            "ACTION:DISPLAY",
            "DESCRIPTION:15 Minute Warning!",
            "END:VALARM",
            "END:VEVENT"
        ])
    ics_lines.append("END:VCALENDAR")
    ics_export = "\r\n".join(ics_lines).encode('utf-8')

    # 4. Pocket PDF Itinerary
    pdf_bytes = None
    try:
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", 'B', 16)
        pdf.cell(0, 10, "WBC 2026 Custom Itinerary", ln=True, align='C')
        pdf.ln(5)
        
        pdf_df = output_df.copy()
        pdf_df['start_dt'] = pdf_df['Date_parsed'] + pd.to_timedelta(pdf_df['Time'], unit='h')
        pdf_df = pdf_df.sort_values('start_dt')
        
        for date_str, group in pdf_df.groupby(pdf_df['start_dt'].dt.strftime('%A, %b %d'), sort=False):
            pdf.set_font("Helvetica", 'B', 12)
            pdf.set_fill_color(200, 220, 255) # Light Blue Headers
            pdf.cell(0, 8, date_str, ln=True, fill=True)
            
            pdf.set_font("Helvetica", '', 10)
            for _, row in group.iterrows():
                s_time = (row['Date_parsed'] + pd.to_timedelta(row['Time'], unit='h')).strftime('%I:%M %p')
                e_time = (row['Date_parsed'] + pd.to_timedelta(row['Time'] + row['Duration'], unit='h')).strftime('%I:%M %p')
                subj = clean_gcal_subject(row)
                loc = str(row.get('Location', ''))
                
                line = f"{s_time} - {e_time}  |  {subj}  |  {loc}"
                line = line.encode('latin-1', 'replace').decode('latin-1') # Strip unsupported unicode
                pdf.cell(0, 6, line, ln=True)
            pdf.ln(3)
            
        try:
            pdf_bytes = pdf.output(dest='S').encode('latin-1') # FPDF1
        except:
            pdf_bytes = bytes(pdf.output()) # FPDF2
    except ImportError:
        pass # If FPDF isn't installed, fail gracefully

    # --- Render Download Buttons ---
    colA, colB, colC, colD = st.columns(4)
    colA.download_button("📥 Standard CSV", data=standard_csv, file_name="wbc_itinerary.csv", mime="text/csv", use_container_width=True)
    colB.download_button("📅 GCal Sync (CSV)", data=gcal_csv, file_name="wbc_gcal_import.csv", mime="text/csv", use_container_width=True)
    colC.download_button("📲 Apple/Outlook (.ICS)", data=ics_export, file_name="wbc_calendar.ics", mime="text/calendar", use_container_width=True)
    
    if pdf_bytes:
        colD.download_button("📄 Pocket PDF", data=pdf_bytes, file_name="wbc_itinerary.pdf", mime="application/pdf", use_container_width=True)
    else:
        colD.button("📄 Pocket PDF (Requires fpdf2)", disabled=True, use_container_width=True)

    st.caption("*Pro-Tip: Use the **.ICS** file to import natively into Apple Calendar or Outlook (includes automatic 15-minute push notification warnings!). If the PDF export button is disabled, open your terminal and run `pip install fpdf2`.*")
    
