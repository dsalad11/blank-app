import streamlit as st
import pandas as pd
import plotly.express as px
import re
# Adding this to fix the error you received
try:
    import matplotlib
except ImportError:
    st.error("Missing dependency: Please add 'matplotlib' to your requirements.txt file.")

# --- Configuration ---
st.set_page_config(page_title="NFL GM Roster ROI", layout="wide")
SALARY_CAP_2026 = 303_500_000

# Grouping logic for the Dashboard
ROI_GROUPS = {
    "QB": ["QB"], "RB": ["RB", "FB"], "WR": ["WR"], "TE": ["TE"],
    "OL": ["LT", "LG", "C", "RG", "RT", "OL", "G", "T"],
    "DL": ["ED", "IDL", "DT", "DE", "DL"], "LB": ["LB", "ILB", "OLB"],
    "DB": ["CB", "S", "FS", "SS", "DB"], "ST": ["K", "P", "LS"]
}

# --- Helper Functions ---
def clean_name(name):
    if pd.isna(name) or name == "-" or "Rank" in str(name) or "Pos" in str(name): return None
    # Remove suffixes like " Q", " IR", etc.
    return re.sub(r'\s(Q|IR|PUP|SUSP|NFI)$', '', str(name)).strip()

def clean_currency(value):
    if pd.isna(value): return 0.0
    clean_val = re.sub(r'[\$,\s]', '', str(value))
    try: return float(clean_val)
    except: return 0.0

# --- Sidebar: Data Center ---
st.sidebar.title("📥 Data Center")
roster_file = st.sidebar.file_uploader("1. Upload Roster/Cap CSV (Ravens 2026)", type=["csv"])
perf_file = st.sidebar.file_uploader("2. Upload Performance CSV (Ravens Rankings)", type=["csv"])

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

    # Map positions from the depth chart (Column 12+)
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

# 2. Process Performance File (Handling your specific Ranking CSV)
if perf_file and not player_data.empty:
    df_perf = pd.read_csv(perf_file)
    perf_map = {}
    
    # Based on your file: Unnamed: 2 is Player, Unnamed: 3 is Rank
    for _, row in df_perf.iterrows():
        p_name = clean_name(row.get('Unnamed: 2'))
        rank_val = row.get('Unnamed: 3')
        
        if p_name and str(rank_val).isdigit():
            rank = int(rank_val)
            # CONVERSION LOGIC: 
            # We treat Rank 1 as 99 and scale down. 
            # If rank is 100+, they get a baseline score of 5.
            score = max(5, 100 - rank)
            perf_map[p_name] = score
    
    player_data['Performance'] = player_data['Player'].map(perf_map).fillna(60) # Default for unranked players
else:
    if not player_data.empty:
        player_data['Performance'] = 70.0 # Default if no rank file

# 3. Calculate ROI
if not player_data.empty:
    player_data['ROI'] = player_data['Performance'] / (player_data['Cap %'] + 0.1)

# --- Dashboard UI ---
st.title("🏈 2026 NFL GM ROI Dashboard")
st.markdown(f"**Salary Cap Target:** ${SALARY_CAP_2026:,}")

if not player_data.empty:
    total_spent = player_data['Cap Hit'].sum()
    cap_left = SALARY_CAP_2026 - total_spent
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Cap Committed", f"${total_spent/1e6:.1f}M", 
              delta=f"{total_spent/SALARY_CAP_2026*100:.1f}% of Cap")
    m2.metric("Cap Space Remaining", f"${cap_left/1e6:.1f}M")
    m3.metric("Team ROI Average", round(player_data['ROI'].mean(), 2))

    st.divider()
    
    # Visualization: Spend vs Efficiency
    c_left, c_right = st.columns([2, 1])
    with c_left:
        st.subheader("Player Value Matrix")
        fig = px.scatter(
            player_data[player_data['Cap Hit'] > 0], 
            x="Cap Hit", y="Performance", size="ROI", color="Position",
            hover_name="Player",
            title="Bargains (Top Left) vs. Overpaid (Bottom Right)",
            color_discrete_sequence=px.colors.qualitative.Plotly
        )
        st.plotly_chart(fig, use_container_width=True)

    with c_right:
        st.subheader("Top ROI 'Steals'")
        steals = player_data.sort_values('ROI', ascending=False).head(10)
        st.dataframe(steals[['Player', 'Position', 'ROI']], hide_index=True)

    # Positional Summary Table
    st.divider()
    st.subheader("Positional Efficiency Summary")
    pos_summary = player_data.groupby('Position').agg({
        'Cap Hit': 'sum',
        'Performance': 'mean',
        'ROI': 'mean'
    }).reset_index().sort_values('ROI', ascending=False)
    
    # Cleaned up display to avoid the Matplotlib error if it's not installed
    st.dataframe(pos_summary.style.format({
        'Cap Hit': '${:,.0f}',
        'Performance': '{:.1f}',
        'ROI': '{:.2f}'
    }))

    # High-Cap Audit
    st.subheader("🕵️ High-Leverage Asset Audit")
    big_contracts = player_data[player_data['Cap %'] > 8].sort_values('Cap %', ascending=False)
    for _, p in big_contracts.iterrows():
        if p['ROI'] > 5:
            st.success(f"**{p['Player']}**: Cap Hit ${p['Cap Hit']/1e6:.1f}M | ROI {p['ROI']:.1f} - **JUSTIFIED**")
        else:
            st.warning(f"**{p['Player']}**: Cap Hit ${p['Cap Hit']/1e6:.1f}M | ROI {p['ROI']:.1f} - **INEFFICIENT**")
else:
    st.info("Upload your Roster and Ranking CSVs to see the ROI analysis.")
