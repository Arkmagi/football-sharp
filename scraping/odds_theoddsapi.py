# scraping/odds_theoddsapi.py

import json
import requests
from pathlib import Path
from typing import Iterable, List, Dict, Any
from datetime import datetime, timezone, timedelta

from utils.db import get_conn
from utils.config import ODDS_API_KEY, ODDS_SPORT_KEYS, BOOKMAKERS
from utils.log import logger
from pipeline.normalize import match_fixture_by_names

BASE = "https://api.the-odds-api.com/v4/sports/{sport_key}/odds"


def _get_events_with_retries(url: str, params: Dict[str, Any], retries: int = 2) -> List[Dict[str, Any]]:
    """Liten helper med naive retries – nyttig dersom leverandøren til tider dropper TLS/forbindelsen."""
    for i in range(retries + 1):
        try:
            r = requests.get(url, params=params, timeout=30)
            if not r.ok:
                logger.error(f"[odds] {r.status_code}: {r.text[:300]}")
                return []
            return r.json() or []
        except Exception as e:
            if i == retries:
                logger.exception(f"[odds] Klarte ikke hente odds etter {retries} retries: {e}")
                return []
            logger.warning(f"[odds] Nettverksfeil, prøver igjen ({i+1}/{retries}) … {e}")
    return []


def fetch_odds(league_keys: Iterable[str]) -> int:
    """
    Henter odds (1X2) fra TheOddsAPI og matcher hvert event mot fixtures
    i vår DB vha. navn + kickoff ± toleranse. Lagres KUN når match finnes.
    I tillegg skriver vi et lite 'sample' av events til data/raw for feilsøking.
    """
    total_written = 0

    for league_key in league_keys:
        sport_key = ODDS_SPORT_KEYS.get(league_key)
        if not sport_key:
            logger.warning(f"[odds] Mangler sport_key for {league_key}; hopper over.")
            continue

        params = {
            "apiKey": ODDS_API_KEY,
            "markets": "h2h",
            "oddsFormat": "decimal",
            "dateFormat": "iso",
            "regions": "eu,uk",
        }
        url = BASE.format(sport_key=sport_key)
        events: List[Dict[str, Any]] = _get_events_with_retries(url, params, retries=2)

        # --- Skriv et lite samplesett til fil for verifisering ---
        try:
            sample = []
            for ev in events[:3]:
                sample.append({
                    "id": ev.get("id"),
                    "commence_time": ev.get("commence_time"),
                    "home_team": ev.get("home_team"),
                    "away_team": ev.get("away_team"),
                    # ta med kun bookmaker- og markednøkler, uten priser (for mindre fil)
                    "bookmakers": [
                        {
                            "key": bk.get("key"),
                            "markets": [m.get("key") for m in (bk.get("markets") or [])]
                        }
                        for bk in (ev.get("bookmakers") or [])
                    ],
                })
            sample_path = Path(f"data/raw/odds_sample_{league_key}.json")
            sample_path.parent.mkdir(parents=True, exist_ok=True)
            sample_path.write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")
            for ev in sample:
                logger.info(f"[odds] sample {league_key}: {ev['home_team']} vs {ev['away_team']} @ {ev['commence_time']}")
        except Exception as e:
            logger.warning(f"[odds] Kunne ikke skrive odds-sample: {e}")

        # --- Match & lagre odds ---
        rows = []
        for event in events:
            home_name = event.get("home_team") or ""
            away_name = event.get("away_team") or ""
            kick_iso  = event.get("commence_time") or ""

            # hopp over langt bak-i-tid events
            try:
                ko_dt = datetime.fromisoformat(kick_iso.replace("Z", "+00:00"))
                if ko_dt < datetime.now(timezone.utc) - timedelta(hours=6):
                    continue
            except Exception:
                pass

            with get_conn() as conn:
                fixture_id = match_fixture_by_names(
                    conn=conn,
                    league=league_key,        # 'EPL' / 'LaLiga' / ...
                    utc_kickoff=kick_iso,     # ISO‑strengen
                    home_name=home_name,
                    away_name=away_name,
                    tolerance_minutes=20,
                )

            if not fixture_id:
                logger.info(f"[odds] Uten match: {home_name} vs {away_name} @ {kick_iso} ({league_key})")
                continue

            for b in (event.get("bookmakers") or []):
                bk_key = b.get("key")
                if BOOKMAKERS and bk_key not in BOOKMAKERS:
                    continue

                for m in (b.get("markets") or []):
                    if m.get("key") != "h2h":
                        continue
                    ts = m.get("last_update")
                    for o in (m.get("outcomes") or []):
                        sel = o.get("name")     # "Home", "Away", "Draw" eller eksplisitte lagnavn
                        price = o.get("price")
                        if sel is None or price is None:
                            continue
                        try:
                            price = float(price)
                        except Exception:
                            continue
                        rows.append((fixture_id, bk_key, "1X2", sel, price, ts))

        if rows:
            with get_conn() as conn:
                conn.executemany(
                    """
                    INSERT OR IGNORE INTO odds
                    (fixture_id, bookmaker, market, selection, price, ts_utc)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
            total_written += len(rows)
            logger.info(f"[odds] Lagret {len(rows)} odds-rader for {league_key}.")

    return total_written
