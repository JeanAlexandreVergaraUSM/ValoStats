import json
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RECENT_MATCHES_CANDIDATES = [
    PROJECT_ROOT / "data" / "recent_matches.csv",
    PROJECT_ROOT / "data" / "tracker" / "data" / "recent_matches.csv",
]

RECENT_FEATURES_PATH = PROJECT_ROOT / "outputs" / "recent_features" / "recent_features.json"
PERFORMANCE_PATH = PROJECT_ROOT / "outputs" / "recent_predictions" / "performance_predictions.json"
STYLE_PATH = PROJECT_ROOT / "outputs" / "recent_predictions" / "style_predictions.json"
TREND_PATH = PROJECT_ROOT / "outputs" / "recent_predictions" / "trend_predictions.json"

REFERENCE_PROFILES_PATH = PROJECT_ROOT / "data" / "rank_reference_profiles.csv"
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "recent_predictions" / "similar_players.json"


RANK_ORDER = {
    "Iron 1": 1,
    "Iron 2": 2,
    "Iron 3": 3,
    "Bronze 1": 4,
    "Bronze 2": 5,
    "Bronze 3": 6,
    "Silver 1": 7,
    "Silver 2": 8,
    "Silver 3": 9,
    "Gold 1": 10,
    "Gold 2": 11,
    "Gold 3": 12,
    "Platinum 1": 13,
    "Platinum 2": 14,
    "Platinum 3": 15,
    "Diamond 1": 16,
    "Diamond 2": 17,
    "Diamond 3": 18,
    "Ascendant 1": 19,
    "Ascendant 2": 20,
    "Ascendant 3": 21,
    "Immortal 1": 22,
    "Immortal 2": 23,
    "Immortal 3": 24,
    "Radiant": 25,
}


RANK_GROUPS = {
    "Iron 1": "Iron",
    "Iron 2": "Iron",
    "Iron 3": "Iron",
    "Bronze 1": "Bronze",
    "Bronze 2": "Bronze",
    "Bronze 3": "Bronze",
    "Silver 1": "Silver",
    "Silver 2": "Silver",
    "Silver 3": "Silver",
    "Gold 1": "Gold",
    "Gold 2": "Gold",
    "Gold 3": "Gold",
    "Platinum 1": "Platinum",
    "Platinum 2": "Platinum",
    "Platinum 3": "Platinum",
    "Diamond 1": "Diamond",
    "Diamond 2": "Diamond",
    "Diamond 3": "Diamond",
    "Ascendant 1": "Ascendant",
    "Ascendant 2": "Ascendant",
    "Ascendant 3": "Ascendant",
    "Immortal 1": "Immortal",
    "Immortal 2": "Immortal",
    "Immortal 3": "Immortal",
    "Radiant": "Radiant",
}


SIMILARITY_FEATURES = [
    "recent_acs",
    "recent_adr",
    "recent_kd",
    "recent_kda",
    "recent_hs",
    "recent_kast",
    "winrate",
    "kills_round",
    "assists_round",
    "recent_dda",
    "recent_entry_success",
    "recent_entry_activity",
]


def load_json(path):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo requerido: {path}")

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def find_recent_matches_path():
    for candidate in RECENT_MATCHES_CANDIDATES:
        if candidate.exists():
            return candidate

    searched = "\n".join(str(path) for path in RECENT_MATCHES_CANDIDATES)

    raise FileNotFoundError(
        "No se encontró recent_matches.csv.\n"
        f"Rutas revisadas:\n{searched}"
    )


def safe_divide(numerator, denominator, default=0.0):
    if denominator is None or denominator == 0:
        return default

    return numerator / denominator


def rank_to_value(rank):
    rank = str(rank).strip()
    return RANK_ORDER.get(rank, np.nan)


def rank_to_group(rank):
    rank = str(rank).strip()
    return RANK_GROUPS.get(rank, "Unknown")


def value_to_nearest_rank(value):
    if pd.isna(value):
        return "Unknown"

    nearest_rank = min(
        RANK_ORDER.items(),
        key=lambda item: abs(item[1] - value),
    )[0]

    return nearest_rank


def load_recent_matches():
    path = find_recent_matches_path()
    df = pd.read_csv(path)

    if df.empty:
        raise ValueError("recent_matches.csv está vacío.")

    if "avg_team_rank" not in df.columns:
        df["avg_team_rank"] = "Unknown"

    df["avg_team_rank"] = df["avg_team_rank"].fillna("Unknown").astype(str)
    df["avg_team_rank_value"] = df["avg_team_rank"].apply(rank_to_value)
    df["avg_team_rank_group"] = df["avg_team_rank"].apply(rank_to_group)

    return df


def get_target_rank_context(recent_matches):
    valid_values = recent_matches["avg_team_rank_value"].dropna()

    if valid_values.empty:
        return {
            "avg_team_rank_mean_value": np.nan,
            "avg_team_rank_nearest": "Unknown",
            "avg_team_rank_group": "Unknown",
            "rank_values_available": 0,
        }

    mean_value = float(valid_values.mean())
    nearest_rank = value_to_nearest_rank(mean_value)
    rank_group = rank_to_group(nearest_rank)

    return {
        "avg_team_rank_mean_value": round(mean_value, 3),
        "avg_team_rank_nearest": nearest_rank,
        "avg_team_rank_group": rank_group,
        "rank_values_available": int(len(valid_values)),
    }


def load_reference_profiles(path=REFERENCE_PROFILES_PATH):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"No existe {path}. Primero ejecuta src/rank_reference_features.py."
        )

    df = pd.read_csv(path)

    if df.empty:
        raise ValueError("rank_reference_profiles.csv está vacío.")

    for column in [
        "matches_analyzed",
        "avg_team_rank_mean_value",
        "winrate",
        "total_kills",
        "total_deaths",
        "total_assists",
        "total_rounds",
        "recent_kd",
        "recent_kda",
        "recent_acs",
        "recent_tracker_score",
        "recent_adr",
        "recent_dda",
        "recent_hs",
        "recent_kast",
        "recent_entry_success",
        "recent_entry_activity",
        "recent_multi_kill_rate",
        "acs_std",
        "trs_std",
    ]:
        if column not in df.columns:
            df[column] = 0

        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

    if "avg_team_rank_group" not in df.columns:
        df["avg_team_rank_group"] = "Unknown"

    df["kills_round"] = df.apply(
        lambda row: safe_divide(row["total_kills"], row["total_rounds"]),
        axis=1,
    )

    df["assists_round"] = df.apply(
        lambda row: safe_divide(row["total_assists"], row["total_rounds"]),
        axis=1,
    )

    return df


def prepare_recent_vector(recent_payload):
    summary = recent_payload["summary"]

    total_kills = summary.get("total_kills", 0)
    total_assists = summary.get("total_assists", 0)
    total_rounds = summary.get("total_rounds", 0)

    vector = pd.DataFrame([{
        "recent_acs": summary.get("recent_acs", 0),
        "recent_adr": summary.get("recent_adr", 0),
        "recent_kd": summary.get("recent_kd", 0),
        "recent_kda": summary.get("recent_kda", 0),
        "recent_hs": summary.get("recent_hs", 0),
        "recent_kast": summary.get("recent_kast", 0),
        "winrate": summary.get("winrate", 0),
        "kills_round": safe_divide(total_kills, total_rounds),
        "assists_round": safe_divide(total_assists, total_rounds),
        "recent_dda": summary.get("recent_dda", 0),
        "recent_entry_success": summary.get("recent_entry_success", 0),
        "recent_entry_activity": summary.get("recent_entry_activity", 0),
        "recent_multi_kill_rate": summary.get("recent_multi_kill_rate", 0),
    }])

    return vector[SIMILARITY_FEATURES]


def prepare_reference_features(reference_profiles):
    features = reference_profiles[SIMILARITY_FEATURES].copy()
    features = features.replace([np.inf, -np.inf], np.nan)

    for column in SIMILARITY_FEATURES:
        features[column] = pd.to_numeric(features[column], errors="coerce")
        features[column] = features[column].fillna(features[column].median())

    features = features.fillna(0)

    return features


def filter_reference_by_rank(reference_profiles, target_rank_context):
    target_group = target_rank_context["avg_team_rank_group"]
    target_value = target_rank_context["avg_team_rank_mean_value"]

    if target_group != "Unknown":
        same_group = reference_profiles[
            reference_profiles["avg_team_rank_group"] == target_group
        ].copy()
    else:
        same_group = pd.DataFrame()

    if len(same_group) >= 3:
        return same_group, {
            "filter_type": "same_rank_group",
            "target_group": target_group,
            "players_available": int(len(same_group)),
            "message": f"Se comparó contra jugadores con media de lobby {target_group}.",
        }

    if not pd.isna(target_value):
        reference_profiles = reference_profiles.copy()
        reference_profiles["rank_distance"] = (
            reference_profiles["avg_team_rank_mean_value"] - target_value
        ).abs()

        nearby = reference_profiles[
            reference_profiles["rank_distance"] <= 3
        ].copy()

        if len(nearby) >= 3:
            return nearby, {
                "filter_type": "nearby_rank_value",
                "target_group": target_group,
                "players_available": int(len(nearby)),
                "message": "No había suficientes jugadores del mismo grupo, se usaron lobbies cercanos.",
            }

    return reference_profiles.copy(), {
        "filter_type": "all_reference_players",
        "target_group": target_group,
        "players_available": int(len(reference_profiles)),
        "message": "No había suficientes jugadores por rango, se usó toda la base de referencia.",
    }


def fit_nearest_neighbors(reference_features, n_neighbors):
    scaler = StandardScaler()
    reference_scaled = scaler.fit_transform(reference_features)

    model = NearestNeighbors(
        n_neighbors=n_neighbors,
        metric="cosine",
    )

    model.fit(reference_scaled)

    return model, scaler


def build_similar_players(filtered_profiles, indices, distances):
    similar_players = []

    for position, (index, distance) in enumerate(zip(indices, distances), start=1):
        row = filtered_profiles.iloc[index]
        similarity = max(0.0, 1.0 - float(distance)) * 100

        item = {
            "rank": position,
            "reference_riot_id": str(row.get("reference_riot_id", "Unknown")),
            "matches_analyzed": int(row.get("matches_analyzed", 0)),
            "current_rank_mode": str(row.get("current_rank_mode", "Unknown")),
            "avg_team_rank_nearest": str(row.get("avg_team_rank_nearest", "Unknown")),
            "avg_team_rank_group": str(row.get("avg_team_rank_group", "Unknown")),
            "similarity": round(similarity, 2),
            "winrate": round(float(row.get("winrate", 0)), 2),
            "recent_kd": round(float(row.get("recent_kd", 0)), 3),
            "recent_kda": round(float(row.get("recent_kda", 0)), 3),
            "recent_acs": round(float(row.get("recent_acs", 0)), 2),
            "recent_tracker_score": round(float(row.get("recent_tracker_score", 0)), 2),
            "recent_adr": round(float(row.get("recent_adr", 0)), 2),
            "recent_dda": round(float(row.get("recent_dda", 0)), 2),
            "recent_hs": round(float(row.get("recent_hs", 0)), 2),
            "recent_kast": round(float(row.get("recent_kast", 0)), 2),
            "recent_entry_success": round(float(row.get("recent_entry_success", 0)), 2),
            "recent_entry_activity": round(float(row.get("recent_entry_activity", 0)), 2),
            "recent_multi_kill_rate": round(float(row.get("recent_multi_kill_rate", 0)), 2),
            "main_agent": str(row.get("main_agent", "Unknown")),
            "main_map": str(row.get("main_map", "Unknown")),
        }

        similar_players.append(item)

    return similar_players


def summarize_similar_group(similar_players):
    if not similar_players:
        return {}

    df = pd.DataFrame(similar_players)

    summary = {
        "players_compared": int(len(df)),
        "avg_similarity": round(float(df["similarity"].mean()), 2),
        "avg_winrate": round(float(df["winrate"].mean()), 2),
        "avg_kd": round(float(df["recent_kd"].mean()), 3),
        "avg_kda": round(float(df["recent_kda"].mean()), 3),
        "avg_acs": round(float(df["recent_acs"].mean()), 2),
        "avg_tracker_score": round(float(df["recent_tracker_score"].mean()), 2),
        "avg_adr": round(float(df["recent_adr"].mean()), 2),
        "avg_dda": round(float(df["recent_dda"].mean()), 2),
        "avg_hs": round(float(df["recent_hs"].mean()), 2),
        "avg_kast": round(float(df["recent_kast"].mean()), 2),
        "avg_entry_success": round(float(df["recent_entry_success"].mean()), 2),
        "avg_entry_activity": round(float(df["recent_entry_activity"].mean()), 2),
        "avg_multi_kill_rate": round(float(df["recent_multi_kill_rate"].mean()), 2),
    }

    rank_group_distribution = df["avg_team_rank_group"].value_counts().to_dict()

    summary["rank_group_distribution"] = {
        str(key): int(value)
        for key, value in rank_group_distribution.items()
    }

    return summary


def build_gap_analysis(recent_payload, similar_summary):
    summary = recent_payload["summary"]

    gaps = {
        "winrate_gap": round(summary.get("winrate", 0) - similar_summary.get("avg_winrate", 0), 2),
        "kd_gap": round(summary.get("recent_kd", 0) - similar_summary.get("avg_kd", 0), 3),
        "acs_gap": round(summary.get("recent_acs", 0) - similar_summary.get("avg_acs", 0), 2),
        "trs_gap": round(summary.get("recent_tracker_score", 0) - similar_summary.get("avg_tracker_score", 0), 2),
        "adr_gap": round(summary.get("recent_adr", 0) - similar_summary.get("avg_adr", 0), 2),
        "dda_gap": round(summary.get("recent_dda", 0) - similar_summary.get("avg_dda", 0), 2),
        "hs_gap": round(summary.get("recent_hs", 0) - similar_summary.get("avg_hs", 0), 2),
        "kast_gap": round(summary.get("recent_kast", 0) - similar_summary.get("avg_kast", 0), 2),
        "entry_success_gap": round(
            summary.get("recent_entry_success", 0)
            - similar_summary.get("avg_entry_success", 0),
            2,
        ),
    }

    return gaps


def build_recommendations(gaps, performance_payload, style_payload, trend_payload):
    recommendations = []

    performance_level = performance_payload["global_prediction"].get("performance_level", "Unknown")
    main_style = style_payload["global_style_prediction"].get("main_style", "Unknown")
    secondary_style = style_payload["global_style_prediction"].get("secondary_style", "Unknown")
    trend_status = trend_payload["global_trend_prediction"].get("trend_status", "Unknown")

    if gaps["acs_gap"] > 15:
        recommendations.append(
            "Tu ACS está por encima del grupo de referencia del mismo rango de lobby; tu impacto de combate reciente es una fortaleza."
        )
    elif gaps["acs_gap"] < -15:
        recommendations.append(
            "Tu ACS está por debajo del grupo de referencia; conviene mejorar daño efectivo e impacto por ronda."
        )

    if gaps["kd_gap"] > 0.15:
        recommendations.append(
            "Tu K/D supera al grupo similar; estás ganando más duelos que jugadores con lobbies parecidos."
        )
    elif gaps["kd_gap"] < -0.15:
        recommendations.append(
            "Tu K/D está por debajo del grupo similar; intenta reducir muertes innecesarias y tomar duelos con más ventaja."
        )

    if gaps["kast_gap"] > 4:
        recommendations.append(
            "Tu KAST está sobre el grupo similar; participas bien en las rondas incluso cuando no siempre consigues kills."
        )
    elif gaps["kast_gap"] < -4:
        recommendations.append(
            "Tu KAST está bajo frente al grupo similar; deberías buscar más participación en rondas mediante trades, utilidad o supervivencia."
        )

    if gaps["entry_success_gap"] > 5:
        recommendations.append(
            "Tu entry success está por encima del grupo similar; tus duelos iniciales están aportando valor."
        )
    elif gaps["entry_success_gap"] < -5:
        recommendations.append(
            "Tu entry success está bajo frente al grupo similar; conviene revisar primeros duelos y evitar entregar first deaths."
        )

    if main_style == "Alto impacto":
        recommendations.append(
            f"Tu estilo principal es {main_style}; aprovecha esa fortaleza, pero controla la agresividad para no perder consistencia."
        )
    elif main_style == "Apoyo táctico":
        recommendations.append(
            f"Tu estilo principal es {main_style}; mantén utilidad y asistencias, pero busca convertir más rondas en impacto directo."
        )
    elif main_style == "Ofensivo consistente":
        recommendations.append(
            f"Tu estilo principal es {main_style}; mantén la estabilidad y busca transformar partidas medias en partidas altas."
        )

    if secondary_style != "Unknown":
        recommendations.append(
            f"También aparece como estilo secundario {secondary_style}, por lo que tu perfil reciente no es único y mezcla más de una forma de juego."
        )

    if trend_status == "Subida probable":
        recommendations.append(
            "La tendencia reciente indica subida probable si mantienes el nivel mostrado en las últimas partidas."
        )
    elif trend_status == "Progreso positivo":
        recommendations.append(
            "La tendencia es positiva; el foco debería estar en sostener rendimiento y reducir partidas bajas."
        )
    elif trend_status == "Riesgo de bajar":
        recommendations.append(
            "La tendencia muestra riesgo competitivo; conviene estabilizar ACS, K/D y KAST antes de jugar más volumen."
        )

    if performance_level == "Alto":
        recommendations.append(
            "El rendimiento global se clasifica como alto, pero se debe vigilar la irregularidad entre partidas."
        )
    elif performance_level == "Destacado":
        recommendations.append(
            "El rendimiento global se clasifica como destacado frente al espacio aprendido por el modelo."
        )

    if not recommendations:
        recommendations.append(
            "El jugador está cerca del grupo similar; la recomendación principal es mantener consistencia y revisar las partidas negativas."
        )

    return recommendations


def main():
    recent_payload = load_json(RECENT_FEATURES_PATH)
    performance_payload = load_json(PERFORMANCE_PATH)
    style_payload = load_json(STYLE_PATH)
    trend_payload = load_json(TREND_PATH)

    recent_matches = load_recent_matches()
    target_rank_context = get_target_rank_context(recent_matches)

    reference_profiles = load_reference_profiles()

    filtered_profiles, filter_info = filter_reference_by_rank(
        reference_profiles,
        target_rank_context,
    )

    reference_features = prepare_reference_features(filtered_profiles)
    recent_vector = prepare_recent_vector(recent_payload)

    n_neighbors = min(10, len(filtered_profiles))

    if n_neighbors == 0:
        raise ValueError("No hay jugadores de referencia disponibles para comparar.")

    model, scaler = fit_nearest_neighbors(reference_features, n_neighbors)

    reference_scaled = scaler.transform(reference_features)
    recent_scaled = scaler.transform(recent_vector)

    distances, indices = model.kneighbors(recent_scaled, n_neighbors=n_neighbors)

    similar_players = build_similar_players(
        filtered_profiles.reset_index(drop=True),
        indices[0],
        distances[0],
    )

    similar_group_summary = summarize_similar_group(similar_players)
    gap_analysis = build_gap_analysis(recent_payload, similar_group_summary)

    recommendations = build_recommendations(
        gap_analysis,
        performance_payload,
        style_payload,
        trend_payload,
    )

    output_payload = {
        "player": recent_payload["player"],
        "summary": recent_payload["summary"],
        "similarity_model": {
            "task": "Búsqueda de jugadores similares por rango de lobby",
            "method": "NearestNeighbors con similitud coseno",
            "features": SIMILARITY_FEATURES,
            "reference_source": "data/rank_reference_profiles.csv",
            "neighbors": n_neighbors,
        },
        "rank_context": {
            "target_avg_team_rank_mean_value": target_rank_context["avg_team_rank_mean_value"],
            "target_avg_team_rank_nearest": target_rank_context["avg_team_rank_nearest"],
            "target_avg_team_rank_group": target_rank_context["avg_team_rank_group"],
            "rank_values_available": target_rank_context["rank_values_available"],
            "filter_info": filter_info,
        },
        "global_context": {
            "performance_level": performance_payload["global_prediction"].get("performance_level", "Unknown"),
            "competitive_status": performance_payload["global_prediction"].get("competitive_status", "Unknown"),
            "main_style": style_payload["global_style_prediction"].get("main_style", "Unknown"),
            "secondary_style": style_payload["global_style_prediction"].get("secondary_style", "Unknown"),
            "trend_status": trend_payload["global_trend_prediction"].get("trend_status", "Unknown"),
        },
        "similar_group_summary": similar_group_summary,
        "gap_analysis": gap_analysis,
        "similar_players": similar_players,
        "recommendations": recommendations,
        "limitations": [
            "La base de referencia corresponde a una muestra limitada de jugadores.",
            "La comparación se realiza por estadísticas recientes agregadas y grupo de rango promedio de partida.",
            "En una versión de mayor escala, la base puede ampliarse con más jugadores y más partidas por rango."
        ],
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
        json.dump(output_payload, file, ensure_ascii=False, indent=2)

    print("\n Jugadores similares por rango generados correctamente")
    print(f" Archivo JSON: {OUTPUT_PATH}")

    print("\nContexto de rango del jugador objetivo:")
    print(f"  Media numérica de lobby: {target_rank_context['avg_team_rank_mean_value']}")
    print(f"  Rango promedio aproximado: {target_rank_context['avg_team_rank_nearest']}")
    print(f"  Grupo de rango: {target_rank_context['avg_team_rank_group']}")
    print(f"  Filtro usado: {filter_info['filter_type']}")
    print(f"  Jugadores disponibles en filtro: {filter_info['players_available']}")

    print("\nContexto global:")
    print(f"  Rendimiento: {output_payload['global_context']['performance_level']}")
    print(f"  Estilo principal: {output_payload['global_context']['main_style']}")
    print(f"  Tendencia: {output_payload['global_context']['trend_status']}")

    print("\nPromedio del grupo similar:")
    for key, value in similar_group_summary.items():
        if key != "rank_group_distribution":
            print(f"  {key}: {value}")

    print("\nBrechas del jugador vs grupo similar:")
    for key, value in gap_analysis.items():
        print(f"  {key}: {value}")

    print("\nTop similares:")
    for player in similar_players[:5]:
        print(
            f"  #{player['rank']} {player['reference_riot_id']} | "
            f"Lobby {player['avg_team_rank_nearest']} | "
            f"Similitud {player['similarity']}% | "
            f"K/D {player['recent_kd']} | ACS {player['recent_acs']} | "
            f"Winrate {player['winrate']}%"
        )

    print("\nRecomendaciones:")
    for recommendation in recommendations:
        print(f"  - {recommendation}")


if __name__ == "__main__":
    main()