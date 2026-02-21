import requests
from typing import Iterable
from utils.db import get_conn
from utils.config import RAPIDAPI_KEY, LEAGUE_IDS, SEASON
from utils.log import logger

BASE = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
}

def fetch_fixtures(league_keys: Iterable[str], date_from: str, date_to: str) -> int:
    """Hent fixtures for utvalgte ligaer mellom datoer (YYYY-MM-DD). Lagrer i DB.
    Returnerer antall innleste rader (inkl. duplikater ignorert).
    """
    total = 0
    for key in league_keys:
        league_id = LEAGUE_IDS[key]
        params = {
            "league": league_id,
            "from": date_from,
            "to": date_to,
            "timezone": "UTC",
            "season": SEASON
        }
        r = requests.get(BASE, headers=HEADERS, params=params, timeout=30)
        r.raise_for_status()
        items = r.json().get("response", [])
        rows = []
        for m in items:
            f_id = str(m["fixture"]["id"])
            utc_kick = m["fixture"]["date"]
            home = str(m["teams"]["home"]["id"]) if m["teams"]["home"] else None
            away = str(m["teams"]["away"]["id"]) if m["teams"]["away"] else None
            status = m["fixture"]["status"]["short"]
            rows.append((f_id, key, f"{SEASON}/2026", utc_kick, home, away, status))
        if rows:
            with get_conn() as conn:
                conn.executemany(
                    """
                    INSERT OR IGNORE INTO fixtures
                    (fixture_id, league, season, utc_kickoff, home_team_id, away_team_id, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
            total += len(rows)
            logger.info(f"Fixtures: lagret {len(rows)} rader for {key} ({date_from}→{date_to}).")
    return total