import streamlit as st
import pandas as pd
import plotly.express as px
import re

# --- Configuration ---
st.set_page_config(page_title="NFL GM ROI Dashboard", layout="wide")

# Standard NFL Positional Mapping (Groups sub-positions into our ROI categories)
ROI_GROUPS = {
    "QB": ["QB"],
    "RB": ["RB", "FB", "HB"],
    "WR": ["WR"],
    "TE": ["TE"],
    "OL": ["LT", "LG", "C", "RG", "RT", "OL", "G", "T"],
    "DL": ["ED", "IDL", "DT", "DE", "DL"],
    "LB": ["LB", "ILB", "OLB"],
    "DB": ["CB", "S", "FS", "SS", "DB"],
    "ST": ["K", "P", "LS", "ST"]
}

# --- Utility: Data Cleaning ---
def clean_name(name):
    if pd.isna(name) or name == "-": return None
    # Remove suffixes like " Q", " IR", or " PUP"
    return re.sub(r'\s(Q|IR|PUP|SUSP|NFI)$', '', str(name)).strip()

def clean_currency(value):
    if pd.isna(value): return 0.0
    # Strip $, commas, and whitespace
    clean_val = re.sub(r'[\$,\s]', '', str(value))
    try:
        return float(clean_val)
    except:
        return 0.0

# --- State Management ---
if "ratios" not in st.session_state:
    st.session_state.ratios = {k: 5.0 for k in ROI_GROUPS.keys()}
if "team_name" not in st.session_state:
    st.session_state.team_name = "New Roster"

# --- Sidebar: Smart Data Ingestion ---
st.sidebar.title("📥 Roster Data Import")
uploaded_file = st.sidebar.file_uploader("Upload Side-by-Side CSV", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    # 1. Parse Financial Table (Left side)
    # Using 'Cap\nNumber' as specified, or similar fuzzy match
    cap_col = next((c for c in df.columns if "cap" in c.lower()), None)
    player_col = "Player" # Assuming standard 'Player' column for financials
    
    if cap_col:
        # Create Player -> Salary Map
        financials = {}
        for _, row in df.iterrows():
            name = clean_name(row[player_col])
            if name:
                financials[name] = clean_currency(row[cap_col])
        
        # 2. Parse Depth Chart (Right side)
        # Position label is usually in 'Unnamed: 12' or the first column after the split
        pos_labels = df.iloc[:, 12] 
        depth_players = df.iloc[:, 13:17] # Starter, 2nd, 3rd, 4th
        
        # Calculate spending per ROI Group
        group_totals = {k: 0.0 for k in ROI_GROUPS.keys()}
        
        for idx, pos_label in enumerate(pos_labels):
            if pd.isna(pos_label): continue
            
            # Find which ROI Group this position belongs to
            target_group = None
            for group, subs in ROI_GROUPS.items():
                if str(pos_label).upper() in subs:
                    target_group = group
                    break
            
            if target_group:
                # Add up the cap hits for all players in this depth chart row
                row_players = depth_players.iloc[idx].dropna().tolist()
                for p_name in row_players:
                    p_clean = clean_name(p_name)
                    if p_clean in financials:
                        group_totals[target_group] += financials[p_clean]

        # 3. Convert to Percentages
        total_team_cap = sum(group_totals.values())
        if total_team_cap > 0:
            st.session_state.ratios = {k: round((v/total_team_cap)*100, 2) for k, v in group_totals.items()}
            st.session_state.team_name = uploaded_file.name.split('.')[0]
            st.sidebar.success(f"✅ Successfully matched {len(financials)} players to Depth Chart!")

# --- UI Controls ---
st.sidebar.divider()
st.sidebar.title("🎮 ROI Modeling")
final_spend = {}
for pos in ROI_GROUPS.keys():
    final_spend[pos] = st.sidebar.slider(f"{pos} Allocation (%)", 0.0, 40.0, float(st.session_state.ratios.get(pos, 5.0)))

# Manual Performance Grades (User inputs these based on 'Drake Maye' or 'Vikings QB' stats)
st.sidebar.subheader("📊 Performance Grades")
perf_grades = {}
for pos in ROI_GROUPS.keys():
    default_grade = 90 if pos == "QB" and "Patriots" in st.session_state.team_name else 60
    perf_grades[pos] = st.sidebar.number_input(f"{pos} Grade (1-100)", 0, 100, default_grade)

# --- Dashboard Logic ---
st.title(f"🏈 {st.session_state.team_name} ROI Dashboard")

# High Level Metrics
total_util = sum(final_spend.values())
avg_perf = sum(perf_grades.values()) / len(perf_grades)
team_roi = (avg_perf / (total_util / len(ROI_GROUPS))) if total_util > 0 else 0

c1, c2, c3 = st.columns(3)
c1.metric("Cap Used", f"{total_util:.1f}%")
c2.metric("Efficiency Rating", f"{team_roi:.2f}")
qb_roi = (perf_grades['QB'] / (final_spend['QB'] if final_spend['QB'] > 0 else 1))
c3.metric("QB ROI Factor", f"{qb_roi:.1f}x")

# Visualization: Spend vs Efficiency
df_plot = pd.DataFrame({
    "Unit": list(ROI_GROUPS.keys()),
    "Allocation": list(final_spend.values()),
    "Performance": list(perf_grades.values())
})
df_plot['ROI'] = (df_plot['Performance'] / (df_plot['Allocation'].replace(0, 1)))

fig = px.scatter(df_plot, x="Allocation", y="Performance", size="ROI", color="ROI",
                 text="Unit", color_continuous_scale="RdYlGn", 
                 title="Efficiency Matrix: Where are you getting the most bang for your buck?")
st.plotly_chart(fig, use_container_width=True)

# AI Audit
st.divider()
st.subheader("🕵️ Executive ROI Audit")
with st.expander("Analysis Breakdown"):
    if qb_roi > 15:
        st.success("**ELITE ROOKIE WINDOW DETECTED:** You are receiving high-level QB play at a fraction of market cost. This is your 'Super Bowl Window.' Aggressively spend on short-term veteran DL and WR assets.")
    elif qb_roi < 5:
        st.error("**EFFICIENCY DRAIN:** Your QB spend-to-production ratio is poor. You are overpaying for production that could be found for less, or your low-cost QB is underperforming. Consider a change in personnel or system.")
    
    st.write(f"""
    **Unit Summary:**
    * **Most Efficient Unit:** {df_plot.loc[df_plot['ROI'].idxmax(), 'Unit']}
    * **Least Efficient Unit:** {df_plot.loc[df_plot['ROI'].idxmin(), 'Unit']}
    """)
