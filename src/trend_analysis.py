import json
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

PERFORMANCE_PATH = PROJECT_ROOT / "outputs" / "recent_predictions" / "performance_predictions.json"
STYLE_PATH = PROJECT_ROOT / "outputs" / "recent_predictions" / "style_predictions.json"
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "recent_predictions" / "trend_predictions.json"


PERFORMANCE_SCORE = {
    "Bajo": 1,
    "Medio": 2,
    "Alto": 3,
    "Destacado": 4,
}


def load_json(path):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo requerido: {path}")

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def safe_divide(numerator, denominator, default=0.0):
    if denominator is None or denominator == 0:
        return default

    return numerator / denominator


def result_to_score(result):
    result = str(result).strip().lower()

    if result == "win":
        return 1.0

    if result == "draw":
        return 0.5

    if result == "loss":
        return 0.0

    return 0.0


def performance_to_score(value):
    return PERFORMANCE_SCORE.get(str(value), 2)


def build_matches_dataframe(performance_payload, style_payload):
    performance_matches = pd.DataFrame(performance_payload["matches"])
    style_matches = pd.DataFrame(style_payload["matches"])

    if performance_matches.empty:
        raise ValueError("No hay predicciones de rendimiento.")

    if style_matches.empty:
        raise ValueError("No hay predicciones de estilo.")

    style_columns = [
        "match_number",
        "style_prediction",
        "style_confidence",
        "style_explanation",
    ]

    style_columns = [
        column for column in style_columns
        if column in style_matches.columns
    ]

    df = performance_matches.merge(
        style_matches[style_columns],
        on="match_number",
        how="left",
    )

    numeric_columns = [
        "tracker_score",
        "acs",
        "kills",
        "deaths",
        "assists",
        "kd_ratio",
        "adr",
        "dda",
        "headshot_percent",
        "kast",
        "first_kills",
        "first_deaths",
        "multi_kills",
    ]

    for column in numeric_columns:
        if column not in df.columns:
            df[column] = 0

        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

    if "result" not in df.columns:
        df["result"] = "Unknown"

    if "performance_prediction" not in df.columns:
        df["performance_prediction"] = "Medio"

    if "style_prediction" not in df.columns:
        df["style_prediction"] = "Unknown"

    df["result_score"] = df["result"].apply(result_to_score)
    df["performance_score"] = df["performance_prediction"].apply(performance_to_score)

    df["entry_duels"] = df["first_kills"] + df["first_deaths"]
    df["entry_success"] = np.where(
        df["entry_duels"] > 0,
        df["first_kills"] / df["entry_duels"],
        0.5,
    )

    return df


def normalize_series(series):
    series = pd.to_numeric(series, errors="coerce").fillna(0)

    minimum = float(series.min())
    maximum = float(series.max())

    if maximum == minimum:
        return pd.Series([0.5] * len(series), index=series.index)

    return (series - minimum) / (maximum - minimum)


def add_trend_scores(df):
    df = df.copy()

    df["acs_norm"] = normalize_series(df["acs"])
    df["tracker_norm"] = normalize_series(df["tracker_score"])
    df["kd_norm"] = normalize_series(df["kd_ratio"])
    df["adr_norm"] = normalize_series(df["adr"])
    df["dda_norm"] = normalize_series(df["dda"])
    df["kast_norm"] = normalize_series(df["kast"])
    df["entry_norm"] = normalize_series(df["entry_success"])
    df["performance_norm"] = (df["performance_score"] - 1) / 3

    df["trend_score"] = (
        df["acs_norm"] * 0.18
        + df["tracker_norm"] * 0.18
        + df["kd_norm"] * 0.16
        + df["adr_norm"] * 0.14
        + df["dda_norm"] * 0.12
        + df["kast_norm"] * 0.10
        + df["entry_norm"] * 0.06
        + df["performance_norm"] * 0.06
    )

    df["trend_score"] = (df["trend_score"] * 100).round(2)

    return df


def classify_match_trend(row):
    trend_score = float(row.get("trend_score", 0))
    result = str(row.get("result", "Unknown"))
    performance = str(row.get("performance_prediction", "Medio"))
    dda = float(row.get("dda", 0))
    kd_ratio = float(row.get("kd_ratio", 0))

    if trend_score >= 70:
        return "Positiva"

    if trend_score >= 58 and performance in ["Alto", "Destacado"]:
        return "Positiva"

    if trend_score <= 38:
        return "Negativa"

    if result == "Loss" and performance == "Bajo" and kd_ratio < 0.9:
        return "Negativa"

    if dda < -25 and kd_ratio < 0.9:
        return "Negativa"

    return "Neutra"


def explain_match_trend(row):
    signal = str(row.get("trend_signal", "Neutra"))
    reasons = []

    acs = float(row.get("acs", 0))
    tracker_score = float(row.get("tracker_score", 0))
    kd_ratio = float(row.get("kd_ratio", 0))
    dda = float(row.get("dda", 0))
    kast = float(row.get("kast", 0))
    performance = str(row.get("performance_prediction", "Medio"))

    if performance in ["Alto", "Destacado"]:
        reasons.append(f"rendimiento {performance.lower()}")

    if acs >= 240:
        reasons.append("ACS competitivo")
    elif acs < 170:
        reasons.append("ACS bajo")

    if tracker_score >= 750:
        reasons.append("TRS alto")
    elif tracker_score < 400:
        reasons.append("TRS bajo")

    if kd_ratio >= 1.2:
        reasons.append("K/D positivo")
    elif kd_ratio < 0.85:
        reasons.append("K/D bajo")

    if dda > 20:
        reasons.append("DDA positivo")
    elif dda < -20:
        reasons.append("DDA negativo")

    if kast >= 78:
        reasons.append("buena participación por ronda")
    elif kast < 65:
        reasons.append("baja participación por ronda")

    if not reasons:
        reasons.append("métricas mixtas")

    return f"Tendencia {signal.lower()}: " + ", ".join(reasons) + "."


def summarize_half(df):
    if df.empty:
        return {
            "matches": 0,
            "winrate": 0.0,
            "avg_acs": 0.0,
            "avg_tracker_score": 0.0,
            "avg_kd": 0.0,
            "avg_adr": 0.0,
            "avg_dda": 0.0,
            "avg_kast": 0.0,
            "avg_trend_score": 0.0,
            "main_style": "Unknown",
            "performance_distribution": {},
            "style_distribution": {},
        }

    style_distribution = df["style_prediction"].value_counts().to_dict()
    performance_distribution = df["performance_prediction"].value_counts().to_dict()

    main_style = "Unknown"
    if style_distribution:
        main_style = max(style_distribution.items(), key=lambda item: item[1])[0]

    return {
        "matches": int(len(df)),
        "winrate": round(float((df["result"] == "Win").mean() * 100), 2),
        "avg_acs": round(float(df["acs"].mean()), 2),
        "avg_tracker_score": round(float(df["tracker_score"].mean()), 2),
        "avg_kd": round(float(df["kd_ratio"].mean()), 3),
        "avg_adr": round(float(df["adr"].mean()), 2),
        "avg_dda": round(float(df["dda"].mean()), 2),
        "avg_kast": round(float(df["kast"].mean()), 2),
        "avg_trend_score": round(float(df["trend_score"].mean()), 2),
        "main_style": main_style,
        "performance_distribution": {
            str(key): int(value)
            for key, value in performance_distribution.items()
        },
        "style_distribution": {
            str(key): int(value)
            for key, value in style_distribution.items()
        },
    }


def calculate_deltas(previous_summary, recent_summary):
    keys = [
        "winrate",
        "avg_acs",
        "avg_tracker_score",
        "avg_kd",
        "avg_adr",
        "avg_dda",
        "avg_kast",
        "avg_trend_score",
    ]

    deltas = {}

    for key in keys:
        deltas[key] = round(
            float(recent_summary.get(key, 0)) - float(previous_summary.get(key, 0)),
            3,
        )

    return deltas


def classify_global_trend(deltas, recent_summary):
    score = 0

    if deltas["avg_trend_score"] >= 8:
        score += 2
    elif deltas["avg_trend_score"] >= 3:
        score += 1
    elif deltas["avg_trend_score"] <= -8:
        score -= 2
    elif deltas["avg_trend_score"] <= -3:
        score -= 1

    if deltas["winrate"] >= 15:
        score += 2
    elif deltas["winrate"] >= 5:
        score += 1
    elif deltas["winrate"] <= -15:
        score -= 2
    elif deltas["winrate"] <= -5:
        score -= 1

    if deltas["avg_acs"] >= 25:
        score += 1
    elif deltas["avg_acs"] <= -25:
        score -= 1

    if deltas["avg_kd"] >= 0.20:
        score += 1
    elif deltas["avg_kd"] <= -0.20:
        score -= 1

    if deltas["avg_kast"] >= 5:
        score += 1
    elif deltas["avg_kast"] <= -5:
        score -= 1

    recent_trend_score = float(recent_summary.get("avg_trend_score", 0))

    if score >= 4 and recent_trend_score >= 65:
        return "Subida probable", score

    if score >= 2:
        return "Progreso positivo", score

    if score <= -3:
        return "Riesgo de bajar", score

    return "Estable", score


def explain_global_trend(trend_status, deltas, previous_summary, recent_summary):
    reasons = []

    if deltas["winrate"] > 0:
        reasons.append(f"winrate subió {deltas['winrate']} puntos")
    elif deltas["winrate"] < 0:
        reasons.append(f"winrate bajó {abs(deltas['winrate'])} puntos")

    if deltas["avg_acs"] > 0:
        reasons.append(f"ACS promedio subió {deltas['avg_acs']}")
    elif deltas["avg_acs"] < 0:
        reasons.append(f"ACS promedio bajó {abs(deltas['avg_acs'])}")

    if deltas["avg_kd"] > 0:
        reasons.append(f"K/D promedio subió {deltas['avg_kd']}")
    elif deltas["avg_kd"] < 0:
        reasons.append(f"K/D promedio bajó {abs(deltas['avg_kd'])}")

    if deltas["avg_kast"] > 0:
        reasons.append(f"KAST subió {deltas['avg_kast']} puntos")
    elif deltas["avg_kast"] < 0:
        reasons.append(f"KAST bajó {abs(deltas['avg_kast'])} puntos")

    previous_style = previous_summary.get("main_style", "Unknown")
    recent_style = recent_summary.get("main_style", "Unknown")

    if previous_style != recent_style:
        reasons.append(f"cambio de estilo principal: {previous_style} → {recent_style}")

    if not reasons:
        reasons.append("las métricas recientes se mantienen similares")

    return f"Tendencia global {trend_status.lower()}: " + ", ".join(reasons) + "."


def build_match_outputs(df):
    output = []

    for _, row in df.iterrows():
        item = {
            "match_number": int(row.get("match_number", 0)),
            "match_id": str(row.get("match_id", "")),
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
            "dda": float(row.get("dda", 0)),
            "kast": float(row.get("kast", 0)),
            "performance_prediction": str(row.get("performance_prediction", "Medio")),
            "style_prediction": str(row.get("style_prediction", "Unknown")),
            "trend_score": float(row.get("trend_score", 0)),
            "trend_signal": str(row.get("trend_signal", "Neutra")),
            "trend_explanation": str(row.get("trend_explanation", "")),
        }

        output.append(item)

    return output


def save_trend_predictions(payload, output_path=OUTPUT_PATH):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    return output_path


def main():
    performance_payload = load_json(PERFORMANCE_PATH)
    style_payload = load_json(STYLE_PATH)

    df = build_matches_dataframe(performance_payload, style_payload)
    df = add_trend_scores(df)

    df["trend_signal"] = df.apply(classify_match_trend, axis=1)
    df["trend_explanation"] = df.apply(explain_match_trend, axis=1)

    # El scraper deja las partidas más recientes primero.
    recent_half = df[df["match_number"] <= 10].copy()
    previous_half = df[df["match_number"] > 10].copy()

    recent_summary = summarize_half(recent_half)
    previous_summary = summarize_half(previous_half)
    deltas = calculate_deltas(previous_summary, recent_summary)

    trend_status, trend_numeric_score = classify_global_trend(
        deltas,
        recent_summary,
    )

    global_explanation = explain_global_trend(
        trend_status,
        deltas,
        previous_summary,
        recent_summary,
    )

    trend_distribution = df["trend_signal"].value_counts().to_dict()

    output_payload = {
        "player": performance_payload["player"],
        "summary": performance_payload["summary"],
        "trend_model": {
            "task": "Estimación de tendencia competitiva reciente",
            "target": "trend_status",
            "method": "Comparación temporal entre primeras 10 y últimas 10 partidas visibles",
            "features": [
                "ACS",
                "TRS",
                "K/D",
                "ADR",
                "DDA",
                "KAST",
                "winrate",
                "performance_level",
                "style_prediction",
            ],
        },
        "global_trend_prediction": {
            "trend_status": trend_status,
            "trend_numeric_score": int(trend_numeric_score),
            "trend_explanation": global_explanation,
            "previous_half": previous_summary,
            "recent_half": recent_summary,
            "deltas": deltas,
            "trend_distribution": {
                str(key): int(value)
                for key, value in trend_distribution.items()
            },
        },
        "matches": build_match_outputs(df),
    }

    output_path = save_trend_predictions(output_payload)

    print("\nPredicción de tendencia generada correctamente")
    print(f"Archivo JSON: {output_path}")

    print("\nTendencia global:")
    print(f"  Estado: {trend_status}")
    print(f"  Puntaje: {trend_numeric_score}")
    print(f"  Explicación: {global_explanation}")

    print("\nComparación temporal:")
    print("  Tramo anterior: partidas 11 a 20")
    print(f"    Winrate: {previous_summary['winrate']}")
    print(f"    ACS promedio: {previous_summary['avg_acs']}")
    print(f"    K/D promedio: {previous_summary['avg_kd']}")
    print(f"    Estilo principal: {previous_summary['main_style']}")

    print("  Tramo reciente: partidas 1 a 10")
    print(f"    Winrate: {recent_summary['winrate']}")
    print(f"    ACS promedio: {recent_summary['avg_acs']}")
    print(f"    K/D promedio: {recent_summary['avg_kd']}")
    print(f"    Estilo principal: {recent_summary['main_style']}")

    print("\nDistribución de tendencia por partida:")
    for signal, count in trend_distribution.items():
        print(f"  {signal}: {count}")

    print("\nPrimeras partidas:")
    for row in output_payload["matches"][:5]:
        print(
            f"  #{row['match_number']} {row['map']} | {row['agent']} | "
            f"{row['result']} | {row['performance_prediction']} | "
            f"{row['style_prediction']} | {row['trend_signal']}"
        )


if __name__ == "__main__":
    main()