"""
Satellite Earth Observation Data Generator
Synthesizes multi-sensor satellite Earth observation measurements (Sentinel-5P TROPOMI,
MODIS/VIIRS, and ERA5 Reanalysis) across regional grid cells for unsupervised
pollution hotspot pattern grouping and airshed assimilative capacity validation.
"""

import os
import numpy as np
import pandas as pd

AIRSHED_REGIONS = [
    {
        "region_name": "Delhi-NCR Airshed Basin",
        "basin": "Indo-Gangetic Plain",
        "lat_range": (28.2, 29.1),
        "lon_range": (76.8, 77.8),
        "primary_tendency": "urban_vehicular",
        "prob_weights": [0.15, 0.65, 0.15, 0.05]
    },
    {
        "region_name": "Singrauli-Korba Coal & Power Belt",
        "basin": "Central Plateau Industrial Basin",
        "lat_range": (23.8, 24.5),
        "lon_range": (82.3, 83.2),
        "primary_tendency": "industrial_power",
        "prob_weights": [0.75, 0.15, 0.05, 0.05]
    },
    {
        "region_name": "Punjab-Haryana Stubble Burning Corridor",
        "basin": "Upper Indo-Gangetic Basin",
        "lat_range": (29.8, 31.4),
        "lon_range": (74.8, 76.8),
        "primary_tendency": "biomass_burning",
        "prob_weights": [0.10, 0.15, 0.70, 0.05]
    },
    {
        "region_name": "Mumbai-Thane Petrochemical & Port Zone",
        "basin": "Western Coastal Maritime Basin",
        "lat_range": (18.9, 19.4),
        "lon_range": (72.7, 73.2),
        "primary_tendency": "industrial_urban_mixed",
        "prob_weights": [0.45, 0.45, 0.02, 0.08]
    },
    {
        "region_name": "Jharkhand-Odisha Mining & Smelter Belt",
        "basin": "Chota Nagpur Industrial Basin",
        "lat_range": (21.8, 23.2),
        "lon_range": (84.8, 86.6),
        "primary_tendency": "industrial_power",
        "prob_weights": [0.70, 0.15, 0.05, 0.10]
    },
    {
        "region_name": "Bengaluru-Mysuru Tech & Highway Corridor",
        "basin": "Southern Deccan Plateau",
        "lat_range": (12.7, 13.2),
        "lon_range": (77.3, 77.8),
        "primary_tendency": "urban_vehicular",
        "prob_weights": [0.05, 0.60, 0.05, 0.30]
    },
    {
        "region_name": "Western Ghats Ecological Biosphere",
        "basin": "Western Highland Biosphere",
        "lat_range": (11.5, 14.5),
        "lon_range": (75.2, 76.5),
        "primary_tendency": "clean_baseline",
        "prob_weights": [0.02, 0.03, 0.05, 0.90]
    },
    {
        "region_name": "Brahmaputra Valley & NE Forest Basin",
        "basin": "Northeastern Valley Basin",
        "lat_range": (25.8, 27.2),
        "lon_range": (91.5, 94.2),
        "primary_tendency": "clean_baseline",
        "prob_weights": [0.03, 0.07, 0.15, 0.75]
    },
    {
        "region_name": "Gujarat-Gulf of Khambhat Industrial Cluster",
        "basin": "Western Industrial Coast",
        "lat_range": (21.5, 22.8),
        "lon_range": (72.2, 73.6),
        "primary_tendency": "industrial_power",
        "prob_weights": [0.65, 0.25, 0.03, 0.07]
    },
    {
        "region_name": "Kolkata-Howrah Industrial & Urban Belt",
        "basin": "Lower Gangetic Delta",
        "lat_range": (22.3, 22.9),
        "lon_range": (88.1, 88.6),
        "primary_tendency": "industrial_urban_mixed",
        "prob_weights": [0.35, 0.50, 0.05, 0.10]
    }
]

ARCHETYPES = [
    "Type 1: Industrial & Power Combustion Hotspot",
    "Type 2: Dense Urban-Vehicular Smog Corridor",
    "Type 3: Agricultural Biomass & Stubble Burning Plume",
    "Type 4: Clean Background & Resilient Airshed"
]

def generate_satellite_pollution_dataset(n_samples: int = 1600, random_state: int = 42) -> pd.DataFrame:
    """
    Synthesizes multi-sensor satellite Earth observation records across regional grid cells.
    Simulates Sentinel-5P TROPOMI trace gas columns, MODIS/VIIRS aerosol and thermal indicators,
    ERA5 meteorological dispersion, and ground-truth validation fields.
    """
    np.random.seed(random_state)
    records = []

    samples_per_region = n_samples // len(AIRSHED_REGIONS)
    remainder = n_samples % len(AIRSHED_REGIONS)

    cell_idx = 1
    for r_idx, reg in enumerate(AIRSHED_REGIONS):
        count = samples_per_region + (1 if r_idx < remainder else 0)
        
        # Determine archetype membership based on regional probability weights
        assigned_archetypes = np.random.choice(
            ARCHETYPES,
            size=count,
            p=reg["prob_weights"]
        )

        for arch in assigned_archetypes:
            lat = np.random.uniform(reg["lat_range"][0], reg["lat_range"][1])
            lon = np.random.uniform(reg["lon_range"][0], reg["lon_range"][1])
            cell_id = f"SAT-EO-{cell_idx:04d}"

            # Base generation conditional on archetype
            if arch == "Type 1: Industrial & Power Combustion Hotspot":
                # High SO2 (coal/smelters), High NO2, High AOD, moderate CO, low FRP
                so2 = np.random.gamma(shape=12.0, scale=12.5) + 30.0    # 100 - 320 umol/m2
                no2 = np.random.gamma(shape=9.0, scale=14.0) + 40.0     # 80 - 280 umol/m2
                co = np.random.normal(loc=38.0, scale=7.0)              # 25 - 55 mmol/m2
                hcho = np.random.normal(loc=35.0, scale=8.0)            # 20 - 55 umol/m2
                aod = np.random.beta(a=5, b=3) * 0.95 + 0.35            # 0.55 - 1.25
                uvai = np.random.normal(loc=1.2, scale=0.45)            # 0.5 - 2.2
                ch4 = np.random.normal(loc=1940.0, scale=35.0)          # 1880 - 2020 ppb
                frp = np.random.exponential(scale=12.0)                 # 0 - 60 MW
                lst = np.random.normal(loc=37.5, scale=4.0)             # 30 - 45 C
                blh = np.random.uniform(400, 1400)                      # 400 - 1400 m
                wind = np.random.uniform(1.2, 5.0)                      # 1.2 - 5.0 m/s
                rh = np.random.uniform(35, 75)
                precip = np.random.exponential(scale=2.0)

            elif arch == "Type 2: Dense Urban-Vehicular Smog Corridor":
                # Very High NO2, High CO, High HCHO, moderate SO2, low-mid FRP, high LST (Urban Heat Island)
                so2 = np.random.gamma(shape=4.0, scale=8.0) + 10.0      # 20 - 75 umol/m2
                no2 = np.random.gamma(shape=14.0, scale=16.0) + 60.0    # 150 - 400 umol/m2
                co = np.random.normal(loc=58.0, scale=10.0)             # 35 - 85 mmol/m2
                hcho = np.random.normal(loc=65.0, scale=15.0)           # 40 - 110 umol/m2
                aod = np.random.beta(a=4, b=4) * 0.8 + 0.30             # 0.45 - 1.10
                uvai = np.random.normal(loc=0.8, scale=0.35)            # 0.2 - 1.6
                ch4 = np.random.normal(loc=1965.0, scale=40.0)          # Landfills & fugitive
                frp = np.random.exponential(scale=8.0)                  # Minimal fires
                lst = np.random.normal(loc=40.0, scale=3.5)             # Intense UHI
                blh = np.random.uniform(300, 1100)                      # Shallow trapped winter inversion
                wind = np.random.uniform(0.8, 3.8)                      # Stagnant ventilation
                rh = np.random.uniform(40, 80)
                precip = np.random.exponential(scale=1.5)

            elif arch == "Type 3: Agricultural Biomass & Stubble Burning Plume":
                # Extreme FRP, High UVAI (smoke), High CO, High AOD, moderate NO2, low SO2
                so2 = np.random.gamma(shape=3.0, scale=6.0) + 5.0       # 10 - 40 umol/m2
                no2 = np.random.gamma(shape=6.0, scale=12.0) + 25.0     # 50 - 160 umol/m2
                co = np.random.normal(loc=68.0, scale=12.0)             # 45 - 95 mmol/m2
                hcho = np.random.normal(loc=55.0, scale=12.0)           # 30 - 85 umol/m2
                aod = np.random.beta(a=7, b=2) * 1.1 + 0.50             # 0.80 - 1.65 (Severe haze)
                uvai = np.random.normal(loc=2.8, scale=0.60)            # 1.6 - 4.2 (High UV absorption)
                ch4 = np.random.normal(loc=1980.0, scale=45.0)          # High biomass methane
                frp = np.random.gamma(shape=8.0, scale=28.0) + 60.0     # 120 - 450 MW (Active fires)
                lst = np.random.normal(loc=35.0, scale=4.5)
                blh = np.random.uniform(250, 950)                       # Trapped plume layer
                wind = np.random.uniform(1.5, 6.0)                      # Smoke advection
                rh = np.random.uniform(30, 65)
                precip = np.random.exponential(scale=0.8)

            else:  # Type 4: Clean Background & Resilient Airshed
                # Low NO2, Low SO2, Low CO, Low AOD, Negative/Low UVAI, High BLH/Ventilation
                so2 = np.random.gamma(shape=2.0, scale=4.0) + 2.0       # 3 - 18 umol/m2
                no2 = np.random.gamma(shape=2.5, scale=5.0) + 5.0       # 8 - 30 umol/m2
                co = np.random.normal(loc=20.0, scale=4.0)              # 12 - 28 mmol/m2
                hcho = np.random.normal(loc=18.0, scale=4.5)            # 10 - 28 umol/m2
                aod = np.random.beta(a=2, b=8) * 0.35 + 0.05            # 0.06 - 0.28
                uvai = np.random.normal(loc=-0.15, scale=0.30)          # -0.6 - 0.4
                ch4 = np.random.normal(loc=1820.0, scale=25.0)          # Baseline
                frp = np.random.exponential(scale=1.5)                  # Virtually 0
                lst = np.random.normal(loc=26.0, scale=4.0)             # Cooler forested/rural
                blh = np.random.uniform(900, 2400)                      # Deep dispersion layer
                wind = np.random.uniform(3.0, 9.5)                      # High ventilation
                rh = np.random.uniform(45, 90)
                precip = np.random.exponential(scale=6.0)

            # Ensure non-negative bounds and physical limits
            so2 = float(np.clip(so2, 1.0, 450.0))
            no2 = float(np.clip(no2, 2.0, 500.0))
            co = float(np.clip(co, 8.0, 120.0))
            hcho = float(np.clip(hcho, 5.0, 160.0))
            aod = float(np.clip(aod, 0.04, 2.20))
            uvai = float(np.clip(uvai, -1.0, 5.0))
            ch4 = float(np.clip(ch4, 1750.0, 2300.0))
            frp = float(np.clip(frp, 0.0, 600.0))
            lst = float(np.clip(lst, 15.0, 55.0))
            blh = float(np.clip(blh, 150.0, 3000.0))
            wind = float(np.clip(wind, 0.4, 16.0))
            rh = float(np.clip(rh, 10.0, 98.0))
            precip = float(np.clip(precip, 0.0, 60.0))

            # Derived Meteorological Dispersion: Ventilation Coefficient = BLH * Wind Speed (m2/s)
            ventilation_coeff = float(blh * wind)

            # Atmospheric chemical indicators
            no2_so2_ratio = float(no2 / (so2 + 1e-4))
            hcho_no2_ratio = float(hcho / (no2 + 1e-4))

            # Ground Station Ground-Truth Validation Synthesis (CAAQMS Network)
            # Physical mapping: PM2.5 closely couples with AOD, FRP, CO, and stagnant ventilation
            inversion_penalty = max(0.0, (1500.0 - blh) / 1500.0)
            pm25_base = (
                aod * 180.0 +
                (co / 100.0) * 80.0 +
                (frp / 400.0) * 140.0 +
                inversion_penalty * 60.0 -
                (precip * 2.5) +
                np.random.normal(0, 12)
            )
            ground_pm25 = float(np.clip(pm25_base, 8.0, 550.0))

            # Ground AQI Category mapping (CPCB National Air Quality Index standard)
            if ground_pm25 <= 30.0:
                ground_aqi_cat = "Good"
            elif ground_pm25 <= 60.0:
                ground_aqi_cat = "Satisfactory"
            elif ground_pm25 <= 90.0:
                ground_aqi_cat = "Moderate"
            elif ground_pm25 <= 120.0:
                ground_aqi_cat = "Poor"
            elif ground_pm25 <= 250.0:
                ground_aqi_cat = "Very Poor"
            else:
                ground_aqi_cat = "Severe"

            # Airshed Assimilative Capacity Index (0 - 100, where < 35 indicates critical carrying capacity deficit)
            dispersion_factor = min(1.0, ventilation_coeff / 6000.0)
            emission_load = (
                0.25 * (no2 / 300.0) +
                0.28 * (so2 / 200.0) +
                0.22 * (aod / 1.5) +
                0.15 * (co / 80.0) +
                0.10 * (frp / 250.0)
            )
            assimilative_capacity = float(np.clip(
                (dispersion_factor * 60.0 + (precip / 40.0) * 20.0 - emission_load * 50.0 + 35.0) +
                np.random.normal(0, 3.5),
                0.0, 100.0
            ))

            airshed_deficit_flag = int(assimilative_capacity < 40.0)

            # Ground Monitor Availability: In developing regional airsheds, CAAQMS monitors are
            # heavily concentrated in urban centers, leaving industrial clusters & rural agricultural
            # stubble zones severely unmonitored (simulating Satellite Blind-Spot Auditing)
            if arch == "Type 2: Dense Urban-Vehicular Smog Corridor":
                has_monitor = bool(np.random.rand() < 0.78)  # 78% monitored
            elif arch == "Type 1: Industrial & Power Combustion Hotspot":
                has_monitor = bool(np.random.rand() < 0.42)  # 42% monitored (many remote smelters/mines)
            elif arch == "Type 3: Agricultural Biomass & Stubble Burning Plume":
                has_monitor = bool(np.random.rand() < 0.22)  # 22% monitored (rural farmland)
            else:
                has_monitor = bool(np.random.rand() < 0.35)  # 35% monitored

            record = {
                "cell_id": cell_id,
                "region_name": reg["region_name"],
                "airshed_basin": reg["basin"],
                "latitude": round(lat, 5),
                "longitude": round(lon, 5),
                # Sentinel-5P TROPOMI Columns
                "no2_column_umol_m2": round(no2, 2),
                "so2_column_umol_m2": round(so2, 2),
                "co_column_mmol_m2": round(co, 2),
                "hcho_column_umol_m2": round(hcho, 2),
                "methane_ch4_ppb": round(ch4, 1),
                # MODIS / VIIRS Aerosol & Thermal Indicators
                "aerosol_optical_depth_550": round(aod, 4),
                "uv_aerosol_index": round(uvai, 3),
                "fire_radiative_power_mw": round(frp, 2),
                "land_surface_temp_c": round(lst, 2),
                # ERA5 Meteorological Reanalysis & Dispersion
                "boundary_layer_height_m": round(blh, 1),
                "surface_wind_speed_ms": round(wind, 2),
                "ventilation_coefficient_m2s": round(ventilation_coeff, 1),
                "relative_humidity_pct": round(rh, 1),
                "precipitation_rate_mm": round(precip, 2),
                # Chemical Diagnostic Ratios
                "no2_to_so2_ratio": round(no2_so2_ratio, 3),
                "hcho_to_no2_ratio": round(hcho_no2_ratio, 3),
                # Authority & Empirical Ground-Truth Benchmarks
                "ground_truth_archetype": arch,
                "ground_pm25_ugm3": round(ground_pm25, 1),
                "ground_aqi_category": ground_aqi_cat,
                "airshed_assimilative_capacity": round(assimilative_capacity, 2),
                "airshed_deficit_flag": airshed_deficit_flag,
                "ground_station_installed": has_monitor
            }
            records.append(record)
            cell_idx += 1

    df = pd.DataFrame(records)
    return df

def save_satellite_dataset(df: pd.DataFrame, output_dir: str = "data/raw") -> str:
    """Saves generated satellite dataset to raw CSV."""
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, "satellite_pollution_hotspots.csv")
    df.to_csv(file_path, index=False)
    print(f"[DataGenerator] Saved {len(df)} satellite grid observation records to {file_path}")
    return file_path

if __name__ == "__main__":
    df = generate_satellite_pollution_dataset(n_samples=1600, random_state=42)
    save_satellite_dataset(df)
