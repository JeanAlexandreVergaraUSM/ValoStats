import argparse
import subprocess
import sys
import os
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SCRIPTS = {
    "scraper": PROJECT_ROOT / "data" / "tracker" / "scraper_valorant.py",
    "recent_features": PROJECT_ROOT / "src" / "recent_features.py",
    "performance": PROJECT_ROOT / "src" / "performance_prediction.py",
    "style": PROJECT_ROOT / "src" / "recent_style_prediction.py",
    "trend": PROJECT_ROOT / "src" / "trend_analysis.py",
    "similar_players": PROJECT_ROOT / "src" / "similar_players.py",
    "final_analysis": PROJECT_ROOT / "src" / "final_player_analysis.py",
    "rank_reference_features": PROJECT_ROOT / "src" / "rank_reference_features.py",
}

OUTPUTS = {
    "recent_matches": PROJECT_ROOT / "data" / "recent_matches.csv",
    "recent_features": PROJECT_ROOT / "outputs" / "recent_features" / "recent_features.json",
    "performance": PROJECT_ROOT / "outputs" / "recent_predictions" / "performance_predictions.json",
    "style": PROJECT_ROOT / "outputs" / "recent_predictions" / "style_predictions.json",
    "trend": PROJECT_ROOT / "outputs" / "recent_predictions" / "trend_predictions.json",
    "similar_players": PROJECT_ROOT / "outputs" / "recent_predictions" / "similar_players.json",
    "final_analysis": PROJECT_ROOT / "outputs" / "recent_predictions" / "final_player_analysis.json",
    "docs_final_analysis": PROJECT_ROOT / "docs" / "final_player_analysis.json",
    "rank_reference_profiles": PROJECT_ROOT / "data" / "rank_reference_profiles.csv",
}


def validate_riot_id(riot_id):
    riot_id = str(riot_id).strip()

    if "#" not in riot_id:
        raise ValueError(
            "El Riot ID debe tener formato Nombre#Tag. "
            "Ejemplo: PoloGB#LAS"
        )

    game_name, tag_line = riot_id.split("#", 1)

    game_name = game_name.strip()
    tag_line = tag_line.strip()

    if not game_name or not tag_line:
        raise ValueError(
            "El Riot ID está incompleto. "
            "Ejemplo válido: PoloGB#LAS"
        )

    return f"{game_name}#{tag_line}"


def check_script_exists(script_path):
    if not script_path.exists():
        raise FileNotFoundError(f"No existe el script requerido: {script_path}")


def run_command(command, step_name):
    print("\n" + "=" * 90)
    print(f"▶ Ejecutando paso: {step_name}")
    print("=" * 90)
    print("Comando:")
    print(" ".join(str(part) for part in command))
    print()

    start_time = time.time()

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    process = subprocess.Popen(
        command,
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        env=env,
    )

    output_lines = []

    try:
        for line in process.stdout:
            print(line, end="")
            output_lines.append(line)

        return_code = process.wait()

    except KeyboardInterrupt:
        print("\n🛑 Proceso detenido manualmente.")
        process.terminate()
        process.wait()
        raise

    elapsed = round(time.time() - start_time, 2)

    if return_code != 0:
        print("\nError en el paso:", step_name)
        print(f"Tiempo antes del error: {elapsed} segundos")
        raise RuntimeError(
            f"Falló el paso '{step_name}' con código {return_code}."
        )

    print(f"\nPaso completado: {step_name}")
    print(f"Tiempo: {elapsed} segundos")

    return output_lines


def check_output(path, label):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"El paso terminó, pero no se encontró la salida esperada: {label}\n"
            f"Ruta esperada: {path}"
        )

    if path.is_file() and path.stat().st_size == 0:
        raise ValueError(
            f"El archivo de salida existe, pero está vacío: {path}"
        )

    print(f"  ✓ {label}: {path}")


def run_pipeline(riot_id, skip_scraper=False, refresh_reference=False):
    riot_id = validate_riot_id(riot_id)

    print("\nIniciando análisis completo de ValoStats")
    print(f"Jugador objetivo: {riot_id}")
    print(f"Proyecto: {PROJECT_ROOT}")

    python_executable = sys.executable

    for script_name, script_path in SCRIPTS.items():
        check_script_exists(script_path)

    if refresh_reference:
        run_command(
            [
                python_executable,
                str(SCRIPTS["rank_reference_features"]),
            ],
            "Actualizar perfiles de referencia por rango",
        )

        check_output(
            OUTPUTS["rank_reference_profiles"],
            "rank_reference_profiles.csv",
        )

    if not skip_scraper:
        run_command(
            [
                python_executable,
                str(SCRIPTS["scraper"]),
                riot_id,
            ],
            "Scraper de partidas recientes",
        )

        check_output(
            OUTPUTS["recent_matches"],
            "recent_matches.csv",
        )
    else:
        print("\nSaltando scraper porque se usó --skip-scraper")
        check_output(
            OUTPUTS["recent_matches"],
            "recent_matches.csv existente",
        )

    run_command(
        [
            python_executable,
            str(SCRIPTS["recent_features"]),
        ],
        "Generar features recientes",
    )

    check_output(
        OUTPUTS["recent_features"],
        "recent_features.json",
    )

    run_command(
        [
            python_executable,
            str(SCRIPTS["performance"]),
        ],
        "Predicción de rendimiento",
    )

    check_output(
        OUTPUTS["performance"],
        "performance_predictions.json",
    )

    run_command(
        [
            python_executable,
            str(SCRIPTS["style"]),
        ],
        "Predicción de estilo de juego",
    )

    check_output(
        OUTPUTS["style"],
        "style_predictions.json",
    )

    run_command(
        [
            python_executable,
            str(SCRIPTS["trend"]),
        ],
        "Predicción de tendencia competitiva",
    )

    check_output(
        OUTPUTS["trend"],
        "trend_predictions.json",
    )

    check_output(
        OUTPUTS["rank_reference_profiles"],
        "rank_reference_profiles.csv",
    )

    run_command(
        [
            python_executable,
            str(SCRIPTS["similar_players"]),
        ],
        "Búsqueda de referentes similares",
    )

    check_output(
        OUTPUTS["similar_players"],
        "similar_players.json",
    )

    run_command(
        [
            python_executable,
            str(SCRIPTS["final_analysis"]),
        ],
        "Generar análisis final unificado",
    )

    check_output(
        OUTPUTS["final_analysis"],
        "final_player_analysis.json",
    )

    check_output(
        OUTPUTS["docs_final_analysis"],
        "docs/final_player_analysis.json",
    )

    print("\n" + "=" * 90)
    print("ANÁLISIS COMPLETO FINALIZADO")
    print("=" * 90)
    print(f"Jugador analizado: {riot_id}")
    print(f"JSON final: {OUTPUTS['final_analysis']}")
    print(f"Copia para la web: {OUTPUTS['docs_final_analysis']}")
    print("\nAhora la web puede leer docs/final_player_analysis.json.")


def main():
    parser = argparse.ArgumentParser(
        description="Ejecuta el pipeline completo de ValoStats para un Riot ID."
    )

    parser.add_argument(
        "riot_id",
        help="Riot ID del jugador. Ejemplo: PoloGB#LAS",
    )

    parser.add_argument(
        "--skip-scraper",
        action="store_true",
        help="No ejecuta el scraper y reutiliza data/recent_matches.csv.",
    )

    parser.add_argument(
        "--refresh-reference",
        action="store_true",
        help="Regenera data/rank_reference_profiles.csv desde rank_reference_matches.csv.",
    )

    args = parser.parse_args()

    run_pipeline(
        riot_id=args.riot_id,
        skip_scraper=args.skip_scraper,
        refresh_reference=args.refresh_reference,
    )


if __name__ == "__main__":
    main()