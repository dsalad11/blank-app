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
                score = max(0, 100 - (rank / total_in_pos * 100))
                perf_map[p_name] = score
            except: continue
    
    player_data['Performance'] = player_data['Player'].map(perf_map).fillna(50)
else:
    if not player_data.empty:
        player_data['Performance'] = 70.0

# 3. Final Calculations
if not player_data.empty:
    player_data['ROI'] = player_data['Performance'] / (player_data['Cap %'] + 0.1)

# --- Dashboard Layout ---
st.title("🏈 2026 NFL GM ROI Dashboard")
st.markdown(f"**Target Salary Cap:** ${SALARY_CAP_2026:,}")

if not player_data.empty:
    total_spent = player_data['Cap Hit'].sum()
    
    # Top Level Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Committed", f"${total_spent/1e6:.1f}M", f"{total_spent/SALARY_CAP_2026*100:.1f}% Use")
    m2.metric("Cap Space", f"${(SALARY_CAP_2026 - total_spent)/1e6:.1f}M")
    m3.metric("Roster ROI Avg", round(player_data['ROI'].mean(), 2))

    st.divider()

    # Matrix Visualization
    col_l, col_r = st.columns([2, 1])
    with col_l:
        st.subheader("Player Value Matrix")
        fig = px.scatter(
            player_data[player_data['Cap Hit'] > 0], 
            x="Cap Hit", y="Performance", size="ROI", color="Position",
            hover_name="Player",
            title="The 'Bargain' Zone (Top Left) vs. 'Overpaid' Zone (Bottom Right)",
            color_discrete_sequence=px.colors.qualitative.Prism
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.subheader("Top ROI 'Steals'")
        top_steals = player_data.sort_values('ROI', ascending=False).head(10)
        st.dataframe(top_steals[['Player', 'Position', 'ROI']], hide_index=True, use_container_width=True)

    # Positional Summary
    st.divider()
    st.subheader("Positional Efficiency Summary")
    pos_summary = player_data.groupby('Position').agg({
        'Cap Hit': 'sum',
        'Performance': 'mean',
        'ROI': 'mean'
    }).reset_index().sort_values('ROI', ascending=False)
    
    st.dataframe(pos_summary.style.format({
        'Cap Hit': '${:,.0f}',
        'Performance': '{:.1f}',
        'ROI': '{:.2f}'
    }), use_container_width=True, hide_index=True)

    # High Leverage Audit
    st.divider()
    st.subheader("🕵️ High-Leverage Asset Audit")
    # Filters for players taking up more than 5% of the cap
    big_contracts = player_data[player_data['Cap %'] > 5].sort_values('Cap %', ascending=False)
    
    for _, p in big_contracts.iterrows():
        if p['ROI'] > 5:
            st.success(f"**{p['Player']}** ({p['Position']}): Cap Hit ${p['Cap Hit']/1e6:.1f}M | ROI: {p['ROI']:.2f} — **JUSTIFIED**. Elite production offsets high cost.")
        elif p['ROI'] > 2:
            st.info(f"**{p['Player']}** ({p['Position']}): Cap Hit ${p['Cap Hit']/1e6:.1f}M | ROI: {p['ROI']:.2f} — **STABLE**. Performance is commensurate with salary.")
        else:
            st.warning(f"**{p['Player']}** ({p['Position']}): Cap Hit ${p['Cap Hit']/1e6:.1f}M | ROI: {p['ROI']:.2f} — **INEFFICIENT**. This contract is a significant drain on roster value.")

else:
    st.info("Upload your Roster and the new 'X/Y' Ranking CSVs to see your team breakdown.")
