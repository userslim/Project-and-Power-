import streamlit as st
import math
import pandas as pd
import io
from fpdf import FPDF

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
    "MSCP (Carpark)": [15, 5, 150, 100, "32A TP", "6.0mm² 5C", 1200, 7.3],
    # Special equipment types (area‑independent)
    "Lift (Passenger)": [0, 0, 0, 0, "32A TP", "6.0mm² 5C", 0, 0],
    "Escalator": [0, 0, 0, 0, "63A TP", "16mm² 5C", 0, 0],
}

# Cable current carrying capacity (PVC, clipped direct)
CABLE_CURRENT = {
    "1.5mm²": 16,
    "2.5mm²": 22,
    "4.0mm²": 30,
    "6.0mm²": 38,
    "10mm²": 52,
    "16mm²": 70,
    "25mm²": 94,
    "35mm²": 115,
    "50mm²": 140
}
CABLE_MV_A_M = {
    "1.5mm²": 29.0,
    "2.5mm²": 18.0,
    "4.0mm²": 11.0,
    "6.0mm²": 7.3,
    "10mm²": 4.4,
    "16mm²": 2.8,
    "25mm²": 1.8,
    "35mm²": 1.35,
    "50mm²": 1.0
}

# --- 2. INITIALISE SESSION STATE ---
if 'project' not in st.session_state:
    st.session_state.project = []
if 'eq_counter' not in st.session_state:
    st.session_state.eq_counter = {'lift': 1, 'esc': 1}  # for unique descriptions

# --- 3. HELPER FUNCTIONS ---
def calculate_zone(area, tech_data, light_wattage, override_light_w_m2=None):
    """
    Return dict with all calculated values for one zone.
    If override_light_w_m2 is provided, it overrides the database light W/m².
    """
    power_w_m2, light_w_m2, _, sqm_per_socket, isolator, cable, _, _ = tech_data
    # Use override if given
    if override_light_w_m2 is not None:
        light_w_m2 = override_light_w_m2
        
    total_power = area * power_w_m2
    total_light_w = area * light_w_m2
    num_sockets = math.ceil(area / sqm_per_socket) if sqm_per_socket > 0 else 0
    num_lights = math.ceil(total_light_w / light_wattage) if light_wattage > 0 else 0
    num_switches = max(1, math.ceil(area / 30))
    return {
        "power_w_m2": power_w_m2,
        "light_w_m2": light_w_m2,
        "total_power": total_power,
        "total_light_w": total_light_w,
        "num_sockets": num_sockets,
        "isolator": isolator,
        "cable": cable,
        "num_lights": num_lights,
        "num_switches": num_switches,
        "num_circuits": num_sockets + num_lights
    }

def estimate_panels(project_df):
    """Return dict with number of main switchboard, DBs and sub-boards."""
    if project_df.empty:
        return {"msb": 1, "db": 0, "sub": 0}
    total_circuits = project_df["num_circuits"].sum()
    db_count = math.ceil(total_circuits / 18)
    # Sub-boards: zones > 50 kW (excluding EV charging rows? we keep them as separate zones)
    sub_count = (project_df["total_power_kW"] > 50).sum()
    return {"msb": 1, "db": db_count, "sub": sub_count}

def auto_cable_size(current, length, voltage=230, phase=1, max_vd_pct=4):
    """Select smallest cable that satisfies current and voltage drop."""
    vd_limit = voltage * max_vd_pct / 100
    suitable = []
    for size, rating in CABLE_CURRENT.items():
        if rating >= current:
            mv = CABLE_MV_A_M[size]
            if phase == 1:
                vd = mv * current * length / 1000
            else:  # three‑phase
                vd = mv * current * length * (3**0.5) / 1000
            if vd <= vd_limit:
                suitable.append(size)
    return suitable[0] if suitable else ">50mm² (custom)"

def generate_pdf(project_df, panel_req, room_check):
    """Create a simple PDF report."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Electrical Project Report", ln=True, align="C")
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Project Summary", ln=True)
    pdf.set_font("Arial", "", 10)
    
    if not project_df.empty:
        col_order = ["description", "type", "area_m2", "total_power_kW", 
                     "sockets", "isolator", "lights", "num_circuits"]
        pdf_data = project_df[col_order].copy()
        for i, row in pdf_data.iterrows():
            pdf.cell(0, 8, f"{row['description']} | {row['type']} | "
                           f"{row['area_m2']:.0f} m² | {row['total_power_kW']} kW | "
                           f"S:{row['sockets']} | {row['isolator']} | L:{row['lights']} | "
                           f"Ckts:{row['num_circuits']}", ln=True)
    pdf.ln(5)
    pdf.cell(0, 8, f"Total Building Load: {project_df['total_power_kW'].sum():.2f} kW", ln=True)
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Panel Schedule & Space Planning", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 8, f"Main Switchboard: {panel_req['msb']}", ln=True)
    pdf.cell(0, 8, f"Distribution Boards (18-way): {panel_req['db']}", ln=True)
    pdf.cell(0, 8, f"Sub-boards (>50kW zones): {panel_req['sub']}", ln=True)
    pdf.ln(5)
    pdf.cell(0, 8, f"Electrical Room: {room_check['length']}m x {room_check['width']}m", ln=True)
    pdf.cell(0, 8, f"800mm clearance check: {room_check['status']}", ln=True)
    
    return pdf.output(dest='S').encode('latin1')

# --- 4. SIDEBAR: MAIN ZONE INPUTS & ADD TO PROJECT ---
with st.sidebar:
    st.header("🏢 Site Parameters")
    z_name = st.text_input("Area Description", "Level 1")
    z_type = st.selectbox("Building Type", list(TECH_REFS.keys()))
    
    # If type is Lift or Escalator, area input is replaced by power input
    if z_type in ["Lift (Passenger)", "Escalator"]:
        # Special handling: ask for power in kW, not area
        equipment_power = st.number_input("Equipment Power (kW)", min_value=0.0, value=15.0, step=1.0)
        z_area = 0.0  # not used, but keep for dataframe consistency
        st.info("Lifts and escalators are added as fixed loads.")
    else:
        z_area = st.number_input("Area (sqm)", min_value=0.0, value=100.0, step=10.0)
        equipment_power = None
    
    light_wattage = st.number_input("Light Fixture Wattage (W)", min_value=1, value=15, step=1)
    
    # --- Lighting Power Density Override ---
    override_light = st.checkbox("Override lighting power density (W/m²)")
    if override_light:
        custom_light_w_m2 = st.number_input("Custom Light W/m²", min_value=0.0, value=10.0, step=1.0)
    else:
        custom_light_w_m2 = None
    
    # --- EV Charging Spare (only for MSCP) ---
    ev_spare = False
    if z_type == "MSCP (Carpark)":
        ev_spare = st.checkbox("Reserve 20% capacity for EV charging")
    
    tech_data = TECH_REFS[z_type]
    
    # Calculate zone data (special handling for lifts/escalators)
    if z_type in ["Lift (Passenger)", "Escalator"]:
        # For equipment, we ignore area-based calc and manually build entry
        total_power = equipment_power * 1000  # convert kW to W
        calc = {
            "power_w_m2": 0,
            "light_w_m2": 0,
            "total_power": total_power,
            "total_light_w": 0,
            "num_sockets": 0,
            "isolator": tech_data[4],  # from database
            "cable": tech_data[5],
            "num_lights": 0,
            "num_switches": 0,
            "num_circuits": 1  # assume one circuit per lift/escalator
        }
    else:
        calc = calculate_zone(z_area, tech_data, light_wattage, custom_light_w_m2)
        total_power = calc["total_power"]
        equipment_power = total_power / 1000  # for display

    st.markdown("---")
    
    # --- ADD MAIN ZONE BUTTON ---
    if st.button("➕ Add to Project", use_container_width=True):
        # Build base entry
        zone_entry = {
            "description": z_name,
            "type": z_type,
            "area_m2": z_area if z_type not in ["Lift (Passenger)", "Escalator"] else 0,
            "power_w_m2": calc["power_w_m2"],
            "light_w_m2": calc.get("light_w_m2", 0),
            "total_power_kW": round(calc["total_power"] / 1000, 2),
            "sockets": calc["num_sockets"],
            "isolator": calc["isolator"],
            "cable": calc["cable"],
            "lights": calc["num_lights"],
            "light_switches": calc["num_switches"],
            "num_circuits": calc["num_circuits"]
        }
        st.session_state.project.append(zone_entry)
        
        # If MSCP and EV spare checked, add an extra EV charging row
        if z_type == "MSCP (Carpark)" and ev_spare:
            ev_power_kw = round(calc["total_power"] / 1000 * 0.2, 2)
            ev_entry = {
                "description": f"{z_name} - EV Charging (20%)",
                "type": "EV Charging",
                "area_m2": 0,
                "power_w_m2": 0,
                "light_w_m2": 0,
                "total_power_kW": ev_power_kw,
                "sockets": 0,
                "isolator": "32A TP",  # typical for EV charger
                "cable": "6.0mm² 5C",
                "lights": 0,
                "light_switches": 0,
                "num_circuits": math.ceil(ev_power_kw / 7.4)  # assume 7.4kW per charger circuit
            }
            st.session_state.project.append(ev_entry)
        
        st.success(f"Added {z_name}")
    
    # --- ADDITIONAL FIXED EQUIPMENT (Lift / Escalator) ---
    with st.expander("🏗️ Additional Fixed Equipment"):
        st.markdown("Add lifts or escalators with custom power ratings.")
        col_eq1, col_eq2 = st.columns(2)
        with col_eq1:
            lift_power = st.number_input("Lift Power (kW)", min_value=0.0, value=15.0, step=1.0, key="lift_power")
            lift_qty = st.number_input("Quantity", min_value=1, value=1, step=1, key="lift_qty")
        with col_eq2:
            esc_power = st.number_input("Escalator Power (kW)", min_value=0.0, value=22.0, step=1.0, key="esc_power")
            esc_qty = st.number_input("Quantity", min_value=1, value=1, step=1, key="esc_qty")
        
        if st.button("➕ Add Fixed Equipment", use_container_width=True):
            # Add lifts
            for i in range(lift_qty):
                desc = f"Lift {st.session_state.eq_counter['lift']}"
                st.session_state.eq_counter['lift'] += 1
                # Use Lift tech data
                lift_tech = TECH_REFS["Lift (Passenger)"]
                entry = {
                    "description": desc,
                    "type": "Lift (Passenger)",
                    "area_m2": 0,
                    "power_w_m2": 0,
                    "light_w_m2": 0,
                    "total_power_kW": lift_power,
                    "sockets": 0,
                    "isolator": lift_tech[4],
                    "cable": lift_tech[5],
                    "lights": 0,
                    "light_switches": 0,
                    "num_circuits": 1
                }
                st.session_state.project.append(entry)
            
            # Add escalators
            for i in range(esc_qty):
                desc = f"Escalator {st.session_state.eq_counter['esc']}"
                st.session_state.eq_counter['esc'] += 1
                esc_tech = TECH_REFS["Escalator"]
                entry = {
                    "description": desc,
                    "type": "Escalator",
                    "area_m2": 0,
                    "power_w_m2": 0,
                    "light_w_m2": 0,
                    "total_power_kW": esc_power,
                    "sockets": 0,
                    "isolator": esc_tech[4],
                    "cable": esc_tech[5],
                    "lights": 0,
                    "light_switches": 0,
                    "num_circuits": 1
                }
                st.session_state.project.append(entry)
            
            st.success(f"Added {lift_qty} lift(s) and {esc_qty} escalator(s)")
    
    st.markdown("---")
    if st.button("🧹 Clear Project", use_container_width=True):
        st.session_state.project = []
        st.session_state.eq_counter = {'lift': 1, 'esc': 1}
        st.rerun()

# --- 5. MAIN PAGE ---
st.title("⚡ All-in-One Electrical Design & Project Management Suite")

# --- 5.1 Current zone results (live) ---
st.header("📐 Current Area Design")
if z_type not in ["Lift (Passenger)", "Escalator"]:
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
else:
    # For lifts/escalators, show equipment power
    st.info(f"**Equipment power:** {equipment_power} kW | **Isolator:** {calc['isolator']} | **Cable:** {calc['cable']}")

# --- 5.2 Project summary ---
st.header("📋 Project Summary")
if st.session_state.project:
    df = pd.DataFrame(st.session_state.project)
    # Ensure all required columns exist
    required_cols = ["description", "type", "area_m2", "power_w_m2", "total_power_kW",
                     "sockets", "isolator", "cable", "lights", "light_switches", "num_circuits"]
    for col in required_cols:
        if col not in df.columns:
            df[col] = 0 if col in ["area_m2", "power_w_m2", "sockets", "lights", "light_switches", "num_circuits", "total_power_kW"] else ""
    df = df[required_cols]
    st.dataframe(df, use_container_width=True, hide_index=True)

    total_building_power_kW = df["total_power_kW"].sum()
    panel_req = estimate_panels(df)
    
    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.success(f"🏢 **Total Load: {total_building_power_kW:.2f} kW**")
    col_b.metric("Main Switchboard", panel_req["msb"])
    col_c.metric("Distribution Boards", panel_req["db"])
    col_d.metric("Sub-boards", panel_req["sub"])
else:
    df = pd.DataFrame()
    st.info("No areas added yet. Use the sidebar to add your first zone.")
    panel_req = {"msb": 0, "db": 0, "sub": 0}

# --- 6. PANEL SCHEDULER & SPACE PLANNER ---
st.header("🔌 Panel Scheduler & Space Planner")

if not st.session_state.project:
    st.info("Add at least one area to enable panel planning.")
else:
    PANEL_DIMS = {"msb": (1.2, 0.6), "db": (0.6, 0.2), "sub": (0.8, 0.3)}
    room_len = st.number_input("Room length (m)", min_value=0.5, value=5.0, step=0.5, key="room_len")
    room_wid = st.number_input("Room width (m)",  min_value=0.5, value=3.0, step=0.5, key="room_wid")

    total_width = (panel_req["msb"] * PANEL_DIMS["msb"][0] +
                   panel_req["db"]  * PANEL_DIMS["db"][0] +
                   panel_req["sub"] * PANEL_DIMS["sub"][0])
    max_depth = max(PANEL_DIMS["msb"][1], PANEL_DIMS["db"][1], PANEL_DIMS["sub"][1])
    required_depth = max_depth + 0.8
    width_ok = room_len >= total_width
    depth_ok = room_wid >= required_depth

    col1, col2 = st.columns(2)
    with col1:
        st.info(f"📏 **Total panel width:** {total_width:.2f} m")
        st.info(f"📐 **Required room depth:** {required_depth:.2f} m")
    with col2:
        if width_ok and depth_ok:
            st.success("✅ Room dimensions satisfy 800 mm clearance.")
        else:
            st.error("❌ Room too small. Adjust dimensions.")
    room_check = {"length": room_len, "width": room_wid, "status": "OK" if width_ok and depth_ok else "FAIL"}

# --- 7. CABLE SIZING TOOL ---
st.header("⚡ Cable Sizing Tool")
st.markdown("Auto‑size a cable based on load current, length and voltage drop (4% max).")
col_i1, col_i2, col_i3 = st.columns(3)
with col_i1:
    current = st.number_input("Load current (A)", min_value=1.0, value=20.0, step=1.0)
with col_i2:
    length = st.number_input("Cable length (m)", min_value=1.0, value=30.0, step=1.0)
with col_i3:
    voltage = st.selectbox("System voltage", [230, 400], index=0)

phase = 1 if voltage == 230 else 3
auto_size = auto_cable_size(current, length, voltage, phase)
st.info(f"✅ **Recommended cable (auto):** {auto_size}")

manual_size = st.selectbox("Manual override (select cable size)", 
                           options=list(CABLE_CURRENT.keys()) + [">50mm² (custom)"],
                           index=list(CABLE_CURRENT.keys()).index(auto_size) if auto_size in CABLE_CURRENT else 0)
if manual_size != auto_size:
    st.warning(f"Manual selection: {manual_size} (auto would be {auto_size})")

# --- 8. EXPORT REPORTS ---
st.header("📤 Export Project Data")
col_e1, col_e2 = st.columns(2)
with col_e1:
    if st.button("📥 Download CSV"):
        if not df.empty:
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Confirm Download", data=csv, file_name="electrical_project.csv", mime="text/csv")
        else:
            st.warning("No data to export.")
with col_e2:
    if st.button("📄 Generate PDF Report"):
        if not df.empty and 'room_len' in st.session_state:
            pdf_bytes = generate_pdf(df, panel_req, room_check)
            st.download_button("Confirm Download PDF", data=pdf_bytes, file_name="electrical_report.pdf", mime="application/pdf")
        else:
            st.warning("Add project data and define room dimensions first.")
