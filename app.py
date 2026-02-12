import streamlit as st
import math
import pandas as pd

st.set_page_config(page_title="Master Electrical Project Suite", layout="wide")

# --- 1. COMPREHENSIVE ENGINEERING DATABASE ---
# [Power W/m2, Light W/m2, Target Lux, Sqm/Socket, ISO, Cable, DB_Cap_sqm, mV_A_m]
TECH_REFS = {
    "Residential": [35, 8, 300, 15, "20A DP", "2.5mm² 3C", 500, 18.0],
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

# --- 2. INITIALISE SESSION STATE ---
if 'project' not in st.session_state:
    st.session_state.project = []

# --- 3. HELPER FUNCTIONS ---
def calculate_zone(area, tech_data, light_wattage):
    """Return dict with all calculated values for one zone."""
    power_w_m2, light_w_m2, _, sqm_per_socket, isolator, _, _, _ = tech_data
    total_power = area * power_w_m2
    total_light_w = area * light_w_m2
    num_sockets = math.ceil(area / sqm_per_socket) if sqm_per_socket > 0 else 0
    num_lights = math.ceil(total_light_w / light_wattage) if light_wattage > 0 else 0
    num_switches = max(1, math.ceil(area / 30))   # one switch per 30m², at least one
    return {
        "power_w_m2": power_w_m2,
        "total_power": total_power,
        "total_light_w": total_light_w,
        "num_sockets": num_sockets,
        "isolator": isolator,
        "num_lights": num_lights,
        "num_switches": num_switches
    }

# --- 4. SIDEBAR: INPUTS & ADD TO PROJECT ---
with st.sidebar:
    st.header("🏢 Site Parameters")
    z_name = st.text_input("Area Description", "Level 1")
    z_type = st.selectbox("Building Type", list(TECH_REFS.keys()))
    z_area = st.number_input("Area (sqm)", min_value=0.0, value=100.0, step=10.0)
    light_wattage = st.number_input("Light Fixture Wattage (W)", min_value=1, value=15, step=1)

    # Get tech data for selected type
    tech_data = TECH_REFS[z_type]
    calc = calculate_zone(z_area, tech_data, light_wattage)

    st.markdown("---")
    if st.button("➕ Add to Project", use_container_width=True):
        # Store all relevant data
        zone_entry = {
            "description": z_name,
            "type": z_type,
            "area_m2": z_area,
            "power_w_m2": calc["power_w_m2"],
            "total_power_kW": round(calc["total_power"] / 1000, 2),
            "sockets": calc["num_sockets"],
            "isolator": calc["isolator"],
            "lights": calc["num_lights"],
            "light_switches": calc["num_switches"]
        }
        st.session_state.project.append(zone_entry)
        st.success(f"Added {z_name}")

    if st.button("🧹 Clear Project", use_container_width=True):
        st.session_state.project = []
        st.rerun()

# --- 5. MAIN PAGE: CURRENT CALCULATION & PROJECT SUMMARY ---
st.title("⚡ All-in-One Electrical Design & Project Management Suite")

# --- 5.1 Current zone results (live) ---
st.header("📐 Current Area Design")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Reference Power Density", f"{calc['power_w_m2']} W/m²")
    st.metric("Total Power Load", f"{calc['total_power']/1000:.2f} kW")
with col2:
    st.metric("13A Socket Outlets", calc["num_sockets"])
    st.metric("Recommended Isolator", calc["isolator"])
with col3:
    st.metric("Light Switches", calc["num_switches"])
    st.metric(f"Lights @ {light_wattage}W", calc["num_lights"])

# --- 5.2 Project summary ---
st.header("📋 Project Summary")
if st.session_state.project:
    df = pd.DataFrame(st.session_state.project)
    # Reorder columns for clarity
    col_order = ["description", "type", "area_m2", "power_w_m2", "total_power_kW",
                 "sockets", "isolator", "lights", "light_switches"]
    df = df[col_order]
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Overall building power load
    total_building_power_kW = df["total_power_kW"].sum()
    st.success(f"🏢 **Overall Building Power Load: {total_building_power_kW:.2f} kW**")
else:
    st.info("No areas added yet. Use the sidebar to add your first zone.")
