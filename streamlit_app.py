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
    if pd.isna(name) or name == "-": return None
    return re.sub(r'\s(Q|IR|PUP|SUSP|NFI)$', '', str(name)).strip()

def clean_currency(value):
    if pd.isna(value): return 0.0
    clean_val = re.sub(r'[\$,\s]', '', str(value))
    try: return float(clean_val)
    except: return 0.0

# --- Sidebar: Data Loading ---
st.sidebar.title("📥 Data Center")
roster_file = st.sidebar.file_uploader("1. Upload Roster/Cap CSV", type=["csv"])
perf_file = st.sidebar.file_uploader("2. Upload Performance CSV (PFF/EPA/Stats)", type=["csv"])

# --- Data Processing ---
player_data = pd.DataFrame()

if roster_file:
    df_rost = pd.read_csv(roster_file)
    cap_col = next((c for c in df_rost.columns if "cap" in c.lower()), "Cap Number")
    
    # Extract Financials
    fin_list = []
    for _, row in df_rost.iterrows():
        name = clean_name(row['Player'])
        if name:
            fin_list.append({'Player': name, 'Cap Hit': clean_currency(row[cap_col])})
    
    player_data = pd.DataFrame(fin_list).drop_duplicates('Player')

    # Extract Positions from Depth Chart (Column 12+)
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

if perf_file and not player_data.empty:
    df_perf = pd.read_csv(perf_file)
    # Fuzzy find a "Grade" or "Rank" column
    grade_col = next((c for c in df_perf.columns if any(x in c.lower() for x in ["grade", "score", "epa", "rating"])), None)
    rank_col = next((c for c in df_perf.columns if "rank" in c.lower()), None)
    
    # Merge performance into roster
    perf_map = {}
    for _, row in df_perf.iterrows():
        p_name = clean_name(row.get('Player', row.get('name', '')))
        if p_name:
            if grade_col:
                perf_map[p_name] = float(row[grade_col])
            elif rank_col:
                # Convert Rank to a 1-100 score (lower rank is better)
                total_players = len(df_perf)
                perf_map[p_name] = 100 - (float(row[rank_col]) / total_players * 100)
    
    player_data['Performance'] = player_data['Player'].map(perf_map).fillna(60) # Default mid-grade
else:
    if not player_data.empty:
        player_data['Performance'] = 70.0 # Placeholder

# Calculate ROI
if not player_data.empty:
    # ROI = Performance / Cap % (Adding 0.1 to avoid division by zero)
    player_data['ROI'] = player_data['Performance'] / (player_data['Cap %'] + 0.1)

# --- Dashboard ---
st.title("🏈 2026 NFL GM ROI Dashboard")
st.markdown(f"**Salary Cap Target:** ${SALARY_CAP_2026:,}")

if not player_data.empty:
    total_spent = player_data['Cap Hit'].sum()
    cap_left = SALARY_CAP_2026 - total_spent
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Cap Committed", f"${total_spent/1e6:.1f}M", 
              delta=f"{total_spent/SALARY_CAP_2026*100:.1f}% of Cap")
    m2.metric("Cap Space Remaining", f"${cap_left/1e6:.1f}M", delta_color="normal")
    m3.metric("Roster ROI Average", round(player_data['ROI'].mean(), 2))

    # --- ROI Visualization ---
    st.divider()
    col_l, col_r = st.columns([2, 1])
    
    with col_l:
        st.subheader("Player Value Matrix")
        # Filter out players with $0 cap hit for better viz
        plot_df = player_data[player_data['Cap Hit'] > 0].copy()
        fig = px.scatter(
            plot_df, x="Cap Hit", y="Performance", 
            size="ROI", color="Position", hover_name="Player",
            title="The 'Bargain' Zone (Top Left) vs. 'Overpaid' Zone (Bottom Right)",
            labels={"Cap Hit": "Cap Hit ($)", "Performance": "Production Grade"}
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.subheader("Top ROI Values (The 'Steals')")
        top_roi = player_data.sort_values('ROI', ascending=False).head(10)
        st.table(top_roi[['Player', 'Position', 'ROI']])

    # --- Positional Summary ---
    st.divider()
    st.subheader("Positional Efficiency Breakdown")
    pos_summary = player_data.groupby('Position').agg({
        'Cap Hit': 'sum',
        'Performance': 'mean',
        'ROI': 'mean'
    }).reset_index().sort_values('ROI', ascending=False)
    
    st.dataframe(pos_summary.style.background_gradient(subset=['ROI'], cmap='RdYlGn'))

    # AI Audit for Lamar / High Cap Players
    high_cap_players = player_data[player_data['Cap %'] > 10]
    if not high_cap_players.empty:
        st.subheader("🕵️ High-Leverage Asset Audit")
        for _, p in high_cap_players.iterrows():
            if p['Performance'] > 85:
                st.success(f"**{p['Player']}** ({p['Position']}): High Cap Hit of ${p['Cap Hit']/1e6:.1f}M is **JUSTIFIED** by elite performance. ROI is stable.")
            else:
                st.error(f"**{p['Player']}** ({p['Position']}): High Cap Hit of ${p['Cap Hit']/1e6:.1f}M is **DANGEROUS**. Performance grade of {p['Performance']} results in poor ROI.")

else:
    st.info("Please upload your Ravens Roster CSV in the sidebar to begin analysis.")
