import streamlit as st
import pandas as pd
import plotly.express as px

# --- Configuration & Memory ---
st.set_page_config(page_title="NFL GM ROI Tool", layout="wide")

# This ensures the sliders don't reset when you click things
if "roster_data" not in st.session_state:
    st.session_state.roster_data = {
        "Minnesota Vikings": [4.5, 2.1, 16.5, 8.2, 15.0, 17.5, 6.2, 12.0, 2.5],
        "New England Patriots": [3.8, 4.2, 8.5, 5.0, 14.0, 16.0, 8.0, 15.0, 3.0]
    }

# --- Sidebar: Data Ingestion ---
st.sidebar.title("📥 Data Import")
uploaded_file = st.sidebar.file_uploader("Upload OTC/Spotrac CSV", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.sidebar.success("Data Loaded!")
    # Logic to map CSV columns to our positions would go here
    # For now, let's keep the manual controls active as well

# --- Roster Selection Logic ---
st.sidebar.divider()
st.sidebar.title("🎮 GM Controls")
team_choice = st.sidebar.selectbox("Select Team", list(st.session_state.roster_data.keys()))

# --- Positional Setup ---
POSITIONS = ["QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB", "ST"]
WEIGHTS = [1.0, 0.3, 0.8, 0.5, 0.9, 0.9, 0.4, 0.7, 0.2]

# Load values into sliders from session state
current_vals = []
for i, pos in enumerate(POSITIONS):
    val = st.sidebar.slider(
        f"{pos} Spend %", 0.0, 30.0, 
        st.session_state.roster_data[team_choice][i],
        key=f"slider_{team_choice}_{pos}" # Unique key per team/pos
    )
    current_vals.append(val)

# Performance Grades (Manual for now, until we link a Stats CSV)
st.sidebar.subheader("📈 Performance Grades")
perf_vals = []
for pos in POSITIONS:
    p = st.sidebar.number_input(f"{pos} Grade", 0, 100, 75, key=f"perf_{pos}")
    perf_vals.append(p)

# --- Calculations ---
total_cap = sum(current_vals)
roi_scores = [(p / (s if s > 0 else 1)) * w for p, s, w in zip(perf_vals, current_vals, WEIGHTS)]
avg_roi = sum(roi_scores) / len(POSITIONS)

# --- Main Dashboard ---
st.title(f"🏈 {team_choice} ROI Analysis")

col1, col2, col3 = st.columns(3)
col1.metric("Cap Utilization", f"{total_cap:.1f}%")
col2.metric("Team Efficiency", f"{avg_roi:.2f}")
qb_roi = (perf_vals[0] / current_vals[0]) if current_vals[0] > 0 else 0
col3.metric("QB Value Multiplier", f"{qb_roi:.1f}x")

# Visualization: Efficiency Matrix
df_plot = pd.DataFrame({
    "Position": POSITIONS,
    "Spend": current_vals,
    "Performance": perf_vals,
    "ROI": roi_scores
})

fig = px.scatter(df_plot, x="Spend", y="Performance", text="Position", size="ROI", color="ROI",
                 color_continuous_scale="RdYlGn", title="Spending vs. Production Efficiency")
st.plotly_chart(fig, use_container_width=True)

# --- AI Breakdown ---
st.divider()
st.subheader("🕵️ AI Audit")
if qb_roi < 5 and perf_vals[0] < 70:
    st.error(f"**Critical Issue:** The {team_choice} are in 'Dead Zone' QB play. Low spend is being met with low production, preventing capital from being 'unlocked' for other positions.")
else:
    st.success(f"**Strategic Insight:** The {team_choice} are successfully leveraging their current roster structure.")

st.info("💡 **Pro Tip:** Download a 'Team Cap' CSV from OverTheCap and upload it via the sidebar to automate this!")

