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
    z_type = st.selectbox("Building/Area Category", list(TECH_REFS.keys()))
    z_area = st.number_input("Floor Area (m²)", min_value=1.0, value=500.0)
    z_dist = st.number_input("Distance from MSB (m)", min_value=1.0, value=40.0)
    
    # Custom Sub-board Count
    suggested_db = math.ceil(z
