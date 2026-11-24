"""
Interactive Streamlit Dashboard
AeroClust AI: Regional Pollution Hotspot Pattern Grouping & Airshed Carrying-Capacity DSS
"""

import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import joblib
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns

from src.clustering import (
    POLLUTION_ARCHETYPES,
    HOTSPOT_TIER_MAPPING,
    TIER_SEVERITY_ORDER
)
from src.feature_engineering import ALL_MODEL_FEATURES, SKEWED_FEATURES

# Set page configuration
st.set_page_config(
    page_title="AeroClust AI | Satellite Pollution Hotspot DSS",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.1rem;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #64748b;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1.1rem;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .badge-red {
        background-color: #fef2f2;
        color: #dc2626;
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: 600;
        border: 1px solid #fecaca;
    }
    .badge-green {
        background-color: #f0fdf4;
        color: #16a34a;
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: 600;
        border: 1px solid #bbf7d0;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def load_all_models_and_data():
    base_dir = "data/processed"
    scaler = joblib.load(os.path.join(base_dir, "feature_scaler.joblib"))
    pca = joblib.load(os.path.join(base_dir, "pca_transformer.joblib"))
    kmeans = joblib.load(os.path.join(base_dir, "kmeans_model.joblib"))

    mapping_df = pd.read_csv(os.path.join(base_dir, "cluster_archetype_mapping.csv"))
    c_to_arch = dict(zip(mapping_df["cluster_id"], mapping_df["pollution_archetype"]))
    arch_to_c = dict(zip(mapping_df["pollution_archetype"], mapping_df["cluster_id"]))
    c_to_tier = dict(zip(mapping_df["cluster_id"], mapping_df["hotspot_risk_tier"]))

    df = pd.read_csv(os.path.join(base_dir, "satellite_clustered.csv"))
    eval_df = pd.read_csv(os.path.join(base_dir, "optimal_k_evaluation.csv"))
    val_agr = pd.read_csv(os.path.join(base_dir, "validation_agreement_metrics.csv"))
    val_cm = pd.read_csv(os.path.join(base_dir, "validation_confusion_matrix.csv"), index_col=0)
    hidden_df = pd.read_csv(os.path.join(base_dir, "validation_hidden_hotspots.csv"))

    return {
        "scaler": scaler,
        "pca": pca,
        "kmeans": kmeans,
        "c_to_arch": c_to_arch,
        "arch_to_c": arch_to_c,
        "c_to_tier": c_to_tier,
        "dataset": df,
        "optimal_k": eval_df,
        "agreement": val_agr,
        "cm": val_cm,
        "hidden": hidden_df
    }

try:
    STORE = load_all_models_and_data()
    DATA_LOADED = True
except Exception as e:
    DATA_LOADED = False
    st.error(f"Please run `python main.py` first to generate processed datasets and models. Error: {e}")

if DATA_LOADED:
    df_main = STORE["dataset"]

    # Header
    st.markdown('<div class="main-header">🛰️ AeroClust AI: Regional Pollution Hotspot Grouping</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Unsupervised Machine Learning for Spatial Hotspot Pattern Profiling, Multi-Sensor Satellite Data & Airshed Carrying-Capacity Validation</div>', unsafe_allow_html=True)

    # Sidebar Filter Controls
    st.sidebar.image("https://images.unsplash.com/photo-1611273426858-450d8e3c9fce?auto=format&fit=crop&w=400&q=80", use_column_width=True)
    st.sidebar.title("Airshed Controls")

    selected_basin = st.sidebar.multiselect(
        "Filter Airshed Basin",
        options=sorted(df_main["airshed_basin"].unique()),
        default=sorted(df_main["airshed_basin"].unique())
    )

    selected_archetype = st.sidebar.multiselect(
        "Filter Pollution Archetype",
        options=POLLUTION_ARCHETYPES,
        default=POLLUTION_ARCHETYPES
    )

    deficit_filter = st.sidebar.checkbox("Show Only Carrying-Capacity Deficits", value=False)
    hidden_filter = st.sidebar.checkbox("Show Only Hidden Unmonitored Hotspots", value=False)

    # Filter dataset
    filtered_df = df_main[
        (df_main["airshed_basin"].isin(selected_basin)) &
        (df_main["predicted_archetype"].isin(selected_archetype))
    ]
    if deficit_filter:
        filtered_df = filtered_df[filtered_df["airshed_deficit_flag"] == 1]
    if hidden_filter:
        filtered_df = filtered_df[
            (~filtered_df["ground_station_installed"]) &
            (filtered_df["predicted_archetype"].isin([
                "Type 1: Industrial & Power Combustion Hotspot",
                "Type 3: Agricultural Biomass & Stubble Burning Plume"
            ])) &
            (filtered_df["airshed_deficit_flag"] == 1)
        ]

    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Executive KPIs",
        "🗺️ Geospatial GIS Explorer",
        "🔬 Real-Time Simulator",
        "📁 Batch Ingestion",
        "🧪 Scientific Validation",
        "📑 Figures Gallery"
    ])

    # TAB 1: Executive KPIs
    with tab1:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Grids Analyzed", f"{len(filtered_df):,}", f"{len(df_main)} Total")
        with col2:
            ind_count = (filtered_df["predicted_archetype"] == "Type 1: Industrial & Power Combustion Hotspot").sum()
            st.metric("Industrial Mega-Hotspots", f"{ind_count:,}", f"{ind_count/len(filtered_df)*100:.1f}%")
        with col3:
            deficit_count = (filtered_df["airshed_deficit_flag"] == 1).sum()
            st.metric("Airshed Capacity Deficits", f"{deficit_count:,}", f"{deficit_count/len(filtered_df)*100:.1f}%")
        with col4:
            st.metric("Hidden Hotspots Discovered", f"{len(STORE['hidden']):,}", "Unmonitored")

        st.markdown("---")
        c_left, c_right = st.columns([1, 1])
        with c_left:
            st.subheader("Archetype Distribution")
            fig_pie, ax_pie = plt.subplots(figsize=(6, 4))
            dist = filtered_df["predicted_archetype"].value_counts()
            colors = ["#e11d48", "#f97316", "#10b981", "#eab308"]
            ax_pie.pie(dist, labels=[s.split(":")[1].strip() for s in dist.index], autopct="%1.1f%%", colors=colors[:len(dist)], startangle=140)
            ax_pie.axis("equal")
            st.pyplot(fig_pie)
            plt.close()

        with c_right:
            st.subheader("Mean Pollution Index by Airshed Region")
            reg_agg = filtered_df.groupby("region_name")["satellite_pollution_index"].mean().sort_values(ascending=True)
            fig_bar, ax_bar = plt.subplots(figsize=(6, 4.3))
            ax_bar.barh(reg_agg.index, reg_agg.values, color="#3b82f6", alpha=0.85)
            ax_bar.set_xlabel("Mean Satellite Pollution Index (0-100)")
            plt.tight_layout()
            st.pyplot(fig_bar)
            plt.close()

        st.subheader("Top Priority Hotspot Locations")
        top_hotspots = filtered_df.sort_values(by="satellite_pollution_index", ascending=False).head(10)
        st.dataframe(
            top_hotspots[[
                "cell_id", "region_name", "airshed_basin", "predicted_archetype",
                "satellite_pollution_index", "so2_column_umol_m2", "no2_column_umol_m2",
                "aerosol_optical_depth_550", "airshed_assimilative_capacity", "ground_station_installed"
            ]],
            use_container_width=True
        )

    # TAB 2: Geospatial GIS Explorer
    with tab2:
        st.subheader("Regional Satellite Hotspot Spatial Map")
        st.write("Spatial projection of satellite grid cells across Indian airshed basins. Colors correspond to unsupervised pollution archetypes.")

        fig_geo, ax_geo = plt.subplots(figsize=(10, 6.5))
        color_map = {
            "Type 1: Industrial & Power Combustion Hotspot": "#e11d48",
            "Type 2: Dense Urban-Vehicular Smog Corridor": "#f97316",
            "Type 3: Agricultural Biomass & Stubble Burning Plume": "#eab308",
            "Type 4: Clean Background & Resilient Airshed": "#10b981"
        }
        for arch, col in color_map.items():
            sub = filtered_df[filtered_df["predicted_archetype"] == arch]
            if len(sub) > 0:
                ax_geo.scatter(
                    sub["longitude"], sub["latitude"],
                    c=col, label=arch.split(":")[1].strip(),
                    s=sub["satellite_pollution_index"] * 1.2 + 15,
                    alpha=0.7, edgecolors="black", linewidth=0.3
                )
        ax_geo.set_xlabel("Longitude (°E)")
        ax_geo.set_ylabel("Latitude (°N)")
        ax_geo.set_title("Geospatial Pollution Hotspots from Satellite Earth Observation")
        ax_geo.legend(loc="lower right")
        plt.tight_layout()
        st.pyplot(fig_geo)
        plt.close()

    # TAB 3: Real-Time Simulator
    with tab3:
        st.subheader("Interactive Satellite Observation Simulation")
        st.write("Adjust multi-sensor satellite parameters below to evaluate real-time unsupervised archetype classification and airshed stress.")

        s_col1, s_col2, s_col3 = st.columns(3)
        with s_col1:
            st.markdown("**Sentinel-5P Trace Gases**")
            sim_no2 = st.slider("Tropospheric NO2 (µmol/m²)", 2.0, 500.0, 185.0)
            sim_so2 = st.slider("Boundary Layer SO2 (µmol/m²)", 1.0, 400.0, 120.0)
            sim_co = st.slider("Carbon Monoxide (mmol/m²)", 10.0, 120.0, 48.0)
            sim_hcho = st.slider("Formaldehyde HCHO (µmol/m²)", 5.0, 150.0, 45.0)
            sim_ch4 = st.slider("Methane CH4 (ppb)", 1750.0, 2250.0, 1920.0)

        with s_col2:
            st.markdown("**MODIS/VIIRS Aerosol & Thermal**")
            sim_aod = st.slider("Aerosol Optical Depth (550nm)", 0.05, 2.2, 0.95)
            sim_uvai = st.slider("UV Aerosol Index", -1.0, 4.5, 1.4)
            sim_frp = st.slider("Fire Radiative Power (MW)", 0.0, 500.0, 25.0)
            sim_lst = st.slider("Land Surface Temp (°C)", 15.0, 55.0, 38.0)

        with s_col3:
            st.markdown("**ERA5 Meteorological Context**")
            sim_blh = st.slider("Boundary Layer Height (m)", 150.0, 3000.0, 850.0)
            sim_wind = st.slider("Surface Wind Speed (m/s)", 0.5, 15.0, 2.5)
            sim_rh = st.slider("Relative Humidity (%)", 10.0, 95.0, 62.0)
            sim_precip = st.slider("Precipitation (mm)", 0.0, 50.0, 0.2)

        if st.button("Classify Satellite Observation", type="primary"):
            from server import predict_single_record
            input_dict = {
                "no2_column_umol_m2": sim_no2,
                "so2_column_umol_m2": sim_so2,
                "co_column_mmol_m2": sim_co,
                "hcho_column_umol_m2": sim_hcho,
                "methane_ch4_ppb": sim_ch4,
                "aerosol_optical_depth_550": sim_aod,
                "uv_aerosol_index": sim_uvai,
                "fire_radiative_power_mw": sim_frp,
                "land_surface_temp_c": sim_lst,
                "boundary_layer_height_m": sim_blh,
                "surface_wind_speed_ms": sim_wind,
                "relative_humidity_pct": sim_rh,
                "precipitation_rate_mm": sim_precip
            }
            res = predict_single_record(input_dict)

            r_col1, r_col2, r_col3 = st.columns(3)
            with r_col1:
                st.metric("Predicted Archetype", res["predicted_archetype"].split(":")[1].strip())
            with r_col2:
                st.metric("Satellite Pollution Index", f"{res['satellite_pollution_index']}/100")
            with r_col3:
                status = "DEFICIT BREACH" if res["airshed_deficit_flag"] else "Within Capacity"
                st.metric("Airshed Capacity Status", status, f"Score: {res['estimated_assimilative_capacity']}/100")

            st.info(f"**Action Protocol:** {res['mitigation_protocol']}")

    # TAB 4: Batch Ingestion
    with tab4:
        st.subheader("Batch Satellite Grid Ingestion")
        st.write("Upload a CSV file containing satellite observations to run batch unsupervised grouping.")
        uploaded_file = st.file_uploader("Upload Satellite CSV", type=["csv"])
        if uploaded_file is not None:
            up_df = pd.read_csv(uploaded_file)
            st.write(f"Loaded {len(up_df)} records. Preview:")
            st.dataframe(up_df.head(5))

    # TAB 5: Scientific Validation
    with tab5:
        st.subheader("External Cluster Validity & Carrying-Capacity Benchmarks")
        st.write("Comparison against ground-truth continuous monitoring stations (CAAQMS) and airshed carrying-capacity models.")

        v_col1, v_col2 = st.columns([1, 1])
        with v_col1:
            st.markdown("### Validity Metrics")
            st.dataframe(STORE["agreement"], use_container_width=True)

            st.markdown("### Alignment Confusion Matrix")
            st.dataframe(STORE["cm"], use_container_width=True)

        with v_col2:
            st.markdown(f"### Discovered Hidden Hotspots ({len(STORE['hidden'])} Total)")
            st.write("Unmonitored critical airshed cells detected exclusively via satellite multi-sensor observation:")
            st.dataframe(
                STORE["hidden"][[
                    "cell_id", "region_name", "predicted_archetype",
                    "satellite_pollution_index", "so2_column_umol_m2", "no2_column_umol_m2"
                ]],
                use_container_width=True
            )

    # TAB 6: Figures Gallery
    with tab6:
        st.subheader("Publication-Quality Figures Suite")
        fig_files = [
            ("01_optimal_k_elbow_silhouette.png", "Figure 1: Optimal Cluster Number (k) Evaluation via Elbow Inertia & Silhouette Analysis"),
            ("02_pca_cluster_space.png", "Figure 2: Latent Atmospheric Feature Space (PCA 2D Projection with Archetype Centroids)"),
            ("03_geospatial_pollution_hotspots_map.png", "Figure 3: Geospatial Distribution of Satellite Pollution Hotspots Across Regional Basins"),
            ("04_confusion_matrix_validation.png", "Figure 4: External Cluster Validity Normalized Confusion Matrix vs CAAQMS"),
            ("05_airshed_capacity_stress_boxplot.png", "Figure 5: Airshed Assimilative Capacity Stress Distribution by Pollution Archetype"),
            ("06_pollutant_fingerprint_radar_profiles.png", "Figure 6: Multi-Pollutant Fingerprint Signatures Across Satellite Pollution Archetypes")
        ]

        for fname, caption in fig_files:
            fpath = os.path.join("reports/figures", fname)
            if os.path.exists(fpath):
                st.image(fpath, caption=caption, use_column_width=True)
                st.markdown("---")
