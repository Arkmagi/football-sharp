import re, json, requests
from utils.db import get_conn
from utils.log import logger

RE_JSON = re.compile(r"JSON\.parse\('([^']+)'\)")

# NB: Understat har ikke stabilt offentlig API; dette kan bryte når HTML endres.
# Tilpass parsing ved behov.

def fetch_match_xg_from_understat(match_id: str):
    url = f"https://understat.com/match/{match_id}"
    html = requests.get(url, timeout=30).text
    data_strs = RE_JSON.findall(html)
    xg_home = xg_away = None
    for s in data_strs:
        payload = json.loads(s.encode('utf-8').decode('unicode_escape'))
        if isinstance(payload, dict) and 'h' in payload and 'a' in payload:
            xg_home = sum(float(shot.get('xG', 0.0)) for shot in payload['h'])
            xg_away = sum(float(shot.get('xG', 0.0)) for shot in payload['a'])
            break
    return xg_home, xg_away


def upsert_xg(fixture_id: str, understat_match_id: str) -> int:
    hxg, axg = fetch_match_xg_from_understat(understat_match_id)
    if hxg is None:
        logger.warning(f"Fant ikke xG for Understat match {understat_match_id}")
        return 0
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO xg (fixture_id, home_xg, away_xg, source, ts_utc)
            VALUES (?, ?, ?, 'understat', datetime('now'))
            ON CONFLICT(fixture_id) DO UPDATE SET
                home_xg=excluded.home_xg,
                away_xg=excluded.away_xg,
                source='understat',
                ts_utc=datetime('now')
            """,
            (fixture_id, hxg, axg),
        )
    logger.info(f"xG: lagret for fixture {fixture_id} (U:{understat_match_id}).")
    return 1