"""
K-Means Clustering and Regional Pollution Archetype Profiling Module
Segments satellite atmospheric observations into distinct regional pollution hotspot
patterns using K-Means++, evaluates optimal cluster numbers across 4 validity metrics,
and maps clusters to standardized environmental archetypes and risk tiers.
"""

import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score
from src.feature_engineering import ALL_MODEL_FEATURES

POLLUTION_ARCHETYPES = [
    "Type 1: Industrial & Power Combustion Hotspot",
    "Type 2: Dense Urban-Vehicular Smog Corridor",
    "Type 3: Agricultural Biomass & Stubble Burning Plume",
    "Type 4: Clean Background & Resilient Airshed"
]

HOTSPOT_TIER_MAPPING = {
    "Type 1: Industrial & Power Combustion Hotspot": "Tier 1 (Red Zone - Industrial Mega-Emitter)",
    "Type 2: Dense Urban-Vehicular Smog Corridor": "Tier 2 (Orange Zone - Dense Urban Smog)",
    "Type 3: Agricultural Biomass & Stubble Burning Plume": "Tier 3 (Amber Zone - Stubble Plume)",
    "Type 4: Clean Background & Resilient Airshed": "Tier 4 (Green Zone - Clean Airshed)"
}

TIER_SEVERITY_ORDER = [
    "Tier 1 (Red Zone - Industrial Mega-Emitter)",
    "Tier 2 (Orange Zone - Dense Urban Smog)",
    "Tier 3 (Amber Zone - Stubble Plume)",
    "Tier 4 (Green Zone - Clean Airshed)"
]

class SatelliteClusterAnalyzer:
    def __init__(self, n_clusters: int = 4, random_state: int = 42):
        self.n_clusters = n_clusters
        self.random_state = random_state
        self.model = KMeans(
            n_clusters=n_clusters,
            init="k-means++",
            n_init=25,
            max_iter=500,
            random_state=random_state
        )
        self.cluster_to_archetype = {}
        self.archetype_to_cluster = {}
        self.cluster_to_tier = {}
        self.fitted = False

    def evaluate_optimal_k(self, X: np.ndarray, k_range: range = range(2, 9)) -> pd.DataFrame:
        """
        Calculates WCSS (Inertia), Silhouette, Davies-Bouldin, and Calinski-Harabasz metrics
        across candidate cluster numbers k to empirically justify the selected k=4.
        """
        metrics = []
        for k in k_range:
            km = KMeans(n_clusters=k, init="k-means++", n_init=15, max_iter=300, random_state=self.random_state)
            labels = km.fit_predict(X)

            inertia = km.inertia_
            sil = silhouette_score(X, labels)
            db = davies_bouldin_score(X, labels)
            ch = calinski_harabasz_score(X, labels)

            metrics.append({
                "k": k,
                "inertia_wcss": np.round(inertia, 2),
                "silhouette_score": np.round(sil, 4),
                "davies_bouldin_index": np.round(db, 4),
                "calinski_harabasz_index": np.round(ch, 2)
            })

        eval_df = pd.DataFrame(metrics)
        return eval_df

    def _determine_archetype_mapping(self, centers: np.ndarray):
        """
        Scientifically matches unsupervised cluster centroids to the 4 environmental archetypes
        based on characteristic trace gas and particulate signatures.
        """
        # Feature indices
        feat_idx = {name: idx for idx, name in enumerate(ALL_MODEL_FEATURES)}
        idx_no2 = feat_idx["no2_column_umol_m2"]
        idx_so2 = feat_idx["so2_column_umol_m2"]
        idx_co = feat_idx["co_column_mmol_m2"]
        idx_hcho = feat_idx["hcho_column_umol_m2"]
        idx_frp = feat_idx["fire_radiative_power_mw"]
        idx_uvai = feat_idx["uv_aerosol_index"]
        idx_aod = feat_idx["aerosol_optical_depth_550"]
        idx_vent = feat_idx["ventilation_coefficient_m2s"]

        # Calculate scores for candidate archetypes
        scores = []
        for c_id in range(self.n_clusters):
            cent = centers[c_id]
            # Industrial Score: High SO2 + High NO2 - High FRP
            ind_score = 0.50 * cent[idx_so2] + 0.35 * cent[idx_no2] - 0.35 * cent[idx_frp]
            # Urban Vehicular Score: High NO2 + High CO + High HCHO - High SO2
            urb_score = 0.50 * cent[idx_no2] + 0.30 * cent[idx_co] + 0.20 * cent[idx_hcho] - 0.30 * cent[idx_so2]
            # Biomass Fire Score: High FRP + High UVAI + High AOD
            bio_score = 0.55 * cent[idx_frp] + 0.25 * cent[idx_uvai] + 0.20 * cent[idx_aod]
            # Clean Baseline Score: Negative trace gases & High Ventilation
            clean_score = -0.40 * cent[idx_no2] - 0.40 * cent[idx_so2] - 0.30 * cent[idx_aod] + 0.30 * cent[idx_vent]

            scores.append({
                "cluster_id": c_id,
                "ind_score": ind_score,
                "urb_score": urb_score,
                "bio_score": bio_score,
                "clean_score": clean_score
            })

        # Match archetypes greedily without duplicates
        assigned_archetypes = {}
        available_clusters = list(range(self.n_clusters))

        # 1. Clean background: highest clean_score
        c_clean = max(available_clusters, key=lambda c: scores[c]["clean_score"])
        assigned_archetypes[c_clean] = "Type 4: Clean Background & Resilient Airshed"
        available_clusters.remove(c_clean)

        # 2. Biomass stubble: highest bio_score among remaining
        c_bio = max(available_clusters, key=lambda c: scores[c]["bio_score"])
        assigned_archetypes[c_bio] = "Type 3: Agricultural Biomass & Stubble Burning Plume"
        available_clusters.remove(c_bio)

        # 3. Industrial: highest ind_score among remaining
        c_ind = max(available_clusters, key=lambda c: scores[c]["ind_score"])
        assigned_archetypes[c_ind] = "Type 1: Industrial & Power Combustion Hotspot"
        available_clusters.remove(c_ind)

        # 4. Urban: remaining cluster
        c_urb = available_clusters[0]
        assigned_archetypes[c_urb] = "Type 2: Dense Urban-Vehicular Smog Corridor"

        self.cluster_to_archetype = assigned_archetypes
        self.archetype_to_cluster = {v: k for k, v in assigned_archetypes.items()}
        self.cluster_to_tier = {
            c_id: HOTSPOT_TIER_MAPPING[arch]
            for c_id, arch in assigned_archetypes.items()
        }

    def fit_predict(self, X: np.ndarray) -> np.ndarray:
        """Fits K-Means++ model and predicts cluster labels."""
        labels = self.model.fit_predict(X)
        self._determine_archetype_mapping(self.model.cluster_centers_)
        self.fitted = True
        return labels

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predicts cluster labels for new observations."""
        if not self.fitted:
            raise RuntimeError("Model must be fitted before predict.")
        return self.model.predict(X)

    def save_artifacts(self, output_dir: str = "data/processed"):
        """Saves fitted K-Means model and cluster mapping tables."""
        os.makedirs(output_dir, exist_ok=True)
        joblib.dump(self.model, os.path.join(output_dir, "kmeans_model.joblib"))

        mapping_records = []
        for c_id in range(self.n_clusters):
            arch = self.cluster_to_archetype[c_id]
            tier = self.cluster_to_tier[c_id]
            mapping_records.append({
                "cluster_id": c_id,
                "pollution_archetype": arch,
                "hotspot_risk_tier": tier
            })
        mapping_df = pd.DataFrame(mapping_records)
        mapping_df.to_csv(os.path.join(output_dir, "cluster_archetype_mapping.csv"), index=False)
        print(f"[Clustering] Saved KMeans model and archetype mapping to {output_dir}")

def run_clustering_pipeline(
    processed_csv_path: str = "data/processed/satellite_processed.csv",
    scaled_npy_path: str = "data/processed/X_scaled.npy",
    output_dir: str = "data/processed"
) -> tuple[pd.DataFrame, SatelliteClusterAnalyzer, pd.DataFrame]:
    """
    Executes hyperparameter evaluation across k in [2..8], fits K-Means++ at optimal k=4,
    maps clusters to archetypes and hotspot tiers, and exports profile summaries.
    """
    os.makedirs(output_dir, exist_ok=True)
    df = pd.read_csv(processed_csv_path)
    X_scaled = np.load(scaled_npy_path)

    analyzer = SatelliteClusterAnalyzer(n_clusters=4, random_state=42)

    # 1. Hyperparameter Evaluation
    print("[Clustering] Evaluating optimal k cluster metrics (k=2 to 8)...")
    eval_df = analyzer.evaluate_optimal_k(X_scaled, k_range=range(2, 9))
    eval_df.to_csv(os.path.join(output_dir, "optimal_k_evaluation.csv"), index=False)
    print(eval_df.to_string(index=False))

    # 2. Fit K-Means++
    print("\n[Clustering] Fitting K-Means++ model with k=4...")
    labels = analyzer.fit_predict(X_scaled)

    df_clustered = df.copy()
    df_clustered["cluster_id"] = labels
    df_clustered["predicted_archetype"] = [analyzer.cluster_to_archetype[lbl] for lbl in labels]
    df_clustered["predicted_risk_tier"] = [analyzer.cluster_to_tier[lbl] for lbl in labels]

    # Calculate distance to assigned cluster centroid
    centers = analyzer.model.cluster_centers_
    distances_to_centroid = [
        np.linalg.norm(X_scaled[i] - centers[labels[i]])
        for i in range(len(labels))
    ]
    df_clustered["dist_to_centroid"] = np.round(distances_to_centroid, 4)

    # Calculate distance to Industrial Mega-Emitter centroid
    ind_cluster_id = analyzer.archetype_to_cluster["Type 1: Industrial & Power Combustion Hotspot"]
    ind_center = centers[ind_cluster_id]
    dist_to_ind = [
        np.linalg.norm(X_scaled[i] - ind_center)
        for i in range(len(labels))
    ]
    df_clustered["dist_to_industrial_centroid"] = np.round(dist_to_ind, 4)

    # 3. Export Archetype Profile Summary
    profile_cols = [
        "no2_column_umol_m2",
        "so2_column_umol_m2",
        "co_column_mmol_m2",
        "hcho_column_umol_m2",
        "aerosol_optical_depth_550",
        "uv_aerosol_index",
        "fire_radiative_power_mw",
        "land_surface_temp_c",
        "ventilation_coefficient_m2s",
        "ground_pm25_ugm3",
        "airshed_assimilative_capacity",
        "satellite_pollution_index"
    ]

    summary = df_clustered.groupby("predicted_archetype")[profile_cols].agg(["mean", "std", "median"])
    summary_path = os.path.join(output_dir, "archetype_profile_summary.csv")
    summary.to_csv(summary_path)

    # Save clustered dataframe
    clustered_path = os.path.join(output_dir, "satellite_clustered.csv")
    df_clustered.to_csv(clustered_path, index=False)
    analyzer.save_artifacts(output_dir)

    print(f"\n[Clustering] Clustered dataset saved to {clustered_path}")
    print(f"[Clustering] Archetype distribution:\n{df_clustered['predicted_archetype'].value_counts()}")

    return df_clustered, analyzer, eval_df

if __name__ == "__main__":
    run_clustering_pipeline()
