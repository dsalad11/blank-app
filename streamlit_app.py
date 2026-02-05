import streamlit as st
import pandas as pd
import plotly.express as px
import re

# --- Configuration ---
st.set_page_config(page_title="NFL GM Roster ROI", layout="wide")
SALARY_CAP_2026 = 303_500_000

# Positional Groups & Premium Weights
# 1.0 = Max Premium, lower values = Non-Premium (higher ROI hurdle)
POS_DATA = {
    "QB": {"groups": ["QB"], "weight": 1.0},
    "WR": {"groups": ["WR"], "weight": 0.95},
    "OL": {"groups": ["LT", "LG", "C", "RG", "RT", "OL", "G", "T"], "weight": 0.9},
    "DL": {"groups": ["ED", "IDL", "DT", "DE", "DL", "LDE", "RDE", "NT"], "weight": 0.9},
    "DB": {"groups": ["CB", "S", "FS", "SS", "DB", "LCB", "RCB"], "weight": 0.85},
    "TE": {"groups": ["TE"], "weight": 0.75},
    "LB": {"groups": ["LB", "ILB", "OLB", "WLB", "LILB", "RILB", "SLB"], "weight": 0.7},
    "RB": {"groups": ["RB", "FB", "HB"], "weight": 0.65},
    "ST": {"groups": ["K", "P", "LS"], "weight": 0.5}
}

# --- Helper Functions ---
def get_roi_category(pos_label):
    if pd.isna(pos_label): return "ST"
    pos_label = str(pos_label).upper()
    for cat, data in POS_DATA.items():
        if pos_label in data['groups']:
            return cat
    return "ST"

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
            if p_clean: pos_map[p_clean] = get_roi_category(label)
    
    player_data['Position'] = player_data['Player'].map(pos_map)
    player_data['Cap %'] = (player_data['Cap Hit'] / SALARY_CAP_2026) * 100

# 2. Process Performance File (Revised Logic for Premium Criticality)
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
                
                # Performance base (100 is best)
                percentile = rank / total_in_pos
                score = max(0, 100 - (percentile * 100))
                perf_map[p_name] = score
            except: continue
    
    player_data['Performance'] = player_data['Player'].map(perf_map).fillna(50)
else:
    if not player_data.empty: player_data['Performance'] = 70.0

# 3. Final ROI Calculation (Positional Hurdle Applied)
if not player_data.empty:
    # ROI = (Performance * Weight) / Cap% 
    # This penalizes high spend on non-premium positions (TE/LB/RB)
    player_data['Weight'] = player_data['Position'].apply(lambda x: POS_DATA.get(x, {'weight': 0.5})['weight'])
    player_data['ROI'] = (player_data['Performance'] * player_data['Weight']) / (player_data['Cap %'] + 0.1)

# --- Dashboard ---
st.title("🏈 2026 NFL GM ROI Dashboard")
st.markdown(f"**Target Salary Cap:** ${SALARY_CAP_2026:,}")

if not player_data.empty:
    total_spent = player_data['Cap Hit'].sum()
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Committed", f"${total_spent/1e6:.1f}M", f"{total_spent/SALARY_CAP_2026*100:.1f}% Use")
    m2.metric("Cap Space", f"${(SALARY_CAP_2026 - total_spent)/1e6:.1f}M")
    m3.metric("Team ROI Avg", round(player_data['ROI'].mean(), 2))

    st.divider()

    col_l, col_r = st.columns([2, 1])
    with col_l:
        st.subheader("Player Value Matrix (Position Weighted)")
        fig = px.scatter(
            player_data[player_data['Cap Hit'] > 0], 
            x="Cap Hit", y="Performance", size="ROI", color="Position",
            hover_name="Player",
            title="Note: Bubble size accounts for Positional Value (LB/TE are smaller at same rank/cost)",
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
    st.subheader("🕵️ Executive Audit: The 'Premium' Filter")
    big_contracts = player_data[player_data['Cap %'] > 5].sort_values('ROI', ascending=True)
    
    for _, p in big_contracts.iterrows():
        if p['ROI'] < 4.0:
            st.error(f"**{p['Player']}** ({p['Position']}): ROI is **Low ({p['ROI']:.2f})**. Ranked {p['Performance']:.0f}/100. At this price point for a non-premium position, elite (Top 5) play is required to justify the cap hit.")
        elif p['ROI'] < 6.0:
            st.warning(f"**{p['Player']}** ({p['Position']}): ROI is **Moderate ({p['ROI']:.2f})**. Efficiency is being tested by high cap utilization.")
        else:
            st.success(f"**{p['Player']}** ({p['Position']}): ROI is **High ({p['ROI']:.2f})**. High cost is currently offset by premium positional value or elite performance.")

else:
    st.info("Upload your Roster and the new 'X/Y' Ranking CSVs to see your team breakdown.")
