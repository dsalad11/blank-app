import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- Page Configuration ---
st.set_page_config(
    page_title="NFL GM Roster ROI Dashboard",
    page_icon="🏈",
    layout="wide"
)

# --- Custom Styling ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# --- Data Structures ---
POSITIONS = [
    {"id": "qb", "name": "Quarterback", "short": "QB", "weight": 1.0},
    {"id": "rb", "name": "Running Back", "short": "RB", "weight": 0.3},
    {"id": "wr", "name": "Wide Receiver", "short": "WR", "weight": 0.8},
    {"id": "te", "name": "Tight End", "short": "TE", "weight": 0.5},
    {"id": "ol", "name": "Offensive Line", "short": "OL", "weight": 0.9},
    {"id": "dl", "name": "Defensive Line", "short": "DL", "weight": 0.9},
    {"id": "lb", "name": "Linebacker", "short": "LB", "weight": 0.4},
    {"id": "db", "name": "Secondary", "short": "DB", "weight": 0.7},
    {"id": "st", "name": "Special Teams", "short": "ST", "weight": 0.2},
]

PRESETS = {
    "2025 Minnesota Vikings": {"spend": [4.5, 2.1, 16.5, 8.2, 15.0, 17.5, 6.2, 12.0, 2.5], "prod": [45, 60, 95, 75, 70, 78, 65, 72, 80]},
    "2025 New England Patriots": {"spend": [3.8, 4.2, 8.5, 5.0, 14.0, 16.0, 8.0, 15.0, 3.0], "prod": [92, 55, 60, 50, 65, 82, 70, 88, 75]},
    "2024 Chiefs (Elite QB)": {"spend": [19.5, 1.5, 7.2, 8.5, 16.5, 15.0, 4.5, 14.5, 2.8], "prod": [98, 70, 65, 90, 85, 88, 75, 92, 85]},
}

# --- Sidebar Inputs ---
st.sidebar.title("🎮 GM Command Center")

selected_preset = st.sidebar.selectbox("Load Team Preset", list(PRESETS.keys()))
preset_spend = PRESETS[selected_preset]["spend"]
preset_prod = PRESETS[selected_preset]["prod"]

st.sidebar.subheader("💰 Cap Allocation (%)")
current_allocations = []
for i, pos in enumerate(POSITIONS):
    val = st.sidebar.slider(f"{pos['short']} Spend", 0.0, 30.0, float(preset_spend[i]), key=f"s_{pos['id']}")
    current_allocations.append(val)

st.sidebar.subheader("📊 Production Grade (1-100)")
current_production = []
for i, pos in enumerate(POSITIONS):
    p_val = st.sidebar.slider(f"{pos['short']} Performance", 0, 100, int(preset_prod[i]), key=f"p_{pos['id']}")
    current_production.append(p_val)

# --- Calculations ---
total_cap = sum(current_allocations)
# ROI = (Production / Spend) weighted by positional importance
roi_components = []
for i in range(len(POSITIONS)):
    spend = current_allocations[i] if current_allocations[i] > 0 else 0.1
    efficiency = (current_production[i] / spend) * POSITIONS[i]['weight']
    roi_components.append(efficiency)

avg_roi = sum(roi_components) / len(POSITIONS)

# --- Dashboard Layout ---
st.title("🏈 NFL Roster ROI & Strategy Tool")

# Top Metric Row
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Cap Used", f"{total_cap:.1f}%", delta=f"{100-total_cap:.1f}% Rem.", delta_color="inverse")
col2.metric("Team Efficiency Rating", f"{avg_roi:.1f}")
qb_roi = (current_production[0] / current_allocations[0]) if current_allocations[0] > 0 else 0
col3.metric("QB ROI (Production/Cost)", f"{qb_roi:.1f}x")

# Logic for Success Twin
twin = "Average Efficiency"
if qb_roi > 20:
    twin = "Elite Rookie Value (Patriots/49ers)"
elif current_allocations[0] > 15 and current_production[0] > 90:
    twin = "Elite Vet (Chiefs/Bengals)"
elif current_production[0] < 60 and current_allocations[0] < 10:
    twin = "QB Purgatory (Vikings/Giants)"

col4.metric("Strategic Archetype", twin)

st.divider()

# Visualizations Row
c1, c2 = st.columns(2)

with c1:
    st.subheader("The Efficiency Matrix: Production vs. Cost")
    # Scatter plot to show ROI clearly
    df_plot = pd.DataFrame({
        "Position": [p['short'] for p in POSITIONS],
        "Spend (%)": current_allocations,
        "Production": current_production,
        "ROI": roi_components
    })
    
    fig_scatter = px.scatter(
        df_scatter := df_plot, x="Spend (%)", y="Production", 
        text="Position", size="ROI", color="ROI",
        color_continuous_scale='RdYlGn',
        title="Upper Left = High ROI (Steals) | Lower Right = Low ROI (Busts)"
    )
    fig_scatter.update_traces(textposition='top center')
    st.plotly_chart(fig_scatter, use_container_width=True)

with c2:
    st.subheader("Weighted ROI per Unit")
    fig_bar = px.bar(
        df_plot, x="Position", y="ROI",
        color="ROI", color_continuous_scale='Viridis'
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# --- AI Strategy Audit ---
st.divider()
st.subheader("✨ AI Executive Audit")

with st.expander("View Financial & Performance Analysis", expanded=True):
    qb_spend = current_allocations[0]
    qb_perf = current_production[0]
    
    if qb_spend < 10 and qb_perf < 60:
        st.warning(f"⚠️ **QB EFFICIENCY ALERT:** You are spending very little ({qb_spend}%) on QB, but the production ({qb_perf}) is sub-par. This is 'False Economy'—the savings aren't being converted into wins.")
    elif qb_spend < 10 and qb_perf > 85:
        st.success(f"💎 **MAXIMUM LEVERAGE:** The {selected_preset} are receiving elite QB play on a budget. This is the 'Super Bowl Window' profile.")
    
    st.write(f"""
    **Unit Analysis:**
    * **Best Value Unit:** {df_plot.loc[df_plot['ROI'].idxmax(), 'Position']}
    * **Worst Value Unit:** {df_plot.loc[df_plot['ROI'].idxmin(), 'Position']}
    
    **GM Recommendation:** Your roster is currently categorized as a **{twin}**. 
    To improve your **{avg_roi:.1f}** Efficiency Rating, look at the units in the lower-right of the Efficiency Matrix. 
    Those units are 'Cap Bleeders'—high cost with low output.
    """)

st.caption("ROI Formula: (Production Grade / Cap Allocation %) * Positional Weighting")
