import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

PERFORMANCE_PATH = PROJECT_ROOT / "outputs" / "recent_predictions" / "performance_predictions.json"
STYLE_PATH = PROJECT_ROOT / "outputs" / "recent_predictions" / "style_predictions.json"
TREND_PATH = PROJECT_ROOT / "outputs" / "recent_predictions" / "trend_predictions.json"
SIMILAR_PLAYERS_PATH = PROJECT_ROOT / "outputs" / "recent_predictions" / "similar_players.json"

OUTPUT_PATH = PROJECT_ROOT / "outputs" / "recent_predictions" / "final_player_analysis.json"

# Copia pensada para la web estática o para pruebas visuales.
DOCS_OUTPUT_PATH = PROJECT_ROOT / "docs" / "final_player_analysis.json"


def load_json(path):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo requerido: {path}")

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json(payload, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    return path


def get_match_map(payload):
    matches = payload.get("matches", [])

    match_map = {}

    for match in matches:
        match_number = int(match.get("match_number", 0))

        if match_number > 0:
            match_map[match_number] = match

    return match_map


def merge_match_predictions(performance_payload, style_payload, trend_payload):
    performance_matches = performance_payload.get("matches", [])
    style_map = get_match_map(style_payload)
    trend_map = get_match_map(trend_payload)

    merged_matches = []

    for performance_match in performance_matches:
        match_number = int(performance_match.get("match_number", 0))

        style_match = style_map.get(match_number, {})
        trend_match = trend_map.get(match_number, {})

        merged_match = {
            "match_number": match_number,
            "match_id": performance_match.get("match_id", ""),
            "date": performance_match.get("date", ""),
            "map": performance_match.get("map", "Unknown"),
            "agent": performance_match.get("agent", "Unknown"),
            "result": performance_match.get("result", "Unknown"),
            "team_score": performance_match.get("team_score", 0),
            "enemy_score": performance_match.get("enemy_score", 0),

            "tracker_score": performance_match.get("tracker_score", 0),
            "acs": performance_match.get("acs", 0),
            "kills": performance_match.get("kills", 0),
            "deaths": performance_match.get("deaths", 0),
            "assists": performance_match.get("assists", 0),
            "kd_ratio": performance_match.get("kd_ratio", 0),
            "adr": performance_match.get("adr", 0),
            "dda": performance_match.get("dda", 0),
            "headshot_percent": performance_match.get("headshot_percent", 0),
            "kast": performance_match.get("kast", 0),
            "first_kills": performance_match.get("first_kills", 0),
            "first_deaths": performance_match.get("first_deaths", 0),
            "multi_kills": performance_match.get("multi_kills", 0),

            "performance_prediction": performance_match.get("performance_prediction", "Unknown"),
            "performance_confidence": performance_match.get("performance_confidence", 0),
            "performance_explanation": performance_match.get("performance_explanation", ""),

            "style_prediction": style_match.get("style_prediction", "Unknown"),
            "style_confidence": style_match.get("style_confidence", 0),
            "style_explanation": style_match.get("style_explanation", ""),

            "trend_score": trend_match.get("trend_score", 0),
            "trend_signal": trend_match.get("trend_signal", "Unknown"),
            "trend_explanation": trend_match.get("trend_explanation", ""),
        }

        merged_matches.append(merged_match)

    return merged_matches


def build_prediction_summary(performance_payload, style_payload, trend_payload, similar_players_payload):
    performance_global = performance_payload.get("global_prediction", {})
    style_global = style_payload.get("global_style_prediction", {})
    trend_global = trend_payload.get("global_trend_prediction", {})
    global_context = similar_players_payload.get("global_context", {})

    prediction_summary = {
        "performance_level": performance_global.get("performance_level", "Unknown"),
        "competitive_status": performance_global.get("competitive_status", "Unknown"),
        "performance_distribution": performance_global.get("performance_distribution", {}),
        "strong_matches": performance_global.get("strong_matches", 0),
        "weak_matches": performance_global.get("weak_matches", 0),

        "main_style": style_global.get("main_style", global_context.get("main_style", "Unknown")),
        "secondary_style": style_global.get("secondary_style", global_context.get("secondary_style", "Unknown")),
        "direct_global_style": style_global.get("direct_global_style", "Unknown"),
        "style_distribution": style_global.get("style_distribution", {}),

        "trend_status": trend_global.get("trend_status", global_context.get("trend_status", "Unknown")),
        "trend_numeric_score": trend_global.get("trend_numeric_score", 0),
        "trend_explanation": trend_global.get("trend_explanation", ""),
        "trend_distribution": trend_global.get("trend_distribution", {}),
    }

    return prediction_summary


def build_methodology_summary(performance_payload, style_payload, trend_payload, similar_players_payload):
    methodology = {
        "problem": (
            "Predecir el rendimiento reciente, el estilo de juego y la tendencia competitiva "
            "de un jugador de Valorant a partir de sus últimas partidas competitivas."
        ),
        "input": (
            "Riot ID del jugador. El sistema obtiene sus últimas partidas competitivas "
            "desde Tracker.gg y calcula métricas por partida."
        ),
        "main_variables": [
            "TRS",
            "ACS",
            "K/D",
            "ADR",
            "DDA",
            "HS%",
            "KAST",
            "FK",
            "FD",
            "MK",
            "resultado",
            "rondas jugadas",
            "entry success",
        ],
        "tasks": [
            {
                "task": "Clasificación de rendimiento por partida",
                "target": "performance_level",
                "output": ["Bajo", "Medio", "Alto", "Destacado"],
                "model_info": performance_payload.get("model_validation", {}),
            },
            {
                "task": "Clasificación de estilo de juego por partida y global",
                "target": "player_type",
                "output": ["Alto impacto", "Apoyo táctico", "Ofensivo consistente"],
                "model_info": style_payload.get("style_model", {}),
            },
            {
                "task": "Estimación de tendencia competitiva reciente",
                "target": "trend_status",
                "output": ["Riesgo de bajar", "Estable", "Progreso positivo", "Subida probable"],
                "model_info": trend_payload.get("trend_model", {}),
            },
            {
                "task": "Búsqueda de referentes similares",
                "target": "similar_players",
                "output": "Jugadores de referencia con media de lobby parecida",
                "model_info": similar_players_payload.get("similarity_model", {}),
            },
        ],
        "rank_reference_logic": (
            "El jugador objetivo se compara contra jugadores de referencia filtrados por "
            "la media del rango promedio de sus partidas. Esto evita comparar directamente "
            "contra jugadores de contextos competitivos muy distintos."
        ),
        "limitations": similar_players_payload.get("limitations", []),
    }

    return methodology


def build_final_payload():
    performance_payload = load_json(PERFORMANCE_PATH)
    style_payload = load_json(STYLE_PATH)
    trend_payload = load_json(TREND_PATH)
    similar_players_payload = load_json(SIMILAR_PLAYERS_PATH)

    merged_matches = merge_match_predictions(
        performance_payload,
        style_payload,
        trend_payload,
    )

    prediction_summary = build_prediction_summary(
        performance_payload,
        style_payload,
        trend_payload,
        similar_players_payload,
    )

    methodology = build_methodology_summary(
        performance_payload,
        style_payload,
        trend_payload,
        similar_players_payload,
    )

    final_payload = {
        "player": performance_payload.get("player", {}),
        "summary": performance_payload.get("summary", {}),
        "prediction_summary": prediction_summary,
        "temporal_evolution": trend_payload.get("global_trend_prediction", {}),
        "rank_context": similar_players_payload.get("rank_context", {}),
        "similar_group_summary": similar_players_payload.get("similar_group_summary", {}),
        "gap_analysis": similar_players_payload.get("gap_analysis", {}),
        "similar_players": similar_players_payload.get("similar_players", []),
        "recommendations": similar_players_payload.get("recommendations", []),
        "matches": merged_matches,
        "methodology": methodology,
        "source_files": {
            "performance": str(PERFORMANCE_PATH.relative_to(PROJECT_ROOT)),
            "style": str(STYLE_PATH.relative_to(PROJECT_ROOT)),
            "trend": str(TREND_PATH.relative_to(PROJECT_ROOT)),
            "similar_players": str(SIMILAR_PLAYERS_PATH.relative_to(PROJECT_ROOT)),
        },
    }

    return final_payload


def print_preview(payload):
    player = payload.get("player", {})
    summary = payload.get("summary", {})
    prediction = payload.get("prediction_summary", {})
    rank_context = payload.get("rank_context", {})
    gap_analysis = payload.get("gap_analysis", {})
    similar_players = payload.get("similar_players", [])
    recommendations = payload.get("recommendations", [])

    print("\nAnálisis final unificado generado correctamente")

    print("\nJugador:")
    print(f"  Riot ID: {player.get('riot_id', 'Unknown')}")
    print(f"  Rango actual: {player.get('current_rank', 'Unknown')}")
    print(f"  Partidas analizadas: {summary.get('matches_analyzed', 0)}")

    print("\nPredicción global:")
    print(f"  Rendimiento: {prediction.get('performance_level', 'Unknown')}")
    print(f"  Estilo principal: {prediction.get('main_style', 'Unknown')}")
    print(f"  Estilo secundario: {prediction.get('secondary_style', 'Unknown')}")
    print(f"  Tendencia: {prediction.get('trend_status', 'Unknown')}")
    print(f"  Estado competitivo: {prediction.get('competitive_status', 'Unknown')}")

    print("\nContexto de rango:")
    print(f"  Media de lobby: {rank_context.get('target_avg_team_rank_nearest', 'Unknown')}")
    print(f"  Grupo de lobby: {rank_context.get('target_avg_team_rank_group', 'Unknown')}")
    print(f"  Filtro: {rank_context.get('filter_info', {}).get('filter_type', 'Unknown')}")

    print("\nBrechas contra grupo similar:")
    for key, value in gap_analysis.items():
        print(f"  {key}: {value}")

    print("\nTop referentes similares:")
    for player_item in similar_players[:5]:
        print(
            f"  #{player_item.get('rank')} {player_item.get('reference_riot_id')} | "
            f"Lobby {player_item.get('avg_team_rank_nearest')} | "
            f"K/D {player_item.get('recent_kd')} | "
            f"ACS {player_item.get('recent_acs')} | "
            f"Winrate {player_item.get('winrate')}%"
        )

    print("\nPrimeras partidas:")
    for match in payload.get("matches", [])[:5]:
        print(
            f"  #{match.get('match_number')} {match.get('map')} | "
            f"{match.get('agent')} | {match.get('result')} | "
            f"{match.get('performance_prediction')} | "
            f"{match.get('style_prediction')} | "
            f"{match.get('trend_signal')}"
        )

    print("\nRecomendaciones:")
    for recommendation in recommendations:
        print(f"  - {recommendation}")


def main():
    final_payload = build_final_payload()

    output_path = save_json(final_payload, OUTPUT_PATH)
    docs_output_path = save_json(final_payload, DOCS_OUTPUT_PATH)

    print_preview(final_payload)

    print("\nArchivos generados:")
    print(f"  {output_path}")
    print(f"  {docs_output_path}")


if __name__ == "__main__":
    main()