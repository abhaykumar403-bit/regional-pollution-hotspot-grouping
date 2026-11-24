"""
Full-Fledged FastAPI Backend Server
AeroClust AI: Regional Pollution Hotspot Pattern Grouping & Airshed Carrying-Capacity DSS
"""

import os
import io
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import joblib
import numpy as np
import pandas as pd
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from src.clustering import (
    POLLUTION_ARCHETYPES,
    HOTSPOT_TIER_MAPPING,
    TIER_SEVERITY_ORDER
)
from src.feature_engineering import ALL_MODEL_FEATURES, SKEWED_FEATURES

app = FastAPI(
    title="AeroClust AI DSS API",
    description="Backend API for Regional Satellite Pollution Hotspot Pattern Grouping and Airshed Carrying-Capacity Audits",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODELS = {}

def load_cached_models():
    if MODELS.get("loaded"):
        return
    base_dir = "data/processed"
    if not os.path.exists(os.path.join(base_dir, "feature_scaler.joblib")):
        print("[Server] Model artifacts not found yet. Run main.py first.")
        return

    MODELS["scaler"] = joblib.load(os.path.join(base_dir, "feature_scaler.joblib"))
    MODELS["pca"] = joblib.load(os.path.join(base_dir, "pca_transformer.joblib"))
    MODELS["kmeans"] = joblib.load(os.path.join(base_dir, "kmeans_model.joblib"))

    mapping_df = pd.read_csv(os.path.join(base_dir, "cluster_archetype_mapping.csv"))
    MODELS["cluster_to_archetype"] = dict(zip(mapping_df["cluster_id"], mapping_df["pollution_archetype"]))
    MODELS["archetype_to_cluster"] = dict(zip(mapping_df["pollution_archetype"], mapping_df["cluster_id"]))
    MODELS["cluster_to_tier"] = dict(zip(mapping_df["cluster_id"], mapping_df["hotspot_risk_tier"]))

    ind_cluster = MODELS["archetype_to_cluster"]["Type 1: Industrial & Power Combustion Hotspot"]
    MODELS["ind_centroid"] = MODELS["kmeans"].cluster_centers_[ind_cluster]

    MODELS["dataset"] = pd.read_csv(os.path.join(base_dir, "satellite_clustered.csv"))
    MODELS["loaded"] = True
    print("[Server] Successfully loaded all models, transformers, and satellite dataset.")

@app.on_event("startup")
def on_startup():
    load_cached_models()

# Ensure models are loaded immediately
load_cached_models()

# Pydantic Schemas
class SatelliteGridInput(BaseModel):
    cell_name: Optional[str] = "SAT-INSPECT-01"
    region_name: Optional[str] = "Delhi-NCR Airshed Basin"
    latitude: Optional[float] = 28.6139
    longitude: Optional[float] = 77.2090
    no2_column_umol_m2: float = Field(..., ge=1.0, le=600.0, description="Sentinel-5P Tropospheric NO2 Column (µmol/m²)")
    so2_column_umol_m2: float = Field(..., ge=1.0, le=500.0, description="Sentinel-5P SO2 Planetary Boundary Layer Column (µmol/m²)")
    co_column_mmol_m2: float = Field(..., ge=5.0, le=150.0, description="Sentinel-5P Carbon Monoxide Column (mmol/m²)")
    hcho_column_umol_m2: float = Field(..., ge=2.0, le=200.0, description="Sentinel-5P Formaldehyde Column (µmol/m²)")
    methane_ch4_ppb: float = Field(..., ge=1700.0, le=2500.0, description="Sentinel-5P Methane Column (ppb)")
    aerosol_optical_depth_550: float = Field(..., ge=0.01, le=2.5, description="MODIS/VIIRS AOD at 550nm")
    uv_aerosol_index: float = Field(..., ge=-1.5, le=6.0, description="Sentinel-5P UV Aerosol Index")
    fire_radiative_power_mw: float = Field(..., ge=0.0, le=800.0, description="MODIS/VIIRS Active Fire Radiative Power (MW)")
    land_surface_temp_c: float = Field(..., ge=10.0, le=60.0, description="Land Surface Temperature (°C)")
    boundary_layer_height_m: float = Field(..., ge=100.0, le=3500.0, description="Boundary Layer Height (m)")
    surface_wind_speed_ms: float = Field(..., ge=0.2, le=25.0, description="Surface Wind Speed (m/s)")
    relative_humidity_pct: float = Field(..., ge=5.0, le=100.0, description="Relative Humidity (%)")
    precipitation_rate_mm: Optional[float] = 0.5

def predict_single_record(data: dict) -> dict:
    load_cached_models()
    # Compute derived ratios
    data_tf = data.copy()
    data_tf["ventilation_coefficient_m2s"] = float(data_tf["boundary_layer_height_m"] * data_tf["surface_wind_speed_ms"])
    data_tf["no2_to_so2_ratio"] = float(data_tf["no2_column_umol_m2"] / (data_tf["so2_column_umol_m2"] + 1e-4))
    data_tf["hcho_to_no2_ratio"] = float(data_tf["hcho_column_umol_m2"] / (data_tf["no2_column_umol_m2"] + 1e-4))

    # Apply skew transformations
    for col in SKEWED_FEATURES:
        data_tf[col] = np.log1p(max(0.0, data_tf[col]))

    feature_vector = np.array([[data_tf[f] for f in ALL_MODEL_FEATURES]])
    X_scaled = MODELS["scaler"].transform(feature_vector)

    cluster_id = int(MODELS["kmeans"].predict(X_scaled)[0])
    archetype = MODELS["cluster_to_archetype"][cluster_id]
    risk_tier = MODELS["cluster_to_tier"][cluster_id]

    dist_to_centroid = float(np.linalg.norm(X_scaled - MODELS["kmeans"].cluster_centers_[cluster_id]))
    dist_to_ind = float(np.linalg.norm(X_scaled - MODELS["ind_centroid"]))
    pca_coords = MODELS["pca"].transform(X_scaled)[0]

    # Compute composite pollution index
    norm_no2 = np.clip(data["no2_column_umol_m2"] / 250.0, 0, 2.0)
    norm_so2 = np.clip(data["so2_column_umol_m2"] / 150.0, 0, 2.0)
    norm_co = np.clip(data["co_column_mmol_m2"] / 70.0, 0, 2.0)
    norm_aod = np.clip(data["aerosol_optical_depth_550"] / 1.2, 0, 2.0)
    norm_uvai = np.clip(max(0, data["uv_aerosol_index"]) / 2.5, 0, 2.0)
    norm_frp = np.clip(data["fire_radiative_power_mw"] / 200.0, 0, 2.0)

    pollution_index = round(float((
        0.24 * norm_no2 +
        0.24 * norm_so2 +
        0.20 * norm_aod +
        0.14 * norm_co +
        0.10 * norm_uvai +
        0.08 * norm_frp
    ) * 100.0 / 1.5), 2)

    # Estimate Airshed Assimilative Capacity and Deficit Condition
    vent_coeff = data["boundary_layer_height_m"] * data["surface_wind_speed_ms"]
    dispersion = min(1.0, vent_coeff / 6000.0)
    emission_load = (
        0.25 * (data["no2_column_umol_m2"] / 300.0) +
        0.28 * (data["so2_column_umol_m2"] / 200.0) +
        0.22 * (data["aerosol_optical_depth_550"] / 1.5) +
        0.15 * (data["co_column_mmol_m2"] / 80.0) +
        0.10 * (data["fire_radiative_power_mw"] / 250.0)
    )
    est_capacity = round(float(np.clip(
        dispersion * 60.0 + (data.get("precipitation_rate_mm", 0.5) / 40.0) * 20.0 - emission_load * 50.0 + 35.0,
        0.0, 100.0
    )), 2)

    deficit_flag = bool(est_capacity < 40.0)

    # Recommended mitigation protocol based on archetype
    mitigations = {
        "Type 1: Industrial & Power Combustion Hotspot": "Immediate Flue-Gas Desulfurization (FGD) verification, thermal plant load throttling, and continuous emission monitoring (CEMS) audit.",
        "Type 2: Dense Urban-Vehicular Smog Corridor": "Trigger Odd-Even vehicular rationing, heavy diesel freight bypass routing, and mist-cannon dust suppression on urban arterial corridors.",
        "Type 3: Agricultural Biomass & Stubble Burning Plume": "Deploy satellite thermal fire tracking, mobilize in-situ crop residue management machinery (Happy Seeders), and enforce fire bans.",
        "Type 4: Clean Background & Resilient Airshed": "Maintain clean airshed buffer baseline; continue regular satellite pass tracking."
    }

    return {
        "predicted_cluster": cluster_id,
        "predicted_archetype": archetype,
        "predicted_risk_tier": risk_tier,
        "satellite_pollution_index": pollution_index,
        "estimated_assimilative_capacity": est_capacity,
        "airshed_deficit_flag": deficit_flag,
        "dist_to_cluster_centroid": round(dist_to_centroid, 4),
        "dist_to_industrial_centroid": round(dist_to_ind, 4),
        "pca_1": round(float(pca_coords[0]), 4),
        "pca_2": round(float(pca_coords[1]), 4),
        "pca_3": round(float(pca_coords[2]), 4),
        "mitigation_protocol": mitigations.get(archetype, "Standard monitoring.")
    }

# Endpoints
@app.get("/api/stats")
def get_stats():
    load_cached_models()
    df = MODELS["dataset"]
    total = len(df)
    archetype_counts = df["predicted_archetype"].value_counts().to_dict()
    tier_counts = df["predicted_risk_tier"].value_counts().to_dict()
    deficits = int((df["airshed_deficit_flag"] == 1).sum())

    hidden_count = 0
    hidden_path = "data/processed/validation_hidden_hotspots.csv"
    if os.path.exists(hidden_path):
        hidden_df = pd.read_csv(hidden_path)
        hidden_count = len(hidden_df)

    avg_pollution = round(float(df["satellite_pollution_index"].mean()), 2)
    unmonitored_pct = round(float((~df["ground_station_installed"]).mean() * 100.0), 1)

    return {
        "total_cells": total,
        "archetype_distribution": archetype_counts,
        "risk_tier_distribution": tier_counts,
        "airshed_deficits_count": deficits,
        "airshed_deficits_percentage": round(deficits / total * 100.0, 1),
        "hidden_hotspots_detected": hidden_count,
        "average_pollution_index": avg_pollution,
        "unmonitored_cells_percentage": unmonitored_pct
    }

@app.get("/api/hotspots")
def get_hotspots(
    archetype: Optional[str] = None,
    region: Optional[str] = None,
    deficit_only: bool = False,
    hidden_only: bool = False,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    load_cached_models()
    df = MODELS["dataset"].copy()

    if archetype:
        df = df[df["predicted_archetype"] == archetype]
    if region:
        df = df[df["region_name"].str.contains(region, case=False, na=False)]
    if deficit_only:
        df = df[df["airshed_deficit_flag"] == 1]
    if hidden_only:
        df = df[(~df["ground_station_installed"]) & (df["predicted_archetype"].isin([
            "Type 1: Industrial & Power Combustion Hotspot",
            "Type 3: Agricultural Biomass & Stubble Burning Plume"
        ])) & (df["airshed_deficit_flag"] == 1)]

    total_filtered = len(df)
    page_df = df.iloc[offset : offset + limit]

    records = page_df[[
        "cell_id", "region_name", "airshed_basin", "latitude", "longitude",
        "predicted_archetype", "predicted_risk_tier", "satellite_pollution_index",
        "no2_column_umol_m2", "so2_column_umol_m2", "co_column_mmol_m2",
        "aerosol_optical_depth_550", "fire_radiative_power_mw",
        "airshed_assimilative_capacity", "airshed_deficit_flag",
        "ground_station_installed"
    ]].to_dict(orient="records")

    return {
        "total": total_filtered,
        "limit": limit,
        "offset": offset,
        "hotspots": records
    }

@app.post("/api/predict")
def predict_endpoint(payload: SatelliteGridInput):
    data = payload.dict()
    res = predict_single_record(data)
    res["cell_name"] = data.get("cell_name")
    res["region_name"] = data.get("region_name")
    return res

@app.post("/api/batch-predict")
async def batch_predict_endpoint(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    content = await file.read()
    try:
        df_upload = pd.read_csv(io.StringIO(content.decode("utf-8")))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")

    # Check required columns
    req_cols = [
        "no2_column_umol_m2", "so2_column_umol_m2", "co_column_mmol_m2",
        "hcho_column_umol_m2", "methane_ch4_ppb", "aerosol_optical_depth_550",
        "uv_aerosol_index", "fire_radiative_power_mw", "land_surface_temp_c",
        "boundary_layer_height_m", "surface_wind_speed_ms", "relative_humidity_pct"
    ]
    missing = [c for c in req_cols if c not in df_upload.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing columns: {missing}")

    predictions = []
    for _, row in df_upload.iterrows():
        p_res = predict_single_record(row.to_dict())
        p_res["cell_id"] = row.get("cell_id", f"UPLOAD-{_}")
        p_res["region_name"] = row.get("region_name", "Custom Region")
        predictions.append(p_res)

    pred_df = pd.DataFrame(predictions)
    archetype_summary = pred_df["predicted_archetype"].value_counts().to_dict()
    deficit_count = int(pred_df["airshed_deficit_flag"].sum())

    return {
        "total_records": len(predictions),
        "archetype_breakdown": archetype_summary,
        "deficits_detected": deficit_count,
        "records": predictions[:100]  # Return preview of first 100
    }

@app.get("/api/validation")
def get_validation_metrics():
    base_dir = "data/processed"
    agr_path = os.path.join(base_dir, "validation_agreement_metrics.csv")
    cm_path = os.path.join(base_dir, "validation_confusion_matrix.csv")
    stress_path = os.path.join(base_dir, "validation_airshed_capacity_stats.csv")

    if not os.path.exists(agr_path):
        raise HTTPException(status_code=404, detail="Validation files not generated.")

    agr_df = pd.read_csv(agr_path)
    cm_df = pd.read_csv(cm_path, index_col=0)
    stress_df = pd.read_csv(stress_path)

    return {
        "agreement_metrics": agr_df.to_dict(orient="records")[0],
        "confusion_matrix": cm_df.to_dict(),
        "airshed_stress_stats": stress_df.to_dict(orient="records")
    }

@app.get("/api/optimal-k")
def get_optimal_k():
    path = "data/processed/optimal_k_evaluation.csv"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Optimal k data not found.")
    df = pd.read_csv(path)
    return df.to_dict(orient="records")

@app.get("/api/hidden-hotspots")
def get_hidden_hotspots(limit: int = 50):
    path = "data/processed/validation_hidden_hotspots.csv"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Hidden hotspots file not found.")
    df = pd.read_csv(path)
    return df.head(limit).to_dict(orient="records")

@app.get("/api/figures/{figure_name}")
def get_figure(figure_name: str):
    fig_path = os.path.join("reports/figures", figure_name)
    if not os.path.exists(fig_path):
        raise HTTPException(status_code=404, detail="Figure not found.")
    return FileResponse(fig_path)

# Serve Frontend static assets
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    def serve_frontend():
        return FileResponse(os.path.join(static_dir, "index.html"))

if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
