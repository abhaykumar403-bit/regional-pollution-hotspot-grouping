"""
Scientific Validation and Airshed Carrying-Capacity Stress Audit Module
Validates unsupervised K-Means satellite hotspot clusters against empirical ground-truth
monitoring stations (CAAQMS), airshed assimilative capacity thresholds, and identifies
unmonitored hidden pollution hotspots across regional air basins.
"""

import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import (
    adjusted_rand_score,
    normalized_mutual_info_score,
    homogeneity_completeness_v_measure,
    confusion_matrix,
    classification_report,
    cohen_kappa_score
)
from src.clustering import POLLUTION_ARCHETYPES, TIER_SEVERITY_ORDER

class AirQualityValidator:
    def __init__(self, df_clustered: pd.DataFrame):
        self.df = df_clustered.copy()
        self.results = {}

    def compute_clustering_agreement_metrics(self) -> dict:
        """
        Computes formal external cluster validity metrics comparing
        unsupervised cluster archetypes against empirical ground-truth classifications.
        """
        y_true = self.df["ground_truth_archetype"]
        y_pred = self.df["predicted_archetype"]

        ari = adjusted_rand_score(y_true, y_pred)
        nmi = normalized_mutual_info_score(y_true, y_pred)
        homo, comp, v_meas = homogeneity_completeness_v_measure(y_true, y_pred)

        # Ordinal mapping for Quadratic Weighted Kappa
        tier_mapping = {arch: idx for idx, arch in enumerate(POLLUTION_ARCHETYPES)}
        y_true_ord = y_true.map(tier_mapping)
        y_pred_ord = y_pred.map(tier_mapping)

        kappa = cohen_kappa_score(y_true_ord, y_pred_ord, weights="quadratic")

        self.results["agreement_metrics"] = {
            "Adjusted_Rand_Index_ARI": np.round(ari, 4),
            "Normalized_Mutual_Info_NMI": np.round(nmi, 4),
            "Homogeneity_Score": np.round(homo, 4),
            "Completeness_Score": np.round(comp, 4),
            "V_Measure_Score": np.round(v_meas, 4),
            "Quadratic_Weighted_Kappa": np.round(kappa, 4)
        }
        return self.results["agreement_metrics"]

    def generate_confusion_matrix_and_report(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Builds confusion matrix and per-archetype classification report
        evaluating alignment accuracy between satellite unsupervised clusters and ground stations.
        """
        y_true = self.df["ground_truth_archetype"]
        y_pred = self.df["predicted_archetype"]

        cm = confusion_matrix(y_true, y_pred, labels=POLLUTION_ARCHETYPES)
        cm_df = pd.DataFrame(
            cm,
            index=[f"True: {a.split(':')[1].strip()}" for a in POLLUTION_ARCHETYPES],
            columns=[f"Pred: {a.split(':')[1].strip()}" for a in POLLUTION_ARCHETYPES]
        )

        report_dict = classification_report(y_true, y_pred, output_dict=True, zero_division=0)
        report_df = pd.DataFrame(report_dict).transpose()

        self.results["confusion_matrix"] = cm_df
        self.results["classification_report"] = report_df
        return cm_df, report_df

    def conduct_airshed_capacity_stress_test(self) -> dict:
        """
        Validates whether unsupervised satellite hotspot clusters accurately distinguish
        airshed assimilative capacity deficits and carrying-capacity breaches.
        """
        # Spearman correlation between satellite pollution index and airshed capacity score
        corr, pval = spearmanr(self.df["satellite_pollution_index"], self.df["airshed_assimilative_capacity"])

        # Deficit identification recall in Red (Type 1) and Orange (Type 2) tiers
        high_severity_mask = self.df["predicted_archetype"].isin([
            "Type 1: Industrial & Power Combustion Hotspot",
            "Type 2: Dense Urban-Vehicular Smog Corridor"
        ])
        actual_deficits = self.df["airshed_deficit_flag"] == 1

        true_positives = (high_severity_mask & actual_deficits).sum()
        false_negatives = ((~high_severity_mask) & actual_deficits).sum()
        false_positives = (high_severity_mask & (~actual_deficits)).sum()

        deficit_recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        deficit_precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0

        # Mean assimilative capacity by archetype
        capacity_by_archetype = self.df.groupby("predicted_archetype")["airshed_assimilative_capacity"].agg(["mean", "std", "count"])

        stress_results = {
            "Spearman_Correlation_Pollution_vs_Capacity": np.round(corr, 4),
            "Correlation_p_value": float(pval),
            "Airshed_Deficit_Detection_Recall": np.round(deficit_recall, 4),
            "Airshed_Deficit_Detection_Precision": np.round(deficit_precision, 4),
            "Total_Airshed_Deficits_Identified": int(true_positives),
            "Total_Actual_Airshed_Deficits": int(actual_deficits.sum())
        }

        self.results["airshed_stress"] = stress_results
        self.results["capacity_by_archetype"] = capacity_by_archetype
        return stress_results

    def audit_hidden_pollution_hotspots(self) -> pd.DataFrame:
        """
        Discovers unmonitored hidden pollution hotspots where ground CAAQMS stations are absent
        (ground_station_installed == False), but satellite observations detect severe
        Type 1 (Industrial Mega-Emitter) or Type 3 (Biomass Fire Plumes) with critical deficit flags!
        """
        hidden_mask = (
            (~self.df["ground_station_installed"]) &
            (self.df["predicted_archetype"].isin([
                "Type 1: Industrial & Power Combustion Hotspot",
                "Type 3: Agricultural Biomass & Stubble Burning Plume"
            ])) &
            (self.df["airshed_deficit_flag"] == 1)
        )

        hidden_df = self.df[hidden_mask].copy()
        hidden_df = hidden_df.sort_values(by="satellite_pollution_index", ascending=False)
        self.results["hidden_hotspots"] = hidden_df
        return hidden_df

    def save_validation_reports(self, output_dir: str = "data/processed"):
        """Exports all validation metrics and audits to CSV files."""
        os.makedirs(output_dir, exist_ok=True)

        # 1. Agreement Metrics
        metrics_df = pd.DataFrame([self.results["agreement_metrics"]])
        metrics_df.to_csv(os.path.join(output_dir, "validation_agreement_metrics.csv"), index=False)

        # 2. Confusion Matrix
        self.results["confusion_matrix"].to_csv(os.path.join(output_dir, "validation_confusion_matrix.csv"))

        # 3. Classification Report
        self.results["classification_report"].to_csv(os.path.join(output_dir, "validation_classification_report.csv"))

        # 4. Hidden Hotspots Audit
        hidden_cols = [
            "cell_id", "region_name", "airshed_basin", "latitude", "longitude",
            "predicted_archetype", "predicted_risk_tier", "satellite_pollution_index",
            "so2_column_umol_m2", "no2_column_umol_m2", "aerosol_optical_depth_550",
            "fire_radiative_power_mw", "airshed_assimilative_capacity", "ground_station_installed"
        ]
        self.results["hidden_hotspots"][hidden_cols].to_csv(
            os.path.join(output_dir, "validation_hidden_hotspots.csv"),
            index=False
        )

        # 5. Airshed Capacity Statistics
        self.results["capacity_by_archetype"].to_csv(os.path.join(output_dir, "validation_airshed_capacity_stats.csv"))

        print(f"[Validation] Saved all scientific validation benchmarks to {output_dir}")

def run_validation_pipeline(
    clustered_csv_path: str = "data/processed/satellite_clustered.csv",
    output_dir: str = "data/processed"
) -> dict:
    """Executes complete validation suite and prints diagnostic summary."""
    df_clustered = pd.read_csv(clustered_csv_path)
    validator = AirQualityValidator(df_clustered)

    print("\n[Validation Stage 1/4] Computing External Cluster Validity Metrics...")
    agreement = validator.compute_clustering_agreement_metrics()
    for k, v in agreement.items():
        print(f"  - {k:32s}: {v}")

    print("\n[Validation Stage 2/4] Generating Alignment Confusion Matrix & Classification Report...")
    cm_df, report_df = validator.generate_confusion_matrix_and_report()
    print("Confusion Matrix:\n", cm_df)

    print("\n[Validation Stage 3/4] Conducting Airshed Assimilative Capacity Stress Test...")
    stress = validator.conduct_airshed_capacity_stress_test()
    for k, v in stress.items():
        print(f"  - {k:36s}: {v}")

    print("\n[Validation Stage 4/4] Auditing Satellite-Detected Hidden Pollution Hotspots...")
    hidden_df = validator.audit_hidden_pollution_hotspots()
    print(f"  - Total Hidden Hotspots Detected in Unmonitored Airsheds: {len(hidden_df)}")
    print(f"  - Top 3 Unmonitored Industrial/Biomass Hotspots:\n",
          hidden_df[["cell_id", "region_name", "predicted_archetype", "satellite_pollution_index"]].head(3).to_string(index=False))

    validator.save_validation_reports(output_dir)
    return validator.results

if __name__ == "__main__":
    run_validation_pipeline()
