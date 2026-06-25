import json
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]

HISTORICAL_DATA_PATH = PROJECT_ROOT / "data" / "val_stats.csv"
RECENT_FEATURES_PATH = PROJECT_ROOT / "outputs" / "recent_features" / "recent_features.json"
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "recent_predictions" / "performance_predictions.json"


MODEL_FEATURES = [
    "score_proxy",
    "damage_proxy",
    "kd_ratio",
    "kills_round",
    "headshot_percent",
    "win_proxy",
    "support_proxy",
    "impact_proxy",
    "entry_proxy",
    "consistency_proxy",
]


PERFORMANCE_ORDER = {
    "Bajo": 1,
    "Medio": 2,
    "Alto": 3,
    "Destacado": 4,
}


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


def prepare_historical_features(df):
    df = df.copy()

    numeric_columns = [
        "score_round",
        "damage_round",
        "kd_ratio",
        "kills_round",
        "headshot_percent",
        "win_percent",
        "kills",
        "deaths",
        "assists",
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

    df["score_proxy"] = df["score_round"]
    df["damage_proxy"] = df["damage_round"]
    df["win_proxy"] = df["win_percent"] / 100

    df["support_proxy"] = df["assists"] / (df["kills"] + 1)

    df["impact_proxy"] = (
        df["clutches"] * 0.45
        + df["aces"] * 0.35
        + df["first_bloods"] * 0.20
    )

    df["entry_proxy"] = df["first_bloods"] / (df["kills"] + 1)

    df["consistency_proxy"] = (
        df["win_proxy"] * 0.60
        + df["kd_ratio"].clip(0, 3) / 3 * 0.40
    )

    features = df[MODEL_FEATURES].copy()
    features = features.replace([np.inf, -np.inf], np.nan)

    for column in MODEL_FEATURES:
        median_value = features[column].median()
        features[column] = features[column].fillna(median_value)

    features = features.fillna(0)

    return features


def percentile_rank(series):
    return series.rank(pct=True) * 100


def create_performance_labels(features):
    score = (
        percentile_rank(features["score_proxy"]) * 0.25
        + percentile_rank(features["damage_proxy"]) * 0.20
        + percentile_rank(features["kd_ratio"]) * 0.20
        + percentile_rank(features["kills_round"]) * 0.15
        + percentile_rank(features["win_proxy"]) * 0.10
        + percentile_rank(features["impact_proxy"]) * 0.10
    )

    labels = pd.cut(
        score,
        bins=[-np.inf, 25, 60, 85, np.inf],
        labels=["Bajo", "Medio", "Alto", "Destacado"],
    )

    return labels.astype(str), score


def train_performance_model(features, labels):
    x_train, x_test, y_train, y_test = train_test_split(
        features,
        labels,
        test_size=0.25,
        random_state=42,
        stratify=labels,
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


def result_to_score(result):
    result = str(result).strip().lower()

    if result == "win":
        return 1.0

    if result == "draw":
        return 0.5

    return 0.0


def prepare_recent_match_features(recent_payload):
    matches = pd.DataFrame(recent_payload["matches"])

    if matches.empty:
        raise ValueError("No hay partidas recientes para predecir.")

    required_columns = [
        "acs",
        "adr",
        "kd_ratio",
        "kills_round",
        "headshot_percent",
        "result",
        "assists_round",
        "impact_score",
        "entry_success",
        "kast",
    ]

    for column in required_columns:
        if column not in matches.columns:
            if column == "result":
                matches[column] = "Unknown"
            else:
                matches[column] = 0.0

    features = pd.DataFrame()
    features["score_proxy"] = pd.to_numeric(matches["acs"], errors="coerce").fillna(0)
    features["damage_proxy"] = pd.to_numeric(matches["adr"], errors="coerce").fillna(0)
    features["kd_ratio"] = pd.to_numeric(matches["kd_ratio"], errors="coerce").fillna(0)
    features["kills_round"] = pd.to_numeric(matches["kills_round"], errors="coerce").fillna(0)
    features["headshot_percent"] = pd.to_numeric(matches["headshot_percent"], errors="coerce").fillna(0)
    features["win_proxy"] = matches["result"].apply(result_to_score)
    features["support_proxy"] = pd.to_numeric(matches["assists_round"], errors="coerce").fillna(0)
    features["impact_proxy"] = pd.to_numeric(matches["impact_score"], errors="coerce").fillna(0)
    features["entry_proxy"] = pd.to_numeric(matches["entry_success"], errors="coerce").fillna(0)
    features["consistency_proxy"] = pd.to_numeric(matches["kast"], errors="coerce").fillna(0) / 100

    features = features[MODEL_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)

    return matches, features


def prepare_global_recent_features(recent_payload):
    summary = recent_payload["summary"]

    total_rounds = summary.get("total_rounds", 0)
    total_kills = summary.get("total_kills", 0)
    total_assists = summary.get("total_assists", 0)

    global_features = pd.DataFrame([{
        "score_proxy": summary.get("recent_acs", 0),
        "damage_proxy": summary.get("recent_adr", 0),
        "kd_ratio": summary.get("recent_kd", 0),
        "kills_round": safe_divide(total_kills, total_rounds, default=0.0),
        "headshot_percent": summary.get("recent_hs", 0),
        "win_proxy": summary.get("winrate", 0) / 100,
        "support_proxy": safe_divide(total_assists, total_rounds, default=0.0),
        "impact_proxy": (
            summary.get("recent_tracker_score", 0) / 1000 * 0.45
            + summary.get("recent_entry_success", 0) / 100 * 0.35
            + summary.get("recent_multi_kill_rate", 0) / 100 * 0.20
        ),
        "entry_proxy": summary.get("recent_entry_success", 0) / 100,
        "consistency_proxy": summary.get("recent_kast", 0) / 100,
    }])

    return global_features[MODEL_FEATURES]


def predict_performance(model, scaler, features):
    scaled_features = scaler.transform(features)
    predictions = model.predict(scaled_features)
    probabilities = model.predict_proba(scaled_features)

    class_names = list(model.classes_)

    confidence = []

    for probability_row in probabilities:
        confidence.append(round(float(np.max(probability_row)), 4))

    return predictions, confidence, probabilities, class_names


def get_global_level_from_match_predictions(match_predictions):
    if not match_predictions:
        return "Medio"

    values = [
        PERFORMANCE_ORDER.get(prediction, 2)
        for prediction in match_predictions
    ]

    average_value = float(np.mean(values))

    if average_value >= 3.50:
        return "Destacado"

    if average_value >= 2.65:
        return "Alto"

    if average_value >= 1.75:
        return "Medio"

    return "Bajo"


def build_competitive_status(global_level, current_rank):
    current_rank = str(current_rank)

    if global_level == "Destacado":
        return f"Rendimiento claramente por encima de {current_rank}."

    if global_level == "Alto":
        return f"Rendimiento acorde o levemente por encima de {current_rank}."

    if global_level == "Medio":
        return f"Rendimiento estable para {current_rank}, con margen de mejora."

    return f"Rendimiento por debajo de lo esperado para {current_rank}."


def explain_match_performance(row, prediction):
    reasons = []

    acs = float(row.get("acs", 0))
    kd_ratio = float(row.get("kd_ratio", 0))
    adr = float(row.get("adr", 0))
    kast = float(row.get("kast", 0))
    dda = float(row.get("dda", 0))

    if acs >= 260:
        reasons.append("ACS alto")
    elif acs < 170:
        reasons.append("ACS bajo")

    if kd_ratio >= 1.30:
        reasons.append("K/D positivo")
    elif kd_ratio < 0.85:
        reasons.append("K/D bajo")

    if adr >= 160:
        reasons.append("ADR alto")
    elif adr < 115:
        reasons.append("ADR bajo")

    if kast >= 78:
        reasons.append("alta participación por ronda")
    elif kast < 65:
        reasons.append("baja participación por ronda")

    if dda > 20:
        reasons.append("DDA positivo")
    elif dda < -20:
        reasons.append("DDA negativo")

    if not reasons:
        reasons.append("métricas generales equilibradas")

    return f"Predicción {prediction}: " + ", ".join(reasons) + "."


def add_match_predictions(matches, predictions, confidence):
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
            "team_score": int(row.get("team_score", 0)),
            "enemy_score": int(row.get("enemy_score", 0)),
            "tracker_score": float(row.get("tracker_score", 0)),
            "acs": float(row.get("acs", 0)),
            "kills": int(row.get("kills", 0)),
            "deaths": int(row.get("deaths", 0)),
            "assists": int(row.get("assists", 0)),
            "kd_ratio": float(row.get("kd_ratio", 0)),
            "adr": float(row.get("adr", 0)),
            "dda": float(row.get("dda", 0)),
            "headshot_percent": float(row.get("headshot_percent", 0)),
            "kast": float(row.get("kast", 0)),
            "first_kills": int(row.get("first_kills", 0)),
            "first_deaths": int(row.get("first_deaths", 0)),
            "multi_kills": int(row.get("multi_kills", 0)),
            "performance_prediction": prediction,
            "performance_confidence": float(confidence[index]),
            "performance_explanation": explain_match_performance(row, prediction),
        }

        output_matches.append(item)

    return output_matches


def summarize_performance_predictions(match_predictions):
    counts = {}

    for prediction in match_predictions:
        prediction = str(prediction)
        counts[prediction] = counts.get(prediction, 0) + 1

    ordered_counts = {
        level: counts.get(level, 0)
        for level in ["Bajo", "Medio", "Alto", "Destacado"]
    }

    return ordered_counts


def save_predictions(payload, output_path=OUTPUT_PATH):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    return output_path


def main():
    historical_df = load_historical_data()
    historical_features = prepare_historical_features(historical_df)
    performance_labels, performance_score = create_performance_labels(historical_features)

    model, scaler, validation = train_performance_model(
        historical_features,
        performance_labels,
    )

    recent_payload = load_recent_features()
    recent_matches, recent_match_features = prepare_recent_match_features(recent_payload)

    match_predictions, match_confidence, _, _ = predict_performance(
        model,
        scaler,
        recent_match_features,
    )

    global_recent_features = prepare_global_recent_features(recent_payload)

    global_prediction_model, global_confidence, _, _ = predict_performance(
        model,
        scaler,
        global_recent_features,
    )

    match_prediction_list = [str(value) for value in match_predictions]
    global_from_matches = get_global_level_from_match_predictions(match_prediction_list)
    global_from_model = str(global_prediction_model[0])

    performance_distribution = summarize_performance_predictions(match_prediction_list)

    strong_matches = (
        performance_distribution.get("Alto", 0)
        + performance_distribution.get("Destacado", 0)
    )

    weak_matches = (
        performance_distribution.get("Bajo", 0)
        + performance_distribution.get("Medio", 0)
    )

    direct_model_confidence = float(global_confidence[0])

    if global_from_model in ["Alto", "Destacado"] and direct_model_confidence >= 0.65 and strong_matches >= weak_matches:
        final_global_level = global_from_model
    else:
        final_global_level = global_from_matches

    current_rank = recent_payload["player"].get("current_rank", "Unknown")
    competitive_status = build_competitive_status(final_global_level, current_rank)

    if performance_distribution.get("Bajo", 0) >= 5:
        competitive_status += " Presenta irregularidad por varias partidas de bajo rendimiento."

    output_payload = {
        "player": recent_payload["player"],
        "summary": recent_payload["summary"],   
        "model_validation": {
            "task": "Clasificación supervisada de nivel de rendimiento",
            "target": "performance_level",
            "features": MODEL_FEATURES,
            "accuracy": validation["accuracy"],
        },
        "global_prediction": {
            "performance_level": final_global_level,
            "performance_level_model_direct": global_from_model,
            "performance_confidence_model_direct": float(global_confidence[0]),
            "competitive_status": competitive_status,
            "performance_distribution": performance_distribution,
            "strong_matches": strong_matches,
            "weak_matches": weak_matches,
        },
        "matches": add_match_predictions(
            recent_matches,
            match_predictions,
            match_confidence,
        ),
    }

    output_path = save_predictions(output_payload)

    print("\nPredicción de rendimiento generada correctamente")
    print(f"Archivo JSON: {output_path}")

    print("\nValidación del modelo histórico:")
    print(f"  Accuracy: {validation['accuracy']}")

    print("\nPredicción global:")
    print(f"  Rendimiento global: {final_global_level}")
    print(f"  Modelo directo sobre resumen: {global_from_model}")
    print(f"  Estado competitivo: {competitive_status}")

    print("\nDistribución por partida:")
    for level, count in output_payload["global_prediction"]["performance_distribution"].items():
        print(f"  {level}: {count}")

    print("\nPrimeras partidas:")
    preview_rows = output_payload["matches"][:5]

    for row in preview_rows:
        print(
            f"  #{row['match_number']} {row['map']} | {row['agent']} | "
            f"{row['result']} | ACS {row['acs']} | "
            f"{row['kills']}/{row['deaths']}/{row['assists']} | "
            f"{row['performance_prediction']}"
        )


if __name__ == "__main__":
    main()