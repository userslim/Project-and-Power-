import streamlit as st
import math
import pandas as pd

st.set_page_config(page_title="Ultimate Electrical Project Suite", layout="wide")

# --- MASTER DATABASE ---
# [Power W/m2, Light W/m2, Target Lux, Sqm/Socket, ISO, Cable, DB_Area_Cap]
TECH_REFS = {
    "Residential": [35, 8, 300, 15, "20A DP", "2.5mm² 3C", 500],
    "Shopping Center": [85, 15, 500, 20, "32A TP", "4.0mm² 5C", 800],
    "Data Center": [1200, 10, 300, 100, "63A TP", "16mm² 5C", 300],
    "Polyclinic": [65, 12, 500, 10, "20A DP", "2.5mm² 3C", 400],
    "Hospital": [110, 15, 600, 8, "32A TP", "6.0mm² 5C", 400],
    "Hawker Center": [180, 12, 300, 5, "32A SP", "4.0mm² 3C", 300],
    "Market (Wet)": [45, 10, 200, 25, "20A DP", "2.5mm² 3C", 600],
    "Factory (Light)": [85, 12, 400, 15, "32A TP", "4.0mm² 5C", 1000],
    "Manufacturing": [450, 15, 500, 30, "63A TP", "25mm² 5C", 1000],
    "MRT Station (UG)": [220, 18, 500, 50, "63A TP", "35mm² 5C", 400],
    "MRT Station (AG)": [120, 12, 400, 50, "32A TP", "10mm² 5C", 600],
    "MSCP (Carpark)": [15, 5, 150, 100, "32A TP", "6.0mm² 5C", 1200]
}

if 'project' not in st.session_state:
    st.session_state.project = []

st.title("⚡ Professional Electrical Design & Project Management Suite")

# --- SIDEBAR: DESIGNER INPUT ---
with st.sidebar:
    st.header("🏢 Zone Configuration")
    z_name = st.text_input("Zone/Level Name", "Level 1")
    z_type = st.selectbox("Building Category", list(TECH_REFS.keys()))
    z_area = st.number_input("Floor Area (m²)", min_value=1.0, value=500.0)
    z_dist = st.number_input("Distance from MSB (m)", min_value=1.0, value=40.0)
    
    # --- FIXED LINE 38 ---
    suggested_db = math.ceil(z_area / TECH_REFS[z_type][6])
    z_db = st.number_input("No. of Sub-boards (DB)", min_value=1, value=suggested_db)
    
    ev_load = 0
    if z_type == "MSCP (Carpark)":
        lots = st.number_input("Parking Lots", min_value=1, value=50)
        # Active (20%) + Spare (20%) of 7.4kW loads
        ev_load = (lots * 7.4) * 0.20 * 1.20 
    
    manpower = st.slider("Electricians Available", 1, 20, 5)

    if st.button("➕ Add to Master Plan"):
        st.session_state.project.append({
            "Name": z_name, "Type": z_type, "Area": z_area, 
            "Dist": z_dist, "DBs": z_db, "EV": ev_load
        })

# --- CALCULATION ENGINE ---
if st.session_state.project:
    full_report = []
    total_md = 0
    total_labor_hrs = 0
    total_cost = 0

    for item in st.session_state.project:
        ref = TECH_REFS[item['Type']]
        p_watt = item['Area'] * ref[0]
        l_watt = item['Area'] * ref[1]
        total_kw = (p_watt + l_watt) / 1000 + item['EV']
        md_kw = total_kw * 0.8 
        total_md += md_kw
        
        sockets = math.ceil(item['Area'] / ref[3])
        fixtures = math.ceil((ref[2] * item['Area']) / (4000 * 0.8 * 0.7))
        switches = math.ceil(fixtures / 8)
        
        hours = (sockets * 0.5) + (fixtures * 0.8) + (item['Dist'] * 0.06) + (item['DBs'] * 6)
        total_labor_hrs += hours
        cost = (item['Dist'] * 15) + (sockets * 25) + (fixtures * 65) + (item['DBs'] * 1200)
        total_cost += cost

        full_report.append({
            "Zone": item['Name'], "Type": item['Type'], "Wattage (kW)": round(total_kw, 1),
            "13A Sockets": sockets, "LED Fixtures": fixtures, "Switches": switches,
            "Isolator": ref[4], "Cable": ref[5], "Sub-boards": item['DBs'], "Labor (Hrs)": round(hours, 1)
        })

    df = pd.DataFrame(full_report)
    st.subheader("📊 Execution & Provisioning Schedule")
    st.table(df)

    # --- PROJECT MANAGEMENT DASHBOARD ---
    st.divider()
    c1, c2, c3 = st.columns(3)
    days = math.ceil(total_labor_hrs / (manpower * 8))
    c1.metric("Max Demand (MD)", f"{total_md:.1f} kW")
    c2.metric("Est. Total Budget", f"${total_cost:,.2f}")
    c3.metric("Installation Timeline", f"{days} Days")

    st.subheader("🚧 Phase-by-Phase Timeline")
    ph1, ph2, ph3 = st.columns(3)
    ph1.info(f"**Phase 1: First Fix ({math.ceil(days*0.4)} days)**\nContainment & Conduits")
    ph2.warning(f"**Phase 2: Second Fix ({math.ceil(days*0.4)} days)**\nWiring & Terminations")
    ph3.success(f"**Phase 3: Final Fix ({math.ceil(days*0.2)} days)**\nFitting & Commissioning")

    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Final Report", data=csv, file_name="master_plan.csv")

    if st.button("🗑️ Reset All"):
        st.session_state.project = []
        st.rerun()
