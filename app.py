import streamlit as st
import math
import pandas as pd

st.set_page_config(page_title="Master Electrical & Project Suite", layout="wide")

# --- 1. ENHANCED ENGINEERING DATABASE ---
# Data derived from "Power Load Calculation.xlsx"
RES_APPLIANCES = [
    "Refrigerator (150W)", "Air Conditioner (2000W)", 
    "10x LED Lights (100W total)", "Television (100W)", 
    "Washing Machine (500W)", "Water Heater (3000W)"
]

TECH_REFS = {
    "Residential": [60, 8, 300, 15, "20A DP", "2.5mm² 3C", 500, 18.0],
    "Shopping Center": [85, 15, 500, 20, "32A TP", "4.0mm² 5C", 800, 11.0],
    "Data Center": [1200, 10, 300, 100, "63A TP", "16mm² 5C", 300, 2.8],
    "Polyclinic": [65, 12, 500, 10, "20A DP", "2.5mm² 3C", 400, 18.0],
    "Hospital": [110, 15, 600, 8, "32A TP", "6.0mm² 5C", 400, 7.3],
    "MRT Station (UG)": [220, 18, 500, 50, "63A TP", "35mm² 5C", 400, 1.35],
    "MRT Station (AG)": [120, 12, 400, 50, "32A TP", "10mm² 5C", 600, 4.4],
    "MSCP (Carpark)": [15, 5, 150, 100, "32A TP", "6.0mm² 5C", 1200, 7.3]
}

if 'project' not in st.session_state:
    st.session_state.project = []

st.title("⚡ Master Electrical Design & Project Suite")

# --- 2. SIDEBAR: DESIGNER INPUTS & DONATION ---
with st.sidebar:
    st.header("🏢 Site Parameters")
    z_name = st.text_input("Area Description", "Level 1")
    z_type = st.selectbox("Building Type", list(TECH_REFS.keys()))
    z_area = st.number_input("Floor Area (m²)", min_value=1.0, value=100.0)
    z_dist = st.number_input("Distance to MSB (m)", min_value=1.0, value=30.0)
    
    sug_db = math.ceil(z_area / TECH_REFS[z_type][6])
    z_db = st.number_input("Sub-boards (DBs)", min_value=1, value=sug_db)
    
    ev_load = 0
    if z_type == "MSCP (Carpark)":
        lots = st.number_input("Total Lots", min_value=1, value=20)
        ev_load = (lots * 7.4) * 0.20 * 1.20 
    
    manpower = st.slider("Electricians on Site", 1, 20, 3)

    if st.button("➕ Add to Master Schedule"):
        st.session_state.project.append({
            "Name": z_name, "Type": z_type, "Area": z_area, 
            "Dist": z_dist, "DBs": z_db, "EV": ev_load
        })
    
    st.divider()
    # --- PAYPAL DONATION SECTION ---
    st.header("☕ Support Development")
    st.write("If this app helps your workflow, consider supporting its development!")
    # Replace the 'YOUR_PAYPAL_EMAIL' with your actual PayPal email or link
    paypal_link = "https://www.paypal.com/donate?business=YOUR_PAYPAL_EMAIL&currency_code=USD"
    st.markdown(f'''
        <a href="{paypal_link}" target="_blank">
            <img src="https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif" border="0" name="submit" title="PayPal - The safer, easier way to pay online!" alt="Donate with PayPal button" />
        </a>
    ''', unsafe_allow_value=True)

# --- 3. CALCULATION ENGINE ---
if st.session_state.project:
    report = []
    total_md, total_hrs, total_cost = 0, 0, 0

    for item in st.session_state.project:
        ref = TECH_REFS[item['Type']]
        total_kw = ((item['Area'] * (ref[0] + ref[1])) / 1000) + item['EV']
        md_kw = total_kw * 0.8
        total_md += md_kw
        
        sockets = math.ceil(item['Area'] / ref[3])
        lights = math.ceil((ref[2] * item['Area']) / (3200 * 0.8 * 0.7))
        
        ib = (md_kw * 1000) / (1.732 * 400 * 0.85)
        vd_pct = ((ref[7] * ib * item['Dist']) / 1000 / 400) * 100
        
        hrs = (sockets * 0.5) + (lights * 0.8) + (item['Dist'] * 0.05) + (item['DBs'] * 5)
        total_hrs += hrs
        cost = (item['Dist'] * 15) + (sockets * 30) + (lights * 60) + (item['DBs'] * 1500)
        total_cost += cost

        report.append({
            "Zone": item['Name'], "Type": item['Type'], "Load (kW)": round(total_kw, 1),
            "Sockets": sockets, "Lights": lights, "Cable": ref[5], 
            "V-Drop %": round(vd_pct, 2), "Status": "✅ Pass" if vd_pct <= 4 else "⚠️ Resize"
        })

    df = pd.DataFrame(report)
    st.subheader("📋 Provisioning & Technical Report")
    st.table(df)

    # --- 4. PROJECT MANAGEMENT & T&C ---
    st.divider()
    days = math.ceil(total_hrs / (manpower * 8))
    c1, c2, c3 = st.columns(3)
    c1.metric("Max Demand", f"{total_md:.1f} kW")
    c2.metric("Project Cost", f"${total_cost:,.2f}")
    c3.metric("Duration", f"{days} Working Days")

    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("🚧 Phase Breakdown")
        st.info(f"**First Fix**: {math.ceil(days*0.4)}d | **Second Fix**: {math.ceil(days*0.4)}d | **T&C**: {math.ceil(days*0.2)}d")
        if any(d['Type'] == "Residential" for d in st.session_state.project):
            st.write("**Residential Provisioning (Based on Load Sheet):**")
            for app in RES_APPLIANCES: st.write(f"- {app}")
    
    with col_right:
        st.subheader("🔍 Testing & Commissioning Checklist")
        st.checkbox("Visual Inspection (Cabling & Terminations)")
        st.checkbox("Continuity of Protective Conductors")
        st.checkbox("Insulation Resistance Test (>1 MΩ)")
        st.checkbox("Polarity Test")
        st.checkbox("Earth Fault Loop Impedance (EFLI)")
        st.checkbox("RCD Operation Test")

    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Export Project Schedule (CSV)", data=csv, file_name="electrical_master_plan.csv")
    
    if st.button("🗑️ Reset All"):
        st.session_state.project = []
        st.rerun()
