import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path('data/footy.sqlite')

@contextmanager
def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA foreign_keys = ON;')
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_schema():
    schema = """
    CREATE TABLE IF NOT EXISTS teams (
        team_id TEXT PRIMARY KEY,
        name TEXT,
        country TEXT,
        alias TEXT
    );

    CREATE TABLE IF NOT EXISTS fixtures (
        fixture_id TEXT PRIMARY KEY,
        league TEXT,
        season TEXT,
        utc_kickoff TEXT,
        home_team_id TEXT,
        away_team_id TEXT,
        status TEXT,
        UNIQUE(league, season, utc_kickoff, home_team_id, away_team_id)
    );

    CREATE TABLE IF NOT EXISTS odds (
        fixture_id TEXT,
        bookmaker TEXT,
        market TEXT,
        selection TEXT,
        price REAL,
        ts_utc TEXT,
        PRIMARY KEY(fixture_id, bookmaker, market, selection, ts_utc)
    );

    CREATE TABLE IF NOT EXISTS xg (
        fixture_id TEXT PRIMARY KEY,
        home_xg REAL,
        away_xg REAL,
        source TEXT,
        ts_utc TEXT
    );

    CREATE TABLE IF NOT EXISTS ratings_elo (
        ts_utc TEXT,
        team_id TEXT,
        rating REAL,
        PRIMARY KEY(ts_utc, team_id)
    );

    CREATE TABLE IF NOT EXISTS probs (
        fixture_id TEXT PRIMARY KEY,
        p_home REAL,
        p_draw REAL,
        p_away REAL,
        model TEXT,
        ts_utc TEXT
    );
    """
    with get_conn() as conn:
        conn.executescript(schema)