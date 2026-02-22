import time
from datetime import datetime, timedelta
from scraping.fixtures_apifootball import fetch_fixtures
from utils.db import get_conn
from utils.log import get_logger

log = get_logger("backfill")

START_DATE = datetime(2025, 8, 1)
API_SLEEP = 1.2   # juster om du treffer rate-limit


def daterange(start, end):
    for n in range(int((end - start).days) + 1):
        yield start + timedelta(n)


def upsert_fixture(cur, f):
    sql = """
    INSERT INTO fixtures (
        fixture_id, home_team, away_team, kickoff_time,
        status_short, elapsed_minutes,
        home_goals, away_goals,
        xg_home, xg_away,
        shots_home, shots_away,
        bc_home, bc_away,
        pos_home, pos_away,
        last_updated
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(fixture_id) DO UPDATE SET
        status_short=excluded.status_short,
        elapsed_minutes=excluded.elapsed_minutes,
        home_goals=excluded.home_goals,
        away_goals=excluded.away_goals,
        xg_home=excluded.xg_home,
        xg_away=excluded.xg_away,
        shots_home=excluded.shots_home,
        shots_away=excluded.shots_away,
        bc_home=excluded.bc_home,
        bc_away=excluded.bc_away,
        pos_home=excluded.pos_home,
        pos_away=excluded.pos_away,
        last_updated=excluded.last_updated;
    """
    cur.execute(sql, (
        f["fixture_id"],
        f["home"],
        f["away"],
        f["kickoff"],
        f["status"],
        f["elapsed"],
        f["hg"],
        f["ag"],
        f["xg_h"],
        f["xg_a"],
        f["shots_h"],
        f["shots_a"],
        f["bc_h"],
        f["bc_a"],
        f["pos_h"],
        f["pos_a"],
        datetime.utcnow().isoformat()
    ))


def normalize_fixture(raw):
    stats = raw.get("statistics", {})

    def stat(key, side):
        return stats.get(key, {}).get(side)

    return {
        "fixture_id": raw["fixture"]["id"],
        "home": raw["teams"]["home"]["name"],
        "away": raw["teams"]["away"]["name"],
        "kickoff": raw["fixture"]["date"],
        "status": raw["fixture"]["status"]["short"],
        "elapsed": raw["fixture"]["status"].get("elapsed"),
        "hg": raw["goals"]["home"],
        "ag": raw["goals"]["away"],
        "xg_h": stat("expected_goals", "home"),
        "xg_a": stat("expected_goals", "away"),
        "shots_h": stat("shots_total", "home"),
        "shots_a": stat("shots_total", "away"),
        "bc_h": stat("big_chances", "home"),
        "bc_a": stat("big_chances", "away"),
        "pos_h": stat("ball_possession", "home"),
        "pos_a": stat("ball_possession", "away"),
    }


def main():
    conn = get_conn()
    cur = conn.cursor()

    today = datetime.utcnow().date()
    log.info(f"Starting backfill from {START_DATE.date()} → {today}")

    for day in daterange(START_DATE, datetime.utcnow()):
        date_str = day.strftime("%Y-%m-%d")
        log.info(f"Fetching fixtures for {date_str}")

        fixtures = fetch_fixtures(date_str)

        if not fixtures:
            continue

        for raw in fixtures:
            try:
                f = normalize_fixture(raw)
                upsert_fixture(cur, f)
            except Exception as e:
                log.error(f"Failed fixture {raw.get('fixture', {}).get('id')}: {e}")

        conn.commit()
        time.sleep(API_SLEEP)

    log.info("Backfill completed successfully")


if __name__ == "__main__":
    main()