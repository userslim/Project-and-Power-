import streamlit as st
import math
import pandas as pd
import io
from datetime import datetime
from fpdf import FPDF

st.set_page_config(page_title="Master Electrical & Project Suite", layout="wide")

# --- 1. ENHANCED ENGINEERING DATABASE ---
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
    "MSCP (Carpark)": [15, 5, 150, 100, "32A TP", "6.0mm² 5C", 1200, 7.3],
    # Special equipment (area‑independent)
    "Lift (Passenger)": [0, 0, 0, 0, "32A TP", "6.0mm² 5C", 0, 0],
    "Escalator": [0, 0, 0, 0, "63A TP", "16mm² 5C", 0, 0],
}

# Residential appliance list (reference)
RES_APPLIANCES = [
    "1x Refrigerator (150W)", "1x Air Conditioner (2000W)",
    "10x LED Lights (100W total)", "1x Television (100W)",
    "1x Washing Machine (500W)", "1x Water Heater (3000W)"
]

# Cable current carrying capacity (PVC, clipped direct)
CABLE_CURRENT = {
    "1.5mm²": 16, "2.5mm²": 22, "4.0mm²": 30, "6.0mm²": 38,
    "10mm²": 52, "16mm²": 70, "25mm²": 94, "35mm²": 115, "50mm²": 140
}
CABLE_MV_A_M = {
    "1.5mm²": 29.0, "2.5mm²": 18.0, "4.0mm²": 11.0, "6.0mm²": 7.3,
    "10mm²": 4.4, "16mm²": 2.8, "25mm²": 1.8, "35mm²": 1.35, "50mm²": 1.0
}
CABLE_DIAMETER = {
    "1.5mm²": 8.0, "2.5mm²": 9.0, "4.0mm²": 10.5, "6.0mm²": 11.5,
    "10mm²": 13.5, "16mm²": 15.5, "25mm²": 18.5, "35mm²": 21.0, "50mm²": 24.0
}
CABLE_AREA = {size: math.pi * (diam/2)**2 for size, diam in CABLE_DIAMETER.items()}

# Standard trunking sizes (width x height in mm)
TRUNKING_SIZES = [
    (50, 50), (75, 50), (100, 50), (100, 75), (150, 75), (200, 100), (300, 150)
]

# Breaker type options
BREAKER_TYPES = ["MCB", "MCCB", "RCBO", "RCCB", "ACB"]

# --- 2. INITIALISE SESSION STATE ---
if 'project' not in st.session_state:
    st.session_state.project = []
if 'eq_counter' not in st.session_state:
    st.session_state.eq_counter = {'lift': 1, 'esc': 1}
if 'project_metadata' not in st.session_state:
    st.session_state.project_metadata = {
        'project_name': '',
        'project_number': '',
        'creator': '',
        'date': datetime.now().strftime("%Y-%m-%d")
    }
if 'fixture_list' not in st.session_state:
    st.session_state.fixture_list = []

# --- 3. HELPER FUNCTIONS ---
def add_fixture(wattage, qty):
    st.session_state.fixture_list.append({"wattage": wattage, "qty": qty})

def remove_fixture(index):
    if 0 <= index < len(st.session_state.fixture_list):
        st.session_state.fixture_list.pop(index)

def calculate_lighting_from_fixtures(fixture_list):
    total_w = 0
    total_qty = 0
    for f in fixture_list:
        total_w += f['wattage'] * f['qty']
        total_qty += f['qty']
    return total_w, total_qty

def calculate_zone(area, tech_data, light_method, light_wattage_single,
                   use_custom_fixtures, fixture_list,
                   override_light_w_m2=None, lux_params=None):
    power_w_m2, light_w_m2, target_lux, sqm_per_socket, isolator, cable, _, _ = tech_data
    
    total_power = area * power_w_m2
    total_power_kw = total_power / 1000
    
    if use_custom_fixtures and fixture_list:
        total_light_w, num_lights = calculate_lighting_from_fixtures(fixture_list)
        light_w_m2_used = total_light_w / area if area > 0 else 0
    else:
        if light_method == "Load-based (W/m²)":
            if override_light_w_m2 is not None:
                light_w_m2 = override_light_w_m2
            total_light_w = area * light_w_m2
            num_lights = math.ceil(total_light_w / light_wattage_single) if light_wattage_single > 0 else 0
            light_w_m2_used = light_w_m2
        else:  # Lux-based
            lux = lux_params.get('lux', target_lux)
            lumens_per_fixture = lux_params.get('lumens_per_fixture', 3200)
            mf = lux_params.get('mf', 0.8)
            uf = lux_params.get('uf', 0.7)
            required_lumens = lux * area
            num_lights = math.ceil(required_lumens / (lumens_per_fixture * mf * uf))
            total_light_w = num_lights * light_wattage_single
            light_w_m2_used = total_light_w / area if area > 0 else 0
    
    num_sockets = math.ceil(area / sqm_per_socket) if sqm_per_socket > 0 else 0
    num_switches = max(1, math.ceil(area / 30))
    num_circuits = num_sockets + num_lights
    
    return {
        "power_w_m2": power_w_m2,
        "light_w_m2": light_w_m2_used,
        "total_power_w": total_power,
        "total_light_w": total_light_w,
        "total_power_kw": total_power_kw,
        "num_sockets": num_sockets,
        "isolator": isolator,
        "cable": cable,
        "num_lights": num_lights,
        "num_switches": num_switches,
        "num_circuits": num_circuits,
    }

def estimate_panels(project_df):
    if project_df.empty:
        return {"msb": 1, "db": 0, "sub": 0}
    total_circuits = project_df["num_circuits"].sum()
    db_count = math.ceil(total_circuits / 18)
    sub_count = (project_df["total_power_kw"] > 50).sum()
    return {"msb": 1, "db": db_count, "sub": sub_count}

def auto_cable_size(current, length, voltage=230, phase=1, max_vd_pct=4):
    vd_limit = voltage * max_vd_pct / 100
    suitable = []
    for size, rating in CABLE_CURRENT.items():
        if rating >= current:
            mv = CABLE_MV_A_M[size]
            if phase == 1:
                vd = mv * current * length / 1000
            else:
                vd = mv * current * length * (3**0.5) / 1000
            if vd <= vd_limit:
                suitable.append(size)
    return suitable[0] if suitable else ">50mm² (custom)"

def recommend_trunking(total_cable_area_mm2):
    required_area = total_cable_area_mm2 / 0.45
    for w, h in TRUNKING_SIZES:
        if w * h >= required_area:
            return f"{w} x {h} mm", w*h, required_area
    return ">300x150 mm (custom)", None, required_area

def generate_pdf(project_df, panel_req, room_check, metadata, trunking_rec):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Electrical Project Report", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, f"Project: {metadata['project_name']}", ln=True)
    pdf.cell(0, 6, f"Project No: {metadata['project_number']}", ln=True)
    pdf.cell(0, 6, f"Created by: {metadata['creator']}", ln=True)
    pdf.cell(0, 6, f"Date: {metadata['date']}", ln=True)
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Project Summary", ln=True)
    pdf.set_font("Arial", "", 10)
    
    if not project_df.empty:
        cols = ["description", "type", "area_m2", "total_power_kw", "sockets",
                "isolator", "breaker_type", "lights", "num_circuits", "db_count"]
        display_cols = [c for c in cols if c in project_df.columns]
        pdf_data = project_df[display_cols].copy()
        for _, row in pdf_data.iterrows():
            line = f"{row['description']} | {row['type']} | "
            if 'area_m2' in row:
                line += f"{row['area_m2']:.0f} m² | "
            line += f"{row['total_power_kw']:.2f} kW | "
            if 'sockets' in row:
                line += f"S:{row['sockets']} | "
            line += f"{row['isolator']} | "
            if 'breaker_type' in row:
                line += f"{row['breaker_type']} | "
            if 'lights' in row:
                line += f"L:{row['lights']} | "
            if 'num_circuits' in row:
                line += f"Ckts:{row['num_circuits']} | "
            if 'db_count' in row:
                line += f"DBs:{row['db_count']}"
            pdf.cell(0, 8, line, ln=True)
    pdf.ln(5)
    pdf.cell(0, 8, f"Total Building Load: {project_df['total_power_kw'].sum():.2f} kW", ln=True)
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
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Cable Trunking Recommendation", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 8, f"Total cable cross‑section: {trunking_rec['total_area']:.0f} mm²", ln=True)
    pdf.cell(0, 8, f"Required trunking area (45% fill): {trunking_rec['required_area']:.0f} mm²", ln=True)
    pdf.cell(0, 8, f"Recommended trunking: {trunking_rec['recommendation']}", ln=True)
    
    return pdf.output(dest='S').encode('latin1')

# --- 4. SIDEBAR: PROJECT METADATA & SITE PARAMETERS ---
with st.sidebar:
    st.header("📁 Project Information")
    proj_name = st.text_input("Project Name", value=st.session_state.project_metadata['project_name'])
    proj_number = st.text_input("Project Number", value=st.session_state.project_metadata['project_number'])
    creator = st.text_input("Created by", value=st.session_state.project_metadata['creator'])
    proj_date = st.date_input("Date", value=datetime.strptime(st.session_state.project_metadata['date'], "%Y-%m-%d"))
    st.session_state.project_metadata = {
        'project_name': proj_name,
        'project_number': proj_number,
        'creator': creator,
        'date': proj_date.strftime("%Y-%m-%d")
    }
    
    st.markdown("---")
    st.header("🏢 Site Parameters")
    z_name = st.text_input("Area Description", "Level 1")
    z_type = st.selectbox("Building Type", list(TECH_REFS.keys()))
    
    if z_type in ["Lift (Passenger)", "Escalator"]:
        equipment_power = st.number_input("Equipment Power (kW)", min_value=0.0, value=15.0, step=1.0)
        z_area = 0.0
        st.info("Lifts and escalators are fixed loads.")
    else:
        z_area = st.number_input("Floor Area (m²)", min_value=0.0, value=100.0, step=10.0)
        equipment_power = None
    
    z_dist = st.number_input("Distance to MSB (m)", min_value=1.0, value=30.0, step=1.0)
    
    if z_type not in ["Lift (Passenger)", "Escalator"]:
        suggested_db = math.ceil(z_area / TECH_REFS[z_type][6]) if TECH_REFS[z_type][6] > 0 else 1
        z_db = st.number_input("Number of Sub‑boards (DBs)", min_value=1, value=suggested_db, step=1)
    else:
        z_db = 1
    
    # --- Breaker type selection (NEW) ---
    default_breaker = "MCB" if "DP" in TECH_REFS[z_type][4] or "SP" in TECH_REFS[z_type][4] else "MCCB"
    breaker_type = st.selectbox("Breaker Type", BREAKER_TYPES, 
                                index=BREAKER_TYPES.index(default_breaker) if default_breaker in BREAKER_TYPES else 0)
    
    # --- Lighting method selection ---
    light_method = st.radio(
        "Lighting Calculation Method",
        ["Load-based (W/m²)", "Lux-based (lumens)"],
        index=0
    )
    
    # --- Custom lighting fixtures ---
    st.subheader("💡 Lighting Fixture Types")
    use_custom_fixtures = st.checkbox("Use multiple fixture types")
    
    if use_custom_fixtures:
        if st.session_state.fixture_list:
            st.write("Current fixtures:")
            for i, f in enumerate(st.session_state.fixture_list):
                col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
                with col_f1:
                    st.text(f"{f['wattage']} W")
                with col_f2:
                    st.text(f"x {f['qty']}")
                with col_f3:
                    if st.button("❌", key=f"del_fix_{i}"):
                        remove_fixture(i)
                        st.rerun()
        else:
            st.info("No custom fixtures defined.")
        
        col_w, col_q, col_a = st.columns([2, 2, 1])
        with col_w:
            new_watt = st.number_input("Wattage", min_value=1, value=15, step=1, key="new_fix_w")
        with col_q:
            new_qty = st.number_input("Qty", min_value=1, value=1, step=1, key="new_fix_q")
        with col_a:
            if st.button("➕ Add"):
                add_fixture(new_watt, new_qty)
                st.rerun()
        light_wattage_single = 15
    else:
        light_wattage_single = st.number_input("Light Fixture Wattage (W)", min_value=1, value=15, step=1)
        if st.session_state.fixture_list:
            st.session_state.fixture_list = []
    
    override_light_w_m2 = None
    lux_params = {}
    if not use_custom_fixtures:
        if light_method == "Load-based (W/m²)":
            override_light = st.checkbox("Override lighting power density (W/m²)")
            if override_light:
                override_light_w_m2 = st.number_input("Custom Light W/m²", min_value=0.0, value=10.0, step=1.0)
        else:
            tech_lux = TECH_REFS[z_type][2] if z_type in TECH_REFS else 300
            lux_val = st.number_input("Target illuminance (lux)", min_value=50, value=tech_lux, step=50)
            lumens = st.number_input("Lumens per fixture", min_value=500, value=3200, step=100)
            mf = st.slider("Maintenance Factor", 0.5, 1.0, 0.8, 0.05)
            uf = st.slider("Utilization Factor", 0.3, 1.0, 0.7, 0.05)
            lux_params = {"lux": lux_val, "lumens_per_fixture": lumens, "mf": mf, "uf": uf}
    
    ev_load_kw = 0
    if z_type == "MSCP (Carpark)":
        lots = st.number_input("Number of parking lots", min_value=1, value=20, step=1)
        ev_load_kw = (lots * 7.4) * 0.20 * 1.20
        st.info(f"EV charging reserve: {ev_load_kw:.1f} kW")
    
    # --- Manpower slider (WITH KEY) ---
    manpower = st.slider("Electricians on Site", 1, 20, 3, key="manpower_slider")
    
    st.markdown("---")
    
    # --- MAIN ADD BUTTON ---
    if st.button("➕ Add to Project", use_container_width=True):
        tech_data = TECH_REFS[z_type]
        
        if z_type in ["Lift (Passenger)", "Escalator"]:
            calc = {
                "total_power_kw": equipment_power,
                "num_sockets": 0,
                "isolator": tech_data[4],
                "cable": tech_data[5],
                "num_lights": 0,
                "num_switches": 0,
                "num_circuits": 1,
                "light_w_m2": 0,
                "power_w_m2": 0,
            }
            light_w_m2_used = 0
            num_lights = 0
        else:
            calc = calculate_zone(
                area=z_area,
                tech_data=tech_data,
                light_method=light_method,
                light_wattage_single=light_wattage_single,
                use_custom_fixtures=use_custom_fixtures,
                fixture_list=st.session_state.fixture_list,
                override_light_w_m2=override_light_w_m2 if "Load-based" in light_method else None,
                lux_params=lux_params if "Lux-based" in light_method else None
            )
            light_w_m2_used = calc["light_w_m2"]
            num_lights = calc["num_lights"]
        
        zone_entry = {
            "description": z_name,
            "type": z_type,
            "area_m2": z_area,
            "power_w_m2": calc["power_w_m2"] if z_type not in ["Lift", "Escalator"] else 0,
            "light_w_m2": light_w_m2_used,
            "total_power_kw": round(calc["total_power_kw"] if z_type not in ["Lift", "Escalator"] else equipment_power, 2),
            "sockets": calc["num_sockets"],
            "isolator": calc["isolator"],
            "breaker_type": breaker_type,   # ✅ Store breaker type
            "cable": calc["cable"],
            "lights": num_lights,
            "light_switches": calc["num_switches"],
            "num_circuits": calc["num_circuits"],
            "distance_m": z_dist,
            "db_count": z_db,
        }
        st.session_state.project.append(zone_entry)
        
        if z_type == "MSCP (Carpark)" and ev_load_kw > 0:
            ev_entry = {
                "description": f"{z_name} - EV Charging",
                "type": "EV Charging",
                "area_m2": 0,
                "power_w_m2": 0,
                "light_w_m2": 0,
                "total_power_kw": round(ev_load_kw, 2),
                "sockets": 0,
                "isolator": "32A TP",
                "breaker_type": "RCBO",   # Typical for EV
                "cable": "6.0mm² 5C",
                "lights": 0,
                "light_switches": 0,
                "num_circuits": math.ceil(ev_load_kw / 7.4),
                "distance_m": z_dist,
                "db_count": 1,
            }
            st.session_state.project.append(ev_entry)
        
        st.success(f"Added {z_name}")
    
    # --- ADDITIONAL FIXED EQUIPMENT ---
    with st.expander("🏗️ Additional Fixed Equipment"):
        st.markdown("Add lifts or escalators (quantity can be zero).")
        col_eq1, col_eq2 = st.columns(2)
        with col_eq1:
            lift_power = st.number_input("Lift Power (kW)", min_value=0.0, value=15.0, step=1.0, key="lift_power_side")
            lift_qty = st.number_input("Quantity", min_value=0, value=1, step=1, key="lift_qty_side")
        with col_eq2:
            esc_power = st.number_input("Escalator Power (kW)", min_value=0.0, value=22.0, step=1.0, key="esc_power_side")
            esc_qty = st.number_input("Quantity", min_value=0, value=1, step=1, key="esc_qty_side")
        
        if st.button("➕ Add Fixed Equipment", use_container_width=True):
            for i in range(lift_qty):
                desc = f"Lift {st.session_state.eq_counter['lift']}"
                st.session_state.eq_counter['lift'] += 1
                lift_tech = TECH_REFS["Lift (Passenger)"]
                entry = {
                    "description": desc, "type": "Lift (Passenger)", "area_m2": 0,
                    "power_w_m2": 0, "light_w_m2": 0, "total_power_kw": lift_power,
                    "sockets": 0, "isolator": lift_tech[4], "breaker_type": "MCCB",
                    "cable": lift_tech[5], "lights": 0, "light_switches": 0,
                    "num_circuits": 1, "distance_m": 30, "db_count": 1,
                }
                st.session_state.project.append(entry)
            for i in range(esc_qty):
                desc = f"Escalator {st.session_state.eq_counter['esc']}"
                st.session_state.eq_counter['esc'] += 1
                esc_tech = TECH_REFS["Escalator"]
                entry = {
                    "description": desc, "type": "Escalator", "area_m2": 0,
                    "power_w_m2": 0, "light_w_m2": 0, "total_power_kw": esc_power,
                    "sockets": 0, "isolator": esc_tech[4], "breaker_type": "MCCB",
                    "cable": esc_tech[5], "lights": 0, "light_switches": 0,
                    "num_circuits": 1, "distance_m": 30, "db_count": 1,
                }
                st.session_state.project.append(entry)
            st.success(f"Added {lift_qty} lift(s) and {esc_qty} escalator(s)")
    
    st.markdown("---")
    if st.button("🧹 Clear Project", use_container_width=True):
        st.session_state.project = []
        st.session_state.eq_counter = {'lift': 1, 'esc': 1}
        st.session_state.fixture_list = []
        st.rerun()

# --- 5. MAIN PAGE ---
st.title("⚡ Master Electrical Design & Project Suite")

# --- 5.1 Current zone preview ---
st.header("📐 Current Area Preview")
if z_type not in ["Lift (Passenger)", "Escalator"]:
    tech_data = TECH_REFS[z_type]
    calc_preview = calculate_zone(
        area=z_area,
        tech_data=tech_data,
        light_method=light_method,
        light_wattage_single=light_wattage_single if not use_custom_fixtures else 15,
        use_custom_fixtures=use_custom_fixtures,
        fixture_list=st.session_state.fixture_list,
        override_light_w_m2=override_light_w_m2 if "Load-based" in light_method else None,
        lux_params=lux_params if "Lux-based" in light_method else None
    )
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Power Density", f"{calc_preview['power_w_m2']} W/m²")
        st.metric("Total Power", f"{calc_preview['total_power_kw']:.2f} kW")
    with col2:
        st.metric("13A Sockets", calc_preview["num_sockets"])
        st.metric("Isolator", calc_preview["isolator"])
    with col3:
        st.metric("Light Switches", calc_preview["num_switches"])
        st.metric("Lights", calc_preview["num_lights"])
else:
    st.info(f"**Equipment power:** {equipment_power} kW | **Isolator:** {TECH_REFS[z_type][4]}")

# --- 5.2 Project Summary Table ---
st.header("📋 Project Summary")
if st.session_state.project:
    df = pd.DataFrame(st.session_state.project)
    
    expected_cols = ["description", "type", "area_m2", "power_w_m2", "light_w_m2", 
                     "total_power_kw", "sockets", "isolator", "breaker_type", "cable",
                     "lights", "light_switches", "num_circuits", "distance_m", "db_count"]
    for col in expected_cols:
        if col not in df.columns:
            if col in ["area_m2", "power_w_m2", "light_w_m2", "sockets", "lights", 
                       "light_switches", "num_circuits", "distance_m", "db_count", "total_power_kw"]:
                df[col] = 0
            else:
                df[col] = ""
    
    display_cols = ["description", "type", "area_m2", "total_power_kw", "sockets", 
                    "lights", "isolator", "breaker_type", "cable", "distance_m", "db_count", "num_circuits"]
    df_display = df[display_cols]
    st.dataframe(df_display, use_container_width=True, hide_index=True)
    
    total_building_power_kw = df["total_power_kw"].sum()
    panel_req = estimate_panels(df)
    
    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.success(f"🏢 **Total Load: {total_building_power_kw:.2f} kW**")
    col_b.metric("Main Switchboard", panel_req["msb"])
    col_c.metric("Distribution Boards", panel_req["db"])
    col_d.metric("Sub-boards", panel_req["sub"])
else:
    df = pd.DataFrame()
    st.info("No areas added yet. Use the sidebar to add your first zone.")
    panel_req = {"msb": 0, "db": 0, "sub": 0}
    total_building_power_kw = 0

# --- 6. DETAILED ENGINEERING REPORT ---
if st.session_state.project:
    st.header("🔧 Per‑Zone Engineering Report")
    
    report_rows = []
    total_md_kw = 0
    total_hrs = 0
    total_cost = 0
    
    for idx, row in df.iterrows():
        area = row["area_m2"]
        total_kw = row["total_power_kw"]
        dist = row["distance_m"]
        db_cnt = row["db_count"]
        sockets = row["sockets"]
        lights = row["lights"]
        cable_str = row["cable"]
        
        md_kw = total_kw * 0.8
        total_md_kw += md_kw
        
        vd_pct = 0.0
        vd_status = "N/A"
        if area > 0 and isinstance(cable_str, str) and cable_str.split()[0] in CABLE_MV_A_M and dist > 0:
            ib = (total_kw * 1000) / (1.732 * 400 * 0.85)
            base_size = cable_str.split()[0]
            mv = CABLE_MV_A_M.get(base_size, 0)
            if mv > 0:
                vd = mv * ib * dist * (3**0.5) / 1000
                vd_pct = (vd / 400) * 100
                vd_status = "✅ Pass" if vd_pct <= 4 else "⚠️ Resize"
        
        hrs = (sockets * 0.5) + (lights * 0.8) + (dist * 0.05) + (db_cnt * 5)
        total_hrs += hrs
        
        cost = (dist * 15) + (sockets * 30) + (lights * 60) + (db_cnt * 1500)
        total_cost += cost
        
        report_rows.append({
            "Zone": row["description"],
            "Type": row["type"],
            "Load (kW)": round(total_kw, 2),
            "MD (kW)": round(md_kw, 2),
            "Sockets": sockets,
            "Lights": lights,
            "Cable": cable_str,
            "Breaker": row.get("breaker_type", ""),
            "V-Drop %": round(vd_pct, 2),
            "VD Status": vd_status,
            "DBs": db_cnt,
            "Man-hrs": round(hrs, 1),
        })
    
    report_df = pd.DataFrame(report_rows)
    st.dataframe(report_df, use_container_width=True, hide_index=True)
    
    # --- PROJECT MANAGEMENT ---
    st.divider()
    st.header("📊 Project Management & Testing")
    
    # ✅ Retrieve manpower from session state (key used in slider)
    manpower = st.session_state.get('manpower_slider', 3)
    days = math.ceil(total_hrs / (manpower * 8)) if total_hrs > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Max Demand (Total)", f"{total_md_kw:.1f} kW")
    col2.metric("Project Cost", f"${total_cost:,.2f}")
    col3.metric("Duration", f"{days} Working Days")
    
    st.subheader("🚧 Phase Breakdown")
    st.info(f"**First Fix**: {math.ceil(days*0.4)}d | **Second Fix**: {math.ceil(days*0.4)}d | **T&C**: {math.ceil(days*0.2)}d")
    
    if any(d['type'] == "Residential" for d in st.session_state.project):
        st.subheader("🏡 Residential Provisioning (Per Unit)")
        for app in RES_APPLIANCES:
            st.write(f"- {app}")
    
    st.subheader("🔍 Testing & Commissioning Checklist")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.checkbox("Visual Inspection (Cabling & Terminations)")
        st.checkbox("Continuity of Protective Conductors")
        st.checkbox("Insulation Resistance Test (>1 MΩ)")
        st.checkbox("Polarity Test")
    with col_t2:
        st.checkbox("Earth Fault Loop Impedance (EFLI)")
        st.checkbox("RCD Operation Test")
        st.checkbox("Functional Testing of All Circuits")
        st.checkbox("Labelling & As‑built Drawings")

# --- 7. PANEL SCHEDULER & SPACE PLANNER ---
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

# --- 8. CABLE TRUNKING / LADDER SIZING ---
st.header("📦 Cable Trunking / Ladder Sizing")

if st.session_state.project and not df.empty:
    total_cable_area = 0
    for idx, row in df.iterrows():
        circuits = row["num_circuits"]
        cable_size = row["cable"].split()[0] if isinstance(row["cable"], str) else ""
        if cable_size in CABLE_AREA:
            area_per_cable = CABLE_AREA[cable_size]
            total_cable_area += area_per_cable * circuits
    
    trunking_rec = {}
    trunking_rec['total_area'] = total_cable_area
    rec_text, trunk_area, req_area = recommend_trunking(total_cable_area)
    trunking_rec['recommendation'] = rec_text
    trunking_rec['required_area'] = req_area if req_area else 0
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.metric("Total cable cross‑section", f"{total_cable_area:.0f} mm²")
        st.metric("Required trunking area (45% fill)", f"{req_area:.0f} mm²" if req_area else "N/A")
    with col_t2:
        st.success(f"**Recommended trunking:** {rec_text}")
        st.markdown("**Custom trunking check**")
        cust_w = st.number_input("Width (mm)", min_value=50, value=100, step=10)
        cust_h = st.number_input("Height (mm)", min_value=50, value=50, step=10)
        cust_area = cust_w * cust_h
        fill_pct = (total_cable_area / cust_area) * 100 if cust_area > 0 else 0
        st.write(f"Fill ratio: {fill_pct:.1f}% (max 45%)")
        if fill_pct <= 45:
            st.success("✅ Acceptable")
        else:
            st.error("❌ Overfilled – increase trunking size")
else:
    st.info("Add project data to calculate trunking requirements.")
    trunking_rec = {"recommendation": "N/A", "total_area": 0, "required_area": 0}

# --- 9. CABLE SIZING TOOL ---
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

# --- 10. EXPORT REPORTS ---
st.header("📤 Export Project Data")
col_e1, col_e2 = st.columns(2)
with col_e1:
    if st.button("📥 Download CSV"):
        if not df.empty:
            export_df = df[display_cols].copy()
            csv = export_df.to_csv(index=False).encode('utf-8')
            st.download_button("Confirm Download", data=csv, file_name="electrical_project.csv", mime="text/csv")
        else:
            st.warning("No data to export.")
with col_e2:
    if st.button("📄 Generate PDF Report"):
        if not df.empty and 'room_len' in st.session_state:
            pdf_bytes = generate_pdf(df, panel_req, room_check, st.session_state.project_metadata, trunking_rec)
            st.download_button("Confirm Download PDF", data=pdf_bytes, file_name="electrical_report.pdf", mime="application/pdf")
        else:
            st.warning("Add project data and define room dimensions first.")
