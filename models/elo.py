from utils.db import get_conn
from utils.log import logger

DEFAULT_K = 20.0

class EloRatings:
    def __init__(self, k: float = DEFAULT_K, base: float = 1500.0):
        self.k = k
        self.base = base
        self.cache = {}  # {team_id: rating}

    def get(self, team_id: str) -> float:
        if team_id in self.cache:
            return self.cache[team_id]
        # hent siste rating fra DB, hvis finnes, ellers base
        with get_conn() as conn:
            row = conn.execute(
                """
                SELECT rating FROM ratings_elo
                WHERE team_id = ?
                ORDER BY ts_utc DESC LIMIT 1
                """,
                (team_id,),
            ).fetchone()
        r = float(row[0]) if row else self.base
        self.cache[team_id] = r
        return r

    def expected(self, rA: float, rB: float, home_adv: float = 55.0):
        # forventning for hjemmelag A vs B
        import math
        return 1.0 / (1.0 + 10 ** (((rB) - (rA + home_adv)) / 400.0))

    def update_match(self, ts_utc: str, home_id: str, away_id: str, result: float, home_adv: float = 55.0):
        """Oppdater Elo etter en kamp.
        result: 1=hjemmeseier, 0.5=uavgjort, 0=borteseier
        """
        rH = self.get(home_id)
        rA = self.get(away_id)
        expH = self.expected(rH, rA, home_adv)
        delta = self.k * (result - expH)
        rH_new = rH + delta
        rA_new = rA - delta
        self.cache[home_id] = rH_new
        self.cache[away_id] = rA_new
        with get_conn() as conn:
            conn.execute('INSERT OR REPLACE INTO ratings_elo (ts_utc, team_id, rating) VALUES (?, ?, ?)', (ts_utc, home_id, rH_new))
            conn.execute('INSERT OR REPLACE INTO ratings_elo (ts_utc, team_id, rating) VALUES (?, ?, ?)', (ts_utc, away_id, rA_new))
        logger.info(f"Elo: {home_id} {rH:.1f}->{rH_new:.1f}, {away_id} {rA:.1f}->{rA_new:.1f}")