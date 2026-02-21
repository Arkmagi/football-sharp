# pipeline/normalize.py
from __future__ import annotations
import re
import json
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import sqlite3

# ------------------------------------------------------------
# Navn-kanonisering (robust mot ulike skrivemåter fra bookmakere)
# ------------------------------------------------------------

WHITESPACE = re.compile(r"\s+")
PARENS = re.compile(r"[\(\)\[\]\{\}]")
NONALNUM = re.compile(r"[^a-z0-9 ]+")

REMOVE_TOKENS = {
    "fc", "afc", "cf", "sc", "ac", "ud", "calcio", "club", "the"
}
# Eksempler: "Man Utd" -> "manchester united"; legg til egne
SPECIAL_MAP = {
    "man utd": "manchester united",
    "manchester utd": "manchester united",
    "spurs": "tottenham hotspur",
    "wolves": "wolverhampton wanderers",
    "newcastle u": "newcastle united",
    "west ham": "west ham united",
    "west ham u": "west ham united",
    "brighton hove albion": "brighton & hove albion",
    "brighton and hove albion": "brighton & hove albion",
    "leeds u": "leeds united",
    "man city": "manchester city",
    "manchester city fc": "manchester city",
    "manchester united fc": "manchester united",
    "arsenal fc": "arsenal",
    "chelsea fc": "chelsea",
    "liverpool fc": "liverpool",
    "everton fc": "everton",
}

def strip_accents(s: str) -> str:
    return ''.join(
        c for c in unicodedata.normalize('NFKD', s)
        if unicodedata.category(c) != 'Mn'
    )

def canonicalize(name: str) -> str:
    """Kanoniser lagnavn: små bokstaver, fjerne aksenter,
    fjerne spesialtegn/parenteser, normalisere whitespace,
    fjerne generiske suffiks som FC/AFC osv.
    """
    if not name:
        return ""
    s = strip_accents(name).lower().strip()
    s = PARENS.sub(" ", s)
    s = WHITESPACE.sub(" ", s)
    # spesialkart først (for vanlige forkortelser)
    if s in SPECIAL_MAP:
        s = SPECIAL_MAP[s]
    # fjern ikke-alfanumeriske, behold mellomrom
    s = NONALNUM.sub(" ", s)
    s = WHITESPACE.sub(" ", s).strip()
    # fjern generiske tokens
    tokens = [t for t in s.split(" ") if t and t not in REMOVE_TOKENS]
    s = " ".join(tokens)
    # spesialkart igjen etter rens (kan hjelpe)
    if s in SPECIAL_MAP:
        s = SPECIAL_MAP[s]
    return s

# ------------------------------------------------------------
# Alias-API: lagre og slå opp alias pr team_id
# teams.alias er en JSON-tekst: ["manchester united","man utd","man utd.", ...]
# ------------------------------------------------------------

def get_aliases(conn: sqlite3.Connection, team_id: str) -> List[str]:
    row = conn.execute("SELECT alias FROM teams WHERE team_id=?", (team_id,)).fetchone()
    if not row or not row[0]:
        return []
    try:
        data = json.loads(row[0])
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []

def set_aliases(conn: sqlite3.Connection, team_id: str, aliases: List[str]) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO teams (team_id, name, country, alias) VALUES (?, ?, ?, ?)",
        (team_id, None, None, json.dumps(aliases, ensure_ascii=False)),
    )
    conn.execute(
        "UPDATE teams SET alias=? WHERE team_id=?",
        (json.dumps(aliases, ensure_ascii=False), team_id),
    )

def register_alias(conn: sqlite3.Connection, team_id: str, *names: str) -> int:
    """Legg til ett eller flere alias på et team_id. Returnerer antall nye alias."""
    curr = set(get_aliases(conn, team_id))
    before = len(curr)
    for nm in names:
        c = canonicalize(nm)
        if c and c not in curr:
            curr.add(c)
    set_aliases(conn, team_id, sorted(curr))
    return len(curr) - before

def find_team_by_name(conn: sqlite3.Connection, league: str, name_raw: str) -> Optional[str]:
    """Finn team_id i denne ligaen ved å slå opp kanonisert navn mot alias.
    Hvis flere lag i ulike ligaer deler alias, begrens via fixtures i samme liga.
    """
    name = canonicalize(name_raw)
    if not name:
        return None

    # Hent kandidater i denne ligaen: team_id-er fra fixtures i ligaen
    team_ids = set()
    for (tid,) in conn.execute(
        "SELECT DISTINCT home_team_id FROM fixtures WHERE league=? UNION "
        "SELECT DISTINCT away_team_id FROM fixtures WHERE league=?",
        (league, league),
    ).fetchall():
        if tid:
            team_ids.add(tid)

    if not team_ids:
        return None

    # Sjekk alias per kandidat
    q = "SELECT team_id, alias FROM teams WHERE team_id IN ({})".format(
        ",".join(["?"] * len(team_ids))
    )
    rows = conn.execute(q, tuple(team_ids)).fetchall()
    for tid, alias_json in rows:
        if not alias_json:
            continue
        try:
            aliases = json.loads(alias_json)
        except Exception:
            continue
        # eksakt treff på kanonisert alias
        if name in aliases:
            return tid

    # Fallback: enkel startswith/contains hvis ingen eksakte alias
    for tid, alias_json in rows:
        if not alias_json:
            continue
        try:
            aliases = json.loads(alias_json)
        except Exception:
            continue
        if any(name in a or a in name for a in aliases):
            return tid

    return None

# ------------------------------------------------------------
# Match odds-event til fixtures: liga + kickoff ± toleranse + navn
# ------------------------------------------------------------

@dataclass
class FixtureCandidate:
    fixture_id: str
    league: str
    kickoff: datetime
    home_team_id: Optional[str]
    away_team_id: Optional[str]

def parse_iso_utc(ts: str) -> datetime:
    # football-data/fixtures bruker ISO med 'Z'
    # sqlite kan lagre Utc strings. Vi parser defensivt.
    try:
        if ts.endswith('Z'):
            return datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return datetime.fromisoformat(ts)
    except Exception:
        # siste utvei
        return datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")

def find_fixtures_in_window(
    conn: sqlite3.Connection,
    league: str,
    center_utc: str,
    tolerance_minutes: int = 15,
) -> List[FixtureCandidate]:
    center = parse_iso_utc(center_utc)
    lo = center - timedelta(minutes=tolerance_minutes)
    hi = center + timedelta(minutes=tolerance_minutes)

    rows = conn.execute(
        """
        SELECT fixture_id, league, utc_kickoff, home_team_id, away_team_id
        FROM fixtures
        WHERE league=?
          AND datetime(utc_kickoff) BETWEEN datetime(?) AND datetime(?)
        ORDER BY utc_kickoff
        """,
        (league, lo.isoformat().replace("+00:00", "Z"), hi.isoformat().replace("+00:00", "Z")),
    ).fetchall()

    out: List[FixtureCandidate] = []
    for fixture_id, lg, ko, h, a in rows:
        out.append(
            FixtureCandidate(
                fixture_id=fixture_id,
                league=lg,
                kickoff=parse_iso_utc(ko),
                home_team_id=h,
                away_team_id=a,
            )
        )
    return out

def match_fixture_by_names(
    conn: sqlite3.Connection,
    league: str,
    utc_kickoff: str,
    home_name: str,
    away_name: str,
    tolerance_minutes: int = 15,
) -> Optional[str]:
    """Prøv å finne riktig fixture_id for et odds-event.
    1) Finn fixtures i gitt liga innenfor kickoff ± toleranse
    2) Slå opp home/away navn mot alias -> team_id
    3) Finn fixture der begge team_id matcher
    """
    cands = find_fixtures_in_window(conn, league, utc_kickoff, tolerance_minutes)
    if not cands:
        return None

    home_id = find_team_by_name(conn, league, home_name)
    away_id = find_team_by_name(conn, league, away_name)

    if not home_id or not away_id:
        return None

    for c in cands:
        if c.home_team_id == home_id and c.away_team_id == away_id:
            return c.fixture_id

    # Hvis hjem/borte er byttet hos bookmaker (skjer av og til)
    for c in cands:
        if c.home_team_id == away_id and c.away_team_id == home_id:
            return c.fixture_id

    return None

# ------------------------------------------------------------
# Seeding: hent offisielle lagnavn fra football-data.org
# og legg til alias pr team_id (fd_<id>)
# ------------------------------------------------------------

def seed_alias_from_football_data(
    conn: sqlite3.Connection,
    token: str,
    league_key: str,
) -> int:
    """
    Henter teams for en konkurranse fra football-data.org og fyller alias for team_id = 'fd_<id>'.
    Vi bruker offisielle felter: name, shortName, tla (tre-bokstavs kode)
    """
    import requests
    from scraping.fixtures_footballdata import FD_COMPETITIONS

    comp = FD_COMPETITIONS.get(league_key)
    if not comp:
        raise ValueError(f"Ukjent league_key: {league_key}")

    headers = {"X-Auth-Token": token}
    r = requests.get(f"https://api.football-data.org/v4/competitions/{comp}/teams", headers=headers, timeout=30)
    if not r.ok:
        raise RuntimeError(f"football-data teams {r.status_code}: {r.text[:300]}")
    data = r.json()
    teams = data.get("teams", [])

    added = 0
    for t in teams:
        tid = f"fd_{t['id']}"
        name = t.get("name") or ""
        short = t.get("shortName") or ""
        tla = t.get("tla") or ""
        # lagre hovednavn i teams.name (valgfritt)
        conn.execute("INSERT OR IGNORE INTO teams (team_id, name, country, alias) VALUES (?, ?, ?, ?)",
                     (tid, name, t.get("area", {}).get("name"), json.dumps([], ensure_ascii=False)))
        # registrer alias (offisielle navnevarianter)
        added += register_alias(conn, tid, name, short, tla)

        # Legg til noen håndlagde alias som ofte dukker opp hos bookmakere
        extra = []
        if "fc" not in name.lower():
            extra.append(f"{name} fc")
        # Fjern generiske spesialtegn for et alias (ex: "Brighton & Hove Albion" → "Brighton Hove Albion")
        extra.append(name.replace("&", " "))
        added += register_alias(conn, tid, *extra)

    conn.commit()
    return added