import streamlit as st
import math
import pandas as pd

st.set_page_config(page_title="Master Electrical Project Suite", layout="wide")

# --- Constants & Data ---
TECH_DB = {
    "Residential": [35, 8, 300, 15, "2.5mm²", 1.20, 18.0],
    "Shopping Center": [85, 15, 500, 20, "4.0mm²", 1.80, 11.0],
    "Data Center": [1200, 10, 300, 100, "16mm²", 6.50, 2.8],
    "Polyclinic": [65, 12, 500, 10, "2.5mm²", 1.20, 18.0],
    "Hospital": [110, 15, 600, 8, "6.0mm²", 2.50, 7.3],
    "MRT Station (UG)": [220, 18, 500, 50, "35mm²", 14.0, 1.35],
    "MSCP (Carpark)": [15, 5, 150, 100, "6.0mm²", 2.50, 7.3]
}

if 'proj' not in st.session_state:
    st.session_state.proj = []

st.title("⚡ Professional Electrical Project Life-Cycle Planner")

# --- Sidebar Inputs ---
with st.sidebar:
    st.header("📍 Site Details")
    name = st.text_input("Zone Name", "Phase 1")
    b_type = st.selectbox("Building Type", list(TECH_DB.keys()))
    area = st.number_input("Floor Area (m²)", min_value=1.0, value=500.0)
    dist = st.number_input("Distance to MSB (m)", min_value=1.0, value=50.0)
    men = st.slider("Electricians on Site", 1, 20, 5)
    
    if st.button("Add to Master Plan"):
        st.session_state.proj.append({"Name": name, "Type": b_type, "Area": area, "Dist": dist})

# --- Calculations ---
if st.session_state.proj:
    summary_data = []
    total_hours = 0
    
    for item in st.session_state.proj:
        ref = TECH_DB[item['Type']]
        sockets = math.ceil(item['Area'] / ref[3])
        lights = math.ceil((ref[2] * item['Area']) / 3500)
        
        # Man-hour logic: Fix 1 (40%), Fix 2 (40%), T&C (20%)
        zone_hours = (sockets * 0.5) + (lights * 0.8) + (item['Dist'] * 0.05) + 8.0
        total_hours += zone_hours
        
        summary_data.append({
            "Zone": item['Name'], "Sockets": sockets, "Lights": lights, 
            "Cable": ref[4], "Total Hrs": round(zone_hours, 1)
        })

    df = pd.DataFrame(summary_data)
    total_days = math.ceil(total_hours / (men * 8))

    # --- Phase Breakdown ---
    st.subheader("📅 Construction Timeline (Phase-by-Phase)")
    
    p1, p2, p3 = st.columns(3)
    with p1:
        st.header("🏗️ First Fix")
        st.write(f"**Duration:** {round(total_days * 0.4, 1)} Days")
        st.info("- Install Trays & Trunking\n- Concealed Conduits\n- Mounting Box installation")
    with p2:
        st.header("🔌 Second Fix")
        st.write(f"**Duration:** {round(total_days * 0.4, 1)} Days")
        st.info("- Cable Pulling\n- DB Termination\n- Socket/Switch Wiring")
    with p3:
        st.header("🔍 Final Fix & T&C")
        st.write(f"**Duration:** {round(total_days * 0.2, 1)} Days")
        st.info("- Fitting Lights/Plates\n- Insulation Resistance Test\n- Polarity & Continuity Test")

    st.divider()
    st.subheader("📊 Material & Labor Dashboard")
    st.table(df)
    
    # Export
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Project Schedule", data=csv, file_name="site_plan.csv")