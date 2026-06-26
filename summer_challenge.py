import streamlit as st
import pandas as pd
from PIL import Image
import pytesseract
import re
from datetime import datetime, timedelta
import io

st.set_page_config(page_title="Summer Challenge", layout="centered")

st.title("🔥 Summer Challenge Tracker")
st.caption("Upload workout screenshots → Auto standings + WhatsApp message")

# --- Config ---
PARTICIPANTS = ["Raaj", "Aarav", "Kiran", "Dev", "Nikhil"]
WEEKS = 12
PENALTY = 500

# Generate week dates starting from this Sunday
start_date = datetime(2026, 6, 28)  # First Sunday
weeks_list = [(start_date + timedelta(weeks=i)).strftime("Week %d - Check-in %Y-%m-%d") 
              for i in range(WEEKS)]

# --- Session State ---
if 'all_data' not in st.session_state:
    st.session_state.all_data = pd.DataFrame(columns=["Week", "Participant", "Minutes", "Screenshot"])

# --- Upload Section ---
selected_week = st.selectbox("Select Week", weeks_list)

st.subheader("📸 Upload Workout Screenshots")
uploaded_files = st.file_uploader("Upload screenshots from Strava/Apple Fitness/etc", 
                                  type=["png", "jpg", "jpeg"], 
                                  accept_multiple_files=True)

if st.button("💾 Save Week + Update Standings"):
    if not uploaded_files:
        st.warning("Upload at least 1 screenshot first!")
    else:
        new_rows = []
        for file in uploaded_files:
            img = Image.open(file)
            text = pytesseract.image_to_string(img)
            
            # Try to extract minutes from OCR text
            minutes = 0
            # Look for patterns like "45 min", "1h 15m", "75 minutes"
            min_match = re.search(r'(\d+)\s*min', text.lower())
            hour_match = re.search(r'(\d+)h\s*(\d+)m', text.lower())
            
            if hour_match:
                minutes = int(hour_match.group(1)) * 60 + int(hour_match.group(2))
            elif min_match:
                minutes = int(min_match.group(1))
            
            # Try to guess participant from filename or text
            participant = "Unknown"
            for p in PARTICIPANTS:
                if p.lower() in text.lower() or p.lower() in file.name.lower():
                    participant = p
                    break
            
            new_rows.append({
                "Week": selected_week,
                "Participant": participant,
                "Minutes": minutes,
                "Screenshot": file.name
            })
        
        # Add to session data
        new_df = pd.DataFrame(new_rows)
        st.session_state.all_data = pd.concat([st.session_state.all_data, new_df], ignore_index=True)
        st.success(f"Saved {len(new_rows)} workouts for {selected_week}!")

# --- FIX: Handle empty data before showing standings ---
all_data = st.session_state.all_data
if all_data.empty:
    st.info("👆 Upload screenshots + click 'Save Week' to see standings")
    st.stop()

# --- Standings ---
st.subheader("📊 Current Standings")
current_week_data = all_data[all_data["Week"] == selected_week]

if not current_week_data.empty:
    standings = current_week_data.groupby("Participant")["Minutes"].sum().reset_index()
    standings = standings.sort_values("Minutes", ascending=False).reset_index(drop=True)
    standings["Rank"] = standings.index + 1
    
    # Add penalties for <120 min
    standings["Penalty"] = standings["Minutes"].apply(lambda x: PENALTY if x < 120 else 0)
    standings["Total"] = standings["Minutes"] - standings["Penalty"]
    
    st.dataframe(standings[["Rank", "Participant", "Minutes", "Penalty", "Total"]], 
                 use_container_width=True, hide_index=True)
    
    # --- WhatsApp Message ---
    if st.button("📱 Generate WhatsApp Message"):
        msg = f"🔥 *Summer Challenge - {selected_week} Standings* 🔥\n\n"
        for _, row in standings.iterrows():
            penalty_text = f" -${PENALTY}" if row["Penalty"] > 0 else ""
            msg += f"{int(row['Rank'])}. {row['Participant']}: {int(row['Minutes'])} min{penalty_text}\n"
        
        msg += f"\nWeek deadline: Sunday 11:59pm\nMinimum: 120 min to avoid ${PENALTY} penalty"
        
        st.code(msg, language="text")
        st.success("Copy the message above and paste in WhatsApp group!")
else:
    st.info("No data for this week yet. Upload screenshots above.")

# --- All Weeks View ---
with st.expander("📈 View All Weeks"):
    if not all_data.empty:
        st.dataframe(all_data, use_container_width=True)
    else:
        st.write("No data yet")
    
