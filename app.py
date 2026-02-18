import streamlit as st
import math
import pandas as pd

st.set_page_config(page_title="Master Electrical Project Suite", layout="wide")

# --- 1. DATA FROM RESIDENTIAL LOAD CALCULATION ---
RES_ITEMS = {
    "Refrigerator": 150,
    "Air Conditioner": 2000,
    "LED Lights (10 nos)": 100,
    "Television": 100,
    "Washing Machine": 500,
    "Water Heater": 3000
}

# [Power W/m2, Light W/m2, Target Lux, Sqm/Socket, ISO, Cable, DB_Cap_sqm, mV_A_m]
TECH_REFS = {
    "Residential": [60, 8, 300, 15, "20A DP", "2.5mm² 3C", 500, 18.0],
    "Shopping Center": [85, 15, 500, 20, "32A TP", "4.0mm² 5C", 800, 11.0],
    "Data Center": [1200, 10, 300, 100, "63A TP", "16mm² 5C", 300, 2.8],
    "Polyclinic": [65, 12, 500, 10, "20A DP", "2.5mm² 3C", 400, 18.0],
    "Hospital": [110, 15, 600, 8, "32A TP", "6.0mm² 5C", 400, 7.3],
    "Hawker Center": [180, 12, 300, 5, "32A SP", "4.0mm² 3C", 300, 11.0],
    "Market (Wet)": [45, 10, 200, 25, "20A DP", "2.5mm² 3C", 600, 18.0],
    "Factory (Light)": [85, 12, 400, 15, "32A TP", "4.0mm² 5C", 1000, 11.0],
    "Manufacturing": [450, 15, 500, 30, "63A TP", "25mm² 5C", 1000, 1.8],
    "MRT Station (UG)": [220, 18, 500, 50, "63A TP", "35mm² 5C", 400, 1.35],
    "MRT Station (AG)": [120, 12, 400, 50, "32A TP", "10mm² 5C", 600, 4.4],
    "MSCP (Carpark)": [15, 5, 150, 100, "32A TP", "6.0mm² 5C", 1200, 7.3]
}

if 'project' not in st.session_state:
    st.session_state.project = []

st.title("⚡ Master Electrical Design & Project Suite")

# --- 2. SIDEBAR: INPUTS & DONATION ---
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
    st.header("☕ Support Development")
    paypal_url = "https://www.paypal.com/donate?business=YOUR_PAYPAL_EMAIL&currency_code=USD"
    st.markdown(f'''
        <a href="{paypal_url}" target="_blank">
            <img src="https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif" border="0" title="Donate with PayPal" alt="Donate" />
        </a>
    ''', unsafe_allow_html=True)

# --- 3. CALCULATION ENGINE ---
if st.session_state.project:
    report = []
    total_md, total_hrs, total_cost = 0, 0, 0

    for item in st.session_state.project:
        ref = TECH_REFS[item['Type']]
        p_density = ref[0]
        l_density = ref[1]
        
        total_kw = ((item['Area'] * (p_density + l_density)) / 1000) + item['EV']
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
            "Zone": item['Name'], 
            "Type": item['Type'],
            "P-Density (W/m²)": p_density,
            "L-Density (W/m²)": l_density,
            "Load (kW)": round(total_kw, 1),
            "Sockets": sockets, 
            "Lights": lights, 
            "Cable": ref[5], 
            "V-Drop %": round(vd_pct, 2), 
            "Status": "✅ Pass" if vd_pct <= 4 else "⚠️ Resize"
        })

    df = pd.DataFrame(report)
    st.subheader("📋 Engineering Provisioning Schedule")
    st.table(df)

    # --- 4. PROJECT DASHBOARD ---
    st.divider()
    days = math.ceil(total_hrs / (manpower * 8))
    m1, m2, m3 = st.columns(3)
    m1.metric("Building Max Demand", f"{total_md:.1f} kW")
    m2.metric("Total Project Cost", f"${total_cost:,.2f}")
    m3.metric("Installation Timeline", f"{days} Days")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🚧 Phase Breakdown")
        st.info(f"**First Fix**: {math.ceil(days*0.4)}d | **Second Fix**: {math.ceil(days*0.4)}d | **T&C**: {math.ceil(days*0.2)}d")
        
        if any(d['Type'] == "Residential" for d in st.session_state.project):
            st.write("**Residential Reference (from Load Sheet):**")
            for app, watts in RES_ITEMS.items():
                st.write(f"- {app}: {watts}W")

    with col2:
        st.subheader("🔍 Reference Standards Table")
        ref_df = pd.DataFrame.from_dict(TECH_REFS, orient='index', 
                                        columns=['P-Density', 'L-Density', 'Lux', 'Sqm/Socket', 'ISO', 'Cable', 'DB_Cap', 'mV/A/m'])
        st.dataframe(ref_df[['P-Density', 'L-Density', 'Lux']])

    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Export Report (CSV)", data=csv, file_name="site_provision_plan.csv")
    
    if st.button("🗑️ Clear All Data"):
        st.session_state.project = []
        st.rerun()
