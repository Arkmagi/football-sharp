# scraping/fixtures_footballdata.py
import requests
from datetime import datetime
from utils.db import get_conn
from utils.log import logger

BASE = "https://api.football-data.org/v4"

# Mapping av din interne liga-nøkkel til football-data.org competition code
FD_COMPETITIONS = {
    "EPL": "PL",         # Premier League
    "LaLiga": "PD",      # La Liga
    "SerieA": "SA",      # Serie A
    "Bundesliga": "BL1", # Bundesliga
}

def fetch_fixtures_fd(league_keys, date_from: str, date_to: str, token: str, season_label: str = "2025/2026") -> int:
    """
    Hent fixtures fra football-data.org for et datointervall (YYYY-MM-DD).
    Lagrer i tabell 'fixtures' med league = din nøkkel (EPL/LaLiga...) og season = season_label.
    """
    headers = {"X-Auth-Token": token}
    total = 0

    for key in league_keys:
        comp = FD_COMPETITIONS.get(key)
        if not comp:
            logger.warning(f"[football-data] Mangler competition code for {key}. Hopper over.")
            continue

        # /matches?competitions=PL&dateFrom=YYYY-MM-DD&dateTo=YYYY-MM-DD
        params = {"competitions": comp, "dateFrom": date_from, "dateTo": date_to}
        r = requests.get(f"{BASE}/matches", headers=headers, params=params, timeout=30)
        if not r.ok:
            logger.error(f"[football-data] {r.status_code}: {r.text[:300]}")
            r.raise_for_status()

        data = r.json()
        matches = data.get("matches", [])
        rows = []
        for m in matches:
            fixture_id = f"fd_{m['id']}"  # prefiks for å skille kilde
            utc_kick = m["utcDate"]       # ISO-tid i UTC
            home_id = f"fd_{m['homeTeam']['id']}"
            away_id = f"fd_{m['awayTeam']['id']}"
            #status = m.get("status", "TBD")
            
            status_fd = m.get("status", "TBD")  # football-data status
            # Normaliser til vårt interne sett
            if status_fd in ("SCHEDULED", "TIMED"):
                status = "NS"
            elif status_fd == "POSTPONED":
                status = "TBD"
            elif status_fd in ("IN_PLAY", "PAUSED"):
                status = "LIVE"
            elif status_fd == "FINISHED":
                status = "FT"
            else:
                status = "TBD"

            rows.append((fixture_id, key, season_label, utc_kick, home_id, away_id, status))

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
            logger.info(f"[football-data] Fixtures: lagret {len(rows)} rader for {key} ({date_from} -> {date_to}).")

    return total