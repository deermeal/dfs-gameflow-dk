import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import StringIO
st.title("🏀 DFS Game Flow Engine (DraftKings)")
st.caption("Game Flow • Lineup Impact • Late Swap Alerts")

st.sidebar.header("DraftKings Auto Import")
st.info(
    "👈 Paste a DraftKings salary CSV URL in the sidebar and upload a boxscore CSV to begin."
)
