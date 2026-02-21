import argparse
from datetime import datetime, timedelta
from utils.db import init_schema, get_conn
from utils.config import HOME_ADV_ELO, DRAW_NU
from scraping.fixtures_apifootball import fetch_fixtures
from scraping.odds_theoddsapi import fetch_odds
from models.probabilities import elo_3way
from utils.log import logger

def iso_today(offset_days=0):
    return (datetime.utcnow() + timedelta(days=offset_days)).date().isoformat()

def compute_probs_for_upcoming():
    # very simple: hent fixtures som ikke har probs
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT f.fixture_id, f.home_team_id, f.away_team_id
            FROM fixtures f
            LEFT JOIN probs p ON p.fixture_id = f.fixture_id
            WHERE p.fixture_id IS NULL
            AND f.status IN ('NS','TBD')
            ORDER BY f.utc_kickoff
            """
        ).fetchall()
    if not rows:
        logger.info('Ingen nye fixtures å beregne sannsynligheter for.')
        return 0

    # Hent siste Elo fra DB eller bruk base via modellen (forenklet – bruker base 1500 når tomt)
    from models.elo import EloRatings
    er = EloRatings()
    inserts = []
    for fixture_id, home_id, away_id in rows:
        rH = er.get(home_id or 'home')
        rA = er.get(away_id or 'away')
        pH, pD, pA = elo_3way(rH, rA, home_adv=HOME_ADV_ELO, nu=DRAW_NU)
        inserts.append((fixture_id, pH, pD, pA, 'elo-davidson'))
    if inserts:
        with get_conn() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO probs (fixture_id, p_home, p_draw, p_away, model, ts_utc)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
                """,
                inserts,
            )
    logger.info(f'Skrevet sannsynligheter for {len(inserts)} fixtures.')
    return len(inserts)

def main():
    parser = argparse.ArgumentParser(description='Daglig kjøring for footy-pipeline')
    parser.add_argument('--init', action='store_true', help='Init DB-skjema')
    parser.add_argument('--days', type=int, default=2, help='Hvor mange dager frem å hente fixtures')
    parser.add_argument('--leagues', nargs='+', default=['EPL'], help='Ligaer (nøkler i config.LEAGUE_IDS)')
    args = parser.parse_args()

    if args.init:
        init_schema()
        logger.info('DB-skjema initialisert.')

    date_from = iso_today(0)
    date_to = iso_today(args.days)

    # 1) Fixtures
    try:
        f_count = fetch_fixtures(args.leagues, date_from, date_to)
        logger.info(f'Fixtures hentet: {f_count}')
    except Exception as e:
        logger.exception(e)

    # 2) Odds (valgfritt – lagrer kun når matching implementeres)
    try:
        o_count = fetch_odds(args.leagues)
        logger.info(f'Odds hentet: {o_count}')
    except Exception as e:
        logger.exception(e)

    # 3) Sannsynligheter (Elo 3-veis)
    try:
        p_count = compute_probs_for_upcoming()
        logger.info(f'Probs beregnet: {p_count}')
    except Exception as e:
        logger.exception(e)

if __name__ == '__main__':
    main()