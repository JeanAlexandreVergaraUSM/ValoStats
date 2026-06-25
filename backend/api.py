import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DOCS_DIR = PROJECT_ROOT / "docs"
INDEX_PATH = DOCS_DIR / "index.html"

RUN_FULL_ANALYSIS_SCRIPT = PROJECT_ROOT / "src" / "run_full_analysis.py"
FINAL_ANALYSIS_PATH = PROJECT_ROOT / "outputs" / "recent_predictions" / "final_player_analysis.json"

PIPELINE_LOCK = threading.Lock()


class AnalyzeRequest(BaseModel):
    riot_id: str = Field(..., examples=["PoloGB#LAS"])
    skip_scraper: bool = False
    refresh_reference: bool = False


class AnalyzeResponse(BaseModel):
    status: str
    riot_id: str
    elapsed_seconds: float
    message: str
    analysis: dict
    logs: list[str]


app = FastAPI(
    title="ValoStats API",
    description="Backend local para analizar partidas recientes de Valorant.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://jeanalexandrevergarausm.github.io",
        "https://jeanalexandrevergarausm.github.io/ValoStats",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def validate_riot_id(riot_id: str) -> str:
    riot_id = str(riot_id).strip()

    if "#" not in riot_id:
        raise ValueError("El Riot ID debe tener formato Nombre#Tag. Ejemplo: PoloGB#LAS")

    game_name, tag_line = riot_id.split("#", 1)

    game_name = game_name.strip()
    tag_line = tag_line.strip()

    if not game_name or not tag_line:
        raise ValueError("El Riot ID está incompleto. Ejemplo válido: PoloGB#LAS")

    return f"{game_name}#{tag_line}"


def read_final_analysis() -> dict:
    if not FINAL_ANALYSIS_PATH.exists():
        raise FileNotFoundError(
            f"No se encontró el análisis final: {FINAL_ANALYSIS_PATH}"
        )

    with open(FINAL_ANALYSIS_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def build_pipeline_command(
    riot_id: str,
    skip_scraper: bool = False,
    refresh_reference: bool = False,
) -> list[str]:
    if not RUN_FULL_ANALYSIS_SCRIPT.exists():
        raise FileNotFoundError(
            f"No existe el script del pipeline: {RUN_FULL_ANALYSIS_SCRIPT}"
        )

    command = [
        sys.executable,
        str(RUN_FULL_ANALYSIS_SCRIPT),
        riot_id,
    ]

    if skip_scraper:
        command.append("--skip-scraper")

    if refresh_reference:
        command.append("--refresh-reference")

    return command


def run_pipeline(
    riot_id: str,
    skip_scraper: bool = False,
    refresh_reference: bool = False,
) -> tuple[dict, list[str], float]:
    riot_id = validate_riot_id(riot_id)

    command = build_pipeline_command(
        riot_id=riot_id,
        skip_scraper=skip_scraper,
        refresh_reference=refresh_reference,
    )

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    start_time = time.time()

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

    logs = []

    try:
        for line in process.stdout:
            clean_line = line.rstrip("\n")
            logs.append(clean_line)
            print(clean_line)

        return_code = process.wait()

    except KeyboardInterrupt:
        process.terminate()
        process.wait()
        raise

    elapsed_seconds = round(time.time() - start_time, 2)

    if return_code != 0:
        last_logs = "\n".join(logs[-40:])

        raise RuntimeError(
            "El pipeline falló.\n"
            f"Código de salida: {return_code}\n\n"
            f"Últimas líneas:\n{last_logs}"
        )

    analysis = read_final_analysis()

    return analysis, logs, elapsed_seconds


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "project_root": str(PROJECT_ROOT),
        "docs_exists": DOCS_DIR.exists(),
        "index_exists": INDEX_PATH.exists(),
        "pipeline_script_exists": RUN_FULL_ANALYSIS_SCRIPT.exists(),
        "final_analysis_exists": FINAL_ANALYSIS_PATH.exists(),
    }


@app.get("/api/latest-analysis")
def get_latest_analysis():
    try:
        analysis = read_final_analysis()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return analysis


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze_player(request: AnalyzeRequest):
    try:
        riot_id = validate_riot_id(request.riot_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if PIPELINE_LOCK.locked():
        raise HTTPException(
            status_code=409,
            detail=(
                "Ya hay un análisis ejecutándose. "
                "Espera a que termine antes de iniciar otro."
            ),
        )

    with PIPELINE_LOCK:
        try:
            analysis, logs, elapsed_seconds = run_pipeline(
                riot_id=riot_id,
                skip_scraper=request.skip_scraper,
                refresh_reference=request.refresh_reference,
            )

        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc))

        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Error inesperado ejecutando el análisis: {exc}",
            )

    return {
        "status": "ok",
        "riot_id": riot_id,
        "elapsed_seconds": elapsed_seconds,
        "message": "Análisis generado correctamente.",
        "analysis": analysis,
        "logs": logs[-120:],
    }


@app.get("/favicon.ico")
def favicon():
    favicon_path = DOCS_DIR / "favicon.ico"

    if favicon_path.exists():
        return FileResponse(favicon_path)

    raise HTTPException(status_code=404, detail="No favicon")


if DOCS_DIR.exists():
    app.mount(
        "/",
        StaticFiles(directory=DOCS_DIR, html=True),
        name="docs",
    )