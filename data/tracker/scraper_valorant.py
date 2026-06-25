import os
import csv
import re
import asyncio
import time
import socket
import subprocess
import shutil
from datetime import datetime
from urllib.parse import quote

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout


DEFAULT_GAME_NAME = "PoloGB"
DEFAULT_TAG_LINE = "LAS"

MATCH_LIMIT = 20
OUTPUT_FOLDER = "data"
OUTPUT_FILE = "recent_matches.csv"

DEBUG_PORT = 9222
CHROME_WAIT_SECONDS = 10
PROFILE_LOAD_WAIT_SECONDS = 10
MAX_PROFILE_RELOADS = 2

SHOW_BROWSER_WHILE_SCRAPING = False

CHROME_PROCESS = None
CHROME_LAUNCHED_BY_SCRIPT = False

MAPS = [
    "Abyss", "Ascent", "Bind", "Breeze", "Fracture", "Haven", "Icebox",
    "Lotus", "Pearl", "Split", "Sunset"
]

AGENTS = [
    "Astra", "Breach", "Brimstone", "Chamber", "Clove", "Cypher",
    "Deadlock", "Fade", "Gekko", "Harbor", "Iso", "Jett", "KAY/O",
    "Kay/O", "Killjoy", "Neon", "Omen", "Phoenix", "Raze", "Reyna",
    "Sage", "Skye", "Sova", "Tejo", "Viper", "Vyse", "Yoru"
]

RANKS = [
    "Iron 1", "Iron 2", "Iron 3",
    "Bronze 1", "Bronze 2", "Bronze 3",
    "Silver 1", "Silver 2", "Silver 3",
    "Gold 1", "Gold 2", "Gold 3",
    "Platinum 1", "Platinum 2", "Platinum 3",
    "Diamond 1", "Diamond 2", "Diamond 3",
    "Ascendant 1", "Ascendant 2", "Ascendant 3",
    "Immortal 1", "Immortal 2", "Immortal 3",
    "Radiant"
]


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize(value: str) -> str:
    value = clean_text(value).lower()
    value = value.replace("#", "")
    return value


def parse_int(value, default=0):
    value = clean_text(value)
    value = value.replace(",", "")
    value = value.replace("+", "")
    value = value.replace("%", "")

    match = re.search(r"-?\d+", value)
    return int(match.group(0)) if match else default


def parse_float(value, default=0.0):
    value = clean_text(value)
    value = value.replace(",", ".")
    value = value.replace("+", "")
    value = value.replace("%", "")

    match = re.search(r"-?\d+(?:\.\d+)?", value)
    return float(match.group(0)) if match else default


def parse_percent(value, default=0.0):
    return parse_float(value, default)


def is_integer_line(value: str) -> bool:
    return bool(re.fullmatch(r"\d{1,2}", clean_text(value)))


def is_stat_value(value: str) -> bool:
    value = clean_text(value)
    return bool(re.fullmatch(r"[+-]?\d+(?:\.\d+)?%?", value))


def detect_rank(text: str) -> str:
    text_clean = clean_text(text)

    for rank in RANKS:
        if re.search(rf"\b{re.escape(rank)}\b", text_clean, re.I):
            return rank

    return "Unknown"


def detect_map(text: str) -> str:
    text_clean = clean_text(text)

    for map_name in MAPS:
        if re.search(rf"\b{re.escape(map_name)}\b", text_clean, re.I):
            return map_name

    return "Unknown"


def detect_agent(text: str) -> str:
    text_clean = clean_text(text)

    for agent in AGENTS:
        if re.search(rf"\b{re.escape(agent)}\b", text_clean, re.I):
            return "KAY/O" if agent.lower() == "kay/o" else agent

    return "Unknown"


def detect_date_from_lines(lines):
    date_patterns = [
        r"\d{1,2}/\d{1,2}/\d{2,4},?\s*\d{1,2}:\d{2}",
        r"\d{4}-\d{2}-\d{2}",
        r"\d{1,2}/\d{1,2}/\d{4}",
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}",
        r"\b\d+d ago\b",
        r"\b\d+h ago\b",
        r"\b\d+m ago\b",
    ]

    for line in lines:
        for pattern in date_patterns:
            match = re.search(pattern, line, re.I)
            if match:
                return match.group(0)

    return datetime.now().strftime("%Y-%m-%d")


def extract_match_id(url: str, index: int) -> str:
    match = re.search(r"/match(?:es)?/([^/?#]+)", url, re.I)

    if match:
        return match.group(1)

    return f"match_{index + 1:03d}"


def is_debug_port_open(host="127.0.0.1", port=DEBUG_PORT):
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def find_chrome_executable():
    possible_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path

    chrome_from_path = shutil.which("chrome")

    if chrome_from_path:
        return chrome_from_path

    raise FileNotFoundError("No encontré Google Chrome. Revisa que esté instalado.")


def launch_chrome_debug_if_needed():
    global CHROME_PROCESS
    global CHROME_LAUNCHED_BY_SCRIPT

    if is_debug_port_open():
        print("Chrome debugging ya está abierto en el puerto 9222")
        CHROME_LAUNCHED_BY_SCRIPT = False
        return

    chrome_path = find_chrome_executable()
    user_data_dir = os.path.join(
        os.environ.get("USERPROFILE", ""),
        "chrome-tracker-debug",
    )

    command = [
    chrome_path,
    f"--remote-debugging-port={DEBUG_PORT}",
    f"--user-data-dir={user_data_dir}",
    "--disable-notifications",
    "--disable-popup-blocking",
]

    if SHOW_BROWSER_WHILE_SCRAPING:
        command.append("--start-maximized")
    else:
        command.extend([
        "--window-position=-32000,-32000",
        "--window-size=1400,1000",
    ])

    print("Abriendo Chrome en modo debugging...")
    print(f"   {chrome_path}")

    CHROME_PROCESS = subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=False,
    )

    CHROME_LAUNCHED_BY_SCRIPT = True

    print(f"Esperando {CHROME_WAIT_SECONDS} segundos para que Chrome inicie...")
    time.sleep(CHROME_WAIT_SECONDS)

    if not is_debug_port_open():
        raise RuntimeError(
            "Chrome se abrió, pero el puerto 9222 no quedó disponible. "
            "Cierra Chrome y vuelve a ejecutar el script."
        )

    print("Chrome debugging iniciado correctamente")

class ValorantTrackerScraper:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def start(self):

        self.playwright = await async_playwright().start()

        if os.getenv("RUNNING_IN_RENDER") == "1":
            print("Ejecutando en Render: usando Chromium interno de Playwright.")

            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-blink-features=AutomationControlled",
                    "--window-size=1400,1000",
                ],
            )

            self.context = await self.browser.new_context(
                viewport={"width": 1400, "height": 1000},
                locale="es-CL",
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
            )

            self.page = await self.context.new_page()
            return


        launch_chrome_debug_if_needed()

        self.playwright = await async_playwright().start()

        print("🔌 Conectando al Chrome real abierto en modo debugging...")

        try:
            self.browser = await self.playwright.chromium.connect_over_cdp(
                f"http://127.0.0.1:{DEBUG_PORT}"
            )
        except Exception as exc:
            raise RuntimeError(
                "No pude conectarme a Chrome en el puerto 9222."
            ) from exc

        if not self.browser.contexts:
            raise RuntimeError("Chrome no tiene contextos disponibles.")

        self.context = self.browser.contexts[0]

        if self.context.pages:
            self.page = self.context.pages[-1]
        else:
            self.page = await self.context.new_page()

        print("Conectado al Chrome real")

    def build_matches_url(self, game_name: str, tag_line: str) -> str:
        riot_id = f"{game_name}#{tag_line}"
        encoded_riot_id = quote(riot_id, safe="")

        return (
            f"https://tracker.gg/valorant/profile/riot/"
            f"{encoded_riot_id}/matches?playlist=competitive&platform=pc"
        )

    async def dismiss_tracker_banners(self, page=None):
        target_page = page or self.page

        selectors = [
            "button:has-text('Dismiss')",
            "button:has-text('Accept')",
            "button:has-text('I Agree')",
            "button:has-text('Agree')",
            "button:has-text('Got it')",
            "button:has-text('Close')",
        ]

        for selector in selectors:
            try:
                button = target_page.locator(selector).first()

                if await button.count() > 0:
                    await button.click(timeout=1500)
                    await asyncio.sleep(0.4)
            except Exception:
                pass

    async def load_matches_page(self, game_name: str, tag_line: str):
        url = self.build_matches_url(game_name, tag_line)

        print(f"Página objetivo: {url}")
        print("Abriendo página en el Chrome real...")

        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=90_000)
        except PlaywrightTimeout:
            print("Timeout al cargar DOM, continuando...")

        await self.dismiss_tracker_banners(self.page)
        await self.page.bring_to_front()

        for attempt in range(1, MAX_PROFILE_RELOADS + 2):
            print(f"Esperando carga del perfil ({attempt}/{MAX_PROFILE_RELOADS + 1})...")
            await asyncio.sleep(PROFILE_LOAD_WAIT_SECONDS)

            await self.dismiss_tracker_banners(self.page)
            await self.scroll_to_load_matches()

            rows = await self.get_profile_match_rows()

            if rows:
                print(f"Partidas detectadas automáticamente: {len(rows)}")
                return

            if attempt <= MAX_PROFILE_RELOADS:
                print("No aparecieron partidas. Recargando perfil...")

                try:
                    await self.page.reload(wait_until="domcontentloaded", timeout=90_000)
                except PlaywrightTimeout:
                    print("Timeout al recargar, continuando...")

        print("No se detectaron partidas automáticamente.")
        print("El scraper intentará continuar igual.")

    async def scroll_to_load_matches(self):
        await self.page.bring_to_front()

        for _ in range(4):
            await self.page.mouse.wheel(0, 850)
            await asyncio.sleep(0.6)

        await self.page.mouse.wheel(0, -3800)
        await asyncio.sleep(1.2)

    async def get_profile_match_rows(self):
        selectors = [
            ".v3-match-row",
            "[class*='match-row']",
            "[class*='MatchRow']",
        ]

        for selector in selectors:
            try:
                rows = await self.page.query_selector_all(selector)
            except Exception:
                continue

            valid_rows = []

            for row in rows:
                try:
                    row_text = clean_text(await row.inner_text())
                except Exception:
                    continue

                has_match_info = (
                    "TRS" in row_text
                    and "ACS" in row_text
                    and ("K/D/A" in row_text or "K/D" in row_text)
                )

                if has_match_info:
                    valid_rows.append(row)

            if valid_rows:
                return valid_rows

        return []

    async def open_match_detail_from_row(self, row, index: int):
        profile_page = self.page
        before_url = profile_page.url

        try:
            await row.scroll_into_view_if_needed(timeout=6000)
        except Exception:
            pass

        await asyncio.sleep(0.8)

        print(f"\nAbriendo detalle de partida {index + 1}...")

        try:
            async with self.context.expect_page(timeout=8000) as page_info:
                await row.click(button="middle", timeout=6000)

            detail_page = await page_info.value
            await detail_page.wait_for_load_state("domcontentloaded", timeout=60_000)
            await asyncio.sleep(3)

            print("Detalle abierto en nueva pestaña")
            return detail_page, "new_tab"

        except Exception:
            await asyncio.sleep(1.5)

        try:
            async with self.context.expect_page(timeout=8000) as page_info:
                await row.click(modifiers=["Control"], timeout=6000)

            detail_page = await page_info.value
            await detail_page.wait_for_load_state("domcontentloaded", timeout=60_000)
            await asyncio.sleep(3)

            print("Detalle abierto con Ctrl+Click")
            return detail_page, "new_tab"

        except Exception:
            await asyncio.sleep(1.5)

        try:
            await row.click(timeout=6000)
            await asyncio.sleep(4)

            if profile_page.url != before_url:
                print("Detalle abierto en la misma pestaña")
                return profile_page, "same_tab"

        except Exception:
            pass

        print("No se pudo abrir el detalle de esta partida")
        return None, "failed"

    async def close_detail_page(self, detail_page, open_mode: str, profile_url: str):
        if open_mode == "new_tab":
            try:
                await detail_page.close()
            except Exception:
                pass

            try:
                await self.page.bring_to_front()
            except Exception:
                pass

            await asyncio.sleep(0.8)
            return

        if open_mode == "same_tab":
            try:
                await self.page.goto(profile_url, wait_until="domcontentloaded", timeout=90_000)
                await asyncio.sleep(3)
                await self.dismiss_tracker_banners(self.page)
            except Exception:
                try:
                    await self.page.go_back(wait_until="domcontentloaded", timeout=90_000)
                    await asyncio.sleep(3)
                    await self.dismiss_tracker_banners(self.page)
                except Exception:
                    pass

    async def get_page_lines(self, page):
        text = await page.locator("body").inner_text()
        lines = []

        for line in text.splitlines():
            cleaned = clean_text(line)

            if cleaned:
                lines.append(cleaned)

        return lines

    def parse_match_metadata_from_lines(self, lines, player_line_index=None):
        full_text = " ".join(lines)

        map_name = "Unknown"

        for i, line in enumerate(lines):
            if line.lower() == "competitive" and i + 1 < len(lines):
                possible_map = detect_map(lines[i + 1])

                if possible_map != "Unknown":
                    map_name = possible_map
                    break

        if map_name == "Unknown":
            map_name = detect_map(full_text)

        date_value = detect_date_from_lines(lines)

        team_a_score = 0
        team_b_score = 0

        for i, line in enumerate(lines):
            if line == "Team A":
                possible_a = self.find_next_small_integer(lines, i + 1, max_steps=6)

                team_b_index = self.find_next_exact_line(lines, "Team B", i + 1, max_steps=12)

                if team_b_index is not None:
                    possible_b = self.find_next_small_integer(lines, team_b_index + 1, max_steps=6)
                else:
                    possible_b = None

                if possible_a is not None and possible_b is not None:
                    team_a_score = possible_a
                    team_b_score = possible_b
                    break

        avg_rank = "Unknown"

        for i, line in enumerate(lines):
            if line.lower() == "average rank":
                nearby = lines[max(0, i - 3): min(len(lines), i + 4)]

                for value in nearby:
                    rank = detect_rank(value)

                    if rank != "Unknown":
                        avg_rank = rank
                        break

            if avg_rank != "Unknown":
                break

        if avg_rank == "Unknown":
            avg_rank = detect_rank(full_text)

        player_team = "Unknown"

        if player_line_index is not None:
            for j in range(player_line_index, -1, -1):
                if lines[j] in ["Team A", "Team B"]:
                    player_team = lines[j]
                    break

        result = "Unknown"

        if team_a_score == team_b_score and team_a_score > 0:
            result = "Draw"
        elif player_team == "Team A":
            if team_a_score > team_b_score:
                result = "Win"
            elif team_b_score > team_a_score:
                result = "Loss"
        elif player_team == "Team B":
            if team_b_score > team_a_score:
                result = "Win"
            elif team_a_score > team_b_score:
                result = "Loss"
        else:
            if team_a_score > team_b_score:
                result = "Win"
            elif team_b_score > team_a_score:
                result = "Loss"

        return {
            "date": date_value,
            "map": map_name,
            "team_a_score": team_a_score,
            "team_b_score": team_b_score,
            "avg_team_rank": avg_rank,
            "player_team": player_team,
            "result": result,
        }

    def find_next_small_integer(self, lines, start, max_steps=8):
        end = min(len(lines), start + max_steps)

        for i in range(start, end):
            if is_integer_line(lines[i]):
                value = parse_int(lines[i])

                if 0 <= value <= 30:
                    return value

        return None

    def find_next_exact_line(self, lines, target, start, max_steps=12):
        end = min(len(lines), start + max_steps)

        for i in range(start, end):
            if lines[i] == target:
                return i

        return None

    def find_player_line_index(self, lines, game_name: str, tag_line: str):
        target_name = normalize(game_name)
        target_tag = normalize(tag_line)

        for i, line in enumerate(lines):
            line_norm = normalize(line)

            if line_norm == target_name or target_name in line_norm:
                window = " ".join(lines[i:i + 5])
                window_norm = normalize(window)

                if target_tag in window_norm:
                    return i

        for i, line in enumerate(lines):
            line_norm = normalize(line)

            if line_norm == target_name or target_name in line_norm:
                return i

        return None

    def find_rank_after_player(self, lines, player_index):
        start = player_index + 1
        end = min(len(lines), player_index + 8)

        for i in range(start, end):
            rank = detect_rank(lines[i])

            if rank != "Unknown":
                return rank, i

        return "Unknown", None

    def collect_stat_values_after_rank(self, lines, rank_index):
        values = []

        if rank_index is None:
            return values

        stop_words = [
            "Team A",
            "Team B",
            "Get the Mobile App",
            "Scoreboard",
            "Performance",
            "Economy",
            "Rounds",
            "Duels",
            "Share",
            "Premium users don't see ads.",
        ]

        for line in lines[rank_index + 1:]:
            if line in stop_words:
                break

            if line.startswith("#"):
                continue

            if detect_rank(line) != "Unknown":
                continue

            if is_stat_value(line):
                values.append(line)

            if len(values) >= 14:
                break

        return values

    def parse_player_stats_from_lines(self, lines, game_name: str, tag_line: str):
        player_index = self.find_player_line_index(lines, game_name, tag_line)

        if player_index is None:
            return None

        match_rank, rank_index = self.find_rank_after_player(lines, player_index)
        values = self.collect_stat_values_after_rank(lines, rank_index)

        if len(values) == 13:
            kills = parse_int(values[2])
            deaths = parse_int(values[3])
            possible_kd_ratio = values[5]

            kill_diff_should_be_zero = kills == deaths
            next_value_looks_like_kd = (
                "." in possible_kd_ratio
                and not possible_kd_ratio.startswith(("+", "-"))
            )

            if kill_diff_should_be_zero and next_value_looks_like_kd:
                values.insert(5, "0")

        if len(values) < 14:
            print("Encontré al jugador, pero no encontré las 14 métricas esperadas.")
            print(f"  Métricas encontradas: {values}")
            return None

        kills = parse_int(values[2])
        deaths = parse_int(values[3])
        kill_diff = parse_int(values[5])

        if kills == deaths and kill_diff != 0:
            kill_diff = 0

        stats = {
            "player_line_index": player_index,
            "current_rank": match_rank,
            "match_rank": match_rank,
            "tracker_score": parse_int(values[0]),
            "acs": parse_int(values[1]),
            "kills": kills,
            "deaths": deaths,
            "assists": parse_int(values[4]),
            "kill_diff": kill_diff,
            "kd_ratio": parse_float(values[6]),
            "dda": parse_float(values[7]),
            "adr": parse_float(values[8]),
            "headshot_percent": parse_percent(values[9]),
            "kast": parse_percent(values[10]),
            "first_kills": parse_int(values[11]),
            "first_deaths": parse_int(values[12]),
            "multi_kills": parse_int(values[13]),
        }

        return stats

    async def get_agent_from_profile_row(self, row):
        try:
            images = await row.query_selector_all("img[alt]")

            for image in images:
                alt = await image.get_attribute("alt")

                if not alt:
                    continue

                alt = clean_text(alt)

                if alt in AGENTS:
                    return "KAY/O" if alt.lower() == "kay/o" else alt
        except Exception:
            pass

        try:
            row_text = clean_text(await row.inner_text())
            return detect_agent(row_text)
        except Exception:
            return "Unknown"

    async def parse_detail_page(self, detail_page, profile_row, index: int, game_name: str, tag_line: str):
        await detail_page.bring_to_front()
        await self.dismiss_tracker_banners(detail_page)

        try:
            await detail_page.wait_for_function(
                """
                () => {
                    const text = document.body.innerText || "";
                    return text.includes("Scoreboard") &&
                           text.includes("TRS") &&
                           text.includes("ACS");
                }
                """,
                timeout=60_000,
            )
        except PlaywrightTimeout:
            print("El detalle no terminó de cargar el scoreboard a tiempo.")

        await asyncio.sleep(1.5)

        lines = await self.get_page_lines(detail_page)
        stats = self.parse_player_stats_from_lines(lines, game_name, tag_line)

        if stats is None:
            print("No pude parsear las métricas del jugador desde el texto del detalle.")
            print("Partida inválida. Este jugador se descarta y se pasa al siguiente.")
            return []

        metadata = self.parse_match_metadata_from_lines(
            lines,
            player_line_index=stats["player_line_index"],
        )

        agent = await self.get_agent_from_profile_row(profile_row)

        if agent == "Unknown":
            agent = detect_agent(" ".join(lines))

        if metadata["player_team"] == "Team A":
            team_score = metadata["team_a_score"]
            enemy_score = metadata["team_b_score"]
        elif metadata["player_team"] == "Team B":
            team_score = metadata["team_b_score"]
            enemy_score = metadata["team_a_score"]
        else:
            team_score = metadata["team_a_score"]
            enemy_score = metadata["team_b_score"]

        rounds_played = team_score + enemy_score

        row_data = {
            "player_name": game_name,
            "tag": tag_line,
            "current_rank": stats["current_rank"],
            "match_rank": stats["match_rank"],
            "avg_team_rank": metadata["avg_team_rank"],
            "match_id": extract_match_id(detail_page.url or "", index),
            "date": metadata["date"],
            "mode": "Competitive",
            "map": metadata["map"],
            "agent": agent,
            "result": metadata["result"],
            "team_score": team_score,
            "enemy_score": enemy_score,
            "rounds_played": rounds_played,
            "tracker_score": stats["tracker_score"],
            "acs": stats["acs"],
            "kills": stats["kills"],
            "deaths": stats["deaths"],
            "assists": stats["assists"],
            "kill_diff": stats["kill_diff"],
            "kd_ratio": stats["kd_ratio"],
            "dda": stats["dda"],
            "adr": stats["adr"],
            "headshot_percent": stats["headshot_percent"],
            "kast": stats["kast"],
            "first_kills": stats["first_kills"],
            "first_deaths": stats["first_deaths"],
            "multi_kills": stats["multi_kills"],
        }

        print(
            f"  ✓ {row_data['map']} | {row_data['agent']} | "
            f"{row_data['result']} | TRS {row_data['tracker_score']} | "
            f"ACS {row_data['acs']} | "
            f"{row_data['kills']}/{row_data['deaths']}/{row_data['assists']} | "
            f"ADR {row_data['adr']} | KAST {row_data['kast']}%"
        )

        return row_data

    async def extract_matches_by_clicking_details(
        self,
        game_name: str,
        tag_line: str,
        limit: int = MATCH_LIMIT,
    ):
        profile_url = self.page.url
        matches = []

        await self.scroll_to_load_matches()

        rows = await self.get_profile_match_rows()

        if not rows:
            print("No se encontraron partidas visibles en el perfil.")
            await self.save_debug_files("debug_no_profile_match_rows")
            return []

        total_to_read = min(limit, len(rows))

        print(f"Partidas visibles encontradas: {len(rows)}")
        print(f"Se intentarán abrir {total_to_read} partidas una por una.")

        for index in range(total_to_read):
            await self.page.bring_to_front()
            await asyncio.sleep(0.8)

            rows = await self.get_profile_match_rows()

            if index >= len(rows):
                print(f"⚠️ Ya no existe la partida índice {index + 1}.")
                break

            profile_row = rows[index]
            detail_page, open_mode = await self.open_match_detail_from_row(profile_row, index)

            if detail_page is None:
                continue

            try:
                match_data = await self.parse_detail_page(
                    detail_page=detail_page,
                    profile_row=profile_row,
                    index=index,
                    game_name=game_name,
                    tag_line=tag_line,
                )

                if match_data:
                    matches.append(match_data)

            finally:
                await self.close_detail_page(detail_page, open_mode, profile_url)

        print(f"\n📊 Total partidas extraídas desde detalles: {len(matches)}")
        return matches

    async def fetch_matches(
        self,
        game_name: str = DEFAULT_GAME_NAME,
        tag_line: str = DEFAULT_TAG_LINE,
        limit: int = MATCH_LIMIT,
    ):
        if not self.page:
            await self.start()

        await self.load_matches_page(game_name, tag_line)

        matches = await self.extract_matches_by_clicking_details(
            game_name=game_name,
            tag_line=tag_line,
            limit=limit,
        )

        return matches

    async def save_debug_files(self, name: str):
        await self.save_debug_files_for_page(self.page, name)

    async def save_debug_files_for_page(self, page, name: str):
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)

        html_path = os.path.join(OUTPUT_FOLDER, f"{name}.html")
        png_path = os.path.join(OUTPUT_FOLDER, f"{name}.png")

        try:
            content = await page.content()

            with open(html_path, "w", encoding="utf-8") as file:
                file.write(content)

            await page.screenshot(path=png_path, full_page=True)

            print(f"  🧪 Debug guardado: {html_path}")
            print(f"  🧪 Screenshot guardado: {png_path}")

        except Exception as exc:
            print(f"  ⚠️ No pude guardar debug: {exc}")

    async def save_to_csv(self, matches, folder: str = OUTPUT_FOLDER):
        os.makedirs(folder, exist_ok=True)
        filepath = os.path.join(folder, OUTPUT_FILE)

        fieldnames = [
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

        with open(filepath, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(matches)

        print(f"\n✅ CSV guardado: {filepath} ({len(matches)} filas)")

    async def close(self):
        global CHROME_PROCESS
        global CHROME_LAUNCHED_BY_SCRIPT

        if self.browser and CHROME_LAUNCHED_BY_SCRIPT:
            try:
                print("Cerrando Chrome abierto por el scraper")
                await self.browser.close()
            except Exception:
                pass

        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception:
                pass

        if CHROME_PROCESS and CHROME_LAUNCHED_BY_SCRIPT:
            try:
                if CHROME_PROCESS.poll() is None:
                    CHROME_PROCESS.terminate()

                    try:
                        CHROME_PROCESS.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        CHROME_PROCESS.kill()
            except Exception:
                pass

        CHROME_PROCESS = None
        CHROME_LAUNCHED_BY_SCRIPT = False

async def main():
    import sys

    riot_id = sys.argv[1] if len(sys.argv) > 1 else f"{DEFAULT_GAME_NAME}#{DEFAULT_TAG_LINE}"

    if "#" in riot_id:
        game_name, tag_line = riot_id.split("#", 1)
    else:
        game_name = DEFAULT_GAME_NAME
        tag_line = DEFAULT_TAG_LINE

    scraper = ValorantTrackerScraper()

    try:
        matches = await scraper.fetch_matches(
            game_name=game_name,
            tag_line=tag_line,
            limit=MATCH_LIMIT,
        )

        await scraper.save_to_csv(matches)

    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())