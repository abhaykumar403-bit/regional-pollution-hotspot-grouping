"""
End-to-End Pipeline Execution Script
AeroClust AI: Regional Pollution Hotspot Pattern Grouping from Satellite Data
Unsupervised Machine Learning for Spatial Hotspot Profiling & Airshed Carrying-Capacity Validation
"""

import os
import sys
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.data_generator import generate_satellite_pollution_dataset, save_satellite_dataset
from src.feature_engineering import process_and_save_features
from src.clustering import run_clustering_pipeline
from src.validation import run_validation_pipeline
from src.visualization import generate_all_visualizations

def run_pipeline():
    start_time = time.time()
    print("=" * 76)
    print(" AEROCLUST AI: REGIONAL POLLUTION HOTSPOT PATTERN GROUPING DSS ")
    print(" Unsupervised Earth Observation Clustering & Airshed Carrying-Capacity Audit ")
    print("=" * 76)

    # 1. Satellite Data Compilation
    print("\n[Stage 1/5] Compiling Multi-Sensor Satellite Data (Sentinel-5P, MODIS, ERA5)...")
    df_raw = generate_satellite_pollution_dataset(n_samples=1600, random_state=42)
    raw_path = save_satellite_dataset(df_raw, "data/raw")

    # 2. Feature Engineering & Scaling
    print("\n[Stage 2/5] Feature Space Construction, Skew Transformations & Robust Scaling...")
    df_proc, X_scaled, pipeline = process_and_save_features(raw_path, "data/processed", scaler_type="robust")

    # 3. K-Means Clustering & Archetype Mapping
    print("\n[Stage 3/5] Evaluating Optimal k (Elbow/Silhouette) & Fitting K-Means++...")
    df_clustered, analyzer, eval_df = run_clustering_pipeline(
        "data/processed/satellite_processed.csv",
        "data/processed/X_scaled.npy",
        "data/processed"
    )

    # 4. Carrying-Capacity Stress Validation
    print("\n[Stage 4/5] Validating Hotspot Clusters Against Ground CAAQMS & Airshed Deficits...")
    val_results = run_validation_pipeline(
        "data/processed/satellite_clustered.csv",
        "data/processed"
    )

    # 5. Visualization Suite
    print("\n[Stage 5/5] Generating Publication-Quality Figures (300 DPI)...")
    figures = generate_all_visualizations(
        "data/processed/satellite_clustered.csv",
        "data/processed/optimal_k_evaluation.csv",
        "data/processed/validation_confusion_matrix.csv",
        "reports/figures"
    )

    elapsed = time.time() - start_time
    print("\n" + "=" * 76)
    print(f" PIPELINE COMPLETED SUCCESSFULLY IN {elapsed:.2f} SECONDS ")
    print("=" * 76)
    print(f" Raw Satellite Dataset  : data/raw/satellite_pollution_hotspots.csv")
    print(f" Processed Features     : data/processed/satellite_processed.csv")
    print(f" Clustered Results      : data/processed/satellite_clustered.csv")
    print(f" Evaluation Metrics     : data/processed/optimal_k_evaluation.csv")
    print(f" Validation Agreement   : data/processed/validation_agreement_metrics.csv")
    print(f" Hidden Hotspots Audit  : data/processed/validation_hidden_hotspots.csv")
    print(f" Visualizations ({len(figures)}): reports/figures/")
    print("=" * 76)

if __name__ == "__main__":
    run_pipeline()
