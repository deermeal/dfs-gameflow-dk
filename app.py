import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import StringIO

# -----------------------------
# PAGE SETUP
# -----------------------------
st.set_page_config(layout="wide")
st.title("🏀 DFS Game Flow Engine (DraftKings)")
st.caption("Game Flow • Lineup Impact • Late Swap Intelligence")

# -----------------------------
# SIDEBAR INPUTS
# -----------------------------
st.sidebar.header("📥 DraftKings Auto Import")

dk_salary_url = st.sidebar.text_input(
    "DraftKings Salary CSV URL",
    placeholder="https://contest-cdn.draftkings.com/..."
)

dk_entries_file = st.sidebar.file_uploader(
    "Upload DK Entries CSV (Your Lineups)",
    type="csv"
)

boxscore_file = st.sidebar.file_uploader(
    "Upload NBA Boxscore CSV (with Q1–Q4)",
    type="csv"
)

current_quarter = st.sidebar.selectbox(
    "Current Game Quarter",
    [1, 2, 3, 4],
    index=2
)

# -----------------------------
# HELPERS
# -----------------------------
def load_dk_csv(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return pd.read_csv(StringIO(r.text))

def dk_points(row):
    return (
        row.get("PTS", 0)
        + row.get("REB", 0) * 1.25
        + row.get("AST", 0) * 1.5
        + row.get("STL", 0) * 2
        + row.get("BLK", 0) * 2
        + row.get("3PM", 0) * 0.5
        - row.get("TOV", 0) * 0.5
    )

# Minutes remaining estimate
def minutes_remaining(q):
    return max(0, (4 - q) * 12)

# -----------------------------
# LOAD DATA
# -----------------------------
salaries = None
if dk_salary_url:
    try:
        salaries = load_dk_csv(dk_salary_url)
        st.sidebar.success("DK Salaries Loaded")
    except:
        st.sidebar.error("Failed to load DK salary CSV")

if not (salaries is not None and dk_entries_file and boxscore_file):
    st.info("👈 Load DK salary URL, DK entries CSV, and boxscore CSV to begin")
    st.stop()

entries = pd.read_csv(dk_entries_file)
stats = pd.read_csv(boxscore_file)

# Ensure quarter columns exist
for q in ["Q1", "Q2", "Q3", "Q4"]:
    if q not in stats.columns:
        stats[q] = 0

stats["DK_POINTS"] = stats.apply(dk_points, axis=1)

player_df = stats.merge(
    salaries[["PLAYER", "Salary"]],
    on="PLAYER",
    how="left"
)

player_df["VALUE"] = player_df["DK_POINTS"] / (player_df["Salary"] / 1000)

# -----------------------------
# PLAYER VIEW
# -----------------------------
st.subheader("📊 Player DFS Output")

st.dataframe(
    player_df[
        ["PLAYER", "DK_POINTS", "Salary", "VALUE", "Q1", "Q2", "Q3", "Q4"]
    ].sort_values("DK_POINTS", ascending=False),
    use_container_width=True
)

# -----------------------------
# LINEUP-LEVEL IMPACT (REAL DK LINEUPS)
# -----------------------------
st.subheader("🧠 Lineup-Level Impact View (PopcornMachine Style)")

lineups = []

lineup_cols = [c for c in entries.columns if "Player" in c]

for i, row in entries.iterrows():
    lineup_players = row[lineup_cols].dropna().tolist()

    lineup_stats = player_df[player_df["PLAYER"].isin(lineup_players)]

    if lineup_stats.empty:
        continue

    q1 = lineup_stats["Q1"].sum()
    q2 = lineup_stats["Q2"].sum()
    q3 = lineup_stats["Q3"].sum()
    q4 = lineup_stats["Q4"].sum()

    total = lineup_stats["DK_POINTS"].sum()
    salary = lineup_stats["Salary"].sum()

    early = q1 + q2
    late = q3 + q4

    mins_left = minutes_remaining(current_quarter)

    swap_urgency = (
        (late / max(total, 1)) *
        (mins_left / 48) *
        (total / max(salary / 1000, 1))
    )

    lineups.append({
        "Lineup #": i + 1,
        "DK Points": round(total, 2),
        "Salary": int(salary),
        "Value": round(total / (salary / 1000), 2),
        "Q1": round(q1, 2),
        "Q2": round(q2, 2),
        "Q3": round(q3, 2),
        "Q4": round(q4, 2),
        "Early (Q1+Q2)": round(early, 2),
        "Late (Q3+Q4)": round(late, 2),
        "Minutes Left": mins_left,
        "Swap Urgency": round(swap_urgency, 3),
    })

lineup_df = pd.DataFrame(lineups)

# -----------------------------
# POPCORN MACHINE BAR VIEW
# -----------------------------
st.subheader("🍿 Game Flow Bars (Q1 → Q4)")

st.dataframe(
    lineup_df.sort_values("Swap Urgency", ascending=False),
    use_container_width=True
)

st.markdown("""
**How to read this:**
- 🟦 Q1/Q2 = early scoring
- 🟥 Q3/Q4 = late scoring
- High *Swap Urgency* = dangerous lineup if players still active
""")

# -----------------------------
# SWAP ALERTS
# -----------------------------
st.subheader("🔁 Late Swap Alerts")

alerts = lineup_df[
    (lineup_df["Swap Urgency"] > lineup_df["Swap Urgency"].quantile(0.75))
]

if not alerts.empty:
    st.error("🚨 HIGH SWAP PRESSURE LINEUPS")
    st.dataframe(
        alerts[
            ["Lineup #", "DK Points", "Late (Q3+Q4)", "Minutes Left", "Swap Urgency"]
        ],
        use_container_width=True
    )
else:
    st.success("✅ No urgent late-swap situations detected")
