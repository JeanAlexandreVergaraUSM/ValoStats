import json
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, silhouette_score, davies_bouldin_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]

HISTORICAL_DATA_PATH = PROJECT_ROOT / "data" / "val_stats.csv"
RECENT_FEATURES_PATH = PROJECT_ROOT / "outputs" / "recent_features" / "recent_features.json"
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "recent_predictions" / "style_predictions.json"


STYLE_FEATURES = [
    "agresividad",
    "precision",
    "impacto",
    "soporte",
    "eficiencia",
    "entry_power",
    "consistencia",
    "kills_round",
    "assists_round",
]


STYLE_LABELS = [
    "Alto impacto",
    "Apoyo táctico",
    "Ofensivo consistente",
]


def clean_numeric_series(series):
    return (
        series.astype(str)
        .str.replace("%", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )


def to_numeric_column(df, column, default=0.0):
    if column not in df.columns:
        df[column] = default
        return df

    df[column] = clean_numeric_series(df[column])
    df[column] = pd.to_numeric(df[column], errors="coerce").fillna(default)
    return df


def safe_divide(numerator, denominator, default=0.0):
    if denominator is None or denominator == 0:
        return default

    return numerator / denominator


def load_historical_data(path=HISTORICAL_DATA_PATH):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"No existe la base histórica: {path}")

    df = pd.read_csv(path, low_memory=False)

    if df.empty:
        raise ValueError("La base histórica está vacía.")

    return df


def prepare_historical_style_features(df):
    df = df.copy()

    numeric_columns = [
        "damage_round",
        "headshot_percent",
        "kills",
        "deaths",
        "assists",
        "kd_ratio",
        "kills_round",
        "score_round",
        "win_percent",
        "clutches",
        "aces",
        "first_bloods",
        "wins",
    ]

    for column in numeric_columns:
        df = to_numeric_column(df, column, default=0.0)

    if "kd_ratio" not in df.columns or df["kd_ratio"].sum() == 0:
        df["kd_ratio"] = df["kills"] / (df["deaths"] + 1)

    if "kills_round" not in df.columns or df["kills_round"].sum() == 0:
        df["kills_round"] = df["kills"] / (df["deaths"] + df["assists"] + 1)

    df["assists_round"] = df["assists"] / (df["deaths"] + df["assists"] + 1)

    df["entry_proxy"] = df["first_bloods"] / (df["kills"] + 1)
    df["support_proxy"] = df["assists"] / (df["kills"] + 1)

    df["impact_proxy"] = (
        (df["score_round"] / 300).clip(0, 2) * 0.35
        + (df["damage_round"] / 180).clip(0, 2) * 0.25
        + df["entry_proxy"].clip(0, 1) * 0.20
        + ((df["clutches"] + df["aces"]) / (df["wins"] + 1)).clip(0, 2) * 0.20
    )

    df["agresividad"] = df["kd_ratio"]
    df["precision"] = df["headshot_percent"]
    df["impacto"] = df["impact_proxy"]
    df["soporte"] = df["support_proxy"]
    df["eficiencia"] = df["damage_round"]
    df["entry_power"] = df["entry_proxy"]
    df["consistencia"] = df["win_percent"]

    features = df[STYLE_FEATURES].copy()
    features = features.replace([np.inf, -np.inf], np.nan)

    for column in STYLE_FEATURES:
        median_value = features[column].median()
        features[column] = features[column].fillna(median_value)

    features = features.fillna(0)

    return features


def train_kmeans_profiles(features, k=3):
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(features)

    model = KMeans(
        n_clusters=k,
        random_state=42,
        n_init=10,
    )

    cluster_ids = model.fit_predict(scaled_features)

    silhouette = silhouette_score(scaled_features, cluster_ids)
    davies_bouldin = davies_bouldin_score(scaled_features, cluster_ids)

    centroids_scaled = pd.DataFrame(
        model.cluster_centers_,
        columns=STYLE_FEATURES,
    )

    centroids_original = pd.DataFrame(
        scaler.inverse_transform(model.cluster_centers_),
        columns=STYLE_FEATURES,
    )

    return model, scaler, cluster_ids, centroids_scaled, centroids_original, silhouette, davies_bouldin


def assign_cluster_names(centroids_scaled):
    centroids = centroids_scaled.copy()

    cluster_names = {}

    support_cluster = centroids["soporte"].idxmax()
    cluster_names[support_cluster] = "Apoyo táctico"

    remaining_clusters = [
        cluster_id for cluster_id in centroids.index
        if cluster_id not in cluster_names
    ]

    impact_score = (
        centroids["impacto"] * 0.35
        + centroids["entry_power"] * 0.25
        + centroids["agresividad"] * 0.25
        + centroids["kills_round"] * 0.15
    )

    remaining_impact_scores = impact_score.loc[remaining_clusters]
    impact_cluster = remaining_impact_scores.idxmax()
    cluster_names[impact_cluster] = "Alto impacto"

    for cluster_id in centroids.index:
        if cluster_id not in cluster_names:
            cluster_names[cluster_id] = "Ofensivo consistente"

    return cluster_names


def train_style_classifier(features, style_labels):
    x_train, x_test, y_train, y_test = train_test_split(
        features,
        style_labels,
        test_size=0.25,
        random_state=42,
        stratify=style_labels,
    )

    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_test_scaled = scaler.transform(x_test)

    model = RandomForestClassifier(
        n_estimators=250,
        max_depth=12,
        min_samples_leaf=4,
        random_state=42,
        class_weight="balanced",
    )

    model.fit(x_train_scaled, y_train)
    y_pred = model.predict(x_test_scaled)

    validation = {
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "classification_report": classification_report(
            y_test,
            y_pred,
            output_dict=True,
            zero_division=0,
        ),
    }

    return model, scaler, validation


def load_recent_features(path=RECENT_FEATURES_PATH):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"No existe {path}. Primero ejecuta src/recent_features.py."
        )

    with open(path, "r", encoding="utf-8") as file:
        payload = json.load(file)

    return payload


def prepare_recent_style_features(recent_payload):
    matches = pd.DataFrame(recent_payload["matches"])

    if matches.empty:
        raise ValueError("No hay partidas recientes para predecir estilo.")

    for column in STYLE_FEATURES:
        if column not in matches.columns:
            matches[column] = 0.0

    features = matches[STYLE_FEATURES].copy()
    features = features.replace([np.inf, -np.inf], np.nan)

    for column in STYLE_FEATURES:
        features[column] = pd.to_numeric(features[column], errors="coerce").fillna(0)

    return matches, features


def prepare_global_style_features(recent_payload):
    matches = pd.DataFrame(recent_payload["matches"])

    if matches.empty:
        raise ValueError("No hay partidas recientes para generar estilo global.")

    for column in STYLE_FEATURES:
        if column not in matches.columns:
            matches[column] = 0.0

    global_features = {}

    for column in STYLE_FEATURES:
        global_features[column] = float(pd.to_numeric(matches[column], errors="coerce").fillna(0).mean())

    return pd.DataFrame([global_features])[STYLE_FEATURES]


def predict_style(model, scaler, features):
    scaled_features = scaler.transform(features)
    predictions = model.predict(scaled_features)
    probabilities = model.predict_proba(scaled_features)

    confidence = []
    for row in probabilities:
        confidence.append(round(float(np.max(row)), 4))

    return predictions, confidence


def get_style_distribution(style_predictions):
    counts = {}

    for prediction in style_predictions:
        prediction = str(prediction)
        counts[prediction] = counts.get(prediction, 0) + 1

    ordered_counts = {
        label: counts.get(label, 0)
        for label in STYLE_LABELS
    }

    return ordered_counts


def get_main_and_secondary_style(style_distribution):
    sorted_styles = sorted(
        style_distribution.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    main_style = sorted_styles[0][0] if sorted_styles else "Unknown"

    secondary_style = "Unknown"
    if len(sorted_styles) > 1 and sorted_styles[1][1] > 0:
        secondary_style = sorted_styles[1][0]

    return main_style, secondary_style


def explain_style_prediction(row, prediction):
    reasons = []

    agresividad = float(row.get("agresividad", 0))
    impacto = float(row.get("impacto", 0))
    soporte = float(row.get("soporte", 0))
    entry_power = float(row.get("entry_power", 0))
    consistencia = float(row.get("consistencia", 0))
    assists = float(row.get("assists", 0))

    if prediction == "Alto impacto":
        if impacto >= 0.55:
            reasons.append("alto impacto ofensivo")
        if entry_power >= 0.05:
            reasons.append("participación en duelos iniciales")
        if agresividad >= 1.2:
            reasons.append("K/D favorable")

    elif prediction == "Apoyo táctico":
        if soporte >= 0.35:
            reasons.append("buen aporte de apoyo")
        if assists >= 6:
            reasons.append("alta cantidad de asistencias")
        if consistencia >= 75:
            reasons.append("buena participación por ronda")

    elif prediction == "Ofensivo consistente":
        if agresividad >= 1.0:
            reasons.append("rendimiento ofensivo estable")
        if consistencia >= 70:
            reasons.append("consistencia aceptable")
        if impacto >= 0.40:
            reasons.append("aporte de impacto moderado")

    if not reasons:
        reasons.append("métricas de estilo equilibradas")

    return f"Estilo {prediction}: " + ", ".join(reasons) + "."


def add_style_predictions_to_matches(matches, predictions, confidence):
    output_matches = []

    for index, row in matches.iterrows():
        prediction = str(predictions[index])

        item = {
            "match_number": int(row.get("match_number", index + 1)),
            "match_id": str(row.get("match_id", f"match_{index + 1:03d}")),
            "date": str(row.get("date", "")),
            "map": str(row.get("map", "Unknown")),
            "agent": str(row.get("agent", "Unknown")),
            "result": str(row.get("result", "Unknown")),
            "tracker_score": float(row.get("tracker_score", 0)),
            "acs": float(row.get("acs", 0)),
            "kills": int(row.get("kills", 0)),
            "deaths": int(row.get("deaths", 0)),
            "assists": int(row.get("assists", 0)),
            "kd_ratio": float(row.get("kd_ratio", 0)),
            "adr": float(row.get("adr", 0)),
            "kast": float(row.get("kast", 0)),
            "style_prediction": prediction,
            "style_confidence": float(confidence[index]),
            "style_explanation": explain_style_prediction(row, prediction),
        }

        output_matches.append(item)

    return output_matches


def save_style_predictions(payload, output_path=OUTPUT_PATH):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    return output_path


def main():
    historical_df = load_historical_data()
    historical_style_features = prepare_historical_style_features(historical_df)

    kmeans_model, kmeans_scaler, cluster_ids, centroids_scaled, centroids_original, silhouette, davies_bouldin = train_kmeans_profiles(
        historical_style_features,
        k=3,
    )

    cluster_name_map = assign_cluster_names(centroids_scaled)

    historical_style_labels = pd.Series(cluster_ids).map(cluster_name_map)

    style_classifier, style_scaler, validation = train_style_classifier(
        historical_style_features,
        historical_style_labels,
    )

    recent_payload = load_recent_features()

    recent_matches, recent_style_features = prepare_recent_style_features(recent_payload)

    match_style_predictions, match_style_confidence = predict_style(
        style_classifier,
        style_scaler,
        recent_style_features,
    )

    global_style_features = prepare_global_style_features(recent_payload)

    global_style_prediction, global_style_confidence = predict_style(
        style_classifier,
        style_scaler,
        global_style_features,
    )

    style_prediction_list = [str(value) for value in match_style_predictions]
    style_distribution = get_style_distribution(style_prediction_list)

    main_style, secondary_style = get_main_and_secondary_style(style_distribution)

    direct_global_style = str(global_style_prediction[0])

    output_payload = {
        "player": recent_payload["player"],
        "summary": recent_payload["summary"],
        "style_model": {
            "task": "Clasificación de estilo de juego",
            "target": "player_type",
            "features": STYLE_FEATURES,
            "k": 3,
            "silhouette": round(float(silhouette), 4),
            "davies_bouldin": round(float(davies_bouldin), 4),
            "classifier_accuracy": validation["accuracy"],
            "cluster_names": {
                str(cluster_id): name
                for cluster_id, name in cluster_name_map.items()
            },
        },
        "global_style_prediction": {
            "main_style": main_style,
            "secondary_style": secondary_style,
            "direct_global_style": direct_global_style,
            "direct_global_style_confidence": float(global_style_confidence[0]),
            "style_distribution": style_distribution,
        },
        "matches": add_style_predictions_to_matches(
            recent_matches,
            match_style_predictions,
            match_style_confidence,
        ),
    }

    output_path = save_style_predictions(output_payload)

    print("\nPredicción de estilo generada correctamente")
    print(f"Archivo JSON: {output_path}")

    print("\nValidación de perfiles:")
    print(f"  Silhouette: {round(float(silhouette), 4)}")
    print(f"  Davies-Bouldin: {round(float(davies_bouldin), 4)}")
    print(f"  Accuracy clasificador: {validation['accuracy']}")

    print("\nEstilo global:")
    print(f"  Estilo predominante: {main_style}")
    print(f"  Estilo secundario: {secondary_style}")
    print(f"  Modelo directo sobre resumen: {direct_global_style}")

    print("\nDistribución por partida:")
    for style, count in style_distribution.items():
        print(f"  {style}: {count}")

    print("\nPrimeras partidas:")
    for row in output_payload["matches"][:5]:
        print(
            f"  #{row['match_number']} {row['map']} | {row['agent']} | "
            f"{row['result']} | {row['style_prediction']}"
        )


if __name__ == "__main__":
    main()