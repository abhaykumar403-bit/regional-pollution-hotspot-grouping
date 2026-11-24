"""
Visualization Module for Satellite Pollution Hotspot Pattern Grouping
Generates publication-quality figures for unsupervised clustering, PCA feature manifolds,
geospatial hotspot distributions, confusion matrix validation, airshed capacity stress,
and multi-pollutant fingerprint profiles.
"""

import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from src.clustering import POLLUTION_ARCHETYPES

ARCHETYPE_COLORS = {
    "Type 1: Industrial & Power Combustion Hotspot": "#e11d48",       # Crimson Red
    "Type 2: Dense Urban-Vehicular Smog Corridor": "#f97316",         # Bright Orange
    "Type 3: Agricultural Biomass & Stubble Burning Plume": "#eab308", # Amber Yellow
    "Type 4: Clean Background & Resilient Airshed": "#10b981"         # Emerald Green
}

SHORT_NAMES = {
    "Type 1: Industrial & Power Combustion Hotspot": "Industrial/Power",
    "Type 2: Dense Urban-Vehicular Smog Corridor": "Urban Smog",
    "Type 3: Agricultural Biomass & Stubble Burning Plume": "Biomass Plume",
    "Type 4: Clean Background & Resilient Airshed": "Clean Airshed"
}

def setup_style():
    sns.set_theme(style="whitegrid", font="sans-serif")
    plt.rcParams.update({
        "font.size": 11,
        "axes.labelsize": 12,
        "axes.titlesize": 13,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "figure.titlesize": 15,
        "figure.dpi": 300
    })

def plot_optimal_k_metrics(eval_df: pd.DataFrame, output_dir: str = "reports/figures") -> str:
    """Generates dual-axis plot for Elbow Method (WCSS) and Silhouette Score."""
    setup_style()
    os.makedirs(output_dir, exist_ok=True)

    fig, ax1 = plt.subplots(figsize=(9, 5))

    color1 = "#2563eb"  # Royal blue
    ax1.set_xlabel("Number of Clusters (k)", fontweight="bold")
    ax1.set_ylabel("Inertia (Within-Cluster Sum of Squares)", color=color1, fontweight="bold")
    line1 = ax1.plot(eval_df["k"], eval_df["inertia_wcss"], marker="o", linewidth=2.5, color=color1, label="Inertia (WCSS)")
    ax1.tick_params(axis="y", labelcolor=color1)

    # Highlight optimal k=4
    ax1.axvline(x=4, color="#ef4444", linestyle="--", alpha=0.85, linewidth=1.8, label="Selected k=4 (Optimal)")

    ax2 = ax1.twinx()
    color2 = "#059669"  # Emerald green
    ax2.set_ylabel("Silhouette Score", color=color2, fontweight="bold")
    line2 = ax2.plot(eval_df["k"], eval_df["silhouette_score"], marker="s", linewidth=2.5, color=color2, label="Silhouette Score")
    ax2.tick_params(axis="y", labelcolor=color2)
    ax2.grid(False)

    lines = line1 + line2 + [ax1.get_lines()[1]]
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc="upper right", frameon=True, facecolor="#ffffff", edgecolor="#cbd5e1")

    plt.title("Evaluation of Optimal Cluster Number (k) on Satellite Observations", fontweight="bold", pad=14)
    plt.tight_layout()

    out_path = os.path.join(output_dir, "01_optimal_k_elbow_silhouette.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    return out_path

def plot_pca_cluster_space(df: pd.DataFrame, output_dir: str = "reports/figures") -> str:
    """Generates 2D PCA latent pollution space with archetypes and decision centroids."""
    setup_style()
    os.makedirs(output_dir, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 6.5))

    for arch, color in ARCHETYPE_COLORS.items():
        subset = df[df["predicted_archetype"] == arch]
        ax.scatter(
            subset["pca_1"],
            subset["pca_2"],
            c=color,
            label=f"{SHORT_NAMES[arch]} (n={len(subset)})",
            alpha=0.68,
            s=48,
            edgecolors="white",
            linewidth=0.5
        )

        # Plot centroid in PCA space
        centroid_x = subset["pca_1"].mean()
        centroid_y = subset["pca_2"].mean()
        ax.scatter(
            centroid_x, centroid_y,
            c=color, s=220, marker="X", edgecolors="black", linewidth=2.0, zorder=5
        )
        ax.annotate(
            SHORT_NAMES[arch],
            (centroid_x, centroid_y),
            textcoords="offset points",
            xytext=(8, 8),
            fontweight="bold",
            fontsize=10,
            bbox=dict(boxstyle="round,pad=0.25", fc="white", alpha=0.88, edgecolor=color)
        )

    ax.set_title("Latent Atmospheric Feature Space: PCA Projection of Satellite Clusters", fontweight="bold", pad=14)
    ax.set_xlabel("Principal Component 1 (Overall Combustion & Aerosol Mass Loading)", fontweight="bold")
    ax.set_ylabel("Principal Component 2 (Source Signature: Acidic Industrial vs Urban VOC)", fontweight="bold")
    ax.legend(title="Pollution Archetype", loc="upper left", frameon=True, facecolor="#ffffff", edgecolor="#cbd5e1")

    plt.tight_layout()
    out_path = os.path.join(output_dir, "02_pca_cluster_space.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    return out_path

def plot_geospatial_hotspots(df: pd.DataFrame, output_dir: str = "reports/figures") -> str:
    """Plots regional geospatial grid cells across Indian sub-continent airshed basins."""
    setup_style()
    os.makedirs(output_dir, exist_ok=True)

    fig, ax = plt.subplots(figsize=(11, 8.5))

    for arch, color in ARCHETYPE_COLORS.items():
        sub = df[df["predicted_archetype"] == arch]
        ax.scatter(
            sub["longitude"],
            sub["latitude"],
            c=color,
            label=SHORT_NAMES[arch],
            s=sub["satellite_pollution_index"] * 1.5 + 20,
            alpha=0.72,
            edgecolors="black",
            linewidth=0.4
        )

    # Highlight major regional centers
    major_regions = df.groupby("region_name")[["latitude", "longitude"]].mean()
    for reg_name, coords in major_regions.iterrows():
        ax.annotate(
            reg_name.split()[0],
            (coords["longitude"], coords["latitude"]),
            fontsize=8.5,
            fontweight="bold",
            color="#1e293b",
            alpha=0.85,
            bbox=dict(boxstyle="round,pad=0.2", fc="#f8fafc", ec="#94a3b8", alpha=0.7)
        )

    ax.set_title("Regional Distribution of Satellite-Derived Pollution Hotspot Archetypes", fontweight="bold", pad=14)
    ax.set_xlabel("Longitude (°E)", fontweight="bold")
    ax.set_ylabel("Latitude (°N)", fontweight="bold")
    ax.legend(title="Archetype (Bubble size ~ Pollution Index)", loc="lower right", frameon=True, facecolor="#ffffff")

    plt.tight_layout()
    out_path = os.path.join(output_dir, "03_geospatial_pollution_hotspots_map.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    return out_path

def plot_confusion_matrix(cm_csv_path: str, output_dir: str = "reports/figures") -> str:
    """Plots normalized confusion matrix heatmap comparing clusters vs CAAQMS ground truth."""
    setup_style()
    os.makedirs(output_dir, exist_ok=True)

    cm_df = pd.read_csv(cm_csv_path, index_col=0)
    cm_norm = cm_df.div(cm_df.sum(axis=1), axis=0).fillna(0)

    fig, ax = plt.subplots(figsize=(9, 7))
    sns.heatmap(
        cm_norm,
        annot=True,
        fmt=".3f",
        cmap="Blues",
        cbar_kws={"label": "Normalized Alignment Ratio"},
        linewidths=1.0,
        linecolor="#cbd5e1",
        ax=ax
    )

    ax.set_title("External Cluster Validity: Satellite Archetypes vs Ground CAAQMS Stations", fontweight="bold", pad=14)
    ax.set_xlabel("Predicted Satellite Cluster Archetype", fontweight="bold")
    ax.set_ylabel("Ground CAAQMS Authority Ground Truth", fontweight="bold")
    plt.xticks(rotation=22, ha="right", fontsize=9.5)
    plt.yticks(rotation=0, fontsize=9.5)

    plt.tight_layout()
    out_path = os.path.join(output_dir, "04_confusion_matrix_validation.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    return out_path

def plot_airshed_capacity_stress(df: pd.DataFrame, output_dir: str = "reports/figures") -> str:
    """Plots airshed carrying-capacity stress distribution across archetypes."""
    setup_style()
    os.makedirs(output_dir, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 6))

    palette = [ARCHETYPE_COLORS[a] for a in POLLUTION_ARCHETYPES]
    order = POLLUTION_ARCHETYPES

    sns.boxplot(
        x="predicted_archetype",
        y="airshed_assimilative_capacity",
        data=df,
        order=order,
        palette=palette,
        hue="predicted_archetype",
        legend=False,
        ax=ax,
        boxprops=dict(alpha=0.75),
        fliersize=3
    )

    # Threshold for critical capacity deficit
    ax.axhline(
        y=40.0,
        color="#dc2626",
        linestyle="--",
        linewidth=2.0,
        label="Critical Assimilative Capacity Threshold (< 40)"
    )

    ax.set_title("Airshed Assimilative Capacity Stress Distribution by Satellite Hotspot Archetype", fontweight="bold", pad=14)
    ax.set_xlabel("Unsupervised Pollution Archetype", fontweight="bold")
    ax.set_ylabel("Assimilative Capacity Score (0-100)", fontweight="bold")
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([SHORT_NAMES[a] for a in order], fontweight="bold")
    ax.legend(loc="upper right", frameon=True, facecolor="#ffffff", edgecolor="#cbd5e1")

    plt.tight_layout()
    out_path = os.path.join(output_dir, "05_airshed_capacity_stress_boxplot.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    return out_path

def plot_pollutant_fingerprint_profiles(df: pd.DataFrame, output_dir: str = "reports/figures") -> str:
    """Generates multi-pollutant fingerprint bar comparison across archetypes."""
    setup_style()
    os.makedirs(output_dir, exist_ok=True)

    features = [
        ("no2_column_umol_m2", "Tropospheric NO2 (µmol/m²)"),
        ("so2_column_umol_m2", "Boundary Layer SO2 (µmol/m²)"),
        ("co_column_mmol_m2", "Carbon Monoxide (mmol/m²)"),
        ("aerosol_optical_depth_550", "AOD (550 nm)"),
        ("uv_aerosol_index", "UV Aerosol Index"),
        ("fire_radiative_power_mw", "Fire Radiative Power (MW)")
    ]

    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    axes = axes.flatten()

    for idx, (feat, label) in enumerate(features):
        ax = axes[idx]
        means = df.groupby("predicted_archetype")[feat].mean()[POLLUTION_ARCHETYPES]
        stds = df.groupby("predicted_archetype")[feat].std()[POLLUTION_ARCHETYPES]

        bars = ax.bar(
            [SHORT_NAMES[a] for a in POLLUTION_ARCHETYPES],
            means,
            yerr=stds * 0.5,
            color=[ARCHETYPE_COLORS[a] for a in POLLUTION_ARCHETYPES],
            alpha=0.85,
            capsize=4,
            edgecolor="#334155"
        )
        ax.set_title(label, fontweight="bold", fontsize=11)
        ax.set_xticks(range(len(POLLUTION_ARCHETYPES)))
        ax.set_xticklabels([SHORT_NAMES[a] for a in POLLUTION_ARCHETYPES], rotation=18, ha="right", fontsize=9)
        ax.grid(axis="y", linestyle="--", alpha=0.6)

    fig.suptitle("Multi-Pollutant Fingerprint Signatures Across Satellite Pollution Archetypes", fontweight="bold", y=0.99, fontsize=15)
    plt.tight_layout()

    out_path = os.path.join(output_dir, "06_pollutant_fingerprint_radar_profiles.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    return out_path

def generate_all_visualizations(
    clustered_csv_path: str = "data/processed/satellite_clustered.csv",
    optimal_k_csv_path: str = "data/processed/optimal_k_evaluation.csv",
    confusion_matrix_csv_path: str = "data/processed/validation_confusion_matrix.csv",
    output_dir: str = "reports/figures"
) -> list[str]:
    """Generates complete suite of publication-quality figures."""
    df = pd.read_csv(clustered_csv_path)
    eval_df = pd.read_csv(optimal_k_csv_path)

    generated = []
    print("[Visualization] Generating publication-quality figures in reports/figures/...")

    p1 = plot_optimal_k_metrics(eval_df, output_dir)
    generated.append(p1)
    print(f"  [1/6] Generated: {p1}")

    p2 = plot_pca_cluster_space(df, output_dir)
    generated.append(p2)
    print(f"  [2/6] Generated: {p2}")

    p3 = plot_geospatial_hotspots(df, output_dir)
    generated.append(p3)
    print(f"  [3/6] Generated: {p3}")

    p4 = plot_confusion_matrix(confusion_matrix_csv_path, output_dir)
    generated.append(p4)
    print(f"  [4/6] Generated: {p4}")

    p5 = plot_airshed_capacity_stress(df, output_dir)
    generated.append(p5)
    print(f"  [5/6] Generated: {p5}")

    p6 = plot_pollutant_fingerprint_profiles(df, output_dir)
    generated.append(p6)
    print(f"  [6/6] Generated: {p6}")

    print(f"[Visualization] All {len(generated)} publication figures successfully compiled.")
    return generated

if __name__ == "__main__":
    generate_all_visualizations()
