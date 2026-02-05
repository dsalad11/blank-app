import streamlit as st
import pandas as pd
import plotly.express as px
import re

# --- Configuration ---
st.set_page_config(page_title="NFL GM Roster ROI", layout="wide")
SALARY_CAP_2026 = 303_500_000

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

# --- Sidebar: Data Center ---
st.sidebar.title("📥 Data Center")
roster_file = st.sidebar.file_uploader("1. Upload Roster/Cap CSV", type=["csv"])
perf_file = st.sidebar.file_uploader("2. Upload Performance CSV", type=["csv"])

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

# 2. Process Performance File
if perf_file and not player_data.empty:
    df_perf = pd.read_csv(perf_file)
    perf_map = {}
    for _, row in df_perf.iterrows():
        p_name = clean_name(row.get('Unnamed: 2'))
        rank_val = row.get('Unnamed: 3')
        if p_name and str(rank_val).isdigit():
            rank = int(rank_val)
            # Rank 1 = 99 Score, Rank 100 = 0 Score
            score = max(0, 100 - rank)
            perf_map[p_name] = score
    
    player_data['Performance'] = player_data['Player'].map(perf_map).fillna(50) 
else:
    if not player_data.empty:
        player_data['Performance'] = 70.0 

# 3. Final ROI Calculation
if not player_data.empty:
    player_data['ROI'] = player_data['Performance'] / (player_data['Cap %'] + 0.1)

# --- Main Dashboard ---
st.title("🏈 NFL GM Roster ROI Dashboard")
st.markdown(f"**2026 Salary Cap:** ${SALARY_CAP_2026:,}")

if not player_data.empty:
    total_spent = player_data['Cap Hit'].sum()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Spent", f"${total_spent/1e6:.1f}M")
    m2.metric("Cap Remaining", f"${(SALARY_CAP
