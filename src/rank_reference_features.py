import json
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

REFERENCE_MATCHES_PATH = PROJECT_ROOT / "data" / "rank_reference_matches.csv"
REFERENCE_PROFILES_PATH = PROJECT_ROOT / "data" / "rank_reference_profiles.csv"
REFERENCE_SUMMARY_PATH = PROJECT_ROOT / "outputs" / "rank_reference" / "rank_reference_summary.json"


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

    if value == "win":
        return "Win"

    if value == "loss":
        return "Loss"

    if value == "draw":
        return "Draw"

    return "Unknown"


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


def load_reference_matches(path=REFERENCE_MATCHES_PATH):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"No existe {path}. Primero ejecuta data/tracker/scraper_reference_batch.py."
        )

    df = pd.read_csv(path)

    if df.empty:
        raise ValueError("rank_reference_matches.csv está vacío.")

    df = df.copy()

    for column in NUMERIC_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

    if "result" in df.columns:
        df["result"] = df["result"].apply(normalize_result)
    else:
        df["result"] = "Unknown"

    if "reference_riot_id" not in df.columns:
        df["reference_riot_id"] = df["player_name"].astype(str) + "#" + df["tag"].astype(str)

    df["avg_team_rank"] = df["avg_team_rank"].fillna("Unknown").astype(str)
    df["match_rank"] = df["match_rank"].fillna("Unknown").astype(str)
    df["current_rank"] = df["current_rank"].fillna("Unknown").astype(str)

    df["avg_team_rank_value"] = df["avg_team_rank"].apply(rank_to_value)
    df["match_rank_value"] = df["match_rank"].apply(rank_to_value)
    df["current_rank_value"] = df["current_rank"].apply(rank_to_value)

    df["avg_team_rank_group"] = df["avg_team_rank"].apply(rank_to_group)
    df["match_rank_group"] = df["match_rank"].apply(rank_to_group)
    df["current_rank_group"] = df["current_rank"].apply(rank_to_group)

    df = df.drop_duplicates(subset=["reference_riot_id", "match_id"])

    return df


def most_common_value(series, default="Unknown"):
    values = series.dropna().astype(str)
    values = values[values.str.lower() != "unknown"]

    if values.empty:
        return default

    return values.value_counts().idxmax()


def summarize_player(group):
    riot_id = str(group["reference_riot_id"].iloc[0])

    matches_analyzed = len(group)

    wins = int((group["result"] == "Win").sum())
    losses = int((group["result"] == "Loss").sum())
    draws = int((group["result"] == "Draw").sum())

    total_kills = int(group["kills"].sum())
    total_deaths = int(group["deaths"].sum())
    total_assists = int(group["assists"].sum())
    total_rounds = int(group["rounds_played"].sum())

    avg_rank_value = float(group["avg_team_rank_value"].dropna().mean()) if group["avg_team_rank_value"].notna().any() else np.nan
    dominant_avg_rank = value_to_nearest_rank(avg_rank_value)
    dominant_rank_group = rank_to_group(dominant_avg_rank)

    first_kills = int(group["first_kills"].sum())
    first_deaths = int(group["first_deaths"].sum())
    entry_duels = first_kills + first_deaths

    row = {
        "reference_riot_id": riot_id,
        "source_player_name": str(group["source_player_name"].iloc[0]),
        "source_tag": str(group["source_tag"].iloc[0]),
        "matches_analyzed": matches_analyzed,
        "current_rank_mode": most_common_value(group["current_rank"]),
        "match_rank_mode": most_common_value(group["match_rank"]),
        "avg_team_rank_mode": most_common_value(group["avg_team_rank"]),
        "avg_team_rank_mean_value": round(avg_rank_value, 3) if not pd.isna(avg_rank_value) else np.nan,
        "avg_team_rank_nearest": dominant_avg_rank,
        "avg_team_rank_group": dominant_rank_group,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "winrate": round(safe_divide(wins, matches_analyzed) * 100, 2),
        "total_kills": total_kills,
        "total_deaths": total_deaths,
        "total_assists": total_assists,
        "total_rounds": total_rounds,
        "recent_kd": round(safe_divide(total_kills, total_deaths), 3),
        "recent_kda": round(safe_divide(total_kills + total_assists, total_deaths), 3),
        "recent_acs": round(float(group["acs"].mean()), 2),
        "recent_tracker_score": round(float(group["tracker_score"].mean()), 2),
        "recent_adr": round(float(group["adr"].mean()), 2),
        "recent_dda": round(float(group["dda"].mean()), 2),
        "recent_hs": round(float(group["headshot_percent"].mean()), 2),
        "recent_kast": round(float(group["kast"].mean()), 2),
        "recent_first_kills": first_kills,
        "recent_first_deaths": first_deaths,
        "recent_entry_success": round(safe_divide(first_kills, entry_duels, default=0.5) * 100, 2),
        "recent_entry_activity": round(safe_divide(entry_duels, total_rounds) * 100, 2),
        "recent_multi_kill_rate": round(safe_divide(float(group["multi_kills"].sum()), total_rounds) * 100, 2),
        "acs_std": round(float(group["acs"].std(ddof=0)), 2) if matches_analyzed > 1 else 0.0,
        "trs_std": round(float(group["tracker_score"].std(ddof=0)), 2) if matches_analyzed > 1 else 0.0,
        "main_agent": most_common_value(group["agent"]),
        "main_map": most_common_value(group["map"]),
    }

    return row


def build_reference_profiles(matches_df):
    profiles = []

    for _, group in matches_df.groupby("reference_riot_id"):
        profiles.append(summarize_player(group))

    profiles_df = pd.DataFrame(profiles)

    profiles_df = profiles_df.sort_values(
        by=["avg_team_rank_mean_value", "reference_riot_id"],
        ascending=[True, True],
    ).reset_index(drop=True)

    return profiles_df


def build_summary(matches_df, profiles_df):
    summary = {
        "total_reference_matches": int(len(matches_df)),
        "total_reference_players": int(profiles_df["reference_riot_id"].nunique()),
        "players_with_20_matches": int((profiles_df["matches_analyzed"] >= 20).sum()),
        "players_with_less_than_20_matches": int((profiles_df["matches_analyzed"] < 20).sum()),
        "rank_group_distribution_matches": {
            str(key): int(value)
            for key, value in matches_df["avg_team_rank_group"].value_counts().to_dict().items()
        },
        "rank_group_distribution_players": {
            str(key): int(value)
            for key, value in profiles_df["avg_team_rank_group"].value_counts().to_dict().items()
        },
        "avg_team_rank_distribution_matches": {
            str(key): int(value)
            for key, value in matches_df["avg_team_rank"].value_counts().to_dict().items()
        },
        "current_rank_distribution_players": {
            str(key): int(value)
            for key, value in profiles_df["current_rank_mode"].value_counts().to_dict().items()
        },
    }

    return summary


def save_outputs(profiles_df, summary):
    REFERENCE_PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
    REFERENCE_SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)

    profiles_df.to_csv(REFERENCE_PROFILES_PATH, index=False)

    with open(REFERENCE_SUMMARY_PATH, "w", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)


def main():
    matches_df = load_reference_matches()
    profiles_df = build_reference_profiles(matches_df)
    summary = build_summary(matches_df, profiles_df)

    save_outputs(profiles_df, summary)

    print("\nBase de referencia por rango generada correctamente")
    print(f"Perfiles: {REFERENCE_PROFILES_PATH}")
    print(f"Resumen: {REFERENCE_SUMMARY_PATH}")

    print("\nResumen:")
    print(f"  Partidas de referencia: {summary['total_reference_matches']}")
    print(f"  Jugadores de referencia: {summary['total_reference_players']}")
    print(f"  Jugadores con 20 partidas: {summary['players_with_20_matches']}")
    print(f"  Jugadores con menos de 20 partidas: {summary['players_with_less_than_20_matches']}")

    print("\nDistribución por grupo de rango de partida:")
    for group, count in summary["rank_group_distribution_matches"].items():
        print(f"  {group}: {count}")

    print("\nPrimeros perfiles:")
    preview_columns = [
        "reference_riot_id",
        "matches_analyzed",
        "current_rank_mode",
        "avg_team_rank_nearest",
        "avg_team_rank_group",
        "winrate",
        "recent_kd",
        "recent_acs",
        "recent_adr",
        "recent_kast",
    ]

    print(profiles_df[preview_columns].head(10).to_string(index=False))


if __name__ == "__main__":
    main()