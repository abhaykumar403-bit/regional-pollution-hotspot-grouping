"""
Feature Engineering and Satellite Observation Preprocessing Pipeline
Normalizes, transforms, and prepares multi-sensor satellite Earth observation vectors
for unsupervised clustering and pollution hotspot pattern grouping.
"""

import os
import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.decomposition import PCA

FEATURE_GROUPS = {
    "trace_gases": [
        "no2_column_umol_m2",
        "so2_column_umol_m2",
        "co_column_mmol_m2",
        "hcho_column_umol_m2",
        "methane_ch4_ppb"
    ],
    "particulate_thermal": [
        "aerosol_optical_depth_550",
        "uv_aerosol_index",
        "fire_radiative_power_mw",
        "land_surface_temp_c"
    ],
    "meteorological_dispersion": [
        "boundary_layer_height_m",
        "surface_wind_speed_ms",
        "ventilation_coefficient_m2s",
        "relative_humidity_pct"
    ],
    "chemical_ratios": [
        "no2_to_so2_ratio",
        "hcho_to_no2_ratio"
    ]
}

ALL_MODEL_FEATURES = (
    FEATURE_GROUPS["trace_gases"] +
    FEATURE_GROUPS["particulate_thermal"] +
    FEATURE_GROUPS["meteorological_dispersion"] +
    FEATURE_GROUPS["chemical_ratios"]
)

# Features that exhibit heavy-tailed distributions in satellite observation
SKEWED_FEATURES = [
    "so2_column_umol_m2",
    "no2_column_umol_m2",
    "co_column_mmol_m2",
    "fire_radiative_power_mw",
    "ventilation_coefficient_m2s",
    "no2_to_so2_ratio"
]

class SatelliteFeaturePipeline:
    def __init__(self, scaler_type: str = "robust", n_pca_components: int = 3):
        """
        scaler_type: 'robust' (RobustScaler, resilient to intense industrial/stubble flare outliers)
                     or 'standard' (StandardScaler)
        n_pca_components: number of PCA components to extract for visualization and latent manifold mapping.
        """
        self.scaler_type = scaler_type
        self.n_pca_components = n_pca_components
        self.scaler = RobustScaler() if scaler_type == "robust" else StandardScaler()
        self.pca = PCA(n_components=n_pca_components, random_state=42)
        self.feature_names = ALL_MODEL_FEATURES
        self.fitted = False

    def transform_skewed_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Applies log1p transformations to heavy-tailed satellite observation features."""
        df_transformed = df.copy()
        for col in SKEWED_FEATURES:
            if col in df_transformed.columns:
                df_transformed[col] = np.log1p(np.clip(df_transformed[col].values, a_min=0, a_max=None))
        return df_transformed

    def fit(self, df: pd.DataFrame):
        """Fits scaler and PCA transformer on input dataframe."""
        df_tf = self.transform_skewed_features(df)
        X = df_tf[self.feature_names].values
        X_scaled = self.scaler.fit_transform(X)
        self.pca.fit(X_scaled)
        self.fitted = True
        return self

    def transform(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        """Transforms input dataframe returning scaled matrix and PCA coordinates."""
        if not self.fitted:
            raise RuntimeError("Pipeline must be fitted before calling transform.")
        df_tf = self.transform_skewed_features(df)
        X = df_tf[self.feature_names].values
        X_scaled = self.scaler.transform(X)
        X_pca = self.pca.transform(X_scaled)
        return X_scaled, X_pca

    def fit_transform(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        """Fits and transforms input dataframe."""
        self.fit(df)
        return self.transform(df)

    def save_artifacts(self, output_dir: str = "data/processed"):
        """Serializes scaler and PCA models using joblib."""
        os.makedirs(output_dir, exist_ok=True)
        joblib.dump(self.scaler, os.path.join(output_dir, "feature_scaler.joblib"))
        joblib.dump(self.pca, os.path.join(output_dir, "pca_transformer.joblib"))
        print(f"[FeaturePipeline] Saved feature scaler and PCA models to {output_dir}")

def process_and_save_features(
    raw_csv_path: str = "data/raw/satellite_pollution_hotspots.csv",
    output_dir: str = "data/processed",
    scaler_type: str = "robust"
) -> tuple[pd.DataFrame, np.ndarray, SatelliteFeaturePipeline]:
    """
    Loads raw satellite dataset, applies skew transformations and robust scaling,
    computes PCA projections, and writes processed dataset and matrices.
    """
    os.makedirs(output_dir, exist_ok=True)
    df_raw = pd.read_csv(raw_csv_path)

    pipeline = SatelliteFeaturePipeline(scaler_type=scaler_type, n_pca_components=3)
    X_scaled, X_pca = pipeline.fit_transform(df_raw)

    # Save X_scaled matrix
    np.save(os.path.join(output_dir, "X_scaled.npy"), X_scaled)

    # Attach PCA projection coordinates to processed dataframe
    df_processed = df_raw.copy()
    df_processed["pca_1"] = np.round(X_pca[:, 0], 4)
    df_processed["pca_2"] = np.round(X_pca[:, 1], 4)
    df_processed["pca_3"] = np.round(X_pca[:, 2], 4)

    # Compute a composite satellite atmospheric pollution score
    # Reflects multi-pollutant severity normalized across trace gases and aerosols
    norm_no2 = np.clip(df_processed["no2_column_umol_m2"] / 250.0, 0, 2.0)
    norm_so2 = np.clip(df_processed["so2_column_umol_m2"] / 150.0, 0, 2.0)
    norm_co = np.clip(df_processed["co_column_mmol_m2"] / 70.0, 0, 2.0)
    norm_aod = np.clip(df_processed["aerosol_optical_depth_550"] / 1.2, 0, 2.0)
    norm_uvai = np.clip(np.maximum(0, df_processed["uv_aerosol_index"]) / 2.5, 0, 2.0)
    norm_frp = np.clip(df_processed["fire_radiative_power_mw"] / 200.0, 0, 2.0)

    composite_score = (
        0.24 * norm_no2 +
        0.24 * norm_so2 +
        0.20 * norm_aod +
        0.14 * norm_co +
        0.10 * norm_uvai +
        0.08 * norm_frp
    ) * 100.0 / 1.5

    df_processed["satellite_pollution_index"] = np.round(np.clip(composite_score, 0.0, 100.0), 2)

    proc_path = os.path.join(output_dir, "satellite_processed.csv")
    df_processed.to_csv(proc_path, index=False)
    pipeline.save_artifacts(output_dir)

    print(f"[FeaturePipeline] Feature engineering complete. Scaled matrix shape: {X_scaled.shape}")
    print(f"[FeaturePipeline] Saved processed dataset with PCA components to {proc_path}")

    return df_processed, X_scaled, pipeline

if __name__ == "__main__":
    process_and_save_features()
