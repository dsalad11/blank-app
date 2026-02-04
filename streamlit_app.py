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
    .main {
        background-color: #f8f9fa;
    }
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
    "2025 Minnesota Vikings": [4.5, 2.1, 16.5, 8.2, 15.0, 17.5, 6.2, 12.0, 2.5],
    "2023 49ers (Rookie QB)": [1.2, 6.5, 18.0, 9.0, 12.0, 19.5, 8.5, 11.5, 2.0],
    "2024 Chiefs (Elite QB)": [19.5, 1.5, 7.2, 8.5, 16.5, 15.0, 4.5, 14.5, 2.8],
}

# --- Sidebar Inputs ---
st.sidebar.title("🎮 GM Command Center")
st.sidebar.info("Adjust positional spending to see the ROI impact.")

selected_preset = st.sidebar.selectbox("Load Team Preset", list(PRESETS.keys()))
preset_vals = PRESETS[selected_preset]

# Initialize session state for sliders if not exists
if 'slider_vals' not in st.session_state:
    st.session_state.slider_vals = preset_vals

# Button to trigger Jefferson Extension
if st.sidebar.button("✍️ Sign Jefferson (Max Extension)"):
    # Setting WR to 18% (Index 2 in our list)
    st.session_state.slider_vals[2] = 18.0

# Generate Sliders
current_allocations = []
for i, pos in enumerate(POSITIONS):
    val = st.sidebar.slider(
        f"{pos['name']} (%)", 
        0.0, 30.0, 
        float(st.session_state.slider_vals[i]), 
        key=f"slider_{pos['id']}"
    )
    current_allocations.append(val)

# --- Calculations ---
total_cap = sum(current_allocations)
raw_roi = sum(val * POSITIONS[i]['weight'] for i, val in enumerate(current_allocations))
roi_score = round(raw_roi / (total_cap / 10 if total_cap > 0 else 1), 1)

# --- Dashboard Layout ---
st.title("🏈 NFL Roster ROI & Strategy Tool")
st.markdown("### Analyzing Capital Allocation vs. Historical Success Twins")

# Top Metric Row
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Cap Used", f"{total_cap:.1f}%", delta=f"{100-total_cap:.1f}% Remaining", delta_color="inverse")
col2.metric("Roster ROI Score", roi_score)
col3.metric("Premium Position Spend", f"{current_allocations[0] + current_allocations[4] + current_allocations[5] + current_allocations[7]:.1f}%")

# Success Twin Logic
twin = "2025 Vikings"
twin_type = "Balanced"
if total_cap > 100:
    twin = "Cap Crisis (Saints Style)"
elif current_allocations[2] >= 18:
    twin = "Mega-WR (Dolphins/Raiders)"
elif current_allocations[0] < 3:
    twin = "Rookie Window (49ers)"
elif current_allocations[0] > 15:
    twin = "Elite QB (Chiefs)"

col4.metric("Success Twin", twin)

# Visualizations Row
st.divider()
c1, c2 = st.columns(2)

with c1:
    st.subheader("Capital Allocation Breakdown")
    fig_pie = px.pie(
        values=current_allocations, 
        names=[p['short'] for p in POSITIONS],
        hole=0.5,
        color_discrete_sequence=px.colors.qualitative.Prism
    )
    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
    fig_pie.update_layout(legend_title_text='Position Groups')
    st.plotly_chart(fig_pie, use_container_width=True)

with c2:
    st.subheader("Positional ROI Efficiency")
    # Calculate individual ROI for bar chart
    roi_vals = [val * POSITIONS[i]['weight'] for i, val in enumerate(current_allocations)]
    
    fig_bar = px.bar(
        x=[p['short'] for p in POSITIONS],
        y=roi_vals,
        labels={'x': 'Position Group', 'y': 'Efficiency Grade (ROI)'},
        color=roi_vals,
        color_continuous_scale='Viridis'
    )
    fig_bar.update_layout(showlegend=False)
    st.plotly_chart(fig_bar, use_container_width=True)

# --- AI Strategy Audit ---
st.divider()
st.subheader("✨ AI Roster Audit & Accounting Narrative")

with st.expander("View Strategic Analysis", expanded=True):
    if total_cap > 100:
        st.error(f"🚨 **HARD CAP VIOLATION:** Your roster is {total_cap-100:.1f}% over the limit. From an accounting perspective, you must restructure contracts (Amortization) or release veterans (Impairment) immediately.")
    
    st.write(f"""
    **Current Posture:** {twin} Strategy.
    
    **Executive Summary:** Your current ROI score of **{roi_score}** suggests a strategy that prioritizes 
    {'Premium positions' if roi_score > 7 else 'Depth and non-premium stability'}. 
    By allocating **{current_allocations[0]}%** to the Quarterback department, you are essentially 
    {'betting on a high-cost CEO multiplier' if current_allocations[0] > 15 else 'leveraging a low-cost rookie asset'}.
    
    **Recommendations:**
    1. **Positional Value:** Your spending on RB/LB/ST totals **{current_allocations[1] + current_allocations[6] + current_allocations[8]:.1f}%**. Successful twins usually keep this below 12% to fund the trenches.
    2. **Sustainability:** Ensure your Dead Money (unallocated costs) doesn't climb as you restructure for the Jefferson extension.
    """)

# --- Footer ---
st.caption("Data sources: OverTheCap, Spotrac, and Pro-Football-Reference. Built for Data Analytics in Accounting.")

