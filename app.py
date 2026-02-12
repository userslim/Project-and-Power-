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
    num_switches = max(1, math.ceil(area / 30))   # one switch per 30m²
    return {
        "power_w_m2": power_w_m2,
        "total_power": total_power,
        "total_light_w": total_light_w,
        "num_sockets": num_sockets,
        "isolator": isolator,
        "num_lights": num_lights,
        "num_switches": num_switches,
        # circuits: each socket + each light = 1 circuit
        "num_circuits": num_sockets + num_lights
    }

def estimate_panels(project_df):
    """Return dict with number of main switchboard, DBs and sub-boards."""
    if project_df.empty:
        return {"msb": 1, "db": 0, "sub": 0}
    
    # Total circuits for the whole building
    total_circuits = project_df["num_circuits"].sum()
    
    # Distribution boards: one 18-way DB per 18 circuits (or part thereof)
    db_count = math.ceil(total_circuits / 18)
    
    # Sub-boards: one per zone that exceeds 50 kW
    sub_count = (project_df["total_power_kW"] > 50).sum()
    
    # Main Switchboard: always 1 for the building
    return {"msb": 1, "db": db_count, "sub": sub_count}

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
        zone_entry = {
            "description": z_name,
            "type": z_type,
            "area_m2": z_area,
            "power_w_m2": calc["power_w_m2"],
            "total_power_kW": round(calc["total_power"] / 1000, 2),
            "sockets": calc["num_sockets"],
            "isolator": calc["isolator"],
            "lights": calc["num_lights"],
            "light_switches": calc["num_switches"],
            "num_circuits": calc["num_circuits"]   # store for later use
        }
        st.session_state.project.append(zone_entry)
        st.success(f"Added {z_name}")

    if st.button("🧹 Clear Project", use_container_width=True):
        st.session_state.project = []
        st.rerun()

# --- 5. MAIN PAGE ---
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
    col_order = ["description", "type", "area_m2", "power_w_m2", "total_power_kW",
                 "sockets", "isolator", "lights", "light_switches", "num_circuits"]
    df = df[col_order]
    st.dataframe(df, use_container_width=True, hide_index=True)

    total_building_power_kW = df["total_power_kW"].sum()
    st.success(f"🏢 **Overall Building Power Load: {total_building_power_kW:.2f} kW**")
else:
    df = pd.DataFrame()  # empty
    st.info("No areas added yet. Use the sidebar to add your first zone.")

# --- 6. PANEL SCHEDULER & SPACE PLANNER ---
st.header("🔌 Panel Scheduler & Space Planner")

if not st.session_state.project:
    st.info("Add at least one area to enable panel planning.")
else:
    # --- 6.1 Automatic panel counts ---
    panel_req = estimate_panels(df)
    
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Main Switchboard (MSB)", panel_req["msb"])
    with col_b:
        st.metric("Distribution Boards (DB)", panel_req["db"])
    with col_c:
        st.metric("Sub‑boards", panel_req["sub"])

    st.markdown("---")
    st.subheader("📏 Electrical Room Space Check (800 mm clearance)")

    # --- 6.2 Standard panel dimensions (width x depth in meters) ---
    PANEL_DIMS = {
        "msb": (1.2, 0.6),   # width, depth
        "db":  (0.6, 0.2),
        "sub": (0.8, 0.3)
    }

    # User inputs for electrical room
    room_len = st.number_input("Room length (m)", min_value=0.5, value=5.0, step=0.5)
    room_wid = st.number_input("Room width (m)",  min_value=0.5, value=3.0, step=0.5)

    # Total wall length required if all panels are placed side‑by‑side
    total_width = (panel_req["msb"] * PANEL_DIMS["msb"][0] +
                   panel_req["db"]  * PANEL_DIMS["db"][0] +
                   panel_req["sub"] * PANEL_DIMS["sub"][0])

    # Required depth: the deepest panel + 0.8m clearance in front
    max_depth = max(PANEL_DIMS["msb"][1], PANEL_DIMS["db"][1], PANEL_DIMS["sub"][1])
    required_depth = max_depth + 0.8

    col1, col2 = st.columns(2)
    with col1:
        st.info(f"📏 **Total panel width:** {total_width:.2f} m")
        st.info(f"📐 **Required room depth:** {required_depth:.2f} m")
    with col2:
        width_ok = room_len >= total_width
        depth_ok = room_wid >= required_depth
        if width_ok and depth_ok:
            st.success("✅ Room dimensions satisfy 800 mm clearance.")
        else:
            st.error("❌ Room too small. Adjust dimensions or panel counts.")

    # Additional layout hint
    if width_ok and depth_ok:
        st.markdown(f"*Place panels along the {room_len:.2f} m wall.*")
    else:
        if not width_ok:
            st.warning(f"Need at least {total_width:.2f} m wall length (current: {room_len:.2f} m).")
        if not depth_ok:
            st.warning(f"Need at least {required_depth:.2f} m room depth (current: {room_wid:.2f} m).")
