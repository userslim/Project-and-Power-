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

if 'project' not in st.session_state:
    st.session_state.project = []

st.title("⚡ All-in-One Electrical Design & Project Management Suite")

# --- 2. SIDEBAR: FULL DESIGNER INPUTS ---
with st.sidebar:
    st.header("🏢 Site Parameters")
    z_name = st.text_input("Area Description", "Level 1")
    z_type = st.selectbox("Building Type", list(TECH_REFS.keys()))
    z_area = st.number_input("
