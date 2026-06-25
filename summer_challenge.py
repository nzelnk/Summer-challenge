import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytesseract
from PIL import Image
import re
import plotly.express as px

st.set_page_config(page_title="Summer Challenge 2026", layout="centered", page_icon="🔥")

st.markdown("""
<style>
.stButton>button {height: 3.2em; font-size: 18px; width: 100%; border-radius: 12px;}
h1 {text-align: center;}
</style>
""", unsafe_allow_html=True)

st.title("☀️ Summer Fitness Challenge 2026")
st.caption("Mon-Sun weeks | 30min+ active | 4 days/week | Sunday check-in")

# CONFIG
PARTICIPANTS = ["Arabhy", "Bhairavy", "Jana", "Kabi", "Naz", "Praveen", "Tharshiga", "Thesikan"]
BUY_IN, PENALTY = 30, 10
POT_HOLDER = "Raaj et arulraaj_k@hotmail.com"
START, END = pd.to_datetime("2026-06-22"), pd.to_datetime("2026-09-20")

weeks = pd.date_range(START, END, freq="W-SUN")
week_labels = [f"Week {i+1} - Check-in {w.date()}" for i, w in enumerate(weeks)]

if 'all_data' not in st.session_state:
    st.session_state.all_data = pd.DataFrame()

def parse_workout(img):
    text = pytesseract.image_to_string(Image.open(img)).lower()
    date_match = re.search(r'(mon|tue|wed|thu|fri|sat|sun),?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+(\d+)', text)
    date = pd.to_datetime(f"{date_match.group(2)} {date_match.group(3)} 2026") if date_match else pd.to_datetime("today").date()

    # Apple Fitness: 0:54:04
    time_match = re.search(r'workout time\s*(\d+):(\d+):(\d+)', text)
    if time_match:
        mins = int(time_match.group(1))*60 + int(time_match.group(2))
        return date.date(), mins

    # Lionheart/F45: 45 on x-axis
    axis_match = re.search(r'\d+\s+(\d+)$', text)
    if axis_match:
        return date.date(), int(axis_match.group(1))

    # Fallback: XX min
    min_match = re.search(r'(\d+)\s*min', text)
    if min_match:
        return date.date(), int(min_match.group(1))
    return date.date(), 0

selected_week = st.selectbox("📅 Select Week", week_labels)
week_num = week_labels.index(selected_week) + 1
week_date = weeks[week_num-1].date()
week_start = week_date - timedelta(days=6)

st.header(f"Week {week_num} - Due Sun {week_date}")

this_week = []
for person in PARTICIPANTS:
    st.subheader(person)
    c1, c2 = st.columns([4,1])
    with c1:
        files = st.file_uploader("Upload screenshots", accept_multiple_files=True,
                                 type=['jpg','png','jpeg'], key=f"{person}_{week_num}")
    with c2:
        free = st.checkbox("Free week", key=f"free_{person}_{week_num}")

    workouts = []
    if files:
        for f in files:
            date, mins = parse_workout(f)
            if mins >= 30: # 30-min rule
                workouts.append({"Name": person, "Date": date, "Week": week_num})

    # AUTO-DEDUPE: max 1 workout per day
    df_temp = pd.DataFrame(workouts).drop_duplicates(subset=["Date"], keep="first")
    this_week.extend(df_temp.to_dict('records'))
    count = len(df_temp)

    if free:
        st.success("🛡️ Free week used")
    elif count >= 4:
        st.success(f"✅ {count}/4 days")
    else:
        st.error(f"❌ {count}/4 days")

if st.button("💾 Save Week + Update Standings"):
    if this_week:
        new_df = pd.DataFrame(this_week)
        st.session_state.all_data = pd.concat([st.session_state.all_data, new_df]).drop_duplicates(subset=["Name","Date"], keep="last")
        st.success("Saved! Standings updated")

all_data = st.session_state.all_data

# CUMULATIVE STANDINGS
standings = []
pot = BUY_IN * 8
for w in range(1, week_num+1):
    week_data = all_data[all_data["Week"] == w]
    for p in PARTICIPANTS:
        count = len(week_data[week_data["Name"] == p])
        free = st.session_state.get(f"free_{p}_{w}", False)
        hit = count >= 4 or free
        pen = 0 if hit else PENALTY
        pot += pen
        standings.append({"Name": p, "Week": w, "Workouts": count, "Hit": hit, "Penalty": pen})

standings_df = pd.DataFrame(standings)
if not standings_df.empty:
    cumulative = standings_df.groupby("Name").agg({"Hit": "sum", "Workouts": "sum", "Penalty": "sum"}).reset_index()
    cumulative = cumulative.sort_values(["Hit", "Workouts"], ascending=[False, False]).reset_index(drop=True)
    cumulative["Rank"] = cumulative.index + 1

    c1, c2, c3 = st.columns(3)
    c1.metric("💰 Pot Total", f"${pot}")
    c2.metric("🥇 Leader", cumulative.iloc[0]["Name"] if len(cumulative)>0 else "-")
    c3.metric("Week Complete", f"{sum(1 for p in PARTICIPANTS if len(all_data[(all_data['Name']==p)&(all_data['Week']==week_num)])>=4)}/8")

    st.subheader("🏆 Cumulative Standings")
    trophies = {1:"🥇", 2:"🥈", 3:"🥉"}
    cumulative["Trophy"] = cumulative["Rank"].map(trophies).fillna(cumulative["Rank"].astype(str))
    display_df = cumulative[["Trophy","Name","Hit","Workouts","Penalty"]].rename(columns={"Hit":"Weeks Won","Workouts":"Total Days"})
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # WHATSAPP EXPORT
    if st.button("📱 Generate WhatsApp Message"):
        week_results = standings_df[standings_df["Week"] == week_num]
        msg = f"*🔥 SUMMER CHALLENGE - WEEK {week_num} CHECK-IN*\n{selected_week}\n\n*THIS WEEK:*\n"
        for _, row in week_results.sort_values("Workouts", ascending=False).iterrows():
            msg += f"{'✅' if row['Hit'] else '❌'} {row['Name']}: {row['Workouts']}/4 days\n"

        owed = week_results[week_results["Penalty"] > 0]
        if not owed.empty:
            msg += f"\n*PENALTIES $10 to Raaj:*\n" + "\n".join([f"💸 {r['Name']}" for _, r in owed.iterrows()])
        else:
            msg += "\n\n🎉 Everyone hit 4! No penalties"

        msg += f"\n\nCurrent pot: ${pot} 💰\nTiebreaker: Total Days"
        st.text_area("Copy + paste to WhatsApp group:", msg, height=280)
else:
    st.info("Upload screenshots + click 'Save Week' to see standings")

st.caption("Rules: 30min+ active workout, max 1/day, 2 free weeks per person, proof by Sunday 11:59pm")
