import streamlit as st
import pandas as pd
import plotly.express as px
import re

# --- Configuration ---
st.set_page_config(page_title="NFL GM Roster ROI", layout="wide")
SALARY_CAP_2026 = 303_500_000

# Grouping logic for calculations
ROI_GROUPS = {
    "QB": ["QB"], "RB": ["RB", "FB"], "WR": ["WR"], "TE": ["TE"],
    "OL": ["LT", "LG", "C", "RG", "RT", "OL", "G", "T"],
    "DL": ["ED", "IDL", "DT", "DE", "DL"], "LB": ["LB", "ILB", "OLB"],
    "DB": ["CB", "S", "FS", "SS", "DB"], "ST": ["K", "P", "LS"]
}

# --- Helper Functions ---
def clean_name(name):
    if pd.isna(name) or name == "-" or "Rank" in str(name) or "Pos" in str(name): return None
    return re.sub(r'\s(Q|IR|PUP|SUSP|NFI)$', '', str(name)).strip()

def clean_currency(value):
    if pd.isna(value): return 0.0
    clean_val = re.sub(r'[\$,\s]', '', str(value))
    try: return float(clean_val)
    except: return 0.0

# --- Sidebar ---
st.sidebar.title("📥 Data Center")
roster_file = st.sidebar.file_uploader("1. Upload Roster/Cap CSV", type=["csv"])
perf_file = st.sidebar.file_uploader("2. Upload Rankings CSV (X/Y Format)", type=["csv"])

player_data = pd.DataFrame()

# 1. Process Roster File
if roster_file:
    df_rost = pd.read_csv(roster_file)
    cap_col = next((c for c in df_rost.columns if "cap" in c.lower()), "Cap Number")
    
    fin_list = []
    for _, row in df_rost.iterrows():
        name = clean_name(row.get('Player'))
        if name:
            fin_list.append({'Player': name, 'Cap Hit': clean_currency(row[cap_col])})
    
    player_data = pd.DataFrame(fin_list).drop_duplicates('Player')

    pos_map = {}
    pos_labels = df_rost.iloc[:, 12]
    depth_players = df_rost.iloc[:, 13:17]
    for idx, label in enumerate(pos_labels):
        if pd.isna(label): continue
        for p_name in depth_players.iloc[idx].dropna():
            p_clean = clean_name(p_name)
            if p_clean: pos_map[p_clean] = str(label).upper()
    
    player_data['Position'] = player_data['Player'].map(pos_map)
    player_data['Cap %'] = (player_data['Cap Hit'] / SALARY_CAP_2026) * 100

# 2. Process Performance File (Handling the new 20/40 format)
if perf_file and not player_data.empty:
    df_perf = pd.read_csv(perf_file)
    perf_map = {}
    for _, row in df_perf.iterrows():
        p_name = clean_name(row.get('Unnamed: 2'))
        rank_raw = str(row.get('Unnamed: 3'))
        
        if p_name and "/" in rank_raw:
            try:
                rank = int(rank_raw.split('/')[0])
                total_in_pos = int(rank_raw.split('/')[1])
                # ROI Performance Score: 100 is elite, 0 is poor
                score = max(0, 10
