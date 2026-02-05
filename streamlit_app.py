import streamlit as st
import pandas as pd
import plotly.express as px

# --- Configuration & Memory ---
st.set_page_config(page_title="NFL GM ROI Tool", layout="wide")

# Standard NFL Positions & Weights
POS_MAP = {
    "QB": ["QB"],
    "RB": ["RB", "FB"],
    "WR": ["WR"],
    "TE": ["TE"],
    "OL": ["LT", "LG", "C", "RG", "RT", "G", "T", "OL"],
    "DL": ["ED", "IDL", "DT", "DE", "DL"],
    "LB": ["LB", "ILB", "OLB"],
    "DB": ["CB", "S", "FS", "SS", "DB"],
    "ST": ["K", "P", "LS"]
}

# Initial State Setup
if "current_spend" not in st.session_state:
    st.session_state.current_spend = {p: 5.0 for p in POS_MAP.keys()} # Default 5% each
if "team_name" not in st.session_state:
    st.session_state.team_name = "Custom Team"

# --- Sidebar: Data Ingestion ---
st.sidebar.title("📥 Data Import")
uploaded_file = st.sidebar.file_uploader("Upload OTC/Spotrac CSV", type=["csv"])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
        
        # --- THE MAPPER LOGIC ---
        # 1. Find the right columns (OTC usually uses 'Pos' and 'Cap Number')
        pos_col = next((c for c in df.columns if "pos" in c.lower()), None)
        cap_col = next((c for c in df.columns if "cap" in c.lower() and "num" in c.lower() or "hit" in c.lower()), None)

        if pos_col and cap_col:
            # Clean the money column (remove $, commas)
            df[cap_col] = df[cap_col].replace(r'[\$,]', '', regex=True).astype(float)
            total_team_cap = df[cap_col].sum()
            
            # Group by our standard categories
            new_spend = {}
            for category, sub_pos in POS_MAP.items():
                category_total = df[df[pos_col].isin(sub_pos)][cap_col].sum()
                percentage = (category_total / total_team_cap) * 100
                new_spend[category] = round(percentage, 1)
            
            # Update Session State
            st.session_state.current_spend = new_spend
            st.sidebar.success("✅ Roster analyzed! Sliders updated.")
        else:
            st.sidebar.error("Could not find 'Position' or 'Cap' columns in this file.")
    except Exception as e:
        st.sidebar.error(f"Error processing file: {e}")

# --- GM Controls ---
st.sidebar.divider()
st.sidebar.title("🎮 GM Controls")

# Create Sliders using the session state values
final_spend = {}
for pos in POS_MAP.keys():
    # We use 'value' from session_state so it updates when the file is uploaded
    final_spend[pos] = st.sidebar.slider(
        f"{pos} Spend %", 0.0, 40.0, 
        value=st.session_state.current_spend.get(pos, 5.0),
        key=f"slider_{pos}"
    )

# --- Main Dashboard ---
st.title(f"🏈 {st.session_state.team_name} ROI Analysis")

# Simple ROI Mockup (Using 75 as a default performance grade)
total_cap = sum(final_spend.values())
perf_grade = 75 # This could be linked to a second file upload for PFF stats
avg_roi = (perf_grade / (total_cap / len(POS_MAP))) if total_cap > 0 else 0

col1, col2, col3 = st.columns(3)
col1.metric("Cap Utilization", f"{total_cap:.1f}%")
col2.metric("Efficiency Score", f"{avg_roi:.2f}")
qb_pct = final_spend["QB"]
col3.metric("QB Spend Level", f"{qb_pct}%")

# Visualization
df_plot = pd.DataFrame({
    "Position": list(final_spend.keys()),
    "Spend": list(final_spend.values())
})
fig = px.bar(df_plot, x="Position", y="Spend", color="Spend", title="Current Cap Allocation")
st.plotly_chart(fig, use_container_width=True)

st.info("The sliders now reflect the data from your uploaded CSV. You can still tweak them manually to see 'What If' scenarios.")
