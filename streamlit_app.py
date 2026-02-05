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
perf_file = st.sidebar.file_uploader("2. Upload Rankings CSV (with X/Y)", type=["csv"])

player_data = pd.DataFrame()

if roster_file:
    df_rost = pd.read_csv(roster_file)
    cap_col = next((c for c in df_rost.columns if "cap" in c.lower()), "Cap Number")
    fin_list = []
    for _, row in df_rost.iterrows():
        name = clean_name(row.get('Player'))
        if name: fin_list.append({'Player': name, 'Cap Hit': clean_currency(row[cap_col])})
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

# --- NEW LOGIC FOR PERFORMANCE STRING PARSING ---
if perf_file and not player_data.empty:
    df_perf = pd.read_csv(perf_file)
    perf_map = {}
    for _, row in df_perf.iterrows():
        p_name = clean_name(row.get('Unnamed: 2'))
        rank_raw = str(row.get('Unnamed: 3'))
        
        if p_name and "/" in rank_raw:
            try:
                # Extracts the '20' from '20/40'
                rank = int(rank_raw.split('/')[0])
                # Extracts the '40' to calculate a percentile score
                total_in_pos = int(rank_raw.split('/')[1])
                score = max(0, 100 - (rank / total_in_pos * 100))
                perf_map[p_name] = score
            except:
                continue
    player_data['Performance'] = player_data['Player'].map(perf_map).fillna(50)
else:
    if not player_data.empty: player_data['Performance'] = 70.0

if not player_data.empty:
    player_data['ROI'] = player_data['Performance'] / (player_data['Cap %'] + 0.1)

# --- Dashboard Display ---
st.title("🏈 NFL GM Roster ROI Dashboard")
if not player_data.empty:
    total_spent = player_data['Cap Hit'].sum()
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Spent", f"${total_spent/1e6:.1f}M")
    m2.metric("Cap Remaining", f"${(SALARY_CAP_2026 - total_spent)/1e6:.1f}M")
    m3.metric("Team ROI Avg", round(player_data['ROI'].mean(), 2))

    st.divider()
    st.subheader("Efficiency Matrix")
    fig = px.scatter(player_data[player_data['Cap Hit'] > 0], x="Cap Hit", y="Performance", size="ROI", color="Position", hover_name="Player")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Unit Summary")
    pos_summary = player_data.groupby('Position').agg({'Cap Hit': 'sum', 'Performance': 'mean', 'ROI': 'mean'}).reset_index().sort_values('ROI', ascending=False)
    st.dataframe(pos_summary.style.format({'Cap Hit': '${:,.0f}', 'Performance': '{:.1f}', 'ROI': '{:.2f}'}), use_container_width=True)
    
