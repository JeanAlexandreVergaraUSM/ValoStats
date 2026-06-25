import json
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECENT_MATCHES_PATH = PROJECT_ROOT / "data" / "recent_matches.csv"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "outputs" / "recent_features" / "recent_features.json"


NUMERIC_COLUMNS = [
    "team_score",
    "enemy_score",
    "rounds_played",
    "tracker_score",
    "acs",
    "kills",
    "deaths",
    "assists",
    "kill_diff",
    "kd_ratio",
    "dda",
    "adr",
    "headshot_percent",
    "kast",
    "first_kills",
    "first_deaths",
    "multi_kills",
]


def safe_divide(numerator, denominator, default=0.0):
    if denominator is None or denominator == 0:
        return default

    return numerator / denominator


def normalize_result(value):
    value = str(value).strip().lower()

    if value in ["win", "victory", "won"]:
        return "Win"

    if value in ["loss", "defeat", "lost"]:
        return "Loss"

    if value in ["draw", "tie"]:
        return "Draw"

    return "Unknown"


def result_to_score(value):
    result = normalize_result(value)

    if result == "Win":
        return 1.0

    if result == "Draw":
        return 0.5

    if result == "Loss":
        return 0.0

    return 0.0


def load_recent_matches(path=DEFAULT_RECENT_MATCHES_PATH):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"No existe el archivo {path}. "
            "Primero ejecuta el scraper para generar data/recent_matches.csv."
        )

    df = pd.read_csv(path)

    if df.empty:
        raise ValueError("recent_matches.csv existe, pero está vacío.")

    df = df.copy()

    for column in NUMERIC_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

    if "result" in df.columns:
        df["result"] = df["result"].apply(normalize_result)
    else:
        df["result"] = "Unknown"

    if "rounds_played" not in df.columns:
        df["rounds_played"] = df.get("team_score", 0) + df.get("enemy_score", 0)

    df["rounds_played"] = df["rounds_played"].replace(0, np.nan)

    fallback_rounds = df["team_score"].fillna(0) + df["enemy_score"].fillna(0)
    df["rounds_played"] = df["rounds_played"].fillna(fallback_rounds)
    df["rounds_played"] = df["rounds_played"].replace(0, 1)

    return df


def create_match_features(df):
    df = df.copy()

    df["match_number"] = np.arange(1, len(df) + 1)

    df["result_score"] = df["result"].apply(result_to_score)

    df["kills_round"] = df["kills"] / df["rounds_played"]
    df["deaths_round"] = df["deaths"] / df["rounds_played"]
    df["assists_round"] = df["assists"] / df["rounds_played"]

    df["kda_ratio"] = (df["kills"] + df["assists"]) / (df["deaths"] + 1)

    df["entry_duels"] = df["first_kills"] + df["first_deaths"]
    df["entry_success"] = np.where(
        df["entry_duels"] > 0,
        df["first_kills"] / df["entry_duels"],
        0.5,
    )

    df["entry_activity"] = df["entry_duels"] / df["rounds_played"]
    df["multi_kill_rate"] = df["multi_kills"] / df["rounds_played"]

    df["support_ratio"] = df["assists"] / (df["kills"] + 1)

    df["support_score"] = (
        df["support_ratio"] * 0.60
        + df["assists_round"] * 0.25
        + (df["kast"] / 100) * 0.15
    )

    df["impact_score"] = (
        df["kills_round"] * 0.30
        + df["entry_success"] * 0.20
        + df["multi_kill_rate"] * 0.20
        + (df["acs"] / 300) * 0.20
        + (df["tracker_score"] / 1000) * 0.10
    )

    df["combat_score"] = (
        df["acs"] * 0.35
        + df["adr"] * 0.30
        + df["tracker_score"] * 0.20
        + df["dda"] * 0.15
    )

    df["survival_score"] = (
        (df["kast"] / 100) * 0.60
        + (1 - df["deaths_round"].clip(0, 1)) * 0.40
    )

    # Features compatibles con el modelo de estilos entrenado con la base histórica.
    df["agresividad"] = df["kd_ratio"]
    df["precision"] = df["headshot_percent"]
    df["impacto"] = df["impact_score"]
    df["soporte"] = df["support_ratio"]
    df["eficiencia"] = df["adr"]
    df["entry_power"] = df["first_kills"] / (df["kills"] + 1)
    df["consistencia"] = df["kast"]

    return df

def summarize_recent_matches(match_features):
    df = match_features.copy()

    total_matches = len(df)
    wins = int((df["result"] == "Win").sum())
    losses = int((df["result"] == "Loss").sum())
    draws = int((df["result"] == "Draw").sum())
    unknown = int((df["result"] == "Unknown").sum())

    total_kills = int(df["kills"].sum())
    total_deaths = int(df["deaths"].sum())
    total_assists = int(df["assists"].sum())
    total_rounds = int(df["rounds_played"].sum())

    recent_kd = safe_divide(total_kills, total_deaths, default=0.0)
    recent_kda = safe_divide(total_kills + total_assists, total_deaths, default=0.0)

    entry_duels = int(df["entry_duels"].sum())
    total_first_kills = int(df["first_kills"].sum())
    total_first_deaths = int(df["first_deaths"].sum())

    recent_entry_success = safe_divide(total_first_kills, entry_duels, default=0.5)
    recent_entry_activity = safe_divide(entry_duels, total_rounds, default=0.0)

    acs_std = float(df["acs"].std(ddof=0)) if total_matches > 1 else 0.0
    trs_std = float(df["tracker_score"].std(ddof=0)) if total_matches > 1 else 0.0

    summary = {
        "matches_analyzed": total_matches,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "unknown_results": unknown,
        "winrate": round(safe_divide(wins, total_matches, default=0.0) * 100, 2),
        "total_kills": total_kills,
        "total_deaths": total_deaths,
        "total_assists": total_assists,
        "total_rounds": total_rounds,
        "recent_kd": round(recent_kd, 3),
        "recent_kda": round(recent_kda, 3),
        "recent_acs": round(float(df["acs"].mean()), 2),
        "recent_tracker_score": round(float(df["tracker_score"].mean()), 2),
        "recent_adr": round(float(df["adr"].mean()), 2),
        "recent_dda": round(float(df["dda"].mean()), 2),
        "recent_hs": round(float(df["headshot_percent"].mean()), 2),
        "recent_kast": round(float(df["kast"].mean()), 2),
        "recent_first_kills": total_first_kills,
        "recent_first_deaths": total_first_deaths,
        "recent_entry_success": round(recent_entry_success * 100, 2),
        "recent_entry_activity": round(recent_entry_activity * 100, 2),
        "recent_multi_kill_rate": round(
            safe_divide(float(df["multi_kills"].sum()), total_rounds, default=0.0) * 100,
            2,
        ),
        "recent_consistency_acs_std": round(acs_std, 2),
        "recent_consistency_trs_std": round(trs_std, 2),
    }

    return summary


def get_current_rank(df):
    if "current_rank" not in df.columns:
        return "Unknown"

    ranks = df["current_rank"].dropna().astype(str)
    ranks = ranks[ranks.str.lower() != "unknown"]

    if ranks.empty:
        return "Unknown"

    return ranks.mode().iloc[0]


def get_main_agents(df, limit=3):
    if "agent" not in df.columns:
        return []

    agents = (
        df["agent"]
        .dropna()
        .astype(str)
        .value_counts()
        .head(limit)
        .to_dict()
    )

    return [
        {"agent": agent, "matches": int(count)}
        for agent, count in agents.items()
    ]


def get_main_maps(df, limit=3):
    if "map" not in df.columns:
        return []

    maps = (
        df["map"]
        .dropna()
        .astype(str)
        .value_counts()
        .head(limit)
        .to_dict()
    )

    return [
        {"map": map_name, "matches": int(count)}
        for map_name, count in maps.items()
    ]


def build_recent_feature_payload(path=DEFAULT_RECENT_MATCHES_PATH):
    raw_df = load_recent_matches(path)
    match_features = create_match_features(raw_df)
    summary = summarize_recent_matches(match_features)

    player_name = str(raw_df["player_name"].iloc[0]) if "player_name" in raw_df.columns else "Unknown"
    tag = str(raw_df["tag"].iloc[0]) if "tag" in raw_df.columns else "Unknown"

    player = {
        "name": player_name,
        "tag": tag,
        "riot_id": f"{player_name}#{tag}",
        "current_rank": get_current_rank(raw_df),
        "main_agents": get_main_agents(raw_df),
        "main_maps": get_main_maps(raw_df),
    }

    selected_match_columns = [
        "match_number",
        "match_id",
        "date",
        "mode",
        "map",
        "agent",
        "result",
        "team_score",
        "enemy_score",
        "rounds_played",
        "tracker_score",
        "acs",
        "kills",
        "deaths",
        "assists",
        "kill_diff",
        "kd_ratio",
        "dda",
        "adr",
        "headshot_percent",
        "kast",
        "first_kills",
        "first_deaths",
        "multi_kills",
        "kills_round",
        "deaths_round",
        "assists_round",
        "kda_ratio",
        "entry_success",
        "entry_activity",
        "multi_kill_rate",
        "support_score",
        "impact_score",
        "combat_score",
        "survival_score",
        "agresividad",
        "precision",
        "impacto",
        "soporte",
        "eficiencia",
        "entry_power",
        "consistencia",
    ]

    existing_columns = [
        column for column in selected_match_columns
        if column in match_features.columns
    ]

    matches = match_features[existing_columns].copy()

    for column in matches.columns:
        if pd.api.types.is_numeric_dtype(matches[column]):
            matches[column] = matches[column].round(4)

    payload = {
        "player": player,
        "summary": summary,
        "matches": matches.to_dict(orient="records"),
    }

    return payload, match_features


def save_recent_features_json(payload, output_path=DEFAULT_OUTPUT_PATH):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    return output_path


def main():
    payload, match_features = build_recent_feature_payload()
    output_path = save_recent_features_json(payload)

    print("\nFeatures recientes generadas correctamente")
    print(f"Archivo JSON: {output_path}")

    print("\nJugador:")
    print(f"  {payload['player']['riot_id']}")
    print(f"  Rango actual: {payload['player']['current_rank']}")

    print("\nResumen:")
    for key, value in payload["summary"].items():
        print(f"  {key}: {value}")

    print("\nPrimeras partidas procesadas:")
    preview_columns = [
        "match_number",
        "map",
        "agent",
        "result",
        "tracker_score",
        "acs",
        "kills",
        "deaths",
        "assists",
        "kd_ratio",
        "adr",
        "kast",
        "entry_success",
        "impact_score",
        "support_score",
    ]

    existing_preview_columns = [
        column for column in preview_columns
        if column in match_features.columns
    ]

    print(match_features[existing_preview_columns].head(5).to_string(index=False))


if __name__ == "__main__":
    main()