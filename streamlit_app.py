import streamlit as st
import pandas as pd
import plotly.express as px
import re

# --- Configuration ---
st.set_page_config(page_title="NFL GM Roster ROI", layout="wide")
SALARY_CAP_2026 = 303_500_000

# Positional Groups & Premium Weights
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
        if pos_label in data['groups']: return cat
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
        if name: fin_list.append({'Player': name, 'Cap Hit': clean_currency(row[cap_col])})
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

# 2. Process Performance File (FIXED PARSING & LABELING)
if perf_file and not player_data.empty:
    df_perf = pd.read_csv(perf_file)
    perf_map = {}
    display_rank_map = {}
    
    for _, row in df_perf.iterrows():
        p_name = clean_name(row.get('Unnamed: 2'))
        rank_raw = str(row.get('Unnamed: 3'))
        
        if p_name and "/" in rank_raw:
            try:
                rank_val = int(rank_raw.split('/')[0])
                total_val = int(rank_raw.split('/')[1])
                # Grade logic: 100 is elite. (e.g. 8/40 = 20th percentile = 80 Grade)
                score = max(0, 100 - (rank_val / total_val * 100))
                perf_map[p_name] = score
                display_rank_map[p_name] = rank_raw
            except: continue
    
    player_data['Grade'] = player_data['Player'].map(perf_map).fillna(50)
    player_data['Actual Rank'] = player_data['Player'].map(display_rank_map).fillna("N/A")
else:
    if not player_data.empty:
        player_data['Grade'] = 70.0
        player_data['Actual Rank'] = "N/A"

# 3. Final Calculations
if not player_data.empty:
    player_data['Weight'] = player_data['Position'].apply(lambda x: POS_DATA.get(x, {'weight': 0.5})['weight'])
    player_data['ROI'] = (player_data['Grade'] * player_data['Weight']) / (player_data['Cap %'] + 0.1)

# --- Dashboard ---
st.title("🏈 2026 NFL GM ROI Dashboard")

if not player_data.empty:
    total_spent = player_data['Cap Hit'].sum()
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Committed", f"${total_spent/1e6:.1f}M", f"{total_spent/SALARY_CAP_2026*100:.1f}% Use")
    m2.metric("Cap Space", f"${(SALARY_CAP_2026 - total_spent)/1e6:.1f}M")
    m3.metric("Roster ROI Avg", round(player_data['ROI'].mean(), 2))

    st.divider()

    col_l, col_r = st.columns([2, 1])
    with col_l:
        st.subheader("Player Value Matrix")
        fig = px.scatter(
            player_data[player_data['Cap Hit'] > 0], 
            x="Cap Hit", y="Grade", size="ROI", color="Position",
            hover_name="Player", custom_data=['Actual Rank'],
            title="Bargains (Top Left) vs. Overpaid (Bottom Right)"
        )
        fig.update_traces(hovertemplate="<b>%{hovertext}</b><br>Grade: %{y}<br>Rank: %{customdata[0]}<br>Cap: $%{x:,.0f}")
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.subheader("Top ROI 'Steals'")
        top_steals = player_data.sort_values('ROI', ascending=False).head(10)
        st.dataframe(top_steals[['Player', 'Position', 'Actual Rank', 'ROI']], hide_index=True)

    # Positional Summary
    st.divider()
    st.subheader("Positional Efficiency Summary")
    pos_summary = player_data.groupby('Position').agg({'Cap Hit': 'sum', 'Grade': 'mean', 'ROI': 'mean'}).reset_index().sort_values('ROI', ascending=False)
    st.dataframe(pos_summary.style.format({'Cap Hit': '${:,.0f}', 'Grade': '{:.1f}', 'ROI': '{:.2f}'}), hide_index=True, use_container_width=True)

    # High Leverage Audit
    st.divider()
    st.subheader("🕵️ Executive Audit")
    # Audit for players making more than $15M
    big_contracts = player_data[player_data['Cap Hit'] > 15_000_000].sort_values('ROI', ascending=True)
    
    for _, p in big_contracts.iterrows():
        # High Cap ROI Thresholds: QB ROI is naturally lower due to high cap.
        # We check if the grade is high enough regardless of raw ROI.
        if p['Grade'] >= 80:
            st.success(f"**{p['Player']}** ({p['Position']}): Rank **{p['Actual Rank']}** | Grade **{p['Grade']:.1f}** — **JUSTIFIED**. High production offsets the \$ {p['Cap Hit']/1e6:.1f}M cap hit.")
        elif p['ROI'] < 3.5:
            st.error(f"**{p['Player']}** ({p['Position']}): Rank **{p['Actual Rank']}** | Grade **{p['Grade']:.1f}** — **INEFFICIENT**. Performance is not commensurate with high salary.")
        else:
            st.warning(f"**{p['Player']}** ({p['Position']}): Rank **{p['Actual Rank']}** | Grade **{p['Grade']:.1f}** — **STABLE**. Acceptable but high-risk efficiency.")
else:
    st.info("Upload your CSV files to see the analysis.")
