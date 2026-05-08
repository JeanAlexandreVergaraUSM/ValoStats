import numpy as np
import pandas as pd

from sklearn.cluster import KMeans, AgglomerativeClustering, DBSCAN
from sklearn.metrics import silhouette_score, davies_bouldin_score
from sklearn.decomposition import PCA


def evaluate_kmeans_range(scaled_df, k_min=2, k_max=8, random_state=42):
    results = []

    for k in range(k_min, k_max + 1):
        model = KMeans(
            n_clusters=k,
            random_state=random_state,
            n_init=10
        )

        labels = model.fit_predict(scaled_df)

        results.append({
            "k": k,
            "silhouette": silhouette_score(scaled_df, labels),
            "davies_bouldin": davies_bouldin_score(scaled_df, labels),
            "inertia": model.inertia_
        })

    return pd.DataFrame(results)


def compare_clustering_algorithms(scaled_df, n_clusters=3, random_state=42):
    algorithms = {
        "KMeans": KMeans(
            n_clusters=n_clusters,
            random_state=random_state,
            n_init=10
        ),
        "Agglomerative": AgglomerativeClustering(
            n_clusters=n_clusters
        ),
        "DBSCAN": DBSCAN(
            eps=1.5,
            min_samples=10
        )
    }

    results = []

    for name, model in algorithms.items():
        labels = model.fit_predict(scaled_df)

        valid_labels = set(labels)

        if len(valid_labels) <= 1:
            results.append({
                "algorithm": name,
                "silhouette": None,
                "davies_bouldin": None,
                "n_clusters_detected": len(valid_labels)
            })
            continue

        results.append({
            "algorithm": name,
            "silhouette": silhouette_score(scaled_df, labels),
            "davies_bouldin": davies_bouldin_score(scaled_df, labels),
            "n_clusters_detected": len(valid_labels)
        })

    return pd.DataFrame(results)


def train_kmeans(scaled_df, n_clusters=3, random_state=42):
    model = KMeans(
        n_clusters=n_clusters,
        random_state=random_state,
        n_init=10
    )

    labels = model.fit_predict(scaled_df)

    metrics = {
        "silhouette": silhouette_score(scaled_df, labels),
        "davies_bouldin": davies_bouldin_score(scaled_df, labels),
        "inertia": model.inertia_
    }

    return model, labels, metrics


def apply_pca(scaled_df, n_components=2):
    pca = PCA(n_components=n_components)
    pca_result = pca.fit_transform(scaled_df)

    return pca, pca_result


def build_cluster_summary(feature_df, group_col="player_type"):
    summary = feature_df.groupby(group_col)[[
        "agresividad",
        "precision",
        "impacto",
        "soporte",
        "eficiencia",
        "entry_power",
        "consistencia",
        "kills_round",
        "win_percent",
        "score_round"
    ]].mean()

    return summary


def assign_player_types(feature_df):
    summary = feature_df.groupby("cluster")[[
        "agresividad",
        "precision",
        "impacto",
        "soporte",
        "eficiencia",
        "entry_power",
        "consistencia"
    ]].mean()

    support_cluster = summary["soporte"].idxmax()
    impact_cluster = summary["impacto"].idxmax()

    remaining_clusters = [
        cluster for cluster in summary.index
        if cluster not in [support_cluster, impact_cluster]
    ]

    if remaining_clusters:
        offensive_consistent_cluster = (
            summary.loc[remaining_clusters][["eficiencia", "consistencia"]]
            .mean(axis=1)
            .idxmax()
        )
    else:
        offensive_consistent_cluster = (
            summary[["eficiencia", "consistencia"]]
            .mean(axis=1)
            .idxmax()
        )

    cluster_names = {}

    for cluster in summary.index:
        if cluster == offensive_consistent_cluster:
            cluster_names[cluster] = "Ofensivo consistente"
        elif cluster == support_cluster:
            cluster_names[cluster] = "Apoyo táctico"
        elif cluster == impact_cluster:
            cluster_names[cluster] = "Alto impacto"
        else:
            cluster_names[cluster] = "Balanceado"

    feature_df = feature_df.copy()
    feature_df["player_type"] = feature_df["cluster"].map(cluster_names)

    return feature_df, cluster_names, summary


def calculate_centroid_distances(kmeans_model, scaled_df):
    distances = kmeans_model.transform(scaled_df)

    distance_df = pd.DataFrame(
        distances,
        index=scaled_df.index,
        columns=[
            f"distance_cluster_{i}"
            for i in range(distances.shape[1])
        ]
    )

    return distance_df


def add_secondary_profiles(feature_df, distance_df, cluster_names):
    feature_df = feature_df.copy()

    ordered_clusters = np.argsort(distance_df.values, axis=1)

    primary_clusters = ordered_clusters[:, 0]
    secondary_clusters = ordered_clusters[:, 1]

    feature_df["primary_cluster"] = primary_clusters
    feature_df["secondary_cluster"] = secondary_clusters

    feature_df["secondary_profile"] = feature_df["secondary_cluster"].map(cluster_names)
    feature_df["profile_mix"] = (
        feature_df["player_type"] +
        " / " +
        feature_df["secondary_profile"]
    )

    return feature_df