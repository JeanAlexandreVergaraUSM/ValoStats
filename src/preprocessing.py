import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler


NUMERIC_COLUMNS = [
    "damage_round",
    "headshots",
    "headshot_percent",
    "aces",
    "clutches",
    "flawless",
    "first_bloods",
    "kills",
    "deaths",
    "assists",
    "kd_ratio",
    "kills_round",
    "most_kills",
    "score_round",
    "wins",
    "win_percent",
]

ENGINEERED_FEATURES = [
    "agresividad",
    "precision",
    "impacto",
    "soporte",
    "eficiencia",
    "entry_power",
    "consistencia",
]

CLUSTERING_FEATURES = [
    "agresividad",
    "precision",
    "impacto",
    "soporte",
    "eficiencia",
    "entry_power",
    "consistencia",
    "kills_round",
    "win_percent",
    "score_round",
]

CLASSIFICATION_FEATURES = CLUSTERING_FEATURES


def load_data(path="../data/val_stats.csv"):
    return pd.read_csv(path, low_memory=False)


def convert_numeric_columns(df):
    df = df.copy()

    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace("%", "", regex=False)
                .str.replace(",", "", regex=False)
                .str.strip()
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def clean_data(df):
    df = df.copy()
    df = df.drop_duplicates()
    df = convert_numeric_columns(df)

    numeric_columns = df.select_dtypes(include=[np.number]).columns

    for col in numeric_columns:
        df[col] = df[col].replace([np.inf, -np.inf], np.nan)
        df[col] = df[col].fillna(df[col].median())

    categorical_columns = df.select_dtypes(include=["object"]).columns

    for col in categorical_columns:
        df[col] = df[col].fillna("Unknown")

    return df


def percentile_score(series):
    return series.rank(pct=True) * 100


def create_features(df):
    df = df.copy()

    raw_agresividad = (
        df["kills_round"] +
        (df["first_bloods"] / (df["wins"] + 1))
    )

    raw_entry_power = df["first_bloods"] / (df["wins"] + 1)

    raw_clutch_rate = df["clutches"] / (df["wins"] + 1)
    raw_ace_rate = df["aces"] / (df["wins"] + 1)
    raw_first_blood_rate = df["first_bloods"] / (df["wins"] + 1)

    raw_soporte = df["assists"] / (
        df["kills"] + df["assists"] + 1
    )

    raw_eficiencia = df["score_round"] * df["kd_ratio"]

    df["agresividad"] = percentile_score(raw_agresividad)
    df["precision"] = df["headshot_percent"]

    df["impacto"] = (
        percentile_score(raw_clutch_rate) +
        percentile_score(raw_ace_rate) +
        percentile_score(raw_first_blood_rate)
    ) / 3

    df["soporte"] = percentile_score(raw_soporte)
    df["eficiencia"] = percentile_score(raw_eficiencia)
    df["entry_power"] = percentile_score(raw_entry_power)

    df["consistencia"] = (
        percentile_score(df["win_percent"]) +
        percentile_score(df["kd_ratio"]) +
        percentile_score(df["kills_round"])
    ) / 3

    return df

def select_clustering_data(df):
    available_features = [
        col for col in CLUSTERING_FEATURES
        if col in df.columns
    ]

    return df[available_features].copy()


def select_classification_data(df):
    available_features = [
        col for col in CLASSIFICATION_FEATURES
        if col in df.columns
    ]

    return df[available_features].copy()


def scale_data(df):
    df = df.copy()
    df = df.replace([np.inf, -np.inf], np.nan)

    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        df[col] = df[col].fillna(df[col].median())

    df = df.fillna(0)

    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(df)

    scaled_df = pd.DataFrame(
        scaled_data,
        columns=df.columns,
        index=df.index
    )

    return scaled_df, scaler


def prepare_pipeline(path="../data/val_stats.csv"):
    raw_df = load_data(path)
    clean_df = clean_data(raw_df)
    feature_df = create_features(clean_df)

    cluster_df = select_clustering_data(feature_df)
    scaled_df, scaler = scale_data(cluster_df)

    return raw_df, clean_df, feature_df, cluster_df, scaled_df, scaler