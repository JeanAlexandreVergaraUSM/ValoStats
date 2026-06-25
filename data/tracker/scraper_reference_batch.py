import argparse
import asyncio
import csv
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from playwright.async_api import TimeoutError as PlaywrightTimeout


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRACKER_FOLDER = PROJECT_ROOT / "data" / "tracker"

sys.path.append(str(TRACKER_FOLDER))

from scraper_valorant import ValorantTrackerScraper


PLAYERS_PATH = PROJECT_ROOT / "data" / "reference_players.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "rank_reference_matches.csv"
FAILURES_PATH = PROJECT_ROOT / "outputs" / "reference_scraping" / "reference_failures.csv"

BATCH_MATCH_LIMIT = 20
MIN_MATCHES_TO_CONSIDER_PLAYER_DONE = 15
WAIT_BETWEEN_PLAYERS_SECONDS = 4
PROFILE_LOAD_WAIT_SECONDS = 10
MAX_PROFILE_RELOADS = 2

# Si Tracker muestra pantalla de error/bloqueo, espera 1 hora y luego refresca.
TRACKER_BLOCK_WAIT_SECONDS = 60 * 60


REFERENCE_FIELDNAMES = [
    "reference_riot_id",
    "source_player_name",
    "source_tag",
    "scraped_at",
    "player_name",
    "tag",
    "current_rank",
    "match_rank",
    "avg_team_rank",
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
]


def normalize_text(value):
    return str(value).strip()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Scraper por tandas para jugadores de referencia de ValoStats."
    )

    parser.add_argument(
        "--start",
        type=int,
        default=1,
        help="Jugador inicial a procesar. Usa numeración humana: 1 = primer jugador.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cantidad máxima de jugadores a procesar en esta ejecución.",
    )

    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="No saltar jugadores que ya aparecen en rank_reference_matches.csv.",
    )

    return parser.parse_args()


def load_reference_players(path=PLAYERS_PATH):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"No existe {path}. Crea data/reference_players.csv con columna riot_id."
        )

    df = pd.read_csv(path)

    if df.empty:
        raise ValueError("reference_players.csv está vacío.")

    df.columns = [str(col).strip().lower() for col in df.columns]

    players = []

    if "riot_id" in df.columns:
        for _, row in df.iterrows():
            riot_id = normalize_text(row.get("riot_id", ""))

            if "#" not in riot_id:
                continue

            game_name, tag_line = riot_id.split("#", 1)

            players.append({
                "player_name": normalize_text(game_name),
                "tag": normalize_text(tag_line),
            })

    elif "player_name" in df.columns and "tag" in df.columns:
        for _, row in df.iterrows():
            player_name = normalize_text(row.get("player_name", ""))
            tag = normalize_text(row.get("tag", ""))

            if not player_name or not tag:
                continue

            players.append({
                "player_name": player_name,
                "tag": tag,
            })

    else:
        raise ValueError(
            "El CSV debe tener columnas player_name,tag o una columna riot_id."
        )

    unique_players = []
    seen = set()

    for player in players:
        key = f"{player['player_name'].lower()}#{player['tag'].lower()}"

        if key not in seen:
            seen.add(key)
            unique_players.append(player)

    return unique_players


def select_player_batch(players, start=1, limit=None):
    if start < 1:
        raise ValueError("--start debe ser mayor o igual a 1.")

    start_index = start - 1

    if start_index >= len(players):
        return []

    if limit is None:
        end_index = len(players)
    else:
        end_index = start_index + limit

    return players[start_index:end_index]


def ensure_output_folders():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    FAILURES_PATH.parent.mkdir(parents=True, exist_ok=True)


async def is_tracker_error_page(page):
    """
    Detecta la pantalla de error de Tracker.gg:
    ERROR / An error occurred / Respawn at Home / Refresh
    """
    try:
        body_text = await page.locator("body").inner_text(timeout=5000)
        body_text = body_text.lower()

        return (
            "an error occurred" in body_text
            or "respawn at home" in body_text
            or ("error" in body_text and "refresh" in body_text)
        )

    except Exception:
        return False


async def wait_if_tracker_blocked(scraper, context=""):
    """
    Si Tracker muestra la pantalla de error/bloqueo,
    espera 1 hora y luego refresca la página.
    """
    blocked = await is_tracker_error_page(scraper.page)

    if not blocked:
        return False

    print("\n" + "!" * 80)
    print("Tracker.gg mostró pantalla de ERROR / bloqueo temporal.")
    print(f"Contexto: {context}")
    print("El scraper se pausará 1 hora antes de refrescar.")
    print("No cierres la terminal ni el navegador.")
    print("!" * 80 + "\n")

    await asyncio.sleep(TRACKER_BLOCK_WAIT_SECONDS)

    print("Pasó 1 hora. Refrescando página...")

    try:
        await scraper.page.reload(wait_until="domcontentloaded", timeout=90_000)
    except PlaywrightTimeout:
        print("Timeout al refrescar después del bloqueo, continuando...")

    await asyncio.sleep(8)
    await scraper.dismiss_tracker_banners(scraper.page)

    return True


def load_already_scraped_players():
    """
    Retorna jugadores que ya tienen suficientes partidas guardadas.

    No basta con que el jugador aparezca una vez en el CSV.
    Solo se considera listo si tiene al menos MIN_MATCHES_TO_CONSIDER_PLAYER_DONE partidas.
    """
    if not OUTPUT_PATH.exists():
        return set()

    try:
        df = pd.read_csv(OUTPUT_PATH)

        if "reference_riot_id" not in df.columns:
            return set()

        counts = df["reference_riot_id"].dropna().astype(str).str.lower().value_counts()

        already_done = set()

        for riot_id, count in counts.items():
            if count >= MIN_MATCHES_TO_CONSIDER_PLAYER_DONE:
                already_done.add(riot_id)

        return already_done

    except Exception:
        return set()


def append_matches_to_csv(matches):
    file_exists = OUTPUT_PATH.exists()
    file_has_content = file_exists and OUTPUT_PATH.stat().st_size > 0

    existing_keys = set()

    if file_has_content:
        try:
            existing_df = pd.read_csv(OUTPUT_PATH)

            if "reference_riot_id" in existing_df.columns and "match_id" in existing_df.columns:
                for _, row in existing_df.iterrows():
                    riot_id = str(row.get("reference_riot_id", "")).lower().strip()
                    match_id = str(row.get("match_id", "")).lower().strip()

                    if riot_id and match_id:
                        existing_keys.add((riot_id, match_id))

        except Exception:
            existing_keys = set()

    with open(OUTPUT_PATH, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=REFERENCE_FIELDNAMES)

        if not file_has_content:
            writer.writeheader()

        saved_count = 0
        skipped_duplicates = 0

        for match in matches:
            riot_id = str(match.get("reference_riot_id", "")).lower().strip()
            match_id = str(match.get("match_id", "")).lower().strip()
            key = (riot_id, match_id)

            if riot_id and match_id and key in existing_keys:
                skipped_duplicates += 1
                continue

            safe_row = {}

            for field in REFERENCE_FIELDNAMES:
                safe_row[field] = match.get(field, "")

            writer.writerow(safe_row)

            if riot_id and match_id:
                existing_keys.add(key)

            saved_count += 1

    print(f"Filas nuevas guardadas: {saved_count}")
    print(f"Duplicados saltados: {skipped_duplicates}")

def append_failure(player_name, tag, reason):
    file_exists = FAILURES_PATH.exists()
    file_has_content = file_exists and FAILURES_PATH.stat().st_size > 0

    with open(FAILURES_PATH, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["player_name", "tag", "riot_id", "reason", "failed_at"],
        )

        if not file_has_content:
            writer.writeheader()

        writer.writerow({
            "player_name": player_name,
            "tag": tag,
            "riot_id": f"{player_name}#{tag}",
            "reason": reason,
            "failed_at": datetime.now().isoformat(timespec="seconds"),
        })


async def load_player_page(scraper, game_name, tag_line):
    url = scraper.build_matches_url(game_name, tag_line)

    print(f"\nAbriendo perfil: {game_name}#{tag_line}")
    print(f"URL: {url}")

    try:
        await scraper.page.goto(url, wait_until="domcontentloaded", timeout=90_000)
    except PlaywrightTimeout:
        print("Timeout al cargar DOM, continuando...")

    await wait_if_tracker_blocked(
        scraper,
        context=f"al abrir perfil {game_name}#{tag_line}",
    )

    await scraper.dismiss_tracker_banners(scraper.page)
    await scraper.page.bring_to_front()

    for attempt in range(1, MAX_PROFILE_RELOADS + 2):
        print(
            f"Esperando carga automática del perfil "
            f"({attempt}/{MAX_PROFILE_RELOADS + 1})..."
        )

        await asyncio.sleep(PROFILE_LOAD_WAIT_SECONDS)

        await wait_if_tracker_blocked(
            scraper,
            context=f"esperando partidas de {game_name}#{tag_line}",
        )

        await scraper.dismiss_tracker_banners(scraper.page)
        await scraper.scroll_to_load_matches()

        await wait_if_tracker_blocked(
            scraper,
            context=f"después de hacer scroll en {game_name}#{tag_line}",
        )

        rows = await scraper.get_profile_match_rows()

        if rows:
            print(f"Partidas visibles detectadas: {len(rows)}")
            return True

        if attempt <= MAX_PROFILE_RELOADS:
            print("No aparecieron partidas. Recargando perfil...")

            try:
                await scraper.page.reload(wait_until="domcontentloaded", timeout=90_000)
            except PlaywrightTimeout:
                print("Timeout al recargar, continuando...")

            await wait_if_tracker_blocked(
                scraper,
                context=f"después de recargar perfil {game_name}#{tag_line}",
            )

    print("No se detectaron partidas para este jugador.")
    return False


def enrich_matches(matches, player_name, tag):
    enriched = []
    scraped_at = datetime.now().isoformat(timespec="seconds")
    reference_riot_id = f"{player_name}#{tag}"

    for match in matches:
        row = dict(match)

        row["reference_riot_id"] = reference_riot_id
        row["source_player_name"] = player_name
        row["source_tag"] = tag
        row["scraped_at"] = scraped_at

        row["player_name"] = row.get("player_name", player_name)
        row["tag"] = row.get("tag", tag)

        enriched.append(row)

    return enriched


async def extract_matches_safely(scraper, player_name, tag, riot_id):
    """
    Extrae partidas y, si Tracker bloquea justo después, espera y reintenta una vez.
    """
    await wait_if_tracker_blocked(
        scraper,
        context=f"antes de extraer detalles de {riot_id}",
    )

    matches = await scraper.extract_matches_by_clicking_details(
        game_name=player_name,
        tag_line=tag,
        limit=BATCH_MATCH_LIMIT,
    )

    was_blocked_after_details = await wait_if_tracker_blocked(
        scraper,
        context=f"después de extraer detalles de {riot_id}",
    )

    if was_blocked_after_details:
        print(f"Se detectó bloqueo después de intentar extraer {riot_id}.")
        print("Reintentando una vez después de la espera...")

        profile_loaded = await load_player_page(scraper, player_name, tag)

        if profile_loaded:
            matches = await scraper.extract_matches_by_clicking_details(
                game_name=player_name,
                tag_line=tag,
                limit=BATCH_MATCH_LIMIT,
            )

    return matches


async def scrape_reference_players(start=1, limit=None, skip_existing=True):
    ensure_output_folders()

    players = load_reference_players()
    selected_players = select_player_batch(players, start=start, limit=None)
    target_successful_players = limit

    already_scraped = load_already_scraped_players() if skip_existing else set()

    if limit is None:
        end_display = len(players)
    else:
        end_display = min(start + limit - 1, len(players))

    print("\nJugadores de referencia cargados:")
    print(f"Total en CSV: {len(players)}")
    print(f"Rango solicitado: jugador {start} al {end_display}")
    print(f"Jugadores disponibles desde start: {len(selected_players)}")
    print(f"Objetivo de jugadores válidos en esta ejecución: {target_successful_players or 'hasta el final'}")
    print(f"Jugadores ya guardados en rank_reference_matches.csv: {len(already_scraped)}")
    print(f"Partidas máximas por jugador: {BATCH_MATCH_LIMIT}")

    if not selected_players:
        print("\nNo hay jugadores para procesar con ese --start y --limit.")
        return

    scraper = ValorantTrackerScraper()

    await scraper.start()

    total_saved = 0
    total_failed = 0
    total_skipped = 0
    total_processed = 0
    successful_players = 0

    try:
        for real_index, player in enumerate(selected_players, start=start):
            player_name = player["player_name"]
            tag = player["tag"]
            riot_id = f"{player_name}#{tag}"
            riot_key = riot_id.lower()

            print("\n" + "=" * 80)
            print(f"Jugador {real_index}/{len(players)}: {riot_id}")

            if target_successful_players is not None and successful_players >= target_successful_players:
                print(f"\nObjetivo cumplido: {successful_players}/{target_successful_players} jugadores válidos.")
                break

            if skip_existing and riot_key in already_scraped:
                print("Ya tiene datos guardados. Cuenta como jugador válido y se salta.")
                total_skipped += 1
                successful_players += 1
                continue

            try:
                total_processed += 1

                profile_loaded = await load_player_page(scraper, player_name, tag)

                if not profile_loaded:
                    append_failure(
                        player_name,
                        tag,
                        "No cargaron partidas visibles automáticamente",
                    )
                    total_failed += 1
                    continue

                matches = await extract_matches_safely(
                    scraper=scraper,
                    player_name=player_name,
                    tag=tag,
                    riot_id=riot_id,
                )

                if not matches:
                    print("No se extrajeron partidas. Pasando al siguiente jugador.")
                    append_failure(player_name, tag, "No se extrajeron partidas")
                    total_failed += 1
                    continue

                if len(matches) < BATCH_MATCH_LIMIT:
                    print(
                        f"Jugador incompleto: solo se extrajeron {len(matches)}/{BATCH_MATCH_LIMIT} partidas. "
                        "No se guardará y se pasará al siguiente jugador."
                    )
                    append_failure(
                        player_name,
                        tag,
                        f"Jugador incompleto: {len(matches)}/{BATCH_MATCH_LIMIT} partidas válidas",
                    )
                    total_failed += 1
                    continue

                enriched_matches = enrich_matches(matches, player_name, tag)

                append_matches_to_csv(enriched_matches)

                already_scraped.add(riot_key)
                total_saved += len(enriched_matches)
                successful_players += 1

                print(f"Guardadas {len(enriched_matches)} partidas de {riot_id}")

                await asyncio.sleep(WAIT_BETWEEN_PLAYERS_SECONDS)

            except KeyboardInterrupt:
                print("\nProceso detenido manualmente.")
                break

            except Exception as exc:
                print(f"Error con {riot_id}: {exc}")
                append_failure(player_name, tag, str(exc))
                total_failed += 1
                await asyncio.sleep(WAIT_BETWEEN_PLAYERS_SECONDS)

    finally:
        await scraper.close()

    print("\n" + "=" * 80)
    print("Batch finalizado")
    print(f"Archivo generado: {OUTPUT_PATH}")
    print(f"Jugadores procesados en esta ejecución: {total_processed}")
    print(f"Jugadores saltados porque ya existían: {total_skipped}")
    print(f"Partidas guardadas en esta ejecución: {total_saved}")
    print(f"Jugadores con error: {total_failed}")


def main():
    args = parse_args()

    asyncio.run(
        scrape_reference_players(
            start=args.start,
            limit=args.limit,
            skip_existing=not args.no_skip_existing,
        )
    )


if __name__ == "__main__":
    main()
