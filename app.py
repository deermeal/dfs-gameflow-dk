import streamlit as st
import pandas as pd
import numpy as np
import requests

# -----------------------------
# PAGE SETUP
# -----------------------------
st.set_page_config(layout="wide")
st.title("🏀 DFS Game Flow Engine (DraftKings)")
st.caption("Game Flow • Lineup Impact • Late Swap Alerts")

# -----------------------------
# SIDEBAR INPUTS
# -----------------------------
st.sidebar.header("DraftKings Auto Import")

dk_url = st.sidebar.text_input(
    "DraftKings Salary CSV URL",
    placeholder="https://contest-cdn.draftkings.com/..."
)

game_id = st.sidebar.text_input(
    "NBA Game ID",
    placeholder="0022300612"
)

# -----------------------------
# LOAD DK SALARIES
# -----------------------------
def load_dk_salary_csv(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return pd.read_csv(pd.compat.StringIO(r.text))

salaries = None
if dk_url:
    try:
        salaries = load_dk_salary_csv(dk_url)
        st.sidebar.success("DraftKings salaries loaded")
    except:
        st.sidebar.error("Failed to load DraftKings CSV")

# -----------------------------
# AUTO BOXSCORE PULL
# -----------------------------
def load_boxscore(game_id):
    url = f"https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{game_id}.json"
    r = requests.get(url)
    r.raise_for_status()
    data = r.json()["game"]["players"]

    rows = []
    for p in data:
        stats = p["statistics"]
        rows.append({
            "PLAYER": f"{p['name']['firstName']} {p['name']['lastName']}",
            "PTS": stats["points"],
            "REB": stats["reboundsTotal"],
            "AST": stats["assists"],
            "STL": stats["steals"],
            "BLK": stats["blocks"],
            "TOV": stats["turnovers"],
            "3PM": stats["threePointersMade"],
            "Q1": stats["pointsQ1"],
            "Q2": stats["pointsQ2"],
            "Q3": stats["pointsQ3"],
            "Q4": stats["pointsQ4"],
        })

    return pd.DataFrame(rows)

stats = None
if game_id:
    try:
        stats = load_boxscore(game_id)
        st.sidebar.success("Live boxscore loaded")
    except:
        st.sidebar.error("Invalid or inactive Game ID")

# -----------------------------
# DK SCORING
# -----------------------------
def dk_points(row):
    return (
        row["PTS"]
        + row["REB"] * 1.25
        + row["AST"] * 1.5
        + row["STL"] * 2
        + row["BLK"] * 2
        + row["3PM"] * 0.5
        - row["TOV"] * 0.5
    )

# -----------------------------
# MAIN LOGIC
# -----------------------------
if salaries is not None and stats is not None:

    stats["DK_POINTS"] = stats.apply(dk_points, axis=1)

    df = stats.merge(
        salaries[["PLAYER", "Salary"]],
        on="PLAYER",
        how="left"
    )

    df["VALUE"] = df["DK_POINTS"] / (df["Salary"] / 1000)

    # -----------------------------
    # GAME FLOW TABLE
    # -----------------------------
    st.subheader("📊 DFS Game Flow (Player Impact)")
    st.dataframe(
        df[["PLAYER", "DK_POINTS", "Salary", "VALUE"]]
        .sort_values("DK_POINTS", ascending=False),
        use_container_width=True
    )

    # -----------------------------
    # QUARTER-BY-QUARTER FLOW
    # -----------------------------
    st.subheader("📈 Quarter-by-Quarter Game Flow")

    quarter_flow = pd.DataFrame({
        "Q1": df["Q1"].sum(),
        "Q2": df["Q2"].sum(),
        "Q3": df["Q3"].sum(),
        "Q4": df["Q4"].sum(),
    }, index=["DK Points"]).T

    st.bar_chart(quarter_flow)

    # -----------------------------
    # LATE SWAP ALERTS
    # -----------------------------
    st.subheader("🔁 Late Swap Alerts")

    late = df[
        (df["VALUE"] >= 5) &
        (df["DK_POINTS"] < df["DK_POINTS"].mean())
    ]

    if not late.empty:
        st.warning("Late swap leverage detected")
        st.dataframe(
            late[["PLAYER", "Salary", "DK_POINTS", "VALUE"]],
            use_container_width=True
        )
    else:
        st.success("No late swap pressure detected")

else:
    st.info("👈 Enter DK salary URL and NBA Game ID to begin")
    # -----------------------------
    # LINEUP-LEVEL IMPACT (POP CORN MACHINE STYLE)
    # -----------------------------
    st.subheader("🧠 Lineup-Level Impact View")

    st.caption(
        "Aggregates player performance into DFS lineups and "
        "measures how game flow affected lineup outcomes."
    )

    # Ensure quarter columns exist
    for q in ["Q1", "Q2", "Q3", "Q4"]:
        if q not in df.columns:
            df[q] = 0

    # Create mock DK lineups (8 players each)
    np.random.seed(42)

    player_pool = df.dropna(subset=["Salary"]).copy()
    player_pool = player_pool[player_pool["Salary"] > 3000]

    NUM_LINEUPS = 50
    LINEUP_SIZE = 8

    lineups = []

    if len(player_pool) >= LINEUP_SIZE:
        for i in range(NUM_LINEUPS):
            lineup = player_pool.sample(LINEUP_SIZE, replace=False)

            lineup_dk = lineup["DK_POINTS"].sum()
            lineup_salary = lineup["Salary"].sum()

            q1 = lineup["Q1"].sum()
            q2 = lineup["Q2"].sum()
            q3 = lineup["Q3"].sum()
            q4 = lineup["Q4"].sum()

            late_push = q3 + q4
            early_push = q1 + q2

            impact_score = (late_push - early_push) / max(lineup_dk, 1)

            lineups.append({
                "Lineup #": i + 1,
                "DK Points": round(lineup_dk, 2),
                "Salary": lineup_salary,
                "Value": round(lineup_dk / (lineup_salary / 1000), 2),
                "Early DK (Q1+Q2)": round(early_push, 2),
                "Late DK (Q3+Q4)": round(late_push, 2),
                "Impact Score": round(impact_score, 3),
            })

        lineup_df = pd.DataFrame(lineups)

        # -----------------------------
        # DISPLAY LINEUP IMPACT TABLE
        # -----------------------------
        st.dataframe(
            lineup_df.sort_values("Impact Score", ascending=False),
            use_container_width=True
        )

        # -----------------------------
        # IMPACT INTERPRETATION
        # -----------------------------
        st.markdown("### 🔍 Impact Interpretation")

        top_impact = lineup_df.sort_values("Impact Score", ascending=False).head(5)
        fragile = lineup_df.sort_values("Impact Score").head(5)

        col1, col2 = st.columns(2)

        with col1:
            st.success("🔥 Late-Surge Lineups (Benefited from Game Flow)")
            st.dataframe(
                top_impact[
                    ["Lineup #", "DK Points", "Late DK (Q3+Q4)", "Impact Score"]
                ],
                use_container_width=True
            )

        with col2:
            st.error("⚠ Fragile Lineups (Early Points Only)")
            st.dataframe(
                fragile[
                    ["Lineup #", "DK Points", "Early DK (Q1+Q2)", "Impact Score"]
                ],
                use_container_width=True
            )
    else:
        st.info("Not enough players to construct lineups.")
