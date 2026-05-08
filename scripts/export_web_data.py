import sys
import json
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.preprocessing import prepare_pipeline
from src.clustering import (
    evaluate_kmeans_range,
    train_kmeans,
    apply_pca,
    assign_player_types,
    calculate_centroid_distances,
    add_secondary_profiles,
)
from src.classification import train_random_forest
from src.recommendation import generate_recommendation, explain_profile


def main():
    raw_df, clean_df, feature_df, cluster_df, scaled_df, scaler = prepare_pipeline(
        PROJECT_ROOT / "data" / "val_stats.csv"
    )

    k_results = evaluate_kmeans_range(scaled_df, 2, 8)

    kmeans_model, clusters, clustering_metrics = train_kmeans(
        scaled_df,
        n_clusters=3
    )

    feature_df["cluster"] = clusters

    pca_model, pca_result = apply_pca(scaled_df)
    feature_df["pca_1"] = pca_result[:, 0]
    feature_df["pca_2"] = pca_result[:, 1]

    feature_df, cluster_names, cluster_summary = assign_player_types(feature_df)

    distance_df = calculate_centroid_distances(kmeans_model, scaled_df)
    feature_df = add_secondary_profiles(feature_df, distance_df, cluster_names)

    feature_df["recommendation"] = feature_df.apply(
        generate_recommendation,
        axis=1
    )

    feature_df["profile_explanation"] = feature_df.apply(
        explain_profile,
        axis=1
    )

    rf_model, X_train, X_test, y_train, y_test, y_pred, classification_metrics = train_random_forest(
        scaled_df,
        feature_df["player_type"]
    )

    # Estimación de tamaño de muestra
    safe_kills_round = feature_df["kills_round"].replace(0, np.nan)
    feature_df["estimated_rounds"] = (
        feature_df["kills"] / safe_kills_round
    ).replace([np.inf, -np.inf], np.nan)

    feature_df["estimated_rounds"] = feature_df["estimated_rounds"].fillna(0)

    # Regla de elegibilidad para ranking/tabla pública
    feature_df["eligible_for_ranking"] = (
        (feature_df["wins"] >= 20) &
        (feature_df["estimated_rounds"] >= 200)
    )

    profile_summary = feature_df.groupby("player_type")[
        [
            "agresividad",
            "precision",
            "impacto",
            "soporte",
            "eficiencia",
            "entry_power",
            "consistencia",
        ]
    ].mean().round(2)

    players = feature_df[
        [
            "name",
            "tag",
            "player_type",
            "secondary_profile",
            "profile_mix",
            "recommendation",
            "profile_explanation",
            "kills",
            "deaths",
            "assists",
            "wins",
            "kills_round",
            "estimated_rounds",
            "eligible_for_ranking",
            "kd_ratio",
            "headshot_percent",
            "win_percent",
            "score_round",
            "agresividad",
            "precision",
            "impacto",
            "soporte",
            "eficiencia",
            "entry_power",
            "consistencia",
            "pca_1",
            "pca_2",
        ]
    ].copy()

    players = players.fillna("Unknown")

    data = {
        "summary": {
            "total_players": int(len(feature_df)),
            "features_used": int(cluster_df.shape[1]),
            "profiles_detected": int(feature_df["player_type"].nunique()),
            "classification_accuracy": round(
                float(classification_metrics["accuracy"]), 4
            ),
            "silhouette": round(
                float(clustering_metrics["silhouette"]), 4
            ),
            "davies_bouldin": round(
                float(clustering_metrics["davies_bouldin"]), 4
            ),
            "eligible_players": int(feature_df["eligible_for_ranking"].sum()),
        },
        "cluster_names": cluster_names,
        "k_results": k_results.round(4).to_dict(orient="records"),
        "profile_summary": profile_summary.reset_index().to_dict(orient="records"),
        "feature_importance": classification_metrics["feature_importance"]
        .round(4)
        .to_dict(orient="records"),
        "players": players.round(4).to_dict(orient="records"),
    }

    docs_dir = PROJECT_ROOT / "docs"
    docs_dir.mkdir(exist_ok=True)

    output_path = docs_dir / "web_data.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Archivo generado correctamente: {output_path}")


if __name__ == "__main__":
    main()